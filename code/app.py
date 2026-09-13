import streamlit as st
import pandas as pd
import os
import sys
from decimal import Decimal
from datetime import datetime

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

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
from main import parse_request, parse_profile, parse_event, parse_payment_option

st.set_page_config(page_title="SafePay | Financial Agent", page_icon="🛡", layout="wide")

DATASET_DIR = os.path.join(root_dir, 'dataset')
try:
    data_loader = SecureDataLoader(DATASET_DIR)
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.stop()

def login_ui():
    st.title("🛡 SafePay")
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

def run_deterministic_engine(req_row, prof_row, events_df, opts_df, messages_df, images_df):
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
    
    state_layer = FinancialStateLayer()
    current_state = state_layer.reconstruct(resolved_events, req_obj)
    
    simulator = Simulator(profile_obj, current_state)
    solver = Solver(simulator, req_obj, payment_opts)
    candidates, amount_safe, earliest_full = solver.generate_candidate_plans()
    
    optimizer = Optimizer(profile_obj)
    best_plan = optimizer.rank_plans(candidates)
    
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
        'request_id': req_obj.request_id,
        'amount_safe_to_pay': str(amount_safe),
        'affordability_status': out_status,
        'recommended_payment_method': out_method,
        'payment_plan': out_plan,
        'earliest_date_for_full_payment': earliest_full if earliest_full else "",
        'spending_changes_needed': "none",
        'decision_explanation': f"Deterministic constraint satisfaction resulted in {out_method}."
    }
    
    verifier = Verifier(simulator, req_obj)
    is_verified = verifier.verify(output_row)
    
    if not is_verified:
        output_row['affordability_status'] = 'not_affordable'
        output_row['recommended_payment_method'] = 'not_recommended'
        output_row['payment_plan'] = 'none'
        
    return output_row, is_verified

def main_dashboard():
    uuid = st.session_state.get('authenticated_uuid')
    dataset_user_id = st.session_state.get('dataset_user_id')
    
    if not uuid:
        login_ui()
        return
        
    security_context = SecurityContext(uuid, dataset_user_id)
    
    with st.sidebar:
        st.markdown(f"**Authenticated as:** `{dataset_user_id}`")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
            
    user_requests = data_loader.get_user_requests(security_context)
    if not user_requests:
        st.info(f"No financial requests are currently linked to {dataset_user_id}.")
        return
        
    selected_request = st.selectbox("Select a Financial Request", user_requests)
    
    if st.button("Analyze Affordability"):
        with st.spinner("Executing Deterministic Financial Engine..."):
            try:
                req_row, prof_row, events_df, opts_df, messages_df, images_df = data_loader.get_request_context(selected_request, security_context)
                
                decision, is_verified = run_deterministic_engine(req_row, prof_row, events_df, opts_df, messages_df, images_df)
                
                st.markdown(f"### 🛡 SafePay | Financial Agent")
                st.divider()
                
                st.subheader("Financial Safety Analysis")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Balance", f"{prof_row['home_currency']} {prof_row['current_available_balance']}")
                with col2:
                    st.metric("Protected Minimum", f"{prof_row['home_currency']} {prof_row['minimum_balance_to_keep']}")
                with col3:
                    st.metric("Requested Amount", f"{prof_row['home_currency']} {req_row['requested_amount']}")
                    
                st.divider()
                
                status = decision.get("affordability_status")
                if status == "affordable_now":
                    st.success("🟢 SAFE TO PAY")
                elif status in ["affordable_with_plan", "affordable_later"]:
                    st.warning("🟡 WAIT OR USE PAYMENT PLAN")
                else:
                    st.error("🔴 NOT SAFE")
                    
                st.subheader("Recommended Action")
                st.info(decision.get("decision_explanation"))
                st.markdown(f"**Plan:** `{decision.get('payment_plan')}`")
                
                st.subheader("Verification")
                if is_verified:
                    st.markdown("- ✅ 90-Day Simulation: PASSED")
                    st.markdown("- ✅ Minimum Balance Constraint: PASSED")
                    st.markdown("- ✅ Payment Plan Validation: PASSED")
                    st.markdown("- ✅ Independent Verification: PASSED")
                else:
                    st.error("Independent Verification Failed. System forced FAIL-CLOSED safety fallback.")
                    
            except PermissionError:
                st.error("Access Denied: Resource ownership violation.")
            except Exception as e:
                import traceback
                st.error(f"Unable to complete the financial analysis safely. Error: {e}")
                st.code(traceback.format_exc())
                print(f"Diagnostics: {e}")

if __name__ == "__main__":
    main_dashboard()
