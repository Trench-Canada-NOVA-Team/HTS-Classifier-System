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

# Input for HS Tariff Code
raw_hs_code = st.text_input("HS Tariff Code", max_chars=12)

# Function to autoformat HS code to XXXX.XX.XX.XX
def format_hs_code(code):
    digits = ''.join(filter(str.isdigit, code))[:12]  # remove non-digits, limit to 12 chars
    sections = [digits[i:j] for i, j in [(0, 4), (4, 6), (6, 8), (8, 10)] if i < len(digits)]
    return '.'.join(sections)

if raw_hs_code:
    formatted_code = format_hs_code(raw_hs_code)
    st.info(f"Formatted HS Code: **{formatted_code}**")

# Mode of delivery dropdown
mode = st.selectbox("Mode of Delivery", ["Ocean Freight", "Air Freight", "Land", "Other"])

invoice_value = st.number_input("Invoice Value (USD)")
brokerage = st.number_input("Brokerage (USD)")
freight = st.number_input("Freight (USD)")

duty_percent = st.number_input("Duty (%)")
tariff_percent = st.number_input("Tariff (%)")

mpf_percent = st.number_input("Merchandise Processing Fee (%)", value=0.3464, format="%.4f")

# Show HMF only if mode is Ocean Freight
if mode == "Ocean Freight":
    hmf_percent = st.number_input("Harbour Maintenance Fee (%)", value=0.125, format="%.3f")
else:
    hmf_percent = 0.0


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
