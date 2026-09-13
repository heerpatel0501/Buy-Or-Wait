import streamlit as st
import pandas as pd
import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal
import plotly.graph_objects as go
import traceback
import io

from streamlit_option_menu import option_menu
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
    p.drawString(50, 750, f"Affordability Status: {data_dict.get('affordability_status', '')}")
    p.drawString(50, 730, f"Recommended Method: {data_dict.get('recommended_payment_method', '')}")
    p.drawString(50, 710, f"Amount Safe to Pay: {data_dict.get('amount_safe_to_pay', '')}")
    p.drawString(50, 690, f"Spending Changes: {data_dict.get('spending_changes_needed', '')}")
    p.drawString(50, 670, f"Verified: {data_dict.get('is_verified', False)}")
    
    p.drawString(50, 640, "Decision Explanation:")
    textobject = p.beginText(50, 620)
    textobject.setFont("Helvetica", 10)
    import textwrap
    lines = textwrap.wrap(data_dict.get('decision_explanation', ''), width=90)
    for line in lines:
        textobject.textLine(line)
    p.drawText(textobject)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def generate_docx(data_dict, req_id):
    doc = Document()
    doc.add_heading(f"SafePay Financial Analysis Report", 0)
    doc.add_paragraph(f"Request ID: {req_id}")
    doc.add_paragraph(f"Affordability Status: {data_dict.get('affordability_status', '')}")
    doc.add_paragraph(f"Recommended Method: {data_dict.get('recommended_payment_method', '')}")
    doc.add_paragraph(f"Amount Safe to Pay: {data_dict.get('amount_safe_to_pay', '')}")
    doc.add_paragraph(f"Spending Changes: {data_dict.get('spending_changes_needed', '')}")
    doc.add_paragraph(f"Verified: {data_dict.get('is_verified', False)}")
    doc.add_heading("Decision Explanation", level=2)
    doc.add_paragraph(data_dict.get('decision_explanation', ''))
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# CUSTOM CSS FOR TALLY-STYLE FINTECH LOOK
# ---------------------------------------------------------
def inject_custom_css():
    theme = st.session_state.get('theme', 'light')
    if theme == 'dark':
        bg = "#111827"
        text = "#F9FAFB"
        card_bg = "#1F2937"
        subtext = "#9CA3AF"
        border = "#374151"
    else:
        bg = "#F6F5F0"
        text = "#2A323D"
        card_bg = "white"
        subtext = "#6C7A89"
        border = "#E2E8F0"

    st.markdown(f"""
    <style>
        /* Base styles */
        .stApp {{
            background-color: {bg};
            color: {text};
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background-color: #2A323D;
        }}
        [data-testid="stSidebar"] * {{
            color: #A0ABC0;
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color: #F6F5F0 !important;
        }}
        
        /* Premium Card Styling */
        .safepay-card {{
            background: {card_bg};
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
            border: 1px solid {border};
            margin-bottom: 24px;
            height: 100%;
        }}
        
        .dark-card {{
            background-color: #2A323D;
            border-radius: 16px;
            padding: 24px;
            color: white;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }}
        
        .section-header {{
            display: flex;
            align-items: center;
            font-size: 14px;
            font-weight: 700;
            color: {subtext};
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
            margin-top: 24px;
        }}
        
        .section-header span {{
            margin-right: 8px;
            font-size: 18px;
        }}
        
        .card-title {{
            font-size: 12px;
            font-weight: 700;
            color: {subtext};
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* Headings */
        h1, h2, h3, h4 {{ color: {text} !important; }}
        h1 {{ font-size: 28px !important; font-weight: 700 !important; }}
        h2 {{ font-size: 24px !important; font-weight: 600 !important; }}
        h3 {{ font-size: 20px !important; font-weight: 600 !important; }}
        
        /* Hide element blocks we don't want */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* Top nav badge */
        .top-badge {{
            background-color: #E6F0E0;
            color: #5D7B45;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
            margin-left: 16px;
            vertical-align: middle;
        }}
        
        /* Flex top bar fix */
        .topbar-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid {border};
            padding-bottom: 12px;
            margin-bottom: 24px;
            width: 100%;
        }}
        
        .header-title-area {{
            display: flex;
            align-items: center;
        }}
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
        <div style="padding: 40px; background-color: #2A323D; border-radius: 16px; color: white; height: 100%;">
            <div style="display: flex; align-items: center; margin-bottom: 24px;">
                <h1 style="color: white !important; margin: 0; font-size: 40px !important;">SafePay Financial</h1>
            </div>
            <h2 style="color: #A0ABC0 !important; font-weight: 400 !important; margin-bottom: 48px;">Know what you can safely afford before you pay.</h2>
            
            <div style="background: rgba(255,255,255,0.05); padding: 16px; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: center;">
                <span style="color: #93AD80; font-size: 20px; margin-right: 12px;">✓</span>
                <span style="font-size: 16px; font-weight: 500;">90-day affordability forecast</span>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 16px; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: center;">
                <span style="color: #93AD80; font-size: 20px; margin-right: 12px;">✓</span>
                <span style="font-size: 16px; font-weight: 500;">Payment-plan comparison</span>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 16px; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: center;">
                <span style="color: #93AD80; font-size: 20px; margin-right: 12px;">✓</span>
                <span style="font-size: 16px; font-weight: 500;">Verified financial evidence</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="safepay-card">
            <h2 style="margin-bottom: 8px;">Sign In</h2>
            <p style="color: #A0ABC0; margin-bottom: 32px; font-size: 14px;">Access your financial dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("User ID", placeholder="e.g. user_04 or user_32")
            password = st.text_input("Password", type="password", placeholder="password123")
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

def create_gauge(title, value, max_val, color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 12, 'color': '#A0ABC0'}},
        number = {'prefix': "$", 'font': {'size': 24, 'color': color, 'weight': 'bold'}},
        gauge = {
            'axis': {'range': [0, max_val], 'visible': False},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "#F1F5F9",
            'borderwidth': 0,
            'shape': "angular"
        }
    ))
    fig.update_layout(height=180, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'family': "Inter"})
    return fig

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
    
    # Sidebar
    with st.sidebar:
        st.markdown("<h2 style='color: white !important; font-size: 20px; font-weight: 700; margin-bottom: 20px;'>SafePay</h2>", unsafe_allow_html=True)
        
        active_nav = option_menu(
            menu_title=None,
            options=["Dashboard", "Purchase Requests", "User History", "Evidence", "Forecast & Simulation", "Verification"],
            icons=["house", "list-ul", "clock-history", "file-earmark-text", "graph-up", "shield-check"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#A0ABC0", "font-size": "16px"}, 
                "nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px", "color": "#A0ABC0", "--hover-color": "#334155"},
                "nav-link-selected": {"background-color": "#334155", "color": "white", "font-weight": "600"},
            }
        )

    # Top Toolbar
    t_col1, t_col2, t_col3, t_col4 = st.columns([4, 3, 0.5, 0.5], gap="small", vertical_alignment="center")
    with t_col1:
        st.markdown(f"<h2 style='margin: 0; font-size: 24px !important;'>{active_nav}</h2>", unsafe_allow_html=True)
    with t_col2:
        st.text_input("Search", placeholder="Search transactions, requests...", label_visibility="collapsed")
    with t_col3:
        with st.popover("⬇️"):
            st.markdown("Download Report")
            pdf_btn = st.empty()
            docx_btn = st.empty()
    with t_col4:
        with st.popover(f"{(dataset_user_id or 'U')[:2].upper()}"):
            theme_choice = st.selectbox("Theme", ["Light", "Dark"], index=0 if st.session_state.get('theme', 'light') == 'light' else 1)
            if theme_choice.lower() != st.session_state.get('theme', 'light'):
                st.session_state['theme'] = theme_choice.lower()
                st.rerun()
                
            is_demo_mode = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
            if is_demo_mode:
                new_user = st.text_input("Switch User (Demo Only)")
                if st.button("Switch"):
                    if new_user:
                        uuid_val = authenticate(new_user, os.environ.get("SAFEPAY_DEMO_PASSWORD", "password123"))
                        if uuid_val:
                            st.session_state['authenticated_uuid'] = uuid_val
                            st.session_state['dataset_user_id'] = new_user
                            st.rerun()
                        else:
                            st.error("Failed to switch")
            
            if st.button("Logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()
                
    st.markdown("<hr style='margin-top: 8px; margin-bottom: 24px; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
    
    user_requests = loader.get_user_requests(security_context)
    if not user_requests:
        st.markdown("""
        <div style="text-align: center; padding: 100px 20px;">
            <h2 style="margin-bottom: 8px;">No financial requests yet</h2>
            <p style="font-size: 16px; max-width: 500px; margin: 0 auto;">Once a purchase request is available, SafePay will analyze whether you can safely afford it.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown("<div style='margin-bottom: 16px;'>", unsafe_allow_html=True)
    selected_request = st.selectbox("Active Request Context", user_requests)
    st.markdown("</div>", unsafe_allow_html=True)
    
    try:
        req_row, prof_row, events_df, opts_df, messages_df, images_df, rates_df = loader.get_request_context(selected_request, security_context)
        
        with st.spinner("Verifying request and deterministic checks..."):
            decision, is_verified, history = run_deterministic_engine_cached(
                req_row.to_dict(), prof_row.to_dict(), 
                events_df.to_json(orient="records"), opts_df.to_json(orient="records"),
                messages_df.to_json(orient="records"), images_df.to_json(orient="records"),
                rates_df.to_json(orient="records")
            )
            
        currency = prof_row['home_currency']
        decision['is_verified'] = is_verified
        
        # Populate download buttons now that decision is generated
        try:
            pdf_data = generate_pdf(decision, selected_request)
            pdf_btn.download_button("Download PDF", data=pdf_data, file_name=f"{selected_request}_report.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e:
            pdf_btn.error("PDF generation failed.")
            
        try:
            docx_data = generate_docx(decision, selected_request)
            docx_btn.download_button("Download DOCX", data=docx_data, file_name=f"{selected_request}_report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        except Exception as e:
            docx_btn.error("DOCX generation failed.")
        
        # Route depending on active tab
        if active_nav == "Dashboard":
            # Calculate Income, Expenses, Net
            income_sum = pd.to_numeric(events_df[events_df['direction'] == 'credit']['amount']).sum()
            expense_sum = pd.to_numeric(events_df[events_df['direction'] == 'debit']['amount']).sum()
            net_saved = max(0, income_sum - expense_sum)
            max_gauge = max(income_sum, expense_sum) * 1.5 if max(income_sum, expense_sum) > 0 else 1000
            
            st.markdown('<div class="section-header">THE PRESENT</div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
                st.plotly_chart(create_gauge("INCOME", float(income_sum), float(max_gauge), "#EAA53B"), use_container_width=True)
                st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 10px; color: #A0ABC0; font-weight: 700; margin-top: -30px;'><span>ACTUAL</span><span>BUDGETED</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 14px; font-weight: 700;'><span>$0</span><span>${float(income_sum):,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with c2:
                st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
                st.plotly_chart(create_gauge("EXPENSES", float(expense_sum), float(max_gauge), "#93AD80"), use_container_width=True)
                st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 10px; color: #A0ABC0; font-weight: 700; margin-top: -30px;'><span>ACTUAL</span><span>BUDGETED</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 14px; font-weight: 700;'><span>$0</span><span>${float(expense_sum):,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with c3:
                st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
                st.plotly_chart(create_gauge("NET (SAVED)", float(net_saved), float(max_gauge), "#EAA53B"), use_container_width=True)
                st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 10px; color: #A0ABC0; font-weight: 700; margin-top: -30px;'><span>ACTUAL</span><span>BUDGETED</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 14px; font-weight: 700;'><span>$0</span><span>${float(net_saved):,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            # Second Row
            c_left, c_right = st.columns([2, 1])
            with c_left:
                st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
                st.markdown('<div style="display: flex; justify-content: space-between;"><span style="font-weight: 700;">Spending over time</span><span style="color: #A0ABC0; font-size: 12px;">Hover a column to see the breakdown</span></div>', unsafe_allow_html=True)
                
                dates = pd.to_datetime(events_df['event_date'])
                events_df['month'] = dates.dt.strftime('%b')
                monthly = events_df[events_df['direction'] == 'debit'].groupby('month')['amount'].sum().reindex(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']).fillna(0)
                
                fig2 = go.Figure(data=[
                    go.Bar(name='Expenses', x=monthly.index, y=monthly.values, marker_color='#D9827C')
                ])
                fig2.update_layout(barmode='stack', height=250, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with c_right:
                st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
                st.markdown('<div style="display: flex; justify-content: space-between; margin-bottom: 24px;"><span style="font-weight: 700;">Liquid net worth</span><span style="color: #93AD80; font-size: 12px; font-weight: 600;">All assets</span></div>', unsafe_allow_html=True)
                
                bal = float(prof_row['current_available_balance'])
                min_bal = float(prof_row['minimum_balance_to_keep'])
                
                st.markdown(f"""
                <div style="display: flex; justify-content: space-around; align-items: flex-end; height: 120px; margin-bottom: 24px;">
                    <div style="text-align: center;">
                        <div style="font-weight: 700; margin-bottom: 8px;">${bal:,.0f}</div>
                        <div style="width: 40px; height: 100px; background-color: #849C73; margin: 0 auto; border-radius: 4px 4px 0 0;"></div>
                        <div style="font-size: 10px; color: #A0ABC0; font-weight: 700; margin-top: 8px;">ASSETS</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-weight: 700; margin-bottom: 8px;">${min_bal:,.0f}</div>
                        <div style="width: 40px; height: 30px; background-color: #D9827C; margin: 0 auto; border-radius: 4px 4px 0 0;"></div>
                        <div style="font-size: 10px; color: #A0ABC0; font-weight: 700; margin-top: 8px;">MINIMUM</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
            st.markdown('<div class="section-header">THE FUTURE</div>', unsafe_allow_html=True)
            
            status_text = "AFFORDABLE" if decision['affordability_status'] in ["affordable_now", "affordable_with_plan"] else "NOT AFFORDABLE"
            color_theme = "#EAA53B" if status_text == "AFFORDABLE" else "#D9827C"
            
            st.markdown(f"""
            <div class="dark-card">
                <div style="font-size: 12px; font-weight: 700; color: #A0ABC0; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">YOUR PLAN IS</div>
                <div style="font-size: 42px; font-weight: 700; color: {color_theme}; margin-bottom: 16px;">{status_text.lower()}</div>
                <p style="color: #A0ABC0; font-size: 16px; max-width: 600px; line-height: 1.5; margin-bottom: 24px;">
                    {decision['decision_explanation']}
                </p>
                <div style="display: flex; gap: 16px;">
                    <div style="background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 20px; font-size: 14px;">
                        <span style="color: #A0ABC0;">Safe to pay: </span><span style="font-weight: 700;">{currency} {decision['amount_safe_to_pay']}</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 20px; font-size: 14px;">
                        <span style="color: #A0ABC0;">Method: </span><span style="font-weight: 700;">{decision['recommended_payment_method'].replace('_', ' ').title()}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if history:
                df_hist = pd.DataFrame(history)
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=df_hist['date'], y=df_hist['balance'], mode='lines',
                    line=dict(color=color_theme, width=3), fill='tozeroy', fillcolor=f'rgba({234 if color_theme=="#EAA53B" else 217}, {165 if color_theme=="#EAA53B" else 130}, {59 if color_theme=="#EAA53B" else 124}, 0.1)', name='Projected Balance'
                ))
                fig3.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    height=200, margin=dict(l=0, r=0, t=10, b=0),
                    xaxis=dict(showgrid=False, showticklabels=True, color="#A0ABC0"),
                    yaxis=dict(showgrid=False, showticklabels=False)
                )
                st.plotly_chart(fig3, use_container_width=True)
                
            st.markdown('</div>', unsafe_allow_html=True)
            
        elif active_nav == "Purchase Requests":
            st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">All Purchase Requests</div>', unsafe_allow_html=True)
            all_req_data = []
            for r_id in user_requests:
                r_ctx, _, _, _, _, _, _ = loader.get_request_context(r_id, security_context)
                all_req_data.append({
                    "Request ID": r_id,
                    "Type": r_ctx['request_type'].title(),
                    "Amount": f"{currency} {r_ctx['requested_amount']}",
                    "Desired Date": r_ctx['desired_completion_date'] or "None"
                })
            st.dataframe(pd.DataFrame(all_req_data), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        elif active_nav == "User History":
            st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Transaction History</div>', unsafe_allow_html=True)
            st.dataframe(events_df, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        elif active_nav == "Evidence":
            st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Extracted Context & Evidence</div>', unsafe_allow_html=True)
            if not messages_df.empty:
                st.markdown("### Messages")
                st.dataframe(messages_df, use_container_width=True)
            else:
                st.info("No message evidence associated with this user.")
                
            if not images_df.empty:
                st.markdown("### Images")
                st.dataframe(images_df, use_container_width=True)
            else:
                st.info("No image evidence associated with this user.")
            st.markdown('</div>', unsafe_allow_html=True)
            
        elif active_nav == "Forecast & Simulation":
            st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">90-Day Simulation Engine</div>', unsafe_allow_html=True)
            if history:
                df_hist = pd.DataFrame(history)
                fig_sim = go.Figure()
                fig_sim.add_trace(go.Scatter(x=df_hist['date'], y=df_hist['balance'], mode='lines', name='Balance'))
                fig_sim.update_layout(title="Projected Balance Timeline", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_sim, use_container_width=True)
                st.dataframe(df_hist, use_container_width=True)
            else:
                st.info("No simulation history available.")
            st.markdown('</div>', unsafe_allow_html=True)
            
        elif active_nav == "Verification":
            st.markdown('<div class="safepay-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Independent Verification Status</div>', unsafe_allow_html=True)
            
            if is_verified:
                st.success("✅ The financial recommendation successfully passed all deterministic backend verification checks.")
            else:
                st.error("❌ The backend verifier caught a safety condition and rolled back to a safe baseline.")
            
            st.markdown("---")
            
            # Additional details logic
            st.markdown(f"**Decision Reasoning**: {decision['decision_explanation']}")
            
            # Amount Chart
            safe_amt = float(decision['amount_safe_to_pay'])
            req_amt = float(req_row['requested_amount'])
            
            fig_amt = go.Figure(data=[
                go.Bar(name='Safe to Pay', x=['Amount'], y=[safe_amt], marker_color='#93AD80'),
                go.Bar(name='Requested', x=['Amount'], y=[req_amt], marker_color='#EAA53B')
            ])
            fig_amt.update_layout(barmode='group', title="Amount Safe vs Requested", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_amt, use_container_width=True)
            
            # 90-day trajectory vs minimum balance
            if history:
                df_hist = pd.DataFrame(history)
                min_bal = float(prof_row['minimum_balance_to_keep'])
                
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Scatter(x=df_hist['date'], y=df_hist['balance'], mode='lines', name='Projected Balance', line=dict(color="#4A90E2", width=3)))
                fig_hist.add_hline(y=min_bal, line_dash="dash", line_color="red", annotation_text="Minimum Allowed Balance")
                
                fig_hist.update_layout(title="90-Day Forecast & Minimum Balance Threshold", height=350, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_hist, use_container_width=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

    except PermissionError:
        st.error("Access denied. Resource ownership violation.")
    except Exception as e:
        st.error(f"SafePay could not complete this analysis safely. Error: {e}")

if __name__ == "__main__":
    main_dashboard()
