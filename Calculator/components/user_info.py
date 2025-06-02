import streamlit as st

def reset_order():
    """Reset user info and start fresh"""
    st.session_state.user_email = ""
    st.session_state.order_number = ""
    st.session_state.country_of_origin = ""
    st.session_state.hs_code_list = []
    st.session_state.form_counter = 0
    st.success("Order reset successfully!")

def render_user_info_section():
    """Render the user information input section"""
    st.subheader("👤 User Information")
    col1, col2 = st.columns(2)

    with col1:
        user_email = st.text_input(
            "User Email", 
            value=st.session_state.user_email,
            placeholder="user@company.com",
            key="persistent_user_email"
        )
        st.session_state.user_email = user_email

    with col2:
        order_number = st.text_input(
            "Order Number", 
            value=st.session_state.order_number,
            placeholder="ORD-123456",
            key="persistent_order_number"
        )
        st.session_state.order_number = order_number

    # Email validation
    if user_email and "@" not in user_email:
        st.error("Please enter a valid email address")
    elif user_email:
        st.success("✅ Valid email format")

def render_new_order_button():
    """Render the start new order button"""
    if st.button("🔄 Start New Order", help="Clear user info and start fresh"):
        reset_order()
        st.rerun()