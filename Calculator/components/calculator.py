import streamlit as st
import sys
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

def calculate_net_value(invoice_value, brokerage, freight, duty_percent, mpf_percent, hmf_percent, tariff_percent):
    """Calculate net value and fee breakdowns"""
    duty = duty_percent / 100
    mpf = mpf_percent / 100
    hmf = hmf_percent / 100
    tariff = tariff_percent / 100
    
    numerator = (invoice_value - brokerage - freight)
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
    
    # Prepare the result
    result = {
        'net_value': net_value,
        'mpf_amount': mpf_amount,
        'hmf_amount': hmf_amount,
        'duty_amount': duty_amount,
        'tariff_amount': tariff_amount,
        'total_amount': invoice_value + mpf_amount + hmf_amount + duty_amount + tariff_amount
    }
    
    # Logging block - silent operation
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
        
        # Prepare calculation data for logging
        calculation_data = {
            'user_email': st.session_state.get('user_email', ''),
            'order_number': st.session_state.get('order_number', ''),
            'country_of_origin': st.session_state.get('country_of_origin', ''),
            'hs_tariff_code': hs_codes_string,
            'duty': total_duty_calculated,
            'tariff': total_tariff_calculated,  
            'mode_of_delivery': st.session_state.get('mode_of_delivery', ''),
            'commercial_invoice_value': float(invoice_value),
            'brokerage': float(brokerage),
            'total_prepaid_freight': float(freight),
            'merchandise_processing_fee': float(mpf_percent),
            'harbour_maintenance_fee': float(hmf_percent),
            'calculated_total': float(result.get('total_amount', 0)),
            'net_value': float(result.get('net_value', 0)),
            'notes': f"HS Codes Count: {len(hs_code_list)}"
        }
        
        # Log the calculation
        logger.log_calculation(calculation_data)
        
    except Exception:
        # Silent fail - don't disrupt user experience
        pass
    
    return result

def render_calculation_inputs():
    """Render calculation input fields"""
    st.subheader("💰 Financial Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        mode = st.selectbox(
            "Mode of Delivery", 
            ["Ocean Freight", "Air Freight", "Land", "Other"],
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
        
        brokerage = st.number_input(
            "Brokerage (USD)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            help="Customs brokerage fees"
        )
    
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
        
        hmf_percent = 0.0
        if mode == "Ocean Freight":
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