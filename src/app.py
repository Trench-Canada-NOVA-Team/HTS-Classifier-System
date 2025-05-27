import re
import streamlit as st
from pathlib import Path
from data_loader.json_loader import HTSDataLoader
from preprocessor.text_processor import TextPreprocessor
from classifier.hts_classifier import HTSClassifier
import time
from loguru import logger

@st.cache_resource
def initialize_classifier():
    data_dir = Path(__file__).parent.parent / "Data"
    data_loader = HTSDataLoader(str(data_dir))
    preprocessor = TextPreprocessor()
    classifier = HTSClassifier(data_loader, preprocessor)
    classifier.build_index()
    return classifier, data_loader

def get_source_data(data_loader, hts_code):
    """Get the source data for a given HTS code"""
    matches = []
    for entry in data_loader.hts_data:
        if entry.get('htsno', '').startswith(hts_code[:6]):
            matches.append(entry)
    return matches

# Add this function at the top with other helper functions
def format_hs_code(code):
    """Format HS code to XXXX.XX.XX.XX format"""
    if not code:
        return code
    # Remove all non-digits
    digits = ''.join(filter(str.isdigit, code))
    # Limit to 10 digits (standard HTS format)
    digits = digits[:10]
    # Format as XXXX.XX.XX.XX
    if len(digits) >= 4:
        formatted = digits[:4]
        if len(digits) >= 6:
            formatted += '.' + digits[4:6]
        if len(digits) >= 8:
            formatted += '.' + digits[6:8]
        if len(digits) >= 10:
            formatted += '.' + digits[8:10]
        return formatted
    return digits

# Set page config
st.set_page_config(
    page_title="HTS Code Classifier",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .result-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        background-color: #f0f2f6;
    }
    .source-data {
        font-family: monospace;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        margin-top: 1rem;
    }
    .feedback-box {
        border: 1px solid #2196F3;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
        background-color: #E3F2FD;
    }
    .stats-box {
        border: 1px solid #9C27B0;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
        background-color: #F3E5F5;
    }
    .stButton > button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title("🔍 HTS Code Classifier")
st.markdown("""
This tool helps you find the correct Harmonized Tariff Schedule (HTS) code for your products.
Simply enter a product description, and the AI will suggest the most relevant HTS codes.
""")

# Initialize the classifier
try:
    classifier, data_loader = initialize_classifier()
    
    # Create two columns for layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Product Description")
        description = st.text_area("Enter your product description:", height=100, 
                                 placeholder="Example: leather wallet made of genuine cowhide")
        
        if st.button("Classify", type="primary"):
            if description:
                with st.spinner("Analyzing product description..."):
                    try:
                        results = classifier.classify(description)
                        
                        # Store results and description in session state
                        st.session_state.classification_results = results
                        st.session_state.classification_description = description
                        
                        # Display results
                        st.subheader("Classification Results")
                        
                        for i, result in enumerate(results):
                            with st.container():
                                st.markdown(f"""
                                ### Match {i+1}
                                - **HTS Code:** {result['hts_code']}
                                - **Description:** {result['description']}
                                - **Confidence:** {result['confidence']}%
                                - **General Rate:** {result['general_rate']}
                                """)
                                
                                if result.get('units'):
                                    st.markdown(f"- **Units:** {', '.join(result['units'])}")
                                
                                # Source data in expander
                                with st.expander(f"View Source Data for {result['hts_code']}"):
                                    source_matches = get_source_data(data_loader, result['hts_code'])
                                    for match in source_matches:
                                        st.markdown(f"""
                                        **Code:** {match.get('htsno', 'N/A')}  
                                        **Description:** {match.get('description', 'N/A')}
                                        ---
                                        """)

                    except Exception as e:
                        st.error(f"An error occurred during classification: {str(e)}")
            else:
                st.warning("Please enter a product description.")
        
        # Move the feedback form OUTSIDE the classify button block
        # Check if we have results in session state to show the feedback form
        if 'classification_results' in st.session_state and st.session_state.classification_results:
            # Feedback section in a form
            with st.form(key="feedback_form"):
                st.subheader("📝 Provide Feedback")
                
                # Define the regex pattern at the top
                allowed_chars_pattern = r"^\d{4}(?:\.\d{2}){0,3}$"
                
                is_correct = st.radio(
                    "Is the top prediction correct?",
                    ["Yes", "No"],
                    key="feedback_choice"
                )
                
                # # Only show correct code input if "No" is selected
                # correct_code = None
                # if is_correct == "No":
                #     correct_code = st.text_input(
                #         "Please provide the correct HTS code:",
                #         max_chars=13,
                #         help="Enter the correct HTS code (up to 13 characters).",
                #         key="correct_code_input"
                #     )
                    
                #     # Add regex validation here
                #     if correct_code and not re.match(allowed_chars_pattern, correct_code):
                #         st.error("Invalid Format: HS Code can only contain digits and periods (e.g., 1234.56.78.90)")
                #     elif correct_code not in (None, ""):
                #         st.success("Input format is valid.")
                
                # Submit button
                submit_feedback = st.form_submit_button("Submit Feedback")
                
                if submit_feedback:
                    print("Submitting feedback...")
                    try:
                        # Get results and description from session state
                        results = st.session_state.classification_results
                        description = st.session_state.classification_description
                        
                        if is_correct == "Yes":
                            # Use predicted code as correct code
                            logger.info(f"Adding positive feedback for prediction {results[0]['hts_code']}")
                            print(f"Adding positive feedback for prediction {results[0]['hts_code']}")
                            classifier.add_feedback(
                                product_description=description,
                                predicted_code=results[0]['hts_code'],
                                correct_code=results[0]['hts_code']
                                # Remove confidence_score parameter
                            )
                            st.success("✅ Thank you! Prediction marked as correct!")
                            
                            # Clear the session state after successful feedback
                            del st.session_state.classification_results
                            del st.session_state.classification_description
                            
                            time.sleep(1)
                            st.rerun()
                        else:  # No
                             # Only show correct code input if "No" is selected
                            # correct_code = None
                            correct_code = st.text_input(
                                "Please provide the correct HTS code:",
                                max_chars=13,
                                help="Enter the correct HTS code (up to 13 characters).",
                                key="correct_code_input"
                            )
                            
                            # Add regex validation here
                            if correct_code and not re.match(allowed_chars_pattern, correct_code):
                                st.error("Invalid Format: HS Code can only contain digits and periods (e.g., 1234.56.78.90)")
                            elif correct_code not in (None, ""):
                                st.success("Input format is valid.")

                            if not correct_code:
                                st.error("⚠️ Please enter the correct HTS code.")
                            elif correct_code and not re.match(allowed_chars_pattern, correct_code):
                                st.error("⚠️ Invalid format: HS Code can only contain digits and periods.")
                            else:
                                # Format the correct code before using it
                                formatted_correct_code = format_hs_code(correct_code)
                                
                                logger.info(f"Adding correction feedback: {results[0]['hts_code']} -> {formatted_correct_code}")
                                print(f"Adding correction feedback: {results[0]['hts_code']} -> {formatted_correct_code}")
                                classifier.add_feedback(
                                    product_description=description,
                                    predicted_code=results[0]['hts_code'],
                                    correct_code=formatted_correct_code
                                    # Remove confidence_score parameter
                                )
                                st.success(f"✅ Thank you! Corrected to {formatted_correct_code}")
                                
                                # Clear the session state after successful feedback
                                del st.session_state.classification_results
                                del st.session_state.classification_description
                            
                                time.sleep(1)
                                st.rerun()
                    except Exception as e:
                        logger.error(f"Error saving feedback: {str(e)}")
                        st.error(f"Error saving feedback: {str(e)}")
    
    with col2:
        st.subheader("Feedback Statistics")
        stats = classifier.get_feedback_stats()
        
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            st.metric("Total Entries", stats['total_entries'])
        with col2_2:
            st.metric("Accuracy", f"{stats['accuracy']*100:.1f}%")
        
        if stats['recent_entries']:
            st.subheader("Recent Feedback")
            for entry in stats['recent_entries']:
                st.markdown(f"""
                ---
                **Description:** {entry['description'][:50]}...  
                **Predicted:** {entry['predicted_code']}  
                **Actual:** {entry['correct_code']}
                """)
                
        else:
            st.info("No feedback entries yet.")
            
except Exception as e:
    st.error(f"Error initializing the classifier: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
*This is an AI-powered tool. The verification data is extracted directly from the official HTS database. 
Please verify the results with official HTS documentation for critical decisions.*
""")