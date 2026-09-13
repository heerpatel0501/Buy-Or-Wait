import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, date
from decimal import Decimal
import plotly.graph_objects as go

from code.auth import authenticate
from code.security import SecurityContext
from code.data_loader import SecureDataLoader
from code.llm import LLMProvider
from code.resolver import ConflictResolver
from code.state import FinancialStateLayer
from code.simulator import Simulator
from code.solver import Solver
from code.optimizer import Optimizer
from code.verifier import Verifier
from code.models import Request, FinancialProfile, FinancialEvent, PaymentOption

# Page Config
st.set_page_config(page_title="SafePay", page_icon="🛡️", layout="wide")

# Paths
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(root_dir, 'dataset')

@st.cache_resource
def get_data_loader():
    return SecureDataLoader(DATASET_DIR)

try:
    data_loader = get_data_loader()
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.stop()

def login_ui():
    st.title("🛡️ SafePay")
    st.subheader("Secure Financial Authorization")
    with st.form("login_form"):
        username = st.text_input("User ID (e.g. user_01)")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Authenticate")
        if submit:
            account_uuid = authenticate(username, password)
            if account_uuid:
                st.session_state.authenticated_uuid = account_uuid
                st.session_state.dataset_user_id = username
                st.rerun()
            else:
                st.error("Authentication failed. Invalid credentials.")

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

def run_deterministic_engine(req_row, prof_row, events_df, opts_df, messages_df, images_df, rates_df):
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing from server configuration.")
        
    req_obj = parse_request(req_row)
    profile_obj = parse_profile(prof_row)
    raw_events = [parse_event(r) for _, r in events_df.iterrows()]
    payment_opts = [parse_payment_option(r) for _, r in opts_df.iterrows()]
    
    llm_provider = LLMProvider(api_key=api_key)
    image_dir = os.path.join(DATASET_DIR, 'media', 'images')
    extracted_facts = llm_provider.extract_facts(req_obj.request_id, messages_df, images_df, events_df, image_dir)
    
    resolver = ConflictResolver()
    resolved_events = resolver.resolve(raw_events, extracted_facts)
    
    state_layer = FinancialStateLayer(rates_df)
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
            'request_id': req_obj.request_id,
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
            best_plan = None
            
        # Get timeline history for chart
        history = []
        if best_plan:
            plan_dict = best_plan.get('plan', {})
            sc = best_plan.get('spending_changes', [])
            _, _, history = simulator.simulate(req_obj.request_date, plan_dict, sc, return_timeline=True)
        else:
            _, _, history = simulator.simulate(req_obj.request_date, {}, [], return_timeline=True)
            
    except ValueError:
        output_row = {
            'request_id': req_obj.request_id,
            'amount_safe_to_pay': "0",
            'affordability_status': "not_affordable",
            'recommended_payment_method': "not_recommended",
            'payment_plan': "none",
            'earliest_date_for_full_payment': "",
            'spending_changes_needed': "none",
            'decision_explanation': "Failed closed due to missing safe exchange rate conversion."
        }
        is_verified = False
        history = []
        
    return output_row, is_verified, history

def format_payment_plan(plan_str):
    if plan_str == 'none' or not plan_str:
        return []
    entries = []
    for entry in plan_str.split('|'):
        parts = entry.split(':')
        if len(parts) == 2:
            entries.append({'Date': parts[0], 'Amount': parts[1]})
    return entries

def format_spending_changes(sc_str, events_df):
    if sc_str == 'none' or not sc_str:
        return []
    changes = []
    for entry in sc_str.split('|'):
        parts = entry.split(':')
        change_type = parts[0]
        event_id = parts[1]
        
        event_desc = event_id
        match = events_df[events_df['event_id'] == event_id]
        if not match.empty:
            event_desc = match.iloc[-1]['description']
            
        if change_type == 'stop':
            changes.append(f"Pause: {event_desc}")
        elif change_type == 'reduce_to' and len(parts) >= 3:
            changes.append(f"Reduce: {event_desc} to {parts[2]}")
    return changes

def main_dashboard():
    uuid = st.session_state.get('authenticated_uuid')
    dataset_user_id = st.session_state.get('dataset_user_id')
    
    if not uuid:
        login_ui()
        return
        
    security_context = SecurityContext(uuid, dataset_user_id)
    
    with st.sidebar:
        st.title("🛡️ SafePay")
        st.markdown(f"**User:** `{dataset_user_id}`")
        st.radio("Navigation", ["Dashboard", "Requests", "Financial Forecast", "Evidence", "Settings"])
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
            
    user_requests = data_loader.get_user_requests(security_context)
    if not user_requests:
        st.info(f"No financial requests are currently linked to {dataset_user_id}.")
        return
        
    st.title("Financial Dashboard")
    selected_request = st.selectbox("Select a Request", user_requests)
    
    req_row, prof_row, events_df, opts_df, messages_df, images_df, rates_df = data_loader.get_request_context(selected_request, security_context)
    
    currency = prof_row['home_currency']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Balance", f"{currency} {prof_row['current_available_balance']}")
    with col2:
        st.metric("Minimum Balance To Keep", f"{currency} {prof_row['minimum_balance_to_keep']}")
    with col3:
        # Calculate upcoming 30 day expenses roughly
        upcoming = events_df[(events_df['direction'] == 'debit') & (events_df['status'] != 'cancelled')]['amount']
        st.metric("Upcoming Expenses (Historical Est.)", f"{currency} {pd.to_numeric(upcoming).sum():.2f}")
        
    st.divider()

    if st.button("Analyze Affordability", type="primary"):
        with st.spinner("Executing Deterministic Financial Engine..."):
            try:
                decision, is_verified, history = run_deterministic_engine(req_row, prof_row, events_df, opts_df, messages_df, images_df, rates_df)
                
                # Decision Card
                st.subheader("Decision Result")
                status = decision.get("affordability_status")
                
                status_color = "🔴"
                if status == "affordable_now":
                    status_color = "🟢"
                elif status in ["affordable_with_plan", "affordable_later"]:
                    status_color = "🟡"
                    
                st.markdown(f"### {status_color} {status.replace('_', ' ').title()}")
                
                scol1, scol2 = st.columns(2)
                with scol1:
                    st.metric("Safe to Pay", f"{currency} {decision['amount_safe_to_pay']}")
                with scol2:
                    st.metric("Requested Amount", f"{currency} {req_row['requested_amount']}")
                    
                st.markdown(f"**Recommended Method:** `{decision['recommended_payment_method']}`")
                st.markdown(f"**Complete By:** `{req_row['desired_completion_date'] or decision['earliest_date_for_full_payment']}`")
                
                if is_verified:
                    st.success("✓ Independently verified")
                else:
                    st.warning("⚠ Verification forced a safe fallback")
                
                st.info(f"**Why this decision?**\n{decision['decision_explanation']}")
                
                st.divider()
                
                col_p, col_s = st.columns(2)
                with col_p:
                    st.subheader("Recommended Payment Schedule")
                    plan_data = format_payment_plan(decision['payment_plan'])
                    if plan_data:
                        st.table(pd.DataFrame(plan_data))
                    else:
                        st.markdown("*No payment recommended*")
                        
                with col_s:
                    st.subheader("Spending Changes Needed")
                    sc_data = format_spending_changes(decision['spending_changes_needed'], events_df)
                    if sc_data:
                        for s in sc_data:
                            st.markdown(f"- {s}")
                    else:
                        st.markdown("*No changes needed*")
                
                st.divider()
                st.subheader("90-Day Financial Forecast")
                if history:
                    df_hist = pd.DataFrame(history)
                    min_bal = float(prof_row['minimum_balance_to_keep'])
                    
                    lowest_row = df_hist.loc[df_hist['balance'].idxmin()]
                    lowest_val = float(lowest_row['balance'])
                    lowest_date = lowest_row['date']
                    
                    fig = go.Figure()
                    
                    # Highlight below minimum
                    below_min = df_hist[df_hist['balance'] < min_bal]
                    if not below_min.empty:
                        fig.add_trace(go.Scatter(
                            x=df_hist['date'], y=df_hist['balance'], mode='lines',
                            line=dict(color='red'), fill='tonexty', fillcolor='rgba(255,0,0,0.2)', name='Balance (Danger)'
                        ))
                    else:
                        fig.add_trace(go.Scatter(
                            x=df_hist['date'], y=df_hist['balance'], mode='lines',
                            line=dict(color='blue'), name='Projected Balance'
                        ))
                        
                    fig.add_hline(y=min_bal, line_dash="dash", line_color="red", annotation_text="Minimum Balance to Keep")
                    fig.add_annotation(x=lowest_date, y=lowest_val, text=f"Lowest: {currency} {lowest_val:.2f} on {lowest_date}", showarrow=True, arrowhead=1)
                    
                    st.plotly_chart(fig, use_container_width=True)
                
            except PermissionError:
                st.error("Access Denied: Resource ownership violation.")
            except Exception as e:
                import traceback
                st.error(f"Unable to complete the financial analysis safely. Error: {e}")
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main_dashboard()
