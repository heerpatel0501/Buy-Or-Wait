import pandas as pd
import json
import os
import time
import PIL.Image
from google import genai
from google.genai import types

def load_datasets(dataset_dir):
    data = {}
    for filename in os.listdir(dataset_dir):
        if filename.endswith('.csv'):
            name = filename.replace('.csv', '')
            data[name] = pd.read_csv(os.path.join(dataset_dir, filename))
    return data

def get_request_context(request_id, data):
    req = data['requests'][data['requests']['request_id'] == request_id].iloc[0]
    user_id = req['user_id']
    profile = data['financial_profiles'][data['financial_profiles']['user_id'] == user_id].iloc[0]
    events = data['financial_events'][data['financial_events']['user_id'] == user_id]
    
    if 'messages' in data and not data['messages'].empty:
        messages = data['messages'][data['messages']['user_id'] == user_id]
    else:
        messages = pd.DataFrame()
        
    if 'images' in data and not data['images'].empty:
        # Get images related to this request or user's events
        # Problem says images are linked to users, requests, or financial events
        images = data['images'][
            (data['images']['user_id'] == user_id) | 
            (data['images']['request_id'] == request_id)
        ]
    else:
        images = pd.DataFrame()
        
    payment_opts = data['request_payment_options'][data['request_payment_options']['request_id'] == request_id]
    
    events = events.fillna('')
    messages = messages.fillna('')
    images = images.fillna('')
    payment_opts = payment_opts.fillna('')
    
    context = {
        "request": req.to_dict(),
        "profile": profile.to_dict(),
        "events": events.to_dict(orient='records'),
        "messages": messages.to_dict(orient='records'),
        "images_metadata": images.to_dict(orient='records'),
        "payment_options": payment_opts.to_dict(orient='records')
    }
    return context, images

def build_system_prompt(problem_statement_path):
    with open(problem_statement_path, 'r', encoding='utf-8') as f:
        problem = f.read()
    return f"""You are an AI-powered financial agent.
Your task is to determine whether a user can safely afford a requested expense.

Here are the rules you MUST follow exactly as written:
{problem}

You will be given the user's financial profile, past and scheduled events, relevant messages, images, and the request details along with payment options.

You must output a JSON object containing EXACTLY these fields:
- "scratchpad": String. Show your step-by-step reasoning. First, list recurring incomes and expenses. Then list modified/cancelled events based on messages. Then forecast daily balances for 90 days. Then evaluate each payment option. Finally, pick the best one using tie-breakers.
- "amount_safe_to_pay": Float
- "affordability_status": String (affordable_now, affordable_with_plan, affordable_later, not_affordable)
- "recommended_payment_method": String (full_payment, partial_payment, installments, wait, not_recommended)
- "payment_plan": String
- "earliest_date_for_full_payment": String (or empty string if not applicable)
- "spending_changes_needed": String
- "decision_explanation": String
"""

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable.")
        return
        
    client = genai.Client(api_key=api_key)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dir = os.path.join(base_dir, 'dataset')
    data = load_datasets(dataset_dir)
    
    system_prompt = build_system_prompt(os.path.join(base_dir, 'problem_statement.md'))
    
    output_rows = []
    
    total_input_tokens = 0
    total_output_tokens = 0
    num_requests = len(data['requests'])
    
    print(f"Processing {num_requests} requests...")
    
    for idx, row in data['requests'].iterrows():
        request_id = row['request_id']
        context, images_df = get_request_context(request_id, data)
        prompt_text = f"User Context:\n{json.dumps(context, indent=2)}"
        
        contents = [prompt_text]
        if not images_df.empty:
            for _, img_row in images_df.iterrows():
                img_id = img_row['image_id']
                img_path = os.path.join(dataset_dir, 'media', 'images', f"{img_id}.png")
                if os.path.exists(img_path):
                    try:
                        img = PIL.Image.open(img_path)
                        contents.append(img)
                    except Exception as e:
                        print(f"Could not load image {img_path}: {e}")
        
        try:
            response = client.models.generate_content(
                model='gemini-1.5-pro',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            
            result = json.loads(response.text)
            
            output_row = {
                'request_id': request_id,
                'amount_safe_to_pay': result.get('amount_safe_to_pay'),
                'affordability_status': result.get('affordability_status'),
                'recommended_payment_method': result.get('recommended_payment_method'),
                'payment_plan': result.get('payment_plan'),
                'earliest_date_for_full_payment': result.get('earliest_date_for_full_payment'),
                'spending_changes_needed': result.get('spending_changes_needed'),
                'decision_explanation': result.get('decision_explanation')
            }
            output_rows.append(output_row)
            
            if response.usage_metadata:
                total_input_tokens += response.usage_metadata.prompt_token_count
                total_output_tokens += response.usage_metadata.candidates_token_count
                
            print(f"Processed {request_id}")
            
        except Exception as e:
            print(f"Error processing {request_id}: {e}")
            
        time.sleep(2)
        
    output_df = pd.DataFrame(output_rows)
    output_df.to_csv(os.path.join(dataset_dir, 'output.csv'), index=False)
    
    os.makedirs(os.path.join(base_dir, 'code', 'evaluation'), exist_ok=True)
    with open(os.path.join(base_dir, 'code', 'evaluation', 'usage_report.md'), 'w') as f:
        f.write("# Token Usage and Cost Analysis\n\n")
        f.write("Model Provider: Google\n")
        f.write("Model Name: gemini-1.5-pro\n")
        f.write(f"Total Model Calls: {num_requests}\n")
        f.write(f"Total Input Tokens: {total_input_tokens}\n")
        f.write(f"Total Output Tokens: {total_output_tokens}\n")
        f.write(f"Average Input Tokens per request: {total_input_tokens/num_requests:.2f}\n")
        f.write(f"Average Output Tokens per request: {total_output_tokens/num_requests:.2f}\n")
        cost = (total_input_tokens / 1_000_000 * 1.25) + (total_output_tokens / 1_000_000 * 5.00)
        f.write(f"Estimated Total Cost: ${cost:.4f}\n")
        f.write(f"Estimated Per-Request Cost: ${cost/num_requests:.4f}\n")

if __name__ == '__main__':
    main()
