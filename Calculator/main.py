import streamlit as st
import sys
from pathlib import Path
import importlib

# FIRST: Set page config before any other Streamlit commands
st.set_page_config(
    page_title="TariffPilot Calculator",
    layout="wide"
)

# Add very light blue background styling
st.markdown("""
<style>
    /* Main background - Very Light Blue */
    .stApp {
        background: linear-gradient(135deg, #e0f2fe 0%, #b3e5fc 100%);
        color: #333;
    }
    
    /* Sidebar styling - Light Blue */
    .css-1d391kg {
        background: linear-gradient(180deg, #e1f5fe 0%, #e0f2fe 100%);
    }
    
    /* Content container styling */
    .main .block-container {
        background: rgba(255, 255, 255, 0.9);
        color: #1a202c;
        border-radius: 15px;
        padding: 2rem;
        margin-top: 1rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }
    
    /* Header styling */
    h1, h2, h3 {
        color: #1565c0 !important;
        font-weight: 600;
    }
    
    /* Section headers with blue accent */
    .stMarkdown h1 {
        background: linear-gradient(90deg, #1565c0, #1976d2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Input field styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: #ffffff;
        border: 2px solid #e3f2fd;
        border-radius: 8px;
        color: #2d3748;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #1976d2;
        box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #1976d2, #2196f3);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(25, 118, 210, 0.2);
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #2196f3, #1976d2);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(25, 118, 210, 0.3);
    }
    
    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(45deg, #1565c0, #1976d2);
        box-shadow: 0 4px 15px rgba(21, 101, 192, 0.3);
    }
    
    /* Metric styling */
    .metric-container {
        background: linear-gradient(135deg, #f9f9f9 0%, #f5f5f5 100%);
        border-left: 4px solid #1976d2;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Alert styling */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid #1976d2;
    }
    
    /* Success message styling */
    .stSuccess {
        background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
        border-left: 4px solid #4caf50;
    }
    
    /* Warning message styling */
    .stWarning {
        background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
        border-left: 4px solid #ff9800;
    }
    
    /* Error message styling */
    .stError {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        border-left: 4px solid #f44336;
    }
    
    /* Info message styling */
    .stInfo {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 4px solid #1976d2;
    }
    
    /* Divider styling */
    .stDivider > div {
        background: linear-gradient(90deg, transparent, #bbdefb, transparent);
        height: 2px;
    }
    
    /* Table styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    }
    
    /* Caption styling */
    .stCaption {
        color: #666;
        font-style: italic;
    }
    
    /* Code block styling */
    .stCode {
        background: #f5f5f5;
        color: #333;
        border-radius: 8px;
        border-left: 4px solid #1976d2;
    }
    
    /* Header image container */
    .header-image {
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Add the current directory to path for importing components
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import and force reload to ensure we get the latest version
import components.calculator
importlib.reload(components.calculator)  # Force reload

from components.session_manager import initialize_session_state
from components.user_info import render_user_info_section, render_new_order_button
from components.hs_code_input import render_hs_code_input, lookup_duty_info
from components.hs_code_manager import add_hs_code_to_list, render_hs_code_list
from components.calculator import render_calculation_inputs, calculate_net_value
from components.results_display import render_calculation_results
from components.tariff_engine import render_tariff_decision_flow, get_calculated_tariffs

def main():
    # st.title("Tariff & Net Value Calculator")
    
    # Initialize session state
    initialize_session_state()

    # Add header image
    try:
        # Display header image
        header_image_path = current_dir / "assets" / "header-image.jpeg"
        if header_image_path.exists():
            st.image(str(header_image_path), use_container_width=True)
        else:
            # Fallback if image not found - show available files for debugging
            st.warning("Header image not found. Looking for files in assets folder...")
            assets_path = current_dir / "assets"
            if assets_path.exists():
                available_files = list(assets_path.glob("*"))
                st.write("Available files in assets folder:", [f.name for f in available_files])
            else:
                st.error("Assets folder not found")
    except Exception as e:
        st.error(f"Error loading header image: {e}")

   
    
    # User Information Section
    render_user_info_section()
    render_new_order_button()
    
    st.divider()
    
    # HS Code Input Section
    formatted_code, duty_percent, tariff_percent, goods_type = render_hs_code_input()
    
    # Auto-lookup duty if HS code is provided
    if formatted_code:
        success, auto_duty = lookup_duty_info(formatted_code)
        if success == 0:
            st.caption("🔄 Autofilled from HS code lookup")
            st.success(f"Auto-filled Duty: {auto_duty}%")
            duty_percent = auto_duty
        elif success == 1:
            st.warning(f"Cannot Autofill duty, Message contained: **{auto_duty}**")
        
        # Add/Clear buttons
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Add HS Code"):
                add_hs_code_to_list(formatted_code, duty_percent, tariff_percent, goods_type)
                st.session_state.form_counter += 1
                st.rerun()
        
        with col2:
            if st.button("Clear All HS Codes"):
                st.session_state.hs_code_list = []
                st.rerun()

     # Tariff Decision Engine
    if st.session_state.hs_code_list:
        st.divider()
        render_tariff_decision_flow()
    
    st.divider()
    
    # HS Code List Display
    render_hs_code_list()
    
    # Calculation Inputs
    invoice_value, brokerage, freight, mpf_percent, hmf_percent = render_calculation_inputs()
    
    # Calculate button
    if st.button("Calculate", type="primary"):
        if not st.session_state.hs_code_list:
            st.error("Please add at least one HS code to calculate duties and tariffs.")
        else:
            try:
                # Calculate total duty and tariff before passing to calculate_net_value
                total_tariff = get_calculated_tariffs()
                
                # Calculate total duty from HS codes list
                total_duty = sum(item['duty_percent'] for item in st.session_state.hs_code_list) if st.session_state.hs_code_list else 0
                
                # Get the freight mode from session state
                freight_mode = st.session_state.get('mode_of_delivery', 'Ocean')
                
                # Use the updated function with ISF support
                result = calculate_net_value(
                    invoice_value, brokerage, freight,
                    total_duty, mpf_percent, hmf_percent, total_tariff,
                    freight_mode=freight_mode
                )
                
                render_calculation_results(result, invoice_value, brokerage, freight, total_duty, total_tariff)
            except ValueError as e:
                st.error(f"Calculation error: {str(e)}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
    else:
        st.info("Please add at least one HS code to proceed with calculations.")

    # Simple, professional footer
    st.markdown("---")
    st.caption("Developed by NOVA Team | Version 1.0.0")
    st.caption("Sean Spencer & Shehbaz Patel")
    st.caption("© 2025 TariffCalculator. All rights reserved.")

if __name__ == "__main__":
    main()