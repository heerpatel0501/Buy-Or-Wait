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
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(base_dir, 'dataset')
    image_dir = os.path.join(dataset_dir, 'media', 'images')
    
    data = load_datasets(dataset_dir)
    
    reqs = data.get('requests', pd.DataFrame())
    
    num_requests = len(reqs)
    output_rows = []
    
    print(f"Processing {num_requests} requests using deterministic engine...")
    rates_df = data.get('exchange_rates', pd.DataFrame())
    state_layer = FinancialStateLayer(rates_df)
    
    for idx, row in reqs.iterrows():
        request_id = row['request_id']
        user_id = row['user_id']
        
        req_obj = parse_request(row)
        prof_row = data['financial_profiles'][data['financial_profiles']['user_id'] == user_id].iloc[0]
        profile_obj = parse_profile(prof_row)
        
        events_df = data['financial_events'][data['financial_events']['user_id'] == user_id]
        raw_events = [parse_event(r) for _, r in events_df.iterrows()]
        
        opts_df = data['request_payment_options'][data['request_payment_options']['request_id'] == request_id]
        payment_opts = [parse_payment_option(r) for _, r in opts_df.iterrows()]
        
        messages_df = data.get('messages', pd.DataFrame())
        if not messages_df.empty:
            messages_df = messages_df[messages_df['user_id'] == user_id]
        images_df = data.get('images', pd.DataFrame())
        if not images_df.empty:
            images_df = images_df[(images_df['user_id'] == user_id) | (images_df['request_id'] == request_id)]
        
        extracted_facts = llm_provider.extract_facts(request_id, messages_df, images_df, events_df, image_dir)
        resolved_events = resolver.resolve(raw_events, extracted_facts)
        
        try:
            current_state = state_layer.reconstruct(resolved_events, req_obj, profile_obj)
            
            simulator = Simulator(profile_obj, current_state)
            solver = Solver(simulator, req_obj, payment_opts)
            candidates, amount_safe, earliest_full = solver.generate_candidate_plans()
            
            optimizer = Optimizer(profile_obj, req_obj)
            best_plan = optimizer.rank_plans(candidates)
            
            if not best_plan:
                out_status = "not_affordable"
                out_method = "not_recommended"
                out_plan = "none"
                sc_needed = "none"
            else:
                out_method = best_plan['method']
                out_plan = best_plan['plan_string']
                
                sc_changes = best_plan.get('spending_changes', [])
                if sc_changes:
                    sc_strs = []
                    for change in sc_changes:
                        if change['type'] == 'stop':
                            sc_strs.append(f"stop:{change['target_event_id']}")
                        else:
                            sc_strs.append(f"reduce_to:{change['target_event_id']}:{change['new_amount']}")
                    sc_needed = "|".join(sc_strs)
                else:
                    sc_needed = "none"
                    
                if out_method == "full_payment":
                    out_status = "affordable_now"
                elif out_method == "wait":
                    out_status = "affordable_later"
                else:
                    out_status = "affordable_with_plan"
                    
            safe_amt_str = f"{amount_safe:.2f}".rstrip('0').rstrip('.') if amount_safe is not None else "0"
            output_row = {
                'request_id': request_id,
                'amount_safe_to_pay': safe_amt_str,
                'affordability_status': out_status,
                'recommended_payment_method': out_method,
                'payment_plan': out_plan,
                'earliest_date_for_full_payment': earliest_full if earliest_full else "",
                'spending_changes_needed': sc_needed,
                'decision_explanation': f"Deterministic calculation selected {out_method}."
            }
            
            verifier = Verifier(simulator, req_obj)
            is_verified = verifier.verify(output_row, best_plan)
            
            if not is_verified:
                output_row['affordability_status'] = 'not_affordable'
                output_row['recommended_payment_method'] = 'not_recommended'
                output_row['payment_plan'] = 'none'
                output_row['spending_changes_needed'] = 'none'
        except ValueError:
            output_row = {
                'request_id': request_id,
                'amount_safe_to_pay': "0",
                'affordability_status': "not_affordable",
                'recommended_payment_method': "not_recommended",
                'payment_plan': "none",
                'earliest_date_for_full_payment': "",
                'spending_changes_needed': "none",
                'decision_explanation': "Failed closed due to missing safe exchange rate conversion."
            }

            
        output_rows.append(output_row)
        print(f"Processed {request_id} -> {output_row['recommended_payment_method']}")
        
    output_df = pd.DataFrame(output_rows)
    # The output MUST be exactly what problem_statement says, in exactly that order
    cols = ['request_id', 'amount_safe_to_pay', 'affordability_status', 'recommended_payment_method', 'payment_plan', 'earliest_date_for_full_payment', 'spending_changes_needed', 'decision_explanation']
    output_df = output_df[cols]
    output_df.to_csv(os.path.join(base_dir, 'output.csv'), index=False)
    
if __name__ == '__main__':
    main()
