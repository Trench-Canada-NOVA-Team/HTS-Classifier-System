import streamlit as st

# ADD THESE 5 LINES at the top (after existing imports)
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
try:
    from utils.simple_logger import SimpleLogger
except:
    class SimpleLogger:
        def start_user_session(self, email): pass

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
    # ADD THIS 1 LINE at the beginning of function
    logger = SimpleLogger()
    
    st.subheader("User Information")
    col1, col2 = st.columns(2)

    with col1:
        user_email = st.text_input(
            "User Email", 
            value=st.session_state.user_email,
            placeholder="user@company.com",
            key="persistent_user_email"
        )
        st.session_state.user_email = user_email
        
        # ADD THIS 1 LINE after setting user_email
        logger.start_user_session(user_email)

        # # ADD THIS - Country of Origin field (was missing)
        # country_origin = st.text_input(
        #     "Country of Origin", 
        #     value=st.session_state.country_of_origin,
        #     placeholder="e.g., China, Mexico, Germany",
        #     key="persistent_country_origin"
        # )
        # st.session_state.country_of_origin = country_origin

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
        st.success("Valid email format")

def render_new_order_button():
    """Render the start new order button"""
    if st.button("Start New Order", help="Clear user info and start fresh"):
        reset_order()
        st.rerun()