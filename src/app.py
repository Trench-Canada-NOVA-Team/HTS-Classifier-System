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
                        
                        # Feedback section in a form
                        with st.form(key="feedback_form"):
                            st.subheader("📝 Provide Feedback")
                            is_correct = st.radio(
                                "Is the top prediction correct?",
                                ["Yes", "No"],
                                key="feedback_choice"
                            )
                            
                            # Only show correct code input if "No" is selected
                            correct_code = None
                            if is_correct == "No":
                                correct_code = st.text_input(
                                    "Please provide the correct HTS code:",
                                    key="correct_code_input"
                                )
                            
                            # Submit button
                            submit_feedback = st.form_submit_button("Submit Feedback")
                            
                            if submit_feedback:
                                try:
                                    if is_correct == "Yes":
                                        # Use predicted code as correct code
                                        logger.info(f"Adding positive feedback for prediction {results[0]['hts_code']}")
                                        classifier.add_feedback(
                                            product_description=description,
                                            predicted_code=results[0]['hts_code'],
                                            correct_code=results[0]['hts_code'],
                                            confidence_score=results[0]['confidence']
                                        )
                                        st.success("✅ Thank you! Prediction marked as correct!")
                                        time.sleep(1)  # Give time for the message to be seen
                                        st.experimental_rerun()
                                    else:  # No
                                        if not correct_code:
                                            st.error("⚠️ Please enter the correct HTS code.")
                                        else:
                                            logger.info(f"Adding correction feedback: {results[0]['hts_code']} -> {correct_code}")
                                            classifier.add_feedback(
                                                product_description=description,
                                                predicted_code=results[0]['hts_code'],
                                                correct_code=correct_code,
                                                confidence_score=results[0]['confidence']
                                            )
                                            st.success(f"✅ Thank you! Corrected to {correct_code}")
                                            time.sleep(1)  # Give time for the message to be seen
                                            st.experimental_rerun()
                                except Exception as e:
                                    logger.error(f"Error saving feedback: {str(e)}")
                                    st.error(f"Error saving feedback: {str(e)}")

                    except Exception as e:
                        st.error(f"An error occurred during classification: {str(e)}")
            else:
                st.warning("Please enter a product description.")
    
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
                **Confidence:** {entry['confidence_score']}%
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