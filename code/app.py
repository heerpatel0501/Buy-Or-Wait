import streamlit as st
import pandas as pd
import json
import os
import PIL.Image
from google import genai
from google.genai import types

# Page config for trustworthy look
st.set_page_config(
    page_title="SafePay Financial Agent | Secure AI",
    page_icon="🔒",
    layout="wide"
)

# Shared logic to load data
@st.cache_data
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
    return context, images, req, profile, payment_opts

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
    st.title("🔒 SafePay Financial Agent")
    st.markdown("### Secure & Verified Affordability Analysis")
    st.markdown("---")
    
    api_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dir = os.path.join(base_dir, 'dataset')
    
    try:
        data = load_datasets(dataset_dir)
        requests_list = data['requests']['request_id'].tolist()
    except Exception as e:
        st.error(f"Failed to load dataset from {dataset_dir}: {e}")
        return

    st.sidebar.markdown("### Select Request")
    selected_request = st.sidebar.selectbox("Choose a Request ID to Analyze", requests_list)
    
    if not selected_request:
        return
        
    context, images_df, req, profile, payment_opts = get_request_context(selected_request, data)
    
    # UI Layout: Two columns for displaying request info
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👤 User Profile")
        st.write(f"**User ID:** {profile['user_id']}")
        st.write(f"**Current Balance:** {profile['current_available_balance']} {profile['home_currency']}")
        st.write(f"**Minimum Protected Balance:** {profile['minimum_balance_to_keep']} {profile['home_currency']}")
        
    with col2:
        st.subheader("🛒 Request Details")
        st.write(f"**Type:** {req['request_type'].capitalize()}")
        st.write(f"**Requested Amount:** {req['requested_amount']} {profile['home_currency']}")
        st.info(f"**User Message:** {req['request_text']}")
        
    st.markdown("#### 💳 Available Payment Options")
    st.dataframe(payment_opts[['payment_method', 'payment_amount', 'number_of_payments', 'total_payable_amount']], use_container_width=True)
    
    if st.button("🛡️ Run Secure Affordability Audit", type="primary"):
        if not api_key:
            st.error("Please enter your Gemini API Key in the sidebar.")
            return
            
        with st.spinner("Analyzing 90-day financial forecast securely..."):
            client = genai.Client(api_key=api_key)
            system_prompt = build_system_prompt(os.path.join(base_dir, 'problem_statement.md'))
            
            prompt_text = f"User Context:\n{json.dumps(context, indent=2)}"
            contents = [prompt_text]
            
            if not images_df.empty:
                for _, img_row in images_df.iterrows():
                    img_id = img_row['image_id']
                    img_path = os.path.join(dataset_dir, 'media', 'images', f"{img_id}.png")
                    if os.path.exists(img_path):
                        img = PIL.Image.open(img_path)
                        contents.append(img)
                        
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
                
                # Display Results
                st.markdown("---")
                st.subheader("✅ Audit Complete")
                
                status = result.get('affordability_status', '')
                if 'not_affordable' in status:
                    st.error(f"**Status:** {status.replace('_', ' ').title()} ❌")
                elif 'later' in status:
                    st.warning(f"**Status:** {status.replace('_', ' ').title()} ⏳")
                else:
                    st.success(f"**Status:** {status.replace('_', ' ').title()} ✔️")
                    
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric("Amount Safe To Pay", f"{result.get('amount_safe_to_pay')} {profile['home_currency']}")
                    st.write(f"**Recommended Method:** {result.get('recommended_payment_method', '').replace('_', ' ').title()}")
                with res_col2:
                    st.write(f"**Payment Plan:** {result.get('payment_plan')}")
                    st.write(f"**Spending Changes Needed:** {result.get('spending_changes_needed')}")
                    
                st.info(f"**Decision Explanation:** {result.get('decision_explanation')}")
                
                with st.expander("🔍 View AI Reasoning (Scratchpad)"):
                    st.text(result.get('scratchpad', 'No reasoning provided.'))
                    
            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")

if __name__ == '__main__':
    main()
