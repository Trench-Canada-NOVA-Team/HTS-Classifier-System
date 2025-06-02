import streamlit as st
from json_search import find_duty_by_hscode
import json
import os
import re
import pandas as pd

MAX_MPF = 634.62
MIN_MPF = 32.71

# Initialize session state for HS code list and form counter
if 'hs_code_list' not in st.session_state:
    st.session_state.hs_code_list = []
if 'form_counter' not in st.session_state:
    st.session_state.form_counter = 0
# Add persistent user info (separate from form counter)
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'order_number' not in st.session_state:
    st.session_state.order_number = ""
if 'country_of_origin' not in st.session_state:
    st.session_state.country_of_origin = ""

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
    numerator = (invoice_value - brokerage - freight)
    denominator = (1 + duty + mpf + hmf + tariff)

    # Avoid division by zero
    if denominator == 0:
        raise ValueError("Denominator is zero, check the input percentages.")

    net_value = round((numerator / denominator), 2)
    # Calculate individual fee amounts
    mpf_amount = net_value * mpf
    hmf_amount = net_value * hmf
    duty_amount = net_value * duty
    tariff_amount = net_value * tariff

    # Check MPF against maximum and minimum values allowed by US Customs
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

st.title("🚢 Tariff & Net Value Calculator")

# User Information Section - PERSISTENT (not tied to form_counter)
st.subheader("👤 User Information")
col1, col2 = st.columns(2)

with col1:
    user_email = st.text_input(
        "User Email", 
        value=st.session_state.user_email,  # Use session state value
        placeholder="user@company.com",
        key="persistent_user_email"  # Fixed key, not tied to form_counter
    )
    # Update session state when input changes
    st.session_state.user_email = user_email

with col2:
    order_number = st.text_input(
        "Order Number", 
        value=st.session_state.order_number,  # Use session state value
        placeholder="ORD-123456",
        key="persistent_order_number"  # Fixed key, not tied to form_counter
    )
    # Update session state when input changes
    st.session_state.order_number = order_number

# Email validation
if user_email and "@" not in user_email:
    st.error("Please enter a valid email address")
elif user_email:
    st.success("✅ Valid email format")

# Add a "Start New Order" button to reset user info when needed
if st.button("🔄 Start New Order", help="Clear user info and start fresh"):
    st.session_state.user_email = ""
    st.session_state.order_number = ""
    st.session_state.country_of_origin = ""
    st.session_state.hs_code_list = []
    st.session_state.form_counter = 0
    st.rerun()

st.divider()  # Visual separator

st.subheader("📦 Input Values")


country_of_origin = st.selectbox(
    "Country of Origin",
    options=["", "Canada", "China", "US", "Italy", "France", "Germany"],
    index=["", "Canada", "China", "US", "Italy", "France", "Germany"].index(st.session_state.country_of_origin) if st.session_state.country_of_origin in ["", "Canada", "China", "US", "Italy", "France", "Germany"] else 0,
    help="Select the country where the goods were manufactured or produced",
    key="persistent_country_of_origin"  # Fixed key, not tied to form_counter
)
# Update session state when input changes
st.session_state.country_of_origin = country_of_origin

# Only HS Code inputs reset with form_counter
raw_hs_code = st.text_input(
    "HS Tariff Code", 
    max_chars=13, 
    help="Enter the HS Tariff Code (up to 13 characters).",
    key=f"raw_hs_code_{st.session_state.form_counter}"  # This resets
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
    key=f"duty_percent_{st.session_state.form_counter}"  # This resets
)

tariff_percent = st.number_input(
    "Tariff (%)",
    format="%.2f",
    help="Enter tariff percentage",
    key=f"tariff_percent_{st.session_state.form_counter}"  # This resets
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
                # Validate required fields before adding
                if not st.session_state.user_email:  # Use session state
                    st.error("⚠️ Please enter user email before adding to list")
                elif not st.session_state.order_number:  # Use session state
                    st.error("⚠️ Please enter order number before adding to list")
                elif "@" not in st.session_state.user_email:  # Use session state
                    st.error("⚠️ Please enter a valid email address")
                elif not st.session_state.country_of_origin:  # Use session state
                    st.error("⚠️ Please select a country of origin")
                else:
                    # Check if HS code already exists in list
                    existing_codes = [item['hs_code'] for item in st.session_state.hs_code_list]
                    if formatted_code not in existing_codes:
                        duty_value = auto_duty if success == 0 else duty_percent
                        st.session_state.hs_code_list.append({
                            'hs_code': formatted_code,
                            'duty_percent': duty_value,
                            'tariff_percent': tariff_percent,
                            'status': 'Auto-filled' if success == 0 else 'Manual',
                            'user_email': st.session_state.user_email,  # Use session state
                            'order_number': st.session_state.order_number,  # Use session state
                            'country_of_origin': st.session_state.country_of_origin  # Use session state
                        })
                        st.success(f"Added {formatted_code} from {st.session_state.country_of_origin} to list for order {st.session_state.order_number}")
                
                        # Reset only the HS code form fields, NOT user info or country
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
    
    # Show current order information
    st.info(f"📧 **User:** {st.session_state.user_email} | 📋 **Order:** {st.session_state.order_number} | 🌍 **Country:** {st.session_state.country_of_origin}")
    
    # Create DataFrame for display - exclude user info columns but show country for reference
    df = pd.DataFrame(st.session_state.hs_code_list)
    
    # Select only the columns we want to display
    display_columns = ['hs_code', 'duty_percent', 'tariff_percent', 'status']
    df_display = df[display_columns]
    
    print(st.session_state.hs_code_list)
    
    # Add edit functionality
    edited_df = st.data_editor(
        df_display,  # Use the filtered dataframe
        column_config={
            "hs_code": "HS Code",
            "duty_percent": st.column_config.NumberColumn(
                "Duty %",
                min_value=0.0,
                max_value=100.0,
                step=0.01,
                format="%.2f"
            ),
            "tariff_percent": st.column_config.NumberColumn(
                "Tariff %",
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
    
    # Update session state with edited data, preserving user info
    for i, edited_row in edited_df.iterrows():
        if i < len(st.session_state.hs_code_list):
            # Update only the editable fields, keep user info intact
            st.session_state.hs_code_list[i]['hs_code'] = edited_row['hs_code']
            st.session_state.hs_code_list[i]['duty_percent'] = edited_row['duty_percent']
            st.session_state.hs_code_list[i]['tariff_percent'] = edited_row['tariff_percent']
            st.session_state.hs_code_list[i]['status'] = edited_row['status']
            # Country of origin is already consistent across all entries
            st.session_state.hs_code_list[i]['country_of_origin'] = st.session_state.country_of_origin
    
    # Calculate and display total duty
    total_tariff = sum(float(row['tariff_percent']) for row in st.session_state.hs_code_list if isinstance(row['tariff_percent'], (int, float)))
    total_duty = sum(float(row['duty_percent']) for row in st.session_state.hs_code_list if isinstance(row['duty_percent'], (int, float)))
    st.metric("Total Duty for Bill", f"{total_duty:.2f}%")
    st.metric("Total Tariff for Bill", f"{total_tariff:.2f}%")

st.divider()  # Visual separator

mode = st.selectbox("Mode of Delivery", ["Ocean Freight", "Air Freight", "Land", "Other"])

invoice_value = st.number_input("Commercial Invoice Value (USD)")
brokerage = st.number_input("Brokerage (USD)")
freight = st.number_input("Total Pre-paid Freight (USD)")

mpf_percent = st.number_input("Merchandise Processing Fee (%)", value=0.3464, format="%.4f", help="MPF is a fee charged by US Customs for processing imported goods. The current rate is 0.3464% of the value of the goods, with a minimum of \$31.67 and a maximum of \$614.35. (19 U.S.C. § 58c(a(a)(9)(B)(i);(b)(8)(A)(i))")

# Show HMF only if mode is Ocean Freight
if mode == "Ocean Freight":
    hmf_percent = st.number_input("Harbour Maintenance Fee (%)", value=0.125, format="%.3f")
else:
    hmf_percent = 0.0


if st.button("Calculate"):
    if not st.session_state.hs_code_list:
        st.error("Please add at least one HS code to calculate duties and tariffs.")
    else:
        try:
            result = calculate_net_value(
                invoice_value, brokerage, freight,
                total_duty, mpf_percent, hmf_percent, total_tariff
            )
            
            # Display breakdown with persistent user information
            st.subheader("📊 Calculation Breakdown")
            st.caption(f"**User:** {st.session_state.user_email} | **Order:** {st.session_state.order_number} | **Country:** {st.session_state.country_of_origin}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Commercial Invoice Value", f"${invoice_value:,.2f}")
                st.metric("Brokerage", f"${brokerage:,.2f}")
                st.metric("Total Pre-paid Freight", f"${freight:,.2f}")
                st.metric("MPF + HMF", f"${result['mpf_amount'] + result['hmf_amount']:,.2f}")
            
            with col2:
                st.metric(f"Duty **({total_duty}%)**", f"${result['duty_amount']:,.2f}", border=True)
                st.metric(f"Tariff **({total_tariff}%)**", f"${result['tariff_amount']:,.2f}", border=True)
                st.metric("**Net Value**", f"${result['net_value']:,.2f}", border=True)
            
            # Additional breakdown table
            breakdown_data = {
                'Component': ['Commercial Invoice Value', 'Brokerage', 'Total Pre-paid Freight', 'MPF', 'HMF', 'Duty', 'Tariff', 'Net Value'],
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
