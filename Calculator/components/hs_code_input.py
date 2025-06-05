import streamlit as st
import re
import os
import json
import sys
from pathlib import Path

def validate_hs_code_format(raw_hs_code):
    """Validate HS code format"""
    allowed_chars_pattern = r"^[0-9. ]*$"
    
    if raw_hs_code and not re.match(allowed_chars_pattern, raw_hs_code):
        st.error("Invalid Format: HS Code can only contain digits and periods (e.g., 1234.56.78.90)")
        return False
    elif raw_hs_code not in (None, ""):
        st.success("Input format is valid.")
        return True
    return True

def format_hs_code_local(code):
    """Local format HS code function to avoid import issues"""
    if not code:
        return None
    
    digits = ''.join(filter(str.isdigit, code))[:12]
    sections = [digits[i:j] for i, j in [(0, 4), (4, 6), (6, 8), (8, 10)] if i < len(digits)]
    return '.'.join(sections)

def lookup_duty_info(formatted_code):
    """Lookup duty information for HS code"""
    try:
        # Import here to avoid circular imports
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utils.json_search import find_duty_by_hscode
        
        # Navigate to the Data folder from Calculator/components/
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'Data', 'combined_data.json'))
        
        if not os.path.exists(data_path):
            st.warning("Data file not found. Please check if combined_data.json exists in the Data folder.")
            return 1, "Data file not found"
        
        with open(data_path, "r") as f:
            data = json.load(f)
        
        duty_info = find_duty_by_hscode(data, formatted_code)
        success = duty_info.get("general")[0]
        auto_duty = duty_info.get("general")[1]
        
        return success, auto_duty
    except Exception as e:
        st.error(f"Error looking up duty: {str(e)}")
        return 1, f"Error: {str(e)}"

def render_goods_type_selector():
    """Render goods type selector with custom option capability"""
    
    # Get current custom goods types
    available_types = st.session_state.custom_goods_types.copy()
    available_types.append("➕ Add Custom Type...")
    
    # Goods type selection
    selected_type = st.selectbox(
        "Goods Type",
        options=available_types,
        help="Select the type of goods or add a custom type",
        key=f"goods_type_{st.session_state.form_counter}"
    )
    
    # Handle custom type addition
    if selected_type == "➕ Add Custom Type...":
        custom_type = st.text_input(
            "Enter custom goods type:",
            placeholder="e.g., Industrial Machinery",
            key=f"custom_goods_type_{st.session_state.form_counter}"
        )
        
        if custom_type and st.button("Add Custom Type", key=f"add_custom_{st.session_state.form_counter}"):
            if custom_type not in st.session_state.custom_goods_types:
                st.session_state.custom_goods_types.append(custom_type)
                st.success(f"Added '{custom_type}' to goods types!")
                st.rerun()
            else:
                st.warning("This goods type already exists!")
        
        return custom_type if custom_type else ""
    
    return selected_type

def render_hs_code_input():
    """Render HS code input section"""
    st.subheader("Input Values")
    
    # Country of origin
    country_of_origin = st.selectbox(
        "Country of Origin",
        options=["", "Canada", "China", "US", "Italy", "France", "Germany"],
        index=["", "Canada", "China", "US", "Italy", "France", "Germany"].index(st.session_state.country_of_origin) if st.session_state.country_of_origin in ["", "Canada", "China", "US", "Italy", "France", "Germany"] else 0,
        help="Select the country where the goods were manufactured or produced",
        key="persistent_country_of_origin"
    )
    st.session_state.country_of_origin = country_of_origin
    
    # HS Code input
    raw_hs_code = st.text_input(
        "HS Tariff Code", 
        max_chars=13, 
        help="Enter the HS Tariff Code (up to 13 characters).",
        key=f"raw_hs_code_{st.session_state.form_counter}"
    )
    
    validate_hs_code_format(raw_hs_code)
    
    formatted_code = format_hs_code_local(raw_hs_code) if raw_hs_code else None
    if formatted_code:
        st.info(f"Inputted HS Code: **{formatted_code}**")
    
    # Duty and tariff inputs
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
    
    # ADD GOODS TYPE SELECTION
    goods_type = render_goods_type_selector()
    
    # RETURN GOODS TYPE AS WELL
    return formatted_code, duty_percent, tariff_percent, goods_type