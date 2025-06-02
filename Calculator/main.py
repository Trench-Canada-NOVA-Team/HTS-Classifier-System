import streamlit as st
import sys
from pathlib import Path

# Add the current directory to path for importing components
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from components.session_manager import initialize_session_state
from components.user_info import render_user_info_section, render_new_order_button
from components.hs_code_input import render_hs_code_input, lookup_duty_info
from components.hs_code_manager import add_hs_code_to_list, render_hs_code_list
from components.calculator import render_calculation_inputs, calculate_net_value
from components.results_display import render_calculation_results

def main():
    st.set_page_config(
        page_title="TariffPilot Calculator",
        page_icon="🚢",
        layout="wide"
    )
    
    st.title("🚢 Tariff & Net Value Calculator")
    
    # Initialize session state
    initialize_session_state()
    
    # User Information Section
    render_user_info_section()
    render_new_order_button()
    
    st.divider()
    
    # HS Code Input Section
    formatted_code, duty_percent, tariff_percent = render_hs_code_input()
    
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
            if st.button("Add to List", key="add_hs"):
                if add_hs_code_to_list(formatted_code, duty_percent, tariff_percent):
                    st.rerun()
        
        with col2:
            if st.button("Clear List", key="clear_list"):
                st.session_state.hs_code_list = []
                st.success("List cleared")
                st.rerun()
    
    # Display HS Code List
    total_duty, total_tariff = render_hs_code_list()
    
    st.divider()
    
    # Calculation Inputs
    invoice_value, brokerage, freight, mpf_percent, hmf_percent = render_calculation_inputs()
    
    # Calculate button
    if st.button("Calculate", type="primary"):
        if not st.session_state.hs_code_list:
            st.error("Please add at least one HS code to calculate duties and tariffs.")
        else:
            try:
                result = calculate_net_value(
                    invoice_value, brokerage, freight,
                    total_duty, mpf_percent, hmf_percent, total_tariff
                )
                render_calculation_results(result, invoice_value, brokerage, freight, total_duty, total_tariff)
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Calculation error: {str(e)}")

if __name__ == "__main__":
    main()