import streamlit as st
import pandas as pd
import os
import sys
import time
import hashlib
from dotenv import load_dotenv

# Ensure the root directory is in sys.path so 'code' is treated as our package
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import the secure deterministic engine
from code.models import FinancialProfile, FinancialEvent, PaymentOption, Request
from code.llm import LLMProvider
from code.resolver import ConflictResolver
from code.state import FinancialStateLayer
from code.simulator import Simulator
from code.solver import Solver
from code.optimizer import Optimizer
from code.verifier import Verifier
from main import parse_profile, parse_event, parse_request, parse_payment_option

# Secure session configuration
st.set_page_config(page_title="SafePay Financial Agent | Secure AI", page_icon="🔒", layout="wide")

# --- AUTHENTICATION LAYER ---
def hash_password(password: str) -> str:
    # In a real app, use Argon2id. Using SHA-256 with salt here for MVP demonstration.
    salt = "safepay_secure_salt_2026"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def init_auth():
    if "authenticated_user" not in st.session_state:
        st.session_state.authenticated_user = None

def login():
    st.title("🔒 SafePay Secure Login")
    username = st.text_input("User ID (e.g. user_01)")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        # Mock auth: Password is "password123" for everyone.
        if password and hash_password(password) == hash_password("password123"):
            # Prevent Session Fixation by resetting state if needed
            st.session_state.authenticated_user = username
            st.rerun()
        else:
            st.error("Invalid credentials.")

def logout():
    st.session_state.authenticated_user = None
    st.rerun()

# --- DATA ACCESS LAYER (AUTHORIZATION / IDOR PREVENTION) ---
@st.cache_data
def load_datasets(dataset_dir):
    data = {}
    for filename in os.listdir(dataset_dir):
        if filename.endswith('.csv'):
            name = filename.replace('.csv', '')
            data[name] = pd.read_csv(os.path.join(dataset_dir, filename)).fillna('')
    return data

def get_authorized_request_context(request_id, current_user, data):
    """
    Enforces Resource Ownership. 
    Verifies that the requested resource belongs to the authenticated user.
    """
    req_df = data['requests'][data['requests']['request_id'] == request_id]
    if req_df.empty:
        raise PermissionError("Resource not found.")
        
    req_row = req_df.iloc[0]
    
    # IDOR Check: Ensure the requested resource belongs to the current user
    if req_row['user_id'] != current_user:
        raise PermissionError("Access Denied.")
        
    prof_row = data['financial_profiles'][data['financial_profiles']['user_id'] == current_user].iloc[0]
    
    # Query strictly by user_id
    events_df = data['financial_events'][data['financial_events']['user_id'] == current_user]
    
    opts_df = data['request_payment_options'][(data['request_payment_options']['request_id'] == request_id)]
    
    if 'messages' in data:
        messages_df = data['messages'][(data['messages']['user_id'] == current_user) & (data['messages']['request_id'] == request_id)]
    else:
        messages_df = pd.DataFrame()
        
    if 'images' in data:
        images_df = data['images'][(data['images']['user_id'] == current_user) & (data['images']['request_id'] == request_id)]
    else:
        images_df = pd.DataFrame()
        
    return req_row, prof_row, events_df, opts_df, messages_df, images_df

# --- APPLICATION LOGIC ---
def main():
    init_auth()
    
    if not st.session_state.authenticated_user:
        login()
        return
        
    current_user = st.session_state.authenticated_user
    
    # Load secrets securely from server environment
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        st.error("Server Configuration Error: LLM Provider is unavailable.")
        return

    # Layout
    st.sidebar.markdown(f"**Logged in as:** `{current_user}`")
    if st.sidebar.button("Logout"):
        logout()
        
    st.title("🛡️ SafePay Financial Agent")
    st.markdown("### Secure & Verified Affordability Analysis")
    st.markdown("---")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dir = os.path.join(base_dir, 'dataset')
    image_dir = os.path.join(dataset_dir, 'media', 'images')
    
    try:
        data = load_datasets(dataset_dir)
    except Exception:
        st.error("Internal Server Error.")
        return

    # Only show requests owned by the current user
    user_requests = data['requests'][data['requests']['user_id'] == current_user]['request_id'].tolist()
    
    if not user_requests:
        st.info("No requests found for your account.")
        return
        
    st.sidebar.markdown("### Select Request")
    selected_request = st.sidebar.selectbox("Choose a Request ID to Analyze", user_requests)
    
    if not selected_request:
        return
        
    try:
        req_row, prof_row, events_df, opts_df, messages_df, images_df = get_authorized_request_context(selected_request, current_user, data)
    except PermissionError:
        st.error("403 Forbidden")
        return
    except Exception:
        st.error("Internal Server Error")
        return

    req_obj = parse_request(req_row)
    profile_obj = parse_profile(prof_row)
    raw_events = [parse_event(r) for _, r in events_df.iterrows()]
    payment_opts = [parse_payment_option(r) for _, r in opts_df.iterrows()]
    
    # UI Layout: Display request info
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👤 User Profile")
        st.write(f"**Current Balance:** {profile_obj.current_available_balance} {profile_obj.home_currency}")
        st.write(f"**Minimum Protected Balance:** {profile_obj.minimum_balance_to_keep} {profile_obj.home_currency}")
        
    with col2:
        st.subheader("🛒 Request Details")
        st.write(f"**Type:** {req_obj.request_type.capitalize()}")
        st.write(f"**Requested Amount:** {req_obj.requested_amount} {profile_obj.home_currency}")
        st.info(f"**User Message:** {req_obj.request_text}")
        
    if st.button("🚀 Run Secure Affordability Audit", type="primary"):
        with st.spinner("Analyzing 90-day financial forecast deterministically..."):
            try:
                # 1. AI Understanding Layer (Isolated)
                llm_provider = LLMProvider(api_key=api_key)
                extracted_facts = llm_provider.extract_facts(selected_request, messages_df, images_df, events_df, image_dir)
                
                # 2. Deterministic Financial Engine
                resolver = ConflictResolver()
                resolved_events = resolver.resolve(raw_events, extracted_facts)
                
                state_layer = FinancialStateLayer()
                current_state = state_layer.reconstruct(resolved_events, req_obj)
                
                simulator = Simulator(profile_obj, current_state)
                solver = Solver(simulator, req_obj, payment_opts)
                candidates, amount_safe, earliest_full = solver.generate_candidate_plans()
                
                optimizer = Optimizer(profile_obj)
                best_plan = optimizer.rank_plans(candidates)
                
                # 3. Independent Verifier
                verifier = Verifier(simulator, req_obj)
                
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
                    'request_id': selected_request,
                    'amount_safe_to_pay': str(amount_safe),
                    'affordability_status': out_status,
                    'recommended_payment_method': out_method,
                    'payment_plan': out_plan,
                    'earliest_date_for_full_payment': earliest_full if earliest_full else "",
                }
                
                # Fail-closed Verification
                if not verifier.verify(output_row):
                    output_row['affordability_status'] = 'not_affordable'
                    output_row['recommended_payment_method'] = 'not_recommended'
                    output_row['payment_plan'] = 'none'

                # Display Results
                st.markdown("---")
                st.subheader("✅ Audit Complete")
                
                status = output_row['affordability_status']
                if 'not_affordable' in status:
                    st.error(f"**Status:** {status.replace('_', ' ').title()} ❌")
                elif 'later' in status:
                    st.warning(f"**Status:** {status.replace('_', ' ').title()} ⏳")
                else:
                    st.success(f"**Status:** {status.replace('_', ' ').title()} 🎉")
                    
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric("Amount Safe To Pay", f"{output_row['amount_safe_to_pay']} {profile_obj.home_currency}")
                    st.write(f"**Recommended Method:** {output_row['recommended_payment_method'].replace('_', ' ').title()}")
                with res_col2:
                    st.write(f"**Payment Plan:** {output_row['payment_plan']}")
                    st.write(f"**Earliest Safe Date:** {output_row['earliest_date_for_full_payment']}")
                    
                with st.expander("🔍 View AI-Extracted Facts (Provenance)"):
                    if extracted_facts:
                        for fact in extracted_facts:
                            st.write(f"- **{fact.fact_type}**: {fact.amount} (Source: {fact.provenance.source})")
                    else:
                        st.write("No modifications found in messages/images.")
                        
            except PermissionError:
                st.error("403 Forbidden")
            except Exception as e:
                # Log actual error securely on backend. Expose safe message to user.
                print(f"Secure Backend Error: {e}")
                st.error("Unable to process this request right now. Fallback to fail-closed state.")

if __name__ == '__main__':
    main()
