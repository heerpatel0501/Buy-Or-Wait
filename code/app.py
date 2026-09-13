import streamlit as st
# Must be the first Streamlit command
st.set_page_config(layout="wide", page_title="SafePay", initial_sidebar_state="expanded")

import pandas as pd
import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal
import plotly.graph_objects as go
import traceback
import io

from reportlab.pdfgen import canvas
from docx import Document

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

def generate_pdf(data_dict, req_id):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, f"SafePay Financial Analysis Report")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, 770, f"Request ID: {req_id}")
    p.drawString(50, 750, f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 720, "Result")
    p.setFont("Helvetica", 12)
    p.drawString(60, 700, f"Status: {data_dict.get('affordability_status', '')}")
    p.drawString(60, 680, f"Method: {data_dict.get('recommended_payment_method', '')}")
    p.drawString(60, 660, f"Amount Safe to Pay: {data_dict.get('amount_safe_to_pay', '')}")
    p.drawString(60, 640, f"Payment Plan: {data_dict.get('payment_plan', '')}")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 610, "Reasoning")
    p.setFont("Helvetica", 11)
    import textwrap
    lines = textwrap.wrap(data_dict.get('decision_explanation', ''), width=90)
    y_pos = 590
    for line in lines:
        p.drawString(60, y_pos, line)
        y_pos -= 15
        
    y_pos -= 10
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_pos, "Verification Proof")
    p.setFont("Helvetica", 11)
    y_pos -= 20
    is_verif = data_dict.get('is_verified', False)
    p.drawString(60, y_pos, f"Pass/Fail: {'PASS' if is_verif else 'FAIL'}")
    y_pos -= 15
    proof_text = "Checks executed: Evaluated 90-day deterministic balance trajectory against minimum balance requirement."
    for line in textwrap.wrap(proof_text, width=90):
        p.drawString(60, y_pos, line)
        y_pos -= 15
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_docx(data_dict, req_id):
    doc = Document()
    doc.add_heading(f"SafePay Financial Analysis Report", 0)
    
    doc.add_paragraph(f"Request ID: {req_id}")
    doc.add_paragraph(f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    doc.add_heading("Result", level=2)
    doc.add_paragraph(f"Status: {data_dict.get('affordability_status', '')}")
    doc.add_paragraph(f"Method: {data_dict.get('recommended_payment_method', '')}")
    doc.add_paragraph(f"Amount Safe to Pay: {data_dict.get('amount_safe_to_pay', '')}")
    doc.add_paragraph(f"Payment Plan: {data_dict.get('payment_plan', '')}")
    
    doc.add_heading("Reasoning", level=2)
    doc.add_paragraph(data_dict.get('decision_explanation', ''))
    
    doc.add_heading("Verification Proof", level=2)
    is_verif = data_dict.get('is_verified', False)
    doc.add_paragraph(f"Pass/Fail: {'PASS' if is_verif else 'FAIL'}")
    doc.add_paragraph("Checks executed: Evaluated 90-day deterministic balance trajectory against minimum balance requirement.")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# SYSTEMIC CSS FOR HIGH CONTRAST & SINGLE PAGE LOOK
# ---------------------------------------------------------
def inject_main_css():
    st.markdown('''
    <style>
        /* Base styles */
        .stApp {
            background-color: #F4F7FE;
            color: #2B3674;
            font-family: 'Inter', -apple-system, sans-serif;
        }
        
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0;
        }
        
        /* Typography overrides */
        h1, h2, h3, h4, p { color: #2B3674; margin-bottom: 8px; }
        h4 { font-size: 18px; font-weight: 700; margin-top: 0; }
        
        /* Metric box / Cards */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 20px !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 10px 30px rgba(112, 144, 176, 0.08) !important;
            border: none !important;
            padding: 20px !important;
            margin-bottom: 20px !important;
        }
        
        /* Metrics Specific */
        .fs-metric-label { font-size: 14px; color: #A3AED0; font-weight: 500; display: flex; justify-content: space-between; }
        .fs-metric-label span.icon { width: 24px; height: 24px; background: #F4F7FE; border-radius: 50%; display: flex; justify-content: center; align-items: center; color: #157F87; }
        .fs-metric-value { font-size: 32px; font-weight: 700; color: #2B3674; margin: 8px 0; }
        .fs-metric-pill { 
            display: inline-block; padding: 4px 10px; border-radius: 16px; 
            font-size: 12px; font-weight: 700; 
        }
        .fs-pill-green { background: #ECFDF5; color: #05CD99; }
        .fs-pill-red { background: #FEF2F2; color: #EE5D50; }
        .fs-pill-neutral { background: #F4F7FE; color: #A3AED0; }
        
        /* Primary Buttons */
        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #157F87 !important;
            border-color: #157F87 !important;
            border-radius: 16px !important;
        }
        div[data-testid="stButton"] button[kind="primary"] p {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background-color: #11676E !important;
        }
        
        /* Secondary Buttons */
        div[data-testid="stButton"] button[kind="secondary"],
        div[data-testid="stDownloadButton"] button {
            background-color: #F4F7FE !important;
            border-color: #F4F7FE !important;
            border-radius: 16px !important;
        }
        div[data-testid="stButton"] button[kind="secondary"] p,
        div[data-testid="stDownloadButton"] button p {
            color: #2B3674 !important;
            font-weight: 600 !important;
        }
        
        /* Text Area / Inputs */
        div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input, div[data-baseweb="select"] {
            background: #F4F7FE !important;
            border-color: #F4F7FE !important;
            border-radius: 12px !important;
            color: #2B3674 !important;
            -webkit-text-fill-color: #2B3674 !important;
        }
        
        /* Sidebar Logo */
        .sidebar-logo {
            font-size: 28px; font-weight: 800; color: #2B3674;
            display: flex; align-items: center; gap: 12px;
            margin-bottom: 40px;
            padding-left: 12px;
        }
        
        /* Sidebar Menu Items */
        .sidebar-menu-item {
            padding: 14px 20px;
            border-radius: 16px;
            margin-bottom: 8px;
            color: #A3AED0;
            font-weight: 700;
            display: flex; align-items: center; gap: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .sidebar-menu-item.active {
            background-color: #157F87;
            color: #FFFFFF;
            box-shadow: 0 4px 12px rgba(21, 127, 135, 0.3);
        }
        
        .block-container {
            padding-top: 2rem !important;
            max-width: 1400px;
        }
    </style>
    ''', unsafe_allow_html=True)

# ---------------------------------------------------------
# ENGINE WRAPPER
# ---------------------------------------------------------
def parse_profile(row) -> FinancialProfile:
    def parse_list(s):
        if not s: return []
        return [x.strip() for x in str(s).split('|')]
    return FinancialProfile(
        user_id=row['user_id'], home_currency=row['home_currency'], current_available_balance=Decimal(str(row['current_available_balance'])),
        minimum_balance_to_keep=Decimal(str(row['minimum_balance_to_keep'])), financial_priorities=parse_list(row['financial_priorities']),
        expense_categories_to_protect=parse_list(row['expense_categories_to_protect']), expense_categories_user_is_willing_to_reduce=parse_list(row['expense_categories_user_is_willing_to_reduce']),
        expense_categories_user_is_willing_to_stop=parse_list(row['expense_categories_user_is_willing_to_stop']), payment_methods_user_will_consider=parse_list(row['payment_methods_user_will_consider']),
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
            
    if output_row['affordability_status'] == 'not_affordable':
        output_row['decision_explanation'] = "Paying the requested amount would cause the projected balance to fall below your required minimum. No safe plan was found."
    elif output_row['affordability_status'] == 'affordable_now':
        output_row['decision_explanation'] = "The full requested amount can be safely paid today without breaching the minimum balance requirement."
    elif output_row['affordability_status'] == 'affordable_with_plan':
        output_row['decision_explanation'] = "The recommended plan completes the purchase while maintaining the required minimum balance."
    else:
        output_row['decision_explanation'] = "The purchase will become safe in the future based on projected cash flow."
        
    return output_row, is_verified, history

@st.cache_data(show_spinner=False)
def run_deterministic_engine_cached(req_dict, prof_dict, events_json, opts_json, msgs_json, imgs_json, rates_json):
    events_df = pd.DataFrame(json.loads(events_json))
    opts_df = pd.DataFrame(json.loads(opts_json))
    messages_df = pd.DataFrame(json.loads(msgs_json))
    images_df = pd.DataFrame(json.loads(imgs_json))
    rates_df = pd.DataFrame(json.loads(rates_json))
    return run_backend(req_dict, prof_dict, events_df, opts_df, messages_df, images_df, rates_df)

# ---------------------------------------------------------
# MAIN APP - SINGLE PAGE
# ---------------------------------------------------------

def main_dashboard():
    uuid_val = st.session_state.get('authenticated_uuid')
    dataset_user_id = st.session_state.get('dataset_user_id')
    
    if not uuid_val:
        login_ui()
        return
        
    inject_main_css()
    security_context = SecurityContext(uuid_val, dataset_user_id)
    
    # ------------------- SIDEBAR -------------------
    with st.sidebar:
        st.markdown('<div class="sidebar-logo"><div style="background:#157F87; color:white; width:36px; height:36px; display:flex; justify-content:center; align-items:center; border-radius:10px;">F</div> SafePay</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu-item active">⊞ Dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu-item">⇆ Transactions</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu-item">💼 Wallet</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu-item">🎯 Goals</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu-item">💰 Budget</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu-item">📈 Analytics</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu-item">⚙️ Settings</div>', unsafe_allow_html=True)
        
        st.markdown('<br><br><br>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-menu-item">❓ Help</div>', unsafe_allow_html=True)
        if st.button("🚪 Log out", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()
            
    # ------------------- TOP BAR -------------------
    tb1, tb2 = st.columns([3, 1], vertical_alignment="center")
    with tb1:
        st.markdown(f'<h1 style="font-size: 34px !important; font-weight: 800; margin-bottom: 4px !important;">Welcome back, {dataset_user_id}!</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color: #A3AED0; margin-top: 0; font-size:15px;">It is the best time to manage your finances</p>', unsafe_allow_html=True)
    with tb2:
        # Profile mock
        st.markdown(f'<div style="display:flex; justify-content:flex-end; align-items:center; gap:16px;">'
                    f'<div style="width: 44px; height: 44px; border-radius: 50%; background: #157F87; color: white; display:flex; justify-content:center; align-items:center; font-weight:bold; font-size:18px;">{dataset_user_id[:2].upper()}</div>'
                    f'<div style="font-weight:700; font-size:15px; color:#2B3674;">{dataset_user_id}<br><span style="color:#A3AED0; font-size:12px; font-weight:500;">Authenticated</span></div></div>', unsafe_allow_html=True)

    # ------------------- MAIN CONTENT -------------------
    user_requests = loader.get_user_requests(security_context)
    if not user_requests:
        st.info("No financial requests yet.")
        return

    # Action Bar
    st.markdown('<br>', unsafe_allow_html=True)
    ab1, ab2, ab3 = st.columns([2, 2, 1], vertical_alignment="center")
    with ab1:
        selected_request = st.selectbox("Active Request", user_requests, label_visibility="collapsed")
    with ab3:
        st.button("+ Add new request", type="primary", use_container_width=True)
        
    try:
        req_row, prof_row, events_df, opts_df, messages_df, images_df, rates_df = loader.get_request_context(selected_request, security_context)
        
        with st.spinner("Analyzing financial history and deterministic constraints..."):
            decision, is_verified, history = run_deterministic_engine_cached(
                req_row.to_dict(), prof_row.to_dict(), 
                events_df.to_json(orient="records"), opts_df.to_json(orient="records"),
                messages_df.to_json(orient="records"), images_df.to_json(orient="records"),
                rates_df.to_json(orient="records")
            )
            
        currency = prof_row['home_currency']
        decision['is_verified'] = is_verified
        
        bal = float(prof_row['current_available_balance'])
        min_bal = float(prof_row['minimum_balance_to_keep'])
        buffer = max(0.0, bal - min_bal)
        safe_to_pay = float(decision.get('amount_safe_to_pay', 0.0))
        
        # 4 Metric Cards
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            with st.container(border=True):
                st.markdown('<div class="fs-metric-label">Total balance <span class="icon">↗</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="fs-metric-value">{currency} {bal:,.2f}</div>', unsafe_allow_html=True)
                st.markdown('<div class="fs-metric-pill fs-pill-green">↑ Active</div> <span style="font-size:12px; color:#A3AED0; margin-left:8px;">vs minimum</span>', unsafe_allow_html=True)
        with m2:
            with st.container(border=True):
                st.markdown('<div class="fs-metric-label">Safe to Pay <span class="icon">↗</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="fs-metric-value">{currency} {safe_to_pay:,.2f}</div>', unsafe_allow_html=True)
                status_color = "fs-pill-green" if safe_to_pay > 0 else "fs-pill-red"
                st.markdown(f'<div class="fs-metric-pill {status_color}">{"↑ Approved" if safe_to_pay > 0 else "↓ Restricted"}</div> <span style="font-size:12px; color:#A3AED0; margin-left:8px;">for request</span>', unsafe_allow_html=True)
        with m3:
            with st.container(border=True):
                st.markdown('<div class="fs-metric-label">Minimum Required <span class="icon">↗</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="fs-metric-value">{currency} {min_bal:,.2f}</div>', unsafe_allow_html=True)
                st.markdown('<div class="fs-metric-pill fs-pill-neutral">→ Baseline</div> <span style="font-size:12px; color:#A3AED0; margin-left:8px;">fixed target</span>', unsafe_allow_html=True)
        with m4:
            with st.container(border=True):
                st.markdown('<div class="fs-metric-label">Available Buffer <span class="icon">↗</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="fs-metric-value">{currency} {buffer:,.2f}</div>', unsafe_allow_html=True)
                buffer_color = "fs-pill-green" if buffer > 0 else "fs-pill-red"
                st.markdown(f'<div class="fs-metric-pill {buffer_color}">{"↑ Safe" if buffer > 0 else "↓ Critical"}</div> <span style="font-size:12px; color:#A3AED0; margin-left:8px;">remaining cash</span>', unsafe_allow_html=True)
                
        # Middle Layout: Chart + Decision Input
        mid1, mid2 = st.columns([1.8, 1.2])
        with mid1:
            with st.container(border=True):
                st.markdown('<div style="display:flex; justify-content:space-between; margin-bottom: 16px;"><h4>Money flow</h4></div>', unsafe_allow_html=True)
                if history:
                    df_hist = pd.DataFrame(history)
                    fig_hist = go.Figure()
                    # Finset style: Bar charts for income/expense, but we have balance line. Let's make it a beautiful filled area chart
                    fig_hist.add_trace(go.Scatter(
                        x=df_hist['date'], y=df_hist['balance'], mode='lines', 
                        name='Projected Balance', 
                        line=dict(color="#157F87", width=4),
                        fill='tozeroy', fillcolor="rgba(21, 127, 135, 0.15)"
                    ))
                    fig_hist.add_hline(y=min_bal, line_dash="dash", line_color="#EE5D50")
                    
                    fig_hist.update_layout(
                        height=280, margin=dict(l=0, r=0, t=10, b=0),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(showgrid=False, tickfont=dict(color="#A3AED0")), 
                        yaxis=dict(showgrid=True, gridcolor="#F4F7FE", tickfont=dict(color="#A3AED0"))
                    )
                    st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
                    
        with mid2:
            with st.container(border=True):
                st.markdown('<h4>Purchase Request Analysis</h4>', unsafe_allow_html=True)
                
                # Ask user to reason why buy
                st.markdown('<span style="font-size:14px; font-weight:600; color:#2B3674;">Why do you need to make this purchase?</span>', unsafe_allow_html=True)
                user_reason = st.text_area("Reason", value=req_row['request_text'], height=68, label_visibility="collapsed")
                
                # In output format give answer with reason why wait or buy
                if st.button("Evaluate Request", type="primary", use_container_width=True):
                    st.success("Decision Processed.")
                    
                st.markdown('<hr style="margin: 16px 0; border-color: #F4F7FE;">', unsafe_allow_html=True)
                status = decision['affordability_status']
                rec_method = decision['recommended_payment_method'].replace('_', ' ').title()
                status_clr = "#05CD99" if "affordable" in status else "#EE5D50"
                
                st.markdown(f'<strong style="color: #A3AED0; font-size:12px; text-transform:uppercase;">Recommendation</strong><br>'
                            f'<div style="font-size:20px; font-weight:800; color: {status_clr}; margin-bottom:8px;">{rec_method}</div>', unsafe_allow_html=True)
                
                st.markdown(f'<strong style="color: #A3AED0; font-size:12px; text-transform:uppercase;">Reasoning</strong><br>'
                            f'<div style="font-size: 14px; color: #2B3674; font-weight:500; line-height:1.5;">{decision["decision_explanation"]}</div>', unsafe_allow_html=True)
                
                # Payment breakdown if applicable
                pp = decision.get('payment_plan', 'none')
                if pp != 'none' and pp:
                    parts = pp.split('|')
                    num_parts = len(parts)
                    start_date = parts[0].split(':')[0]
                    end_date = parts[-1].split(':')[0]
                    st.markdown(f'<div style="background: #F4F7FE; padding: 16px; border-radius: 12px; margin-top:16px;">'
                                f'<strong style="color: #2B3674; font-size:14px;">Payment Schedule</strong><br>'
                                f'<div style="font-size: 13px; color: #A3AED0; font-weight:600; margin-top:4px;">'
                                f'<span style="color:#157F87;">• Total parts:</span> {num_parts}<br>'
                                f'<span style="color:#157F87;">• Starts on:</span> {start_date}<br>'
                                f'<span style="color:#157F87;">• Completes on:</span> {end_date}'
                                f'</div></div>', unsafe_allow_html=True)

        # Bottom Layout: Recent Transactions + Saving Goals
        bot1, bot2 = st.columns([1.8, 1.2])
        with bot1:
            with st.container(border=True):
                st.markdown('<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;"><h4>Recent transactions</h4><div style="color:#A3AED0; font-weight:600; font-size:14px;">See all ></div></div>', unsafe_allow_html=True)
                if not events_df.empty:
                    display_df = events_df[['event_date', 'direction', 'amount', 'category', 'description']].sort_values('event_date', ascending=False).head(4)
                    
                    # Manual HTML table for custom FinSet look
                    html_table = '<table style="width:100%; text-align:left; border-collapse: collapse;">'
                    html_table += '<tr style="color:#A3AED0; font-size:12px; text-transform:uppercase; border-bottom: 1px solid #F4F7FE;"><th style="padding:12px 8px;">Date</th><th style="padding:12px 8px;">Amount</th><th style="padding:12px 8px;">Name</th><th style="padding:12px 8px;">Category</th></tr>'
                    
                    for _, row in display_df.iterrows():
                        amt_color = "#EE5D50" if row['direction'] == 'debit' else "#05CD99"
                        amt_sign = "-" if row['direction'] == 'debit' else "+"
                        html_table += f'<tr style="font-weight:600; font-size:14px; border-bottom: 1px solid #F4F7FE;">'
                        html_table += f'<td style="padding:16px 8px; color:#A3AED0;">{row["event_date"]}</td>'
                        html_table += f'<td style="padding:16px 8px; color:{amt_color};">{amt_sign}{currency} {row["amount"]}</td>'
                        html_table += f'<td style="padding:16px 8px; color:#2B3674;">{row["description"]}</td>'
                        html_table += f'<td style="padding:16px 8px; color:#A3AED0;">{row["category"]}</td>'
                        html_table += '</tr>'
                    html_table += '</table>'
                    st.markdown(html_table, unsafe_allow_html=True)
        with bot2:
            with st.container(border=True):
                st.markdown('<h4>Verification Goals</h4>', unsafe_allow_html=True)
                is_v = decision.get('is_verified', False)
                v_clr = "#157F87" if is_v else "#EE5D50"
                v_txt = "System Verified" if is_v else "Validation Failed"
                pct = "100%" if is_v else "15%"
                
                st.markdown(f'''
                <div style="margin-bottom: 24px; margin-top: 16px;">
                    <div style="display:flex; justify-content:space-between; font-size:14px; font-weight:700; color:#2B3674; margin-bottom:8px;">
                        <span>Backend Confidence</span> <span>{pct}</span>
                    </div>
                    <div style="background: #F4F7FE; border-radius: 12px; height: 12px; width: 100%; overflow: hidden;">
                        <div style="background: {v_clr}; height: 100%; width: {pct}; border-radius: 12px;"></div>
                    </div>
                    <div style="font-size:13px; color:#A3AED0; font-weight:600; margin-top:8px;">{v_txt}</div>
                </div>
                ''', unsafe_allow_html=True)
                
                # Add exports
                st.markdown('<hr style="margin: 24px 0; border-color: #F4F7FE;">', unsafe_allow_html=True)
                st.markdown('<div style="font-size:14px; font-weight:700; color:#2B3674; margin-bottom:12px;">Export Analysis Report</div>', unsafe_allow_html=True)
                dl_c1, dl_c2 = st.columns(2)
                with dl_c1:
                    pdf_data = generate_pdf(decision, selected_request)
                    st.download_button("📄 PDF", data=pdf_data, file_name=f"{selected_request}.pdf", mime="application/pdf", use_container_width=True)
                with dl_c2:
                    docx_data = generate_docx(decision, selected_request)
                    st.download_button("📝 DOCX", data=docx_data, file_name=f"{selected_request}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

    except PermissionError:
        st.error("Access denied.")
    except Exception as e:
        st.error(f"Error: {e}")
