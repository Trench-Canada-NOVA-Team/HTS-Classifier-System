import streamlit as st

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
    
    return {
        'net_value': net_value,
        'mpf_amount': mpf_amount,
        'hmf_amount': hmf_amount,
        'duty_amount': duty_amount,
        'tariff_amount': tariff_amount
    }

def render_calculation_inputs():
    """Render calculation input fields"""
    mode = st.selectbox("Mode of Delivery", ["Ocean Freight", "Air Freight", "Land", "Other"])
    
    invoice_value = st.number_input("Commercial Invoice Value (USD)")
    brokerage = st.number_input("Brokerage (USD)")
    freight = st.number_input("Total Pre-paid Freight (USD)")
    
    mpf_percent = st.number_input(
        "Merchandise Processing Fee (%)", 
        value=0.3464, 
        format="%.4f", 
        help="MPF is a fee charged by US Customs for processing imported goods. The current rate is 0.3464% of the value of the goods, with a minimum of $31.67 and a maximum of $614.35."
    )
    
    hmf_percent = 0.0
    if mode == "Ocean Freight":
        hmf_percent = st.number_input("Harbour Maintenance Fee (%)", value=0.125, format="%.3f")
    
    return invoice_value, brokerage, freight, mpf_percent, hmf_percent