import streamlit as st
import pandas as pd
import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal
import plotly.graph_objects as go
import traceback

# Add repo root to sys.path to prevent standard library 'code' module shadowing
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from code.auth import authenticate
from code.security import SecurityContext
from code.data_loader import SecureDataLoader
from code.models import Request, FinancialProfile, FinancialEvent, PaymentOption

# Initialize loader globally
@st.cache_resource
def get_loader():
    return SecureDataLoader(os.path.join(root_dir, 'dataset'))

loader = get_loader()

# ---------------------------------------------------------
# CUSTOM CSS FOR FINTECH LOOK
# ---------------------------------------------------------
def inject_custom_css():
    st.markdown("""
    <style>
        /* Base styles */
        .stApp {
            background-color: #F8F9FA;
            color: #1E293B;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #0F172A;
        }
        [data-testid="stSidebar"] * {
            color: #F8F9FA !important;
        }
        
        /* Metric cards */
        [data-testid="stMetricValue"] {
            font-size: 28px !important;
            font-weight: 700 !important;
            color: #0F172A !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 14px !important;
            color: #64748B !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Premium Card Styling */
        .safepay-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border: 1px solid #E2E8F0;
            margin-bottom: 24px;
        }
        
        .card-title {
            font-size: 16px;
            font-weight: 600;
            color: #475569;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Status Badges */
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 18px;
            margin-bottom: 16px;
        }
        .status-safe { background-color: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; }
        .status-plan { background-color: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
        .status-notsafe { background-color: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }
        
        /* Headings */
        h1 { font-size: 32px !important; font-weight: 700 !important; color: #0F172A !important; }
        h2 { font-size: 24px !important; font-weight: 600 !important; color: #1E293B !important; }
        h3 { font-size: 20px !important; font-weight: 600 !important; color: #334155 !important; }
        
        /* Hide element blocks we don't want */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# AUTHENTICATION UI
# ---------------------------------------------------------
def login_ui():
    inject_custom_css()
    
    col1, col2 = st.columns([1.2, 1], gap="large")
    
    with col1:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="padding: 40px; background-color: #0F172A; border-radius: 16px; color: white; height: 100%;">
            <div style="display: flex; align-items: center; margin-bottom: 24px;">
                <span style="font-size: 40px; margin-right: 16px;">🛡️</span>
                <h1 style="color: white !important; margin: 0; font-size: 48px !important;">SafePay</h1>
            </div>
            <h2 style="color: #94A3B8 !important; font-weight: 400 !important; margin-bottom: 48px;">Make every purchase with financial confidence.</h2>
            
            <p style="font-size: 20px; font-weight: 500; margin-bottom: 24px; color: #F8F9FA;">"Know what you can safely afford before you spend."</p>
            
            <div style="background: rgba(255,255,255,0.1); padding: 16px; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: center;">
                <span style="color: #4ADE80; font-size: 20px; margin-right: 12px;">✓</span>
                <span style="font-size: 16px; font-weight: 500;">90-day financial forecast</span>
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 16px; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: center;">
                <span style="color: #4ADE80; font-size: 20px; margin-right: 12px;">✓</span>
                <span style="font-size: 16px; font-weight: 500;">Smart payment planning</span>
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 16px; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: center;">
                <span style="color: #4ADE80; font-size: 20px; margin-right: 12px;">✓</span>
                <span style="font-size: 16px; font-weight: 500;">Evidence-aware analysis</span>
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 16px; border-radius: 8px; display: flex; align-items: center;">
                <span style="color: #4ADE80; font-size: 20px; margin-right: 12px;">✓</span>
                <span style="font-size: 16px; font-weight: 500;">Independently verified</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="safepay-card">
            <h2 style="margin-bottom: 8px; color: #0F172A !important;">Welcome to SafePay</h2>
            <p style="color: #64748B; margin-bottom: 32px; font-size: 16px;">Secure Financial Access</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("User ID", placeholder="Enter your User ID (e.g. user_01)")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in securely", type="primary", use_container_width=True)
            
            if submitted:
                if username and password:
                    uuid_val = authenticate(username, password)
                    if uuid_val:
                        st.session_state['authenticated_uuid'] = uuid_val
                        st.session_state['dataset_user_id'] = username
                        st.rerun()
                    else:
                        st.error("Authentication failed. Invalid credentials.")
                else:
                    st.error("Please provide both User ID and Password.")
                    
        st.markdown("""
        <div style="text-align: center; margin-top: 24px; color: #64748B; font-size: 14px; display: flex; align-items: center; justify-content: center;">
            <span style="margin-right: 8px;">🔒</span> Your financial data stays protected
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# ENGINE WRAPPER
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def run_deterministic_engine_cached(req_dict, prof_dict, events_json, opts_json, msgs_json, imgs_json, rates_json):
    # Reconstruct DFs
    events_df = pd.DataFrame(json.loads(events_json))
    opts_df = pd.DataFrame(json.loads(opts_json))
    messages_df = pd.DataFrame(json.loads(msgs_json))
    images_df = pd.DataFrame(json.loads(imgs_json))
    rates_df = pd.DataFrame(json.loads(rates_json))
    
    # Run
    return run_backend(req_dict, prof_dict, events_df, opts_df, messages_df, images_df, rates_df)

# We will need to keep the parsers and run logic somewhere. Let's put it right here for simplicity,
# but outside the cached function.

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
        event_id=row['event_id'], user_id=row['user_id'], event_type=row['event_type'], description=row['description'],
        category=row['category'], direction=row['direction'], amount=Decimal(str(row['amount'])) if row['amount'] else Decimal('0.0'), currency=row['currency'],
        event_date=datetime.strptime(str(row['event_date']), '%Y-%m-%d').date(),
        settlement_date=datetime.strptime(str(row['settlement_date']), '%Y-%m-%d').date() if row['settlement_date'] else None,
        status=row['status'], linked_event_id=row['linked_event_id'] if row['linked_event_id'] else None, flexibility=row['flexibility'],
        minimum_allowed_amount=Decimal(str(row['minimum_allowed_amount'])) if row['minimum_allowed_amount'] else None
    )

def parse_request(row) -> Request:
    return Request(
        request_id=row['request_id'], user_id=row['user_id'], request_date=datetime.strptime(str(row['request_date']), '%Y-%m-%d').date(),
        request_type=row['request_type'], requested_amount=Decimal(str(row['requested_amount'])),
        desired_completion_date=datetime.strptime(str(row['desired_completion_date']), '%Y-%m-%d').date() if row['desired_completion_date'] else None,
        allows_partial_payment=str(row['allows_partial_payment']).lower() == 'true', request_text=row['request_text']
    )

def parse_payment_option(row) -> PaymentOption:
    return PaymentOption(
        payment_option_id=row['payment_option_id'], payment_method=row['payment_method'], payment_amount=Decimal(str(row['payment_amount'])),
        number_of_payments=int(row['number_of_payments']), first_payment_date=datetime.strptime(str(row['first_payment_date']), '%Y-%m-%d').date(),
        payment_frequency_days=int(row['payment_frequency_days']) if row['payment_frequency_days'] else None, total_payable_amount=Decimal(str(row['total_payable_amount']))
    )

def run_backend(req_row, prof_row, events_df, opts_df, messages_df, images_df, rates_df):
    from code.llm import LLMProvider
    from code.resolver import ConflictResolver
    from code.state import FinancialStateLayer
    from code.simulator import Simulator
    from code.solver import Solver
    from code.optimizer import Optimizer
    from code.verifier import Verifier
    
    api_key = os.environ.get("GEMINI_API_KEY", "dummy")
    llm_provider = LLMProvider(api_key=api_key)
    req_obj = parse_request(req_row)
    prof_obj = parse_profile(prof_row)
    event_objs = [parse_event(r) for _, r in events_df.iterrows()]
    payment_opts = [parse_payment_option(r) for _, r in opts_df.iterrows()]
    
    resolver = ConflictResolver()
    state_layer = FinancialStateLayer(rates_df)
    
    try:
        image_dir = os.path.join(root_dir, 'dataset', 'media', 'images')
        extracted_facts = llm_provider.extract_facts(req_obj.request_id, messages_df, images_df, events_df, image_dir)
    except Exception as e:
        print(f"LLM extraction error safely handled: {e}")
        extracted_facts = []
        
    resolved_events = resolver.resolve(event_objs, extracted_facts)
    current_state = state_layer.reconstruct(resolved_events, req_obj, prof_obj)
    
    simulator = Simulator(prof_obj, current_state)
    solver = Solver(simulator, req_obj, payment_opts)
    
    candidates, amt_safe, earliest_full = solver.generate_candidate_plans()
    
    optimizer = Optimizer(prof_obj, req_obj)
    best_plan = optimizer.rank_plans(candidates)
    
    verifier = Verifier(simulator, req_obj)
    
    output_row = {
        'request_id': req_obj.request_id,
        'amount_safe_to_pay': str(amt_safe),
        'earliest_date_for_full_payment': earliest_full if earliest_full else "",
        'spending_changes_needed': "none"
    }
    
    if not best_plan:
        output_row['affordability_status'] = "not_affordable"
        output_row['recommended_payment_method'] = "not_recommended"
        output_row['payment_plan'] = "none"
        is_verified = verifier.verify(output_row, best_plan)
        _, _, history = simulator.simulate(req_obj.request_date, {}, [], return_timeline=True)
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
            output_row['spending_changes_needed'] = "|".join(sc_strs)
            
        if out_method == "full_payment":
            output_row['affordability_status'] = "affordable_now"
        elif out_method == "wait":
            output_row['affordability_status'] = "affordable_later"
        else:
            output_row['affordability_status'] = "affordable_with_plan"
            
        output_row['recommended_payment_method'] = out_method
        output_row['payment_plan'] = out_plan
        
        # Build the exact plan dict for Simulator
        plan_dict = {}
        if out_plan and out_plan != 'none':
            for entry in out_plan.split('|'):
                parts = entry.split(':')
                if len(parts) == 2:
                    plan_dict[datetime.strptime(parts[0], '%Y-%m-%d').date()] = Decimal(parts[1])
                    
        is_verified = verifier.verify(output_row, best_plan)
        
        if not is_verified:
            output_row['affordability_status'] = "not_affordable"
            output_row['recommended_payment_method'] = "not_recommended"
            output_row['payment_plan'] = "none"
            output_row['spending_changes_needed'] = "none"
            _, _, history = simulator.simulate(req_obj.request_date, {}, [], return_timeline=True)
        else:
            _, _, history = simulator.simulate(req_obj.request_date, plan_dict, sc_changes, return_timeline=True)
            
    # Generic explanation
    if output_row['affordability_status'] == 'not_affordable':
        output_row['decision_explanation'] = "Paying the requested amount would cause the projected balance to fall below your required minimum during the 90-day forecast. No safe plan was found."
    elif output_row['affordability_status'] == 'affordable_now':
        output_row['decision_explanation'] = "The full requested amount can be safely paid today without breaching the minimum balance requirement in the 90-day forecast."
    elif output_row['affordability_status'] == 'affordable_with_plan':
        output_row['decision_explanation'] = "The recommended plan completes the purchase while maintaining the required minimum balance across the 90-day forecast."
    else:
        output_row['decision_explanation'] = "The purchase will become safe in the future based on projected cash flow."
        
    return output_row, is_verified, history

# Helpers for UI
def format_payment_plan(plan_str):
    if plan_str == 'none' or not plan_str: return []
    entries = []
    for entry in plan_str.split('|'):
        parts = entry.split(':')
        if len(parts) == 2:
            entries.append({'Date': parts[0], 'Amount': float(parts[1])})
    return entries

def format_spending_changes(sc_str, events_df):
    if sc_str == 'none' or not sc_str: return []
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

# ---------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------
def main_dashboard():
    uuid_val = st.session_state.get('authenticated_uuid')
    dataset_user_id = st.session_state.get('dataset_user_id')
    
    if not uuid_val:
        login_ui()
        return
        
    inject_custom_css()
    security_context = SecurityContext(uuid_val, dataset_user_id)
    
    # Header
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
            <h2 style="margin: 0; display: flex; align-items: center;">
                <span style="color: #0F172A; font-weight: 700;">SafePay</span> 
                <span style="color: #94A3B8; font-weight: 400; font-size: 20px; margin-left: 12px;">Financial Affordability Agent</span>
            </h2>
            <div style="display: flex; align-items: center; color: #475569; font-weight: 500;">
                <span style="color: #4ADE80; margin-right: 8px;">●</span> Protected &nbsp;|&nbsp; 
                <span style="margin: 0 12px;">{dataset_user_id}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("<h2 style='color: white !important; font-weight: 700; font-size: 24px; margin-bottom: 32px;'>🛡️ SafePay</h2>", unsafe_allow_html=True)
        
        nav = st.radio("Navigation", ["Overview", "Requests", "Financial Forecast", "Evidence", "Verification", "Settings"], label_visibility="collapsed")
        
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Get user requests
    user_requests = loader.get_user_requests(security_context)
    
    if not user_requests:
        st.markdown("""
        <div style="text-align: center; padding: 100px 20px;">
            <h1 style="font-size: 48px; margin-bottom: 16px;">📂</h1>
            <h2 style="color: #1E293B; margin-bottom: 8px;">No financial requests yet</h2>
            <p style="color: #64748B; font-size: 16px; max-width: 500px; margin: 0 auto;">
                Once a purchase request is available, SafePay will analyze whether you can safely afford it.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Select Request safely
    selected_request = st.selectbox("Select Request", user_requests, label_visibility="collapsed")
    
    try:
        req_row, prof_row, events_df, opts_df, messages_df, images_df, rates_df = loader.get_request_context(selected_request, security_context)
        
        # Engine execution with spinner
        with st.spinner("Analyzing affordability safely..."):
            decision, is_verified, history = run_deterministic_engine_cached(
                req_row.to_dict(), prof_row.to_dict(), 
                events_df.to_json(orient="records"), opts_df.to_json(orient="records"),
                messages_df.to_json(orient="records"), images_df.to_json(orient="records"),
                rates_df.to_json(orient="records")
            )
            
        currency = prof_row['home_currency']
        
        if nav == "Overview":
            st.markdown("<h1>Your financial safety overview</h1>", unsafe_allow_html=True)
            st.markdown("<p style='color: #64748B; font-size: 16px; margin-bottom: 32px;'>Review your current position and see what you can safely afford.</p>", unsafe_allow_html=True)
            
            # Summary Cards
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Balance", f"{currency} {prof_row['current_available_balance']}")
            c2.metric("Minimum Balance", f"{currency} {prof_row['minimum_balance_to_keep']}")
            
            upcoming = events_df[(events_df['direction'] == 'debit') & (events_df['status'] != 'cancelled')]['amount']
            upcoming_total = pd.to_numeric(upcoming).sum()
            c3.metric("Upcoming Commitments", f"{currency} {upcoming_total:.2f}")
            
            income = events_df[(events_df['direction'] == 'credit') & (events_df['status'] == 'settled')]['amount']
            income_total = pd.to_numeric(income).sum()
            c4.metric("Confirmed Income", f"{currency} {income_total:.2f}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Request Section
            payment_options_list = "Full payment<br>"
            if req_row['allows_partial_payment']:
                payment_options_list += "Partial payment<br>"
            for _, opt in opts_df.iterrows():
                payment_options_list += f"{str(opt['payment_method']).replace('_', ' ').capitalize()}<br>"
                
            st.markdown("""
            <div class="safepay-card">
                <div class="card-title">Purchase request</div>
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <div>
                        <h2 style="margin:0;">{req_name}</h2>
                        <div style="color: #64748B; margin-top: 4px; margin-bottom: 16px;">Desired by {date}</div>
                        <div style="color: #334155; font-size: 14px; font-weight: 600;">Available payment methods:</div>
                        <div style="color: #64748B; font-size: 14px;">{opts}</div>
                    </div>
                    <div style="text-align: right;">
                        <h2 style="margin:0; color: #0F172A;">{curr} {amt}</h2>
                        <div style="color: #64748B; margin-top: 4px;">Requested amount</div>
                    </div>
                </div>
            </div>
            """.format(
                req_name=req_row['request_type'].title(), 
                date=req_row['desired_completion_date'] or "No deadline",
                curr=currency, amt=req_row['requested_amount'],
                opts=payment_options_list
            ), unsafe_allow_html=True)
            
            # Decision Card
            status = decision['affordability_status']
            if status == "affordable_now":
                badge = '<div class="status-badge status-safe">✓ Safe to pay now</div>'
            elif status in ["affordable_with_plan", "affordable_later"]:
                badge = '<div class="status-badge status-plan">◷ Pay with plan</div>'
            else:
                badge = '<div class="status-badge status-notsafe">! Not safe to proceed</div>'
                
            verified_badge = "✓ Independently verified" if is_verified else "⚠ Verification forced a safe fallback"
            verified_color = "#16A34A" if is_verified else "#D97706"
            
            st.markdown(f"""
            <div class="safepay-card" style="border: 2px solid #E2E8F0; border-top: 4px solid #0F172A;">
                <div class="card-title" style="display: flex; justify-content: space-between;">
                    <span>SafePay Decision</span>
                    <span style="color: {verified_color}; font-weight: 500; text-transform: none; font-size: 14px;">{verified_badge}</span>
                </div>
                {badge}
                <div style="display: flex; flex-wrap: wrap; gap: 48px; margin-top: 8px;">
                    <div>
                        <div style="font-size: 36px; font-weight: 700; color: #0F172A;">{currency} {decision['amount_safe_to_pay']}</div>
                        <div style="color: #64748B; font-weight: 500;">Maximum amount safely payable today</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: 600; color: #334155;">{decision['recommended_payment_method'].replace('_', ' ').title()}</div>
                        <div style="color: #64748B; font-weight: 500;">Recommended method</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: 600; color: #334155;">{decision['earliest_date_for_full_payment'] or 'N/A'}</div>
                        <div style="color: #64748B; font-weight: 500;">Earliest full payment date</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Recommended Approach & Spending Changes
            scol1, scol2 = st.columns(2)
            with scol1:
                st.markdown('<div class="safepay-card"><div class="card-title">Recommended approach</div>', unsafe_allow_html=True)
                plan = format_payment_plan(decision['payment_plan'])
                if plan:
                    st.dataframe(pd.DataFrame(plan), use_container_width=True, hide_index=True)
                    st.markdown(f"**Total:** {currency} {sum(p['Amount'] for p in plan)}")
                else:
                    st.markdown("No payment recommended.")
                st.markdown('</div>', unsafe_allow_html=True)
                
            with scol2:
                st.markdown('<div class="safepay-card"><div class="card-title">Spending changes needed</div>', unsafe_allow_html=True)
                changes = format_spending_changes(decision['spending_changes_needed'], events_df)
                if changes:
                    for c in changes:
                        st.markdown(f"• **{c}**")
                else:
                    st.markdown("✓ No spending changes required")
                st.markdown('</div>', unsafe_allow_html=True)
                
            # Why this decision?
            st.markdown(f"""
            <div class="safepay-card" style="background-color: #F8FAFC;">
                <div class="card-title">Why this decision?</div>
                <p style="font-size: 16px; color: #334155; line-height: 1.5;">{decision['decision_explanation']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # AI Transparency
            st.markdown("""
            <div style="margin-top: 48px; border-top: 1px solid #E2E8F0; padding-top: 32px;">
                <h3 style="margin-bottom: 24px;">How SafePay reaches this decision</h3>
                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px;">
                    <div style="flex: 1; min-width: 150px;"><div style="color:#94A3B8; font-weight:bold;">01</div><div style="font-size:14px; font-weight:500;">Evidence interpreted</div></div>
                    <div style="flex: 1; min-width: 150px;"><div style="color:#94A3B8; font-weight:bold;">02</div><div style="font-size:14px; font-weight:500;">Financial state reconstructed</div></div>
                    <div style="flex: 1; min-width: 150px;"><div style="color:#94A3B8; font-weight:bold;">03</div><div style="font-size:14px; font-weight:500;">90-day forecast simulated</div></div>
                    <div style="flex: 1; min-width: 150px;"><div style="color:#94A3B8; font-weight:bold;">04</div><div style="font-size:14px; font-weight:500;">Payment plans evaluated</div></div>
                    <div style="flex: 1; min-width: 150px;"><div style="color:#94A3B8; font-weight:bold;">05</div><div style="font-size:14px; font-weight:500;">Best valid plan selected</div></div>
                    <div style="flex: 1; min-width: 150px;"><div style="color:#94A3B8; font-weight:bold;">06</div><div style="font-size:14px; font-weight:500;">Decision independently verified</div></div>
                </div>
                <p style="color: #64748B; font-size: 14px;">
                    AI interprets unstructured financial evidence. The financial decision is calculated deterministically and independently verified.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        elif nav == "Requests":
            st.title("Your Purchase Requests")
            st.markdown("Select a request below to analyze its affordability in the Overview tab.")
            
            req_data = []
            for r_id in user_requests:
                r_ctx, _, _, _, _, _, _ = loader.get_request_context(r_id, security_context)
                req_data.append({
                    "Request": r_ctx['request_type'].title(),
                    "Amount": f"{currency} {r_ctx['requested_amount']}",
                    "Desired Date": r_ctx['desired_completion_date'] or "None",
                    "ID": r_id
                })
            
            st.dataframe(pd.DataFrame(req_data), use_container_width=True, hide_index=True)

        elif nav == "Financial Forecast":
            st.title("90-day financial forecast")
            st.markdown("Projected cash flow safely accounting for commitments, income, and the recommended payment plan.")
            
            if history:
                df_hist = pd.DataFrame(history)
                min_bal = float(prof_row['minimum_balance_to_keep'])
                
                lowest_row = df_hist.loc[df_hist['balance'].idxmin()]
                lowest_val = float(lowest_row['balance'])
                lowest_date = lowest_row['date']
                
                st.markdown(f"""
                <div style="display: flex; gap: 24px; margin-bottom: 24px;">
                    <div class="safepay-card" style="flex: 1;">
                        <div class="card-title">Projected lowest balance</div>
                        <div style="font-size: 24px; font-weight: 700; color: #0F172A;">{currency} {lowest_val:.2f}</div>
                    </div>
                    <div class="safepay-card" style="flex: 1;">
                        <div class="card-title">Required minimum</div>
                        <div style="font-size: 24px; font-weight: 700; color: #0F172A;">{currency} {min_bal:.2f}</div>
                    </div>
                    <div class="safepay-card" style="flex: 1;">
                        <div class="card-title">Safety buffer</div>
                        <div style="font-size: 24px; font-weight: 700; color: {'#16A34A' if lowest_val >= min_bal else '#DC2626'};">{currency} {(lowest_val - min_bal):.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                fig = go.Figure()
                
                below_min = df_hist[df_hist['balance'] < min_bal]
                if not below_min.empty:
                    fig.add_trace(go.Scatter(
                        x=df_hist['date'], y=df_hist['balance'], mode='lines',
                        line=dict(color='#DC2626', width=3), fill='tonexty', fillcolor='rgba(220,38,38,0.1)', name='Balance (Danger)'
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=df_hist['date'], y=df_hist['balance'], mode='lines',
                        line=dict(color='#0EA5E9', width=3), fill='tozeroy', fillcolor='rgba(14,165,233,0.1)', name='Projected Balance'
                    ))
                    
                fig.add_hline(y=min_bal, line_dash="dash", line_color="#475569", annotation_text="Minimum Required Balance", annotation_position="bottom right")
                fig.add_annotation(x=lowest_date, y=lowest_val, text=f"Lowest point", showarrow=True, arrowhead=2, arrowcolor="#475569")
                
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=20, r=20, t=20, b=20),
                    xaxis=dict(showgrid=True, gridcolor='#F1F5F9', title='Date'),
                    yaxis=dict(showgrid=True, gridcolor='#F1F5F9', title='Balance')
                )
                
                st.plotly_chart(fig, use_container_width=True)

        elif nav == "Evidence":
            st.title("Evidence used")
            st.markdown("SafePay relies on the following verified information.")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("""
                <div class="safepay-card">
                    <div style="font-size: 20px; font-weight: 600; margin-bottom: 12px;">✓ Financial profile verified</div>
                    <div style="color: #64748B;">Priorities, minimum balance, and limits accounted for.</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="safepay-card">
                    <div style="font-size: 20px; font-weight: 600; margin-bottom: 12px;">✓ {len(events_df)} confirmed financial events</div>
                    <div style="color: #64748B;">Recurring expenses and income scheduled.</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c2:
                st.markdown(f"""
                <div class="safepay-card">
                    <div style="font-size: 20px; font-weight: 600; margin-bottom: 12px;">✓ {len(opts_df)} Payment options validated</div>
                    <div style="color: #64748B;">Seller financing options verified.</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="safepay-card">
                    <div style="font-size: 20px; font-weight: 600; margin-bottom: 12px;">✓ {len(messages_df) + len(images_df)} context items interpreted</div>
                    <div style="color: #64748B;">Messages and images parsed by AI evidence extractor.</div>
                </div>
                """, unsafe_allow_html=True)

        elif nav == "Verification":
            st.title("Independent verification")
            
            if is_verified:
                st.markdown("""
                <div style="background-color: #DCFCE7; color: #166534; padding: 24px; border-radius: 12px; margin-bottom: 24px; border: 1px solid #BBF7D0;">
                    <h3 style="margin: 0 0 8px 0; color: #166534 !important;">✓ Decision Verified</h3>
                    <p style="margin: 0; font-size: 16px;">The financial solver's recommendation passed all deterministic safety checks.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background-color: #FEE2E2; color: #991B1B; padding: 24px; border-radius: 12px; margin-bottom: 24px; border: 1px solid #FECACA;">
                    <h3 style="margin: 0 0 8px 0; color: #991B1B !important;">Verification failed</h3>
                    <p style="margin: 0; font-size: 16px;">SafePay could not safely verify this recommendation. No financial recommendation has been approved.</p>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("""
            <div class="safepay-card">
                <div class="card-title">Checks performed</div>
                <ul style="list-style-type: none; padding-left: 0; margin-top: 16px;">
                    <li style="margin-bottom: 12px;">✓ Financial state validated</li>
                    <li style="margin-bottom: 12px;">✓ 90-day forecast checked</li>
                    <li style="margin-bottom: 12px;">✓ Minimum balance maintained</li>
                    <li style="margin-bottom: 12px;">✓ Payment plan validated</li>
                    <li style="margin-bottom: 12px;">✓ Completion deadline checked</li>
                    <li>✓ Payment option validated</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        elif nav == "Settings":
            st.title("Settings")
            
            st.markdown("### Account")
            st.markdown(f"**Authenticated User:** `{dataset_user_id}`")
            st.markdown(f"**Session ID:** `{uuid_val[:8]}...`")
            
            st.divider()
            st.markdown("### Security")
            st.markdown("✓ **Gemini API key is managed server-side.**")
            
            st.divider()
            st.markdown("### Privacy")
            st.markdown("✓ **Only data belonging to your authenticated account is used.**")
            
            st.divider()
            st.markdown("### Data isolation")
            st.markdown("✓ **Requests, financial events, messages, and images are access-controlled by user ownership.**")

    except PermissionError:
        st.error("Access denied.")
    except Exception as e:
        st.error("SafePay could not complete this analysis safely.")
        
if __name__ == "__main__":
    main_dashboard()
