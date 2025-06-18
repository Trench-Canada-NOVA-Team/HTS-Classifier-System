import streamlit as st
import pandas as pd
from .isf_fee_calculator import ISFFeeCalculator

def render_calculation_results(result, invoice_value, brokerage, freight, total_duty, total_tariff):
    """Render the calculation results and breakdown"""
    st.subheader("Calculation Breakdown")
    st.caption(f"**User:** {st.session_state.user_email} | **Order:** {st.session_state.order_number} | **Country:** {st.session_state.country_of_origin}")
    
    # # Add ISF fee display in a new row
    # freight_mode = st.session_state.get('mode_of_delivery', 'Ocean')
    # isf_fee = result.get('isf_fee', 0.0)
    
    # # Display ISF fee information at the top
    # st.info(f"🚛 **ISF Fee ({freight_mode}): ${isf_fee:,.2f}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Commercial Invoice Value", f"${invoice_value:,.2f}")
        st.metric("Brokerage", f"${brokerage:,.2f}")
        st.metric("Total Pre-paid Freight", f"${freight:,.2f}")
        st.metric("MPF + HMF", f"${result['mpf_amount'] + result['hmf_amount']:,.2f}")
    
    with col2:
        st.metric(f"Duty ({total_duty}%)", f"${result['duty_amount']:,.2f}", border=True)
        st.metric(f"Tariff ({total_tariff}%)", f"${result['tariff_amount']:,.2f}", border=True)
        st.metric("**Net Value**", f"${result['net_value']:,.2f}", border=True)
        # Add ISF fee metric
        # st.metric(f"ISF Fee ({freight_mode})", f"${isf_fee:,.2f}", border=True)

    # Detailed breakdown table - ADD ISF fee to the table
    breakdown_data = {
        'Component': [
            'Commercial Invoice Value', 
            'Brokerage', 
            'Total Pre-paid Freight', 
            # f'ISF Fee ({freight_mode})',  # ADD this line
            'MPF', 
            'HMF', 
            'Duty', 
            'Tariff', 
            'Net Value'
        ],
        'Amount ($)': [
            f"{invoice_value:,.2f}",
            f"{brokerage:,.2f}",
            f"{freight:,.2f}",
            # f"{isf_fee:,.2f}",  # ADD this line
            f"{result['mpf_amount']:,.2f}",
            f"{result['hmf_amount']:,.2f}",
            f"{result['duty_amount']:,.2f}",
            f"{result['tariff_amount']:,.2f}",
            f"{result['net_value']:,.2f}"
        ]
    }

    # Header with download option
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Detailed Breakdown")
    with col2:
        # Single download button
        breakdown_df = pd.DataFrame(breakdown_data)
        csv = breakdown_df.to_csv(index=False)
        
        st.download_button(
            label="Download",
            data=csv,
            file_name=f"calculation_{st.session_state.order_number}.csv",
            mime="text/csv"
        )
    
    # Display the table
    st.dataframe(breakdown_df, use_container_width=True)

