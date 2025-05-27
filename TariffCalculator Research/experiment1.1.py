import streamlit as st
from json_search import find_duty_by_hscode
import json
import os
import re
import pandas as pd

# Initialize session state for HS code list and form counter
if 'hs_code_list' not in st.session_state:
    st.session_state.hs_code_list = []
if 'form_counter' not in st.session_state:
    st.session_state.form_counter = 0

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
    # Calculate individual fee amounts
    mpf_amount = net_value * mpf
    hmf_amount = net_value * hmf
    duty_amount = net_value * duty
    tariff_amount = net_value * tariff
    
    return {
        'net_value': net_value,
        'mpf_amount': mpf_amount,
        'hmf_amount': hmf_amount,
        'duty_amount': duty_amount,
        'tariff_amount': tariff_amount
    }

st.title(" Tariff & Net Value Calculator")

st.subheader(" Input Values")

# Input for HS Tariff Code - use form_counter to reset
raw_hs_code = st.text_input(
    "HS Tariff Code", 
    max_chars=13, 
    help="Enter the HS Tariff Code (up to 13 characters).",
    key=f"raw_hs_code_{st.session_state.form_counter}"
)

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

duty_percent = st.number_input(
    "Duty (%)",
    format="%.2f",
    help="Enter duty percentage manually if not autofilled",
    key=f"duty_percent_{st.session_state.form_counter}"
)

tariff_percent = st.number_input(
    "Tariff (%)",
    format="%.2f",
    help="Enter tariff percentage",
    key=f"tariff_percent_{st.session_state.form_counter}"
)

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
            st.caption("🔄 Autofilled from HS code lookup")
            st.success(f"Auto-filled Duty: {auto_duty}%")
            # Update the duty_percent with auto_duty value
            duty_percent = auto_duty
        elif success == 1:
            st.warning(f"Cannot Autofill duty, Message contained: **{auto_duty}** (Note: Message may be truncated)")

        # Add button to add HS code to list
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Add to List", key="add_hs"):
                # Check if HS code already exists in list
                existing_codes = [item['hs_code'] for item in st.session_state.hs_code_list]
                if formatted_code not in existing_codes:
                    duty_value = auto_duty if success == 0 else duty_percent
                    st.session_state.hs_code_list.append({
                        'hs_code': formatted_code,
                        'duty_percent': duty_value,
                        'tariff_percent': tariff_percent,
                        'status': 'Auto-filled' if success == 0 else 'Manual'
                    })
                    st.success(f"Added {formatted_code} to list")
            
                    # Reset the form by incrementing the counter
                    st.session_state.form_counter += 1
                    st.rerun()
                else:
                    st.warning("HS Code already in list")
        
        with col2:
            if st.button("Clear List", key="clear_list"):
                st.session_state.hs_code_list = []
                st.success("List cleared")

    except ValueError as e:
        st.error(str(e))

# Display HS Code List
if st.session_state.hs_code_list:
    st.subheader("HS Code List")
    
    # Create DataFrame for display
    df = pd.DataFrame(st.session_state.hs_code_list)
    
    # Add edit functionality
    edited_df = st.data_editor(
        df,
        column_config={
            "hs_code": "HS Code",
            "duty_percent": st.column_config.NumberColumn(
                "Duty %",
                min_value=0.0,
                max_value=100.0,
                step=0.01,
                format="%.2f"
            ),
            "status": "Status"
        },
        num_rows="dynamic",
        use_container_width=True
    )
    
    # Update session state with edited data
    st.session_state.hs_code_list = edited_df.to_dict('records')
    
    # Calculate and display total duty
    total_tariff = sum(float(row['tariff_percent']) for row in st.session_state.hs_code_list if isinstance(row['tariff_percent'], (int, float)))
    total_duty = sum(float(row['duty_percent']) for row in st.session_state.hs_code_list if isinstance(row['duty_percent'], (int, float)))
    st.metric("Total Duty for Bill", f"{total_duty:.2f}%")
    st.metric("Total Tariff for Bill", f"{total_tariff:.2f}%")

mode = st.selectbox("Mode of Delivery", ["Ocean Freight", "Air Freight", "Land", "Other"])

invoice_value = st.number_input("Invoice Value (USD)")
brokerage = st.number_input("Brokerage (USD)")
freight = st.number_input("Freight (USD)")

mpf_percent = st.number_input("Merchandise Processing Fee (%)", value=0.3464, format="%.4f")

# Show HMF only if mode is Ocean Freight
if mode == "Ocean Freight":
    hmf_percent = st.number_input("Harbour Maintenance Fee (%)", value=0.125, format="%.3f")
else:
    hmf_percent = 0.0


if st.button("Calculate"):
    try:
        result = calculate_net_value(
            invoice_value, brokerage, freight,
            total_duty, mpf_percent, hmf_percent, total_tariff
        )
        
        # Display breakdown in the requested format
        st.subheader("📊 Calculation Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Invoice Value", f"${invoice_value:,.2f}")
            st.metric("Brokerage", f"${brokerage:,.2f}")
            st.metric("Freight", f"${freight:,.2f}")
            st.metric("MPF (HMF)", f"${result['mpf_amount'] + result['hmf_amount']:,.2f}")
        
        with col2:
            st.metric(f"Duty **({total_duty}%)**", f"${result['duty_amount']:,.2f}", border=True)
            st.metric(f"Tariff **({total_tariff}%)**", f"${result['tariff_amount']:,.2f}", border=True)
            st.metric("**Net Value**", f"${result['net_value']:,.2f}", border=True)
        
        # Additional breakdown table
        breakdown_data = {
            'Component': ['Invoice Value', 'Brokerage', 'Freight', 'MPF', 'HMF', 'Duty', 'Tariff', 'Net Value'],
            'Amount ($)': [
                f"{invoice_value:,.2f}",
                f"{brokerage:,.2f}",
                f"{freight:,.2f}",
                f"{result['mpf_amount']:,.2f}",
                f"{result['hmf_amount']:,.2f}",
                f"{result['duty_amount']:,.2f}",
                f"{result['tariff_amount']:,.2f}",
                f"{result['net_value']:,.2f}"
            ]
        }
        
        st.subheader("📋 Detailed Breakdown")
        breakdown_df = pd.DataFrame(breakdown_data)
        st.dataframe(breakdown_df, use_container_width=True)
        
    except ValueError as e:
        st.error(str(e))
    except NameError:
        st.error("Please add at least one HS code to calculate duties and tariffs.")
