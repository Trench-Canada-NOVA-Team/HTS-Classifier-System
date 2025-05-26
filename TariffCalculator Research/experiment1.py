import streamlit as st

def calculate_net_value(
    invoice_value,
    brokerage,
    freight,
    duty_percent,
    mpf_percent,
    hmf_percent,
    tariff_percent
):
    # Convert percentages to decimals
    duty = duty_percent / 100
    mpf = mpf_percent / 100
    hmf = hmf_percent / 100
    tariff = tariff_percent / 100

    # Apply formula
    numerator = invoice_value - brokerage - freight
    denominator = 1 + duty + mpf + hmf + tariff

    # Avoid division by zero
    if denominator == 0:
        raise ValueError("Denominator is zero, check the input percentages.")

    net_value = numerator / denominator
    tariff_cost = net_value * tariff
    return net_value, tariff_cost


st.title(" Tariff & Net Value Calculator")

st.subheader(" Input Values")
invoice_value = st.number_input("Invoice Value (USD)")
brokerage = st.number_input("Brokerage (USD)")
freight = st.number_input("Freight (USD)")

duty_percent = st.number_input("Duty (%)")
mpf_percent = st.number_input("MPF (%)", value=0.3464, format="%.4f")
hmf_percent = st.number_input("HMF (%)", value=0.125, format="%.3f")
tariff_percent = st.number_input("Tariff (%)")

if st.button("Calculate"):
    try:
        net_value, tariff_cost = calculate_net_value(
            invoice_value, brokerage, freight,
            duty_percent, mpf_percent, hmf_percent, tariff_percent
        )
        st.success(f" Net Value: ${net_value:,.2f}")
        st.success(f" Tariff Cost: ${tariff_cost:,.2f}")
    except ValueError as e:
        st.error(str(e))
