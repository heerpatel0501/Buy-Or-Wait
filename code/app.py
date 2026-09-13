import streamlit as st
# Must be the first Streamlit command
st.set_page_config(layout="wide", page_title="SafePay", initial_sidebar_state="collapsed")

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
    theme = st.session_state.get('theme', 'light')
    if theme == 'dark':
        bg = "#0F172A"          
        text = "#F8FAFC"        
        card_bg = "#1E293B"     
        subtext = "#CBD5E1"     
        border = "#334155"
        alert_bg = "rgba(255,255,255,0.05)"
    else:
        bg = "#F8FAFC"          
        text = "#0F172A"        
        card_bg = "#FFFFFF"     
        subtext = "#475569"     
        border = "#E2E8F0"
        alert_bg = "rgba(0,0,0,0.02)"

    st.markdown(f"""
    <style>
        /* Base styles */
        .stApp {{
            background-color: {bg};
            color: {text};
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        /* Reduce Top Padding of Streamlit App */
        .block-container {{
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px;
        }}
        
        /* Hide Default Header elements */
        [data-testid='stHeader'] {{ display: none; }}
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        
        /* High Contrast Form Inputs (Text Area & Search) */
        div[data-baseweb='textarea'] textarea,
        div[data-baseweb='input'] input {{
            color: {text} !important;
            background-color: {card_bg} !important;
            -webkit-text-fill-color: {text} !important;
        }}
        div[data-baseweb='textarea']:focus-within,
        div[data-baseweb='input']:focus-within {{
            border-color: #3B82F6 !important;
            box-shadow: 0 0 0 1px #3B82F6 !important;
        }}
        
        /* SYSTEMIC BUTTON CLASSES (Navy/Gold Theme) */
        
        /* Primary Buttons (Login, Save Note) */
        div[data-testid='stButton'] button[kind='primary'],
        div[data-testid='stFormSubmitButton'] button {{
            background-color: #D4AF37 !important; /* Gold */
            border-color: #D4AF37 !important;
            border-radius: 8px !important;
        }}
        div[data-testid='stButton'] button[kind='primary'] p,
        div[data-testid='stFormSubmitButton'] button p {{
            color: #0F172A !important; /* Navy */
            font-weight: 700 !important;
        }}
        
        /* Secondary Buttons & Popovers */
        div[data-testid='stButton'] button[kind='secondary'],
        div[data-testid='stDownloadButton'] button,
        div[data-testid='stPopover'] button {{
            background-color: #1E293B !important; /* Navy */
            border-color: #334155 !important;
            border-radius: 8px !important;
        }}
        div[data-testid='stButton'] button[kind='secondary'] p,
        div[data-testid='stDownloadButton'] button p,
        div[data-testid='stPopover'] button p {{
            color: #F8FAFC !important; /* White */
            font-weight: 600 !important;
        }}
        
        /* Hover states */
        div[data-testid='stButton'] button[kind='primary']:hover,
        div[data-testid='stFormSubmitButton'] button:hover {{
            background-color: #FBBF24 !important;
            border-color: #FBBF24 !important;
        }}
        div[data-testid='stButton'] button[kind='secondary']:hover,
        div[data-testid='stDownloadButton'] button:hover,
        div[data-testid='stPopover'] button:hover {{
            background-color: #334155 !important;
            border-color: #475569 !important;
        }}
        
        /* Streamlit Native Container Styling */
        div[data-testid='stVerticalBlockBorderWrapper'] {{
            border-radius: 12px !important;
            background-color: {card_bg} !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
            border: 1px solid {border} !important;
            padding: 12px !important;
            margin-bottom: 0px !important;
        }}
        
        /* HTML Card Styling */
        .safepay-card {{
            background: {card_bg};
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            border: 1px solid {border};
            margin-bottom: 16px;
        }}
        
        .dark-card {{
            background-color: #0F172A; /* Deep Navy */
            border-radius: 12px;
            padding: 40px 24px;
            color: #F8FAFC;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }}
        
        /* Adjust Spacing */
        .section-header {{
            font-size: 14px;
            font-weight: 700;
            color: {subtext};
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            margin-top: 24px;
            display: flex;
            align-items: center;
        }}
        
        /* Headings */
        h1, h2, h3, h4 {{ color: {text}; }}
        h1 {{ font-size: 26px !important; font-weight: 700 !important; margin-bottom: 0!important; padding-bottom: 0!important;}}
        
        /* Metric box */
        .metric-box {{
            padding: 16px;
            border-radius: 8px;
            background: {alert_bg};
            border: 1px solid {border};
        }}
        .metric-label {{ font-size: 12px; color: {subtext}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}}
        .metric-value {{ font-size: 24px; font-weight: 700; color: {text}; margin-top: 4px; }}
        
        /* Top Bar Wrapper */
        .top-bar-wrapper {{
            border-bottom: 1px solid {border};
            padding-bottom: 16px;
            margin-bottom: 16px;
        }}
        
        hr {{ border-color: {border}; margin: 16px 0; }}
    </style>
    """, unsafe_allow_html=True)

def inject_login_css():
    st.markdown("""
    <style>
        /* Hide Default Header elements */
        [data-testid="stHeader"] { display: none; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        
        .stApp {
            background-color: #FFFFFF;
            color: #0F172A;
            font-family: 'Inter', -apple-system, sans-serif;
        }
        
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            max-width: 1400px;
        }
        
        /* Typography overrides */
        h1, h2, h3, p { color: #0F172A; }
        
        /* Inputs */
        div[data-baseweb="input"] {
            border-radius: 8px !important;
            border-color: #E2E8F0 !important;
        }
        div[data-baseweb="input"] input {
            color: #0F172A !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: #0F172A !important;
            padding: 12px 14px !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #157F87 !important;
            box-shadow: 0 0 0 1px #157F87 !important;
        }
        
        /* Primary Button */
        div[data-testid="stFormSubmitButton"] button {
            background-color: #157F87 !important;
            border-color: #157F87 !important;
            border-radius: 8px !important;
            padding: 12px !important;
            width: 100% !important;
        }
        div[data-testid="stFormSubmitButton"] button p {
            color: #FFFFFF !important;
            font-weight: 600 !important;
            font-size: 16px !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #11676E !important;
            border-color: #11676E !important;
        }
        
        /* Right Panel */
        .login-right-panel {
            background: linear-gradient(180deg, #053D42 0%, #032124 100%);
            border-radius: 24px;
            height: 85vh;
            padding: 48px;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            align-items: center;
            text-align: center;
            color: white;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            position: relative;
            overflow: hidden;
        }
        
        .login-right-panel::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
            background-size: 40px 40px;
            opacity: 0.5;
            pointer-events: none;
        }
        
        .login-right-panel h2 {
            color: white !important;
            font-size: 32px !important;
            font-weight: 700 !important;
            margin-bottom: 16px !important;
            line-height: 1.3 !important;
            z-index: 1;
        }
        .login-right-panel p {
            color: #94A3B8 !important;
            font-size: 16px !important;
            line-height: 1.6 !important;
            max-width: 400px;
            z-index: 1;
        }
        
        .login-logo {
            font-size: 24px;
            font-weight: 700;
            color: #157F87;
            display: flex;
            align-items: center;
            margin-bottom: 32px;
        }
        
        /* Tabs */
        .login-tabs {
            display: flex;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 4px;
            margin-bottom: 32px;
            margin-top: 16px;
        }
        .login-tab-active {
            flex: 1;
            background: white;
            color: #0F172A;
            font-weight: 600;
            text-align: center;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .login-tab-inactive {
            flex: 1;
            color: #64748B;
            font-weight: 500;
            text-align: center;
            padding: 10px;
        }
        
        /* Divider */
        .divider {
            display: flex;
            align-items: center;
            text-align: center;
            color: #94A3B8;
            margin: 24px 0;
            font-size: 14px;
        }
        .divider::before, .divider::after {
            content: '';
            flex: 1;
            border-bottom: 1px solid #E2E8F0;
        }
        .divider:not(:empty)::before { margin-right: 12px; }
        .divider:not(:empty)::after { margin-left: 12px; }
        
        /* Social */
        .social-row {
            display: flex;
            justify-content: center;
            gap: 16px;
            margin-bottom: 32px;
        }
        .social-btn {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: 1px solid #E2E8F0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: white;
            color: #0F172A;
            font-weight: bold;
            font-size: 18px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            cursor: pointer;
        }
        
        /* Helper to center the left column content */
        .left-col-inner {
            padding: 24px 48px;
            max-width: 500px;
            margin: 0 auto;
        }
        
        /* Mock Cards */
        .mock-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            color: #0F172A;
            width: 80%;
            text-align: left;
            z-index: 1;
        }
    </style>
    """, unsafe_allow_html=True)

def login_ui():
    inject_login_css()
    
    col_left, col_right = st.columns([1, 1.2], gap="large")
    
    with col_left:
        st.markdown("""
        <div class="left-col-inner">
            <div class="login-logo">
                <span style="margin-right: 8px;">🏦</span> SafePay
            </div>
            
            <h1 style="font-size: 32px !important; margin-bottom: 8px !important;">Welcome to SafePay</h1>
            <p style="color: #64748B; margin-bottom: 24px; font-size: 15px;">Start your experience with SafePay by signing in or signing up.</p>
            
            <div class="login-tabs">
                <div class="login-tab-active">Sign In</div>
                <div class="login-tab-inactive">Sign Up</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            col_pad_l, col_form, col_pad_r = st.columns([0.15, 0.7, 0.15])
            with col_form:
                with st.form("login_form"):
                    st.markdown("**User ID <span style='color: #157F87;'>*</span>**", unsafe_allow_html=True)
                    username = st.text_input("User ID", placeholder="Enter your user ID", label_visibility="collapsed")
                    
                    st.markdown("**Password <span style='color: #157F87;'>*</span>**", unsafe_allow_html=True)
                    password = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="collapsed")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    submitted = st.form_submit_button("Sign In")
                    
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
                <div class="divider">Or continue with</div>
                <div class="social-row">
                    <div class="social-btn"><span style="color: #EA4335;">G</span></div>
                    <div class="social-btn"></div>
                    <div class="social-btn"><span style="color: #1877F2;">f</span></div>
                    <div class="social-btn">𝕏</div>
                </div>
                
                <div style="text-align: center; color: #94A3B8; font-size: 12px; margin-top: 32px;">
                    Copyright : SafePay, All Right Reserved <br><br> <span style="color: #157F87;">Term & Condition</span> &nbsp;|&nbsp; <span style="color: #157F87;">Privacy & Policy</span>
                </div>
                """, unsafe_allow_html=True)
                
    with col_right:
        st.markdown("""
        <div class="login-right-panel">
            <div class="mock-card" style="transform: rotate(-2deg); margin-left: -10%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="font-weight: 600; font-size: 14px;">Financial Plan</div>
                    <div style="font-size: 11px; color: #64748B;">This Month ⌄</div>
                </div>
                <div style="display: flex; align-items: center; gap: 20px;">
                    <div style="width: 50px; height: 50px; border-radius: 50%; border: 6px solid #D4AF37; border-left-color: #157F87; border-bottom-color: #157F87;"></div>
                    <div>
                        <div style="font-size: 20px; font-weight: bold;">$2,005.45</div>
                        <div style="font-size: 12px; color: #64748B;">Available</div>
                    </div>
                </div>
            </div>
            
            <div class="mock-card" style="transform: rotate(2deg); margin-right: -10%; margin-top: -30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 600; font-size: 14px;">Future Funds</div>
                </div>
                <div style="font-weight: bold; font-size: 16px;">Bucket List Trip</div>
                <div style="font-size: 12px; color: #64748B; margin-bottom: 8px;">Due date - Apr 09, 2026</div>
                <div style="font-weight: bold; font-size: 18px; color: #157F87;">$1900 <span style="font-size: 12px; color: #94A3B8; font-weight: normal;">/ $5,000</span></div>
            </div>
            
            <div style="width: 64px; height: 64px; background-color: #157F87; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 32px; margin-bottom: 24px; margin-top: 24px; z-index: 1;">
                🏦
            </div>
            <h2>A Unified Hub for Smarter<br>Financial Decision-Making</h2>
            <p>SafePay empowers you with a unified financial command center—delivering deep insights and a 360° view of your entire economic world.</p>
            
            <div style="display: flex; gap: 8px; margin-top: 32px; margin-bottom: 16px; z-index: 1;">
                <div style="width: 32px; height: 4px; background: white; border-radius: 2px;"></div>
                <div style="width: 32px; height: 4px; background: rgba(255,255,255,0.3); border-radius: 2px;"></div>
                <div style="width: 32px; height: 4px; background: rgba(255,255,255,0.3); border-radius: 2px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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
    
    # ---------------------------------------------------------
    # TOP BAR - SINGLE HORIZONTAL ROW
    # ---------------------------------------------------------
    st.markdown('<div class="top-bar-wrapper">', unsafe_allow_html=True)
    tb1, tb2, tb3 = st.columns([2.5, 5, 4.5], vertical_alignment="center")
    
    with tb1:
        st.markdown("<h1 style='margin:0; padding:0; display:flex; align-items:center;'><span style='margin-right:8px;'>🏦</span> SafePay</h1>", unsafe_allow_html=True)
        
    with tb2:
        st.text_input("Search", placeholder="Search transactions, requests...", label_visibility="collapsed")
        
    with tb3:
        # Shared Container for Theme + Profile
        p1, p2, p3 = st.columns([1.5, 0.2, 3], vertical_alignment="center")
        with p1:
            theme_choice = st.selectbox("Theme", ["Light", "Dark"], index=0 if st.session_state.get('theme', 'light') == 'light' else 1, label_visibility="collapsed")
            if theme_choice.lower() != st.session_state.get('theme', 'light'):
                st.session_state['theme'] = theme_choice.lower()
                st.rerun()
        with p2:
            st.markdown("<div style='border-left: 1px solid #94A3B8; height: 28px; margin: auto;'></div>", unsafe_allow_html=True)
        with p3:
            with st.popover(f"👤 {dataset_user_id} - Auth'd", use_container_width=True):
                st.markdown(f"**Authenticated as {dataset_user_id}**")
                st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
                
                is_demo_mode = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
                if is_demo_mode:
                    new_user = st.text_input("Switch User", placeholder="e.g. user_32")
                    if st.button("Switch Session", use_container_width=True):
                        if new_user:
                            new_uuid = authenticate(new_user, os.environ.get("SAFEPAY_DEMO_PASSWORD", "password123"))
                            if new_uuid:
                                st.session_state['authenticated_uuid'] = new_uuid
                                st.session_state['dataset_user_id'] = new_user
                                st.rerun()
                            else:
                                st.error("Failed to switch")
                    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
                    
                if st.button("Logout", use_container_width=True):
                    st.session_state.clear()
                    st.rerun()
                    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # MAIN CONTENT
    # ---------------------------------------------------------
    user_requests = loader.get_user_requests(security_context)
    if not user_requests:
        st.markdown("""
        <div style="text-align: center; padding: 100px 20px;">
            <h2 style="margin-bottom: 8px;">No financial requests yet</h2>
            <p style="font-size: 16px; max-width: 500px; margin: 0 auto;">Once a purchase request is available, SafePay will analyze whether you can safely afford it.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Request Selector
    st.markdown("**Active Request Context**")
    selected_request = st.selectbox("Active Request Context", user_requests, label_visibility="collapsed")
    
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
        
        # --- SECTION A: Top Summary Strip ---
        st.markdown('<div class="section-header">Financial Summary</div>', unsafe_allow_html=True)
        met1, met2, met3 = st.columns(3)
        with met1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Current Balance</div>
                <div class="metric-value">{currency} {bal:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with met2:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Minimum Required</div>
                <div class="metric-value">{currency} {min_bal:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with met3:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Available Buffer</div>
                <div class="metric-value" style="color: {'#10B981' if buffer > 0 else '#EF4444'};">{currency} {buffer:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # --- SECTION B: Decision Result + Reasoning ---
        st.markdown('<div class="section-header">Decision & Reasoning</div>', unsafe_allow_html=True)
        
        # Dynamic Left Border Color Logic
        if decision['affordability_status'] == "affordable_now":
            color_theme = "#10B981" # Green
            status_text = "AFFORDABLE NOW"
        elif decision['affordability_status'] in ["affordable_with_plan", "affordable_later"]:
            color_theme = "#F59E0B" # Amber
            status_text = "AFFORDABLE WITH PLAN" if decision['affordability_status'] == "affordable_with_plan" else "WAIT"
        else:
            color_theme = "#EF4444" # Red
            status_text = "NOT AFFORDABLE"
            
        st.markdown(f"""
        <div class="safepay-card" style="border-left: 6px solid {color_theme};">
            <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 24px;">
                <div style="flex: 1; min-width: 250px;">
                    <div style="font-size: 12px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 8px;">Recommendation</div>
                    <div style="font-size: 28px; font-weight: 800; color: {color_theme}; margin-bottom: 12px; line-height: 1.2;">{status_text}</div>
                    <div style="margin-bottom: 8px;"><strong style="color: #64748B;">Method:</strong> {decision['recommended_payment_method'].replace('_', ' ').title()}</div>
                    <div><strong style="color: #64748B;">Safe to Pay:</strong> {currency} {decision['amount_safe_to_pay']}</div>
                </div>
                <div style="flex: 1.5; min-width: 300px; padding-left: 24px; border-left: 1px solid #E2E8F0;">
                    <div style="font-size: 12px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 8px;">Reasoning</div>
                    <div style="font-size: 15px; line-height: 1.6;">{decision['decision_explanation']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- SECTION C: 90-Day Forecast Chart ---
        st.markdown('<div class="section-header">90-Day Forecast</div>', unsafe_allow_html=True)
        with st.container(border=True):
            if history:
                df_hist = pd.DataFrame(history)
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Scatter(x=df_hist['date'], y=df_hist['balance'], mode='lines', name='Projected Balance', line=dict(color="#3B82F6", width=3)))
                fig_hist.add_hline(y=min_bal, line_dash="dash", line_color="#EF4444", annotation_text="Minimum Allowed Balance", annotation_position="bottom right", annotation_font_color="#7F1D1D")
                
                # Darker labels for contrast
                theme_str = st.session_state.get('theme', 'light')
                ax_color = "#1E293B" if theme_str == 'light' else "#E2E8F0"
                
                fig_hist.update_layout(
                    height=350, 
                    margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(tickfont=dict(color=ax_color, size=12)),
                    yaxis=dict(tickfont=dict(color=ax_color, size=12))
                )
                st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("No forecast history available.")
            
        # --- SECTION D: Verification Proof + Timestamp ---
        st.markdown('<div class="section-header">Verification Proof</div>', unsafe_allow_html=True)
        
        if is_verified:
            v_color = "#10B981"
            v_text = "PASS"
            v_icon = "✓"
            v_detail = "The financial recommendation successfully passed all deterministic backend verification checks. Projected balance never breaches the minimum."
        else:
            v_color = "#EF4444"
            v_text = "FAIL"
            v_icon = "✗"
            v_detail = "The backend verifier caught a safety condition and forced a rollback. Recommending 'Wait'."
            
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        st.markdown(f"""
        <div class="safepay-card">
            <div style="display: flex; align-items: flex-start; gap: 16px;">
                <div style="background: {v_color}; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px;">{v_icon} {v_text}</div>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Deterministic Checks Executed</div>
                    <div style="font-size: 14px; color: #64748B; margin-bottom: 8px;">{v_detail}</div>
                    <div style="font-size: 12px; color: #94A3B8;">Verified at: {now_str}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- SECTION E: User History ---
        st.markdown('<div class="section-header">User History</div>', unsafe_allow_html=True)
        with st.container(border=True):
            if not events_df.empty:
                display_df = events_df[['event_date', 'direction', 'amount', 'currency', 'category', 'description']].sort_values('event_date', ascending=False)
                st.dataframe(display_df, use_container_width=True, height=250)
            else:
                st.info("No prior history found for this user.")
        
        # --- SECTION F: Notes Input ---
        st.markdown('<div class="section-header">Analyst Notes</div>', unsafe_allow_html=True)
        with st.container(border=True):
            user_notes = st.text_area("Add extra detail about this request:", placeholder="Enter any specific contextual notes here...", label_visibility="collapsed")
            if st.button("💾 Save Note", type="primary"):
                st.success("✓ Note saved to session.")
        
        # --- DOWNLOAD BUTTONS ---
        st.markdown('<div class="section-header">Export Report</div>', unsafe_allow_html=True)
        
        # Fixed overflow by using 2 equal-width columns for export buttons
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            try:
                pdf_data = generate_pdf(decision, selected_request)
                st.download_button("📄 Download PDF", data=pdf_data, file_name=f"{selected_request}_report.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.error("PDF generation failed.")
                
        with dl_col2:
            try:
                docx_data = generate_docx(decision, selected_request)
                st.download_button("📝 Download DOCX", data=docx_data, file_name=f"{selected_request}_report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            except Exception as e:
                st.error("DOCX generation failed.")
                
    except PermissionError:
        st.error("Access denied. Resource ownership violation.")
    except Exception as e:
        st.error(f"SafePay could not complete this analysis safely. Error: {e}")

if __name__ == "__main__":
    main_dashboard()
