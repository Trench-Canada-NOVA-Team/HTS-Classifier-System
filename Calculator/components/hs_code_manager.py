import streamlit as st
import pandas as pd

def add_hs_code_to_list(formatted_code, duty_percent, tariff_percent):
    """Add HS code to the session state list"""
    # Validation
    if not st.session_state.user_email:
        st.error("Please enter user email before adding to list")
        return False
    elif not st.session_state.order_number:
        st.error("Please enter order number before adding to list")
        return False
    elif "@" not in st.session_state.user_email:
        st.error("Please enter a valid email address")
        return False
    elif not st.session_state.country_of_origin:
        st.error("Please select a country of origin")
        return False
    
    # Check if HS code already exists
    existing_codes = [item['hs_code'] for item in st.session_state.hs_code_list]
    if formatted_code not in existing_codes:
        st.session_state.hs_code_list.append({
            'hs_code': formatted_code,
            'duty_percent': duty_percent,
            'tariff_percent': tariff_percent,
            'status': 'Active',
            'user_email': st.session_state.user_email,
            'order_number': st.session_state.order_number,
            'country_of_origin': st.session_state.country_of_origin
        })
        st.success(f"Added {formatted_code} from {st.session_state.country_of_origin} to list for order {st.session_state.order_number}")
        st.session_state.form_counter += 1
        return True
    else:
        st.warning("HS Code already in list")
        return False

def render_hs_code_list():
    """Render the HS code list with editing capabilities"""
    if not st.session_state.hs_code_list:
        return 0, 0
    
    st.subheader("HS Code List")
    st.info(f"**User:** {st.session_state.user_email} |  **Order:** {st.session_state.order_number} |  **Country:** {st.session_state.country_of_origin}")
    
    # Create DataFrame for display
    df = pd.DataFrame(st.session_state.hs_code_list)
    display_columns = ['hs_code', 'duty_percent', 'tariff_percent', 'status']
    df_display = df[display_columns]
    
    # Add edit functionality
    edited_df = st.data_editor(
        df_display,
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
    
    # Update session state with edited data
    for i, edited_row in edited_df.iterrows():
        if i < len(st.session_state.hs_code_list):
            st.session_state.hs_code_list[i]['hs_code'] = edited_row['hs_code']
            st.session_state.hs_code_list[i]['duty_percent'] = edited_row['duty_percent']
            st.session_state.hs_code_list[i]['tariff_percent'] = edited_row['tariff_percent']
            st.session_state.hs_code_list[i]['status'] = edited_row['status']
            st.session_state.hs_code_list[i]['country_of_origin'] = st.session_state.country_of_origin
    
    # Calculate totals
    total_tariff = sum(float(row['tariff_percent']) for row in st.session_state.hs_code_list if isinstance(row['tariff_percent'], (int, float)))
    total_duty = sum(float(row['duty_percent']) for row in st.session_state.hs_code_list if isinstance(row['duty_percent'], (int, float)))
    
    st.metric("Total Duty for Bill", f"{total_duty:.2f}%")
    st.metric("Total Tariff for Bill", f"{total_tariff:.2f}%")
    
    return total_duty, total_tariff