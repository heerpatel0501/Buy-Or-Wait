import pandas as pd
import os
import time
from decimal import Decimal
from datetime import datetime

from code.models import FinancialProfile, FinancialEvent, PaymentOption, Request
from code.llm import LLMProvider
from code.resolver import ConflictResolver
from code.state import FinancialStateLayer
from code.simulator import Simulator
from code.solver import Solver
from code.optimizer import Optimizer
from code.verifier import Verifier

def load_datasets(dataset_dir):
    data = {}
    for filename in os.listdir(dataset_dir):
        if filename.endswith('.csv'):
            name = filename.replace('.csv', '')
            data[name] = pd.read_csv(os.path.join(dataset_dir, filename)).fillna('')
    return data

def parse_profile(row) -> FinancialProfile:
    def parse_list(s):
        if not s: return []
        return [x.strip() for x in str(s).split('|')]
        
    return FinancialProfile(
        user_id=row['user_id'],
        home_currency=row['home_currency'],
        current_available_balance=Decimal(str(row['current_available_balance'])),
        minimum_balance_to_keep=Decimal(str(row['minimum_balance_to_keep'])),
        financial_priorities=parse_list(row['financial_priorities']),
        expense_categories_to_protect=parse_list(row['expense_categories_to_protect']),
        expense_categories_user_is_willing_to_reduce=parse_list(row['expense_categories_user_is_willing_to_reduce']),
        expense_categories_user_is_willing_to_stop=parse_list(row['expense_categories_user_is_willing_to_stop']),
        payment_methods_user_will_consider=parse_list(row['payment_methods_user_will_consider']),
        max_installment_months=int(row['max_installment_months']) if row['max_installment_months'] else None
    )

def parse_event(row) -> FinancialEvent:
    return FinancialEvent(
        event_id=row['event_id'],
        user_id=row['user_id'],
        event_type=row['event_type'],
        description=row['description'],
        category=row['category'],
        direction=row['direction'],
        amount=Decimal(str(row['amount'])) if row['amount'] else Decimal('0.0'),
        currency=row['currency'],
        event_date=datetime.strptime(str(row['event_date']), '%Y-%m-%d').date(),
        settlement_date=datetime.strptime(str(row['settlement_date']), '%Y-%m-%d').date() if row['settlement_date'] else None,
        status=row['status'],
        linked_event_id=row['linked_event_id'] if row['linked_event_id'] else None,
        flexibility=row['flexibility'],
        minimum_allowed_amount=Decimal(str(row['minimum_allowed_amount'])) if row['minimum_allowed_amount'] else None
    )

def parse_request(row) -> Request:
    return Request(
        request_id=row['request_id'],
        user_id=row['user_id'],
        request_date=datetime.strptime(str(row['request_date']), '%Y-%m-%d').date(),
        request_type=row['request_type'],
        requested_amount=Decimal(str(row['requested_amount'])),
        desired_completion_date=datetime.strptime(str(row['desired_completion_date']), '%Y-%m-%d').date() if row['desired_completion_date'] else None,
        allows_partial_payment=str(row['allows_partial_payment']).lower() == 'true',
        request_text=row['request_text']
    )

def parse_payment_option(row) -> PaymentOption:
    return PaymentOption(
        payment_option_id=row['payment_option_id'],
        payment_method=row['payment_method'],
        payment_amount=Decimal(str(row['payment_amount'])),
        number_of_payments=int(row['number_of_payments']),
        first_payment_date=datetime.strptime(str(row['first_payment_date']), '%Y-%m-%d').date(),
        payment_frequency_days=int(row['payment_frequency_days']) if row['payment_frequency_days'] else None,
        total_payable_amount=Decimal(str(row['total_payable_amount']))
    )

def main():
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable.")
        return
        
    llm_provider = LLMProvider(api_key=api_key)
    resolver = ConflictResolver()
    state_layer = FinancialStateLayer()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(base_dir, 'dataset')
    image_dir = os.path.join(dataset_dir, 'media', 'images')
    
    data = load_datasets(dataset_dir)
    num_requests = len(data['requests'])
    output_rows = []
    
    print(f"Processing {num_requests} requests using deterministic engine...")
    
    for idx, row in data['requests'].iterrows():
        request_id = row['request_id']
        user_id = row['user_id']
        
        # 1. Parse base structures
        req_obj = parse_request(row)
        prof_row = data['financial_profiles'][data['financial_profiles']['user_id'] == user_id].iloc[0]
        profile_obj = parse_profile(prof_row)
        
        events_df = data['financial_events'][data['financial_events']['user_id'] == user_id]
        raw_events = [parse_event(r) for _, r in events_df.iterrows()]
        
        opts_df = data['request_payment_options'][data['request_payment_options']['request_id'] == request_id]
        payment_opts = [parse_payment_option(r) for _, r in opts_df.iterrows()]
        
        # 2. Extract Facts via LLM (Relevance filtering)
        messages_df = data['messages'][data['messages']['user_id'] == user_id] if 'messages' in data else pd.DataFrame()
        images_df = data['images'][(data['images']['user_id'] == user_id) | (data['images']['request_id'] == request_id)] if 'images' in data else pd.DataFrame()
        
        extracted_facts = llm_provider.extract_facts(request_id, messages_df, images_df, events_df, image_dir)
        
        # 3. Resolve Conflicts deterministically
        resolved_events = resolver.resolve(raw_events, extracted_facts)
        
        # 4. Reconstruct Financial State
        current_state = state_layer.reconstruct(resolved_events, req_obj)
        
        # 5. Simulate & Solve
        simulator = Simulator(profile_obj, current_state)
        solver = Solver(simulator, req_obj, payment_opts)
        candidates, amount_safe, earliest_full = solver.generate_candidate_plans()
        
        # 6. Optimize
        optimizer = Optimizer(profile_obj)
        best_plan = optimizer.rank_plans(candidates)
        
        # 7. Verify
        verifier = Verifier(simulator, req_obj)
        
        # Output building
        if not best_plan:
            out_status = "not_affordable"
            out_method = "not_recommended"
            out_plan = "none"
        else:
            out_method = best_plan['method']
            out_plan = best_plan['plan_string']
            if out_method == "full_payment":
                out_status = "affordable_now"
            elif out_method == "wait":
                out_status = "affordable_later"
            else:
                out_status = "affordable_with_plan"
                
        output_row = {
            'request_id': request_id,
            'amount_safe_to_pay': str(amount_safe),
            'affordability_status': out_status,
            'recommended_payment_method': out_method,
            'payment_plan': out_plan,
            'earliest_date_for_full_payment': earliest_full if earliest_full else "",
            'spending_changes_needed': "none",  # Not implemented in strict deterministic MVP to avoid complexity
            'decision_explanation': f"Deterministic calculation selected {out_method}."
        }
        
        is_verified = verifier.verify(output_row)
        if not is_verified:
            # Fail-closed
            output_row['affordability_status'] = 'not_affordable'
            output_row['recommended_payment_method'] = 'not_recommended'
            output_row['payment_plan'] = 'none'
            
        output_rows.append(output_row)
        print(f"Processed {request_id} -> {output_row['recommended_payment_method']}")
        
    output_df = pd.DataFrame(output_rows)
    output_df.to_csv(os.path.join(dataset_dir, 'output.csv'), index=False)
    
if __name__ == '__main__':
    main()
