import streamlit as st
from json_search import find_duty_by_hscode
import json
import os
import re

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
raw_hs_code = st.text_input("HS Tariff Code", max_chars=13, help="Enter the HS Tariff Code (up to 13 characters).")

allowed_chars_pattern = r"^[0-9. ]*$"

# Check the pattern
if raw_hs_code and not re.match(allowed_chars_pattern, raw_hs_code):
    st.error("Invalid Format: HS Code can only contain digits and periods (e.g., 1234.56.78.90)")
elif raw_hs_code not in (None, ""):
    st.success("Input format is valid.")

# Function to autoformat HS code to XXXX.XX.XX.XX
def format_hs_code(code):
    digits = ''.join(filter(str.isdigit, code))[:12]  # remove non-digits, limit to 12 chars
    sections = [digits[i:j] for i, j in [(0, 4), (4, 6), (6, 8), (8, 10)] if i < len(digits)]
    return '.'.join(sections)

if raw_hs_code:
    formatted_code = format_hs_code(raw_hs_code)
    st.info(f"Inputted HS Code: **{formatted_code}**\n")
else:
    formatted_code = None

# Attempt to autofill duty information based on HS code

auto_duty = 0.00
success = None

if formatted_code:
    try:
        # Retrieve path to combined json file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.abspath(os.path.join(script_dir, '..', 'Data', 'combined_data.json'))

        # the data file and defining data tuple
        with open(data_path, "r") as f:
            data = json.load(f)
        duty_info = find_duty_by_hscode(data, formatted_code)
        print(duty_info)

        # retrieving success code and duty percentage
        success = duty_info.get("general")[0]
        auto_duty = duty_info.get("general")[1]

        # success code 0 means duty was found and is a float
        # success code 1 means duty was found but is a string (e.g. a message)
        if success == 0:
            st.success(f"Auto-filled Duty: {auto_duty}%")
        elif success == 1:
            st.warning(f"Cannot Autofill duty, Message contained: **{auto_duty}** (Note: Message may be truncated)")
    except ValueError as e:
        st.error(str(e))

# Mode of delivery dropdown
mode = st.selectbox("Mode of Delivery", ["Ocean Freight", "Air Freight", "Land", "Other"])

invoice_value = st.number_input("Invoice Value (USD)")
brokerage = st.number_input("Brokerage (USD)")
freight = st.number_input("Freight (USD)")

if success == 0:
    duty_percent = st.number_input("Duty (%)", value=auto_duty, format="%.2f")
    st.caption("🔄 Autofilled from HS code lookup")
else:
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
