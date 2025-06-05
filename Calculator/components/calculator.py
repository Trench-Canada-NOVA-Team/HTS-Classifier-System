import streamlit as st
import sys
import pandas as pd
from .isf_fee_calculator import ISFFeeCalculator
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
try:
    from utils.simple_logger import SimpleLogger
except:
    class SimpleLogger:
        def log_calculation(self, data): pass

MAX_MPF = 634.62
MIN_MPF = 32.71

def calculate_net_value(invoice_value, brokerage, freight, duty_percent, mpf_percent, hmf_percent, tariff_percent, freight_mode=None):
    """Calculate net value and fee breakdowns with ISF integration"""
    duty = duty_percent / 100
    mpf = mpf_percent / 100
    hmf = hmf_percent / 100
    tariff = tariff_percent / 100
    
    # Get ISF fee if freight mode is provided
    isf_fee = 0.0
    if freight_mode:
        isf_fee = ISFFeeCalculator.get_total_fee(freight_mode)
    
    # Updated numerator to include ISF fee
    numerator = (invoice_value - brokerage - freight )
    denominator = (1 + duty + mpf + hmf + tariff)

    if denominator == 0:
        raise ValueError("Denominator cannot be zero")

    net_value = round((numerator / denominator), 2)
    
    # Calculate individual fee amounts
    mpf_amount = net_value * mpf
    hmf_amount = net_value * hmf
    duty_amount = net_value * duty
    tariff_amount = net_value * tariff

    # Check MPF limits
    if mpf_amount < MIN_MPF:
        mpf_amount = MIN_MPF
    elif mpf_amount > MAX_MPF:
        mpf_amount = MAX_MPF
    
    # Prepare the result with ISF fee included
    result = {
        'net_value': net_value,
        'mpf_amount': mpf_amount,
        'hmf_amount': hmf_amount,
        'duty_amount': duty_amount,
        'tariff_amount': tariff_amount,
        'isf_fee': isf_fee,  # Add ISF fee to results
        'total_amount': invoice_value + mpf_amount + hmf_amount + duty_amount + tariff_amount + isf_fee
    }
    
    # Update logging to include ISF fee
    try:
        logger = SimpleLogger()
        
        # Extract HS codes from session state
        hs_code_list = st.session_state.get('hs_code_list', [])
        hs_codes_string = ""
        
        if hs_code_list and len(hs_code_list) > 0:
            # Create detailed HS code string
            hs_details = []
            for item in hs_code_list:
                if isinstance(item, dict):
                    code = str(item.get('hs_code', 'Unknown'))
                    duty_val = item.get('duty_percent', 0)
                    tariff_val = item.get('tariff_percent', 0)
                    hs_details.append(f"{code}(D:{duty_val}%,T:{tariff_val}%)")
                else:
                    hs_details.append(str(item))
            
            hs_codes_string = " | ".join(hs_details)
        else:
            hs_codes_string = "No HS codes added"
        
        # Calculate totals from HS code list
        total_duty_calculated = sum([float(item.get('duty_percent', 0)) for item in hs_code_list if isinstance(item, dict)])
        total_tariff_calculated = sum([float(item.get('tariff_percent', 0)) for item in hs_code_list if isinstance(item, dict)])
        
        # Prepare calculation data for logging with ISF fee
        calculation_data = {
            'user_email': st.session_state.get('user_email', ''),
            'order_number': st.session_state.get('order_number', ''),
            'country_of_origin': st.session_state.get('country_of_origin', ''),
            'hs_tariff_code': hs_codes_string,
            'duty': total_duty_calculated,
            'tariff': total_tariff_calculated,  
            'mode_of_delivery': freight_mode or st.session_state.get('mode_of_delivery', ''),
            'commercial_invoice_value': float(invoice_value),
            'brokerage': float(brokerage),
            'total_prepaid_freight': float(freight),
            'merchandise_processing_fee': float(mpf_percent),
            'harbour_maintenance_fee': float(hmf_percent),
            'isf_fee': float(isf_fee),  # Add ISF fee to logging
            'calculated_total': float(result.get('total_amount', 0)),
            'net_value': float(result.get('net_value', 0)),
            'notes': f"HS Codes Count: {len(hs_code_list)}, ISF Fee: ${isf_fee:.2f}"
        }
        
        # Log the calculation
        logger.log_calculation(calculation_data)
        
    except Exception:
        # Silent fail - don't disrupt user experience
        pass
    
    return result

def render_calculation_inputs():
    """Render calculation input fields"""
    st.subheader("Financial Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Replace the existing mode selectbox with ISF-enabled options
        mode = st.selectbox(
            "Mode of Delivery", 
            ISFFeeCalculator.get_available_modes(),  # Use ISF module instead of hardcoded list
            help="Select the shipping method for your goods"
        )
        
        # Store mode in session state for logging
        st.session_state.mode_of_delivery = mode
        
        invoice_value = st.number_input(
            "Commercial Invoice Value (USD)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            help="Total value of goods as shown on commercial invoice"
        )
        
        # Auto-fill ISF fee into brokerage field
        isf_fee = ISFFeeCalculator.get_total_fee(mode) if mode else 0.0
        
        brokerage = st.number_input(
            "Brokerage (USD)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=isf_fee,  # Auto-fill with ISF fee
            help=f"Customs brokerage fees (Auto-filled with {mode} ISF fee: ${isf_fee:.2f})"
        )
        
        # # Show ISF fee breakdown as caption
        # if mode and isf_fee > 0:
        #     isf_data = ISFFeeCalculator.calculate_isf_fee(mode)
        #     if isf_data['isf_fee'] > 0:
        #         st.caption(f"🔄 Auto-filled: Base Fee ${isf_data['base_fee']:.2f} + ISF Filing ${isf_data['isf_fee']:.2f} = ${isf_data['total']:.2f}")
        #     else:
        #         st.caption(f"🔄 Auto-filled: {mode} Processing Fee ${isf_data['base_fee']:.2f}")
    
    with col2:
        freight = st.number_input(
            "Total Pre-paid Freight (USD)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            help="Total shipping costs paid in advance"
        )
        
        mpf_percent = st.number_input(
            "Merchandise Processing Fee (%)", 
            value=0.3464, 
            min_value=0.0,
            max_value=100.0,
            step=0.0001,
            format="%.4f", 
            help="MPF is a fee charged by US Customs for processing imported goods. Current rate is 0.3464%"
        )
        
        # Update HMF logic to use ISF module mode names
        hmf_percent = 0.0
        if mode == "Ocean":  # Changed from "Ocean Freight" to "Ocean"
            hmf_percent = st.number_input(
                "Harbour Maintenance Fee (%)", 
                value=0.125, 
                min_value=0.0,
                max_value=100.0,
                step=0.001,
                format="%.3f",
                help="HMF applies to ocean freight shipments. Current rate is 0.125%"
            )
    
    return invoice_value, brokerage, freight, mpf_percent, hmf_percent