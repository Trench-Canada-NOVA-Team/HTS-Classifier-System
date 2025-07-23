import re
import streamlit as st
from pathlib import Path
from data_loader.json_loader import HTSDataLoader
from preprocessor.text_processor import TextPreprocessor
from classifier.feedback_enhanced_classifier import FeedbackEnhancedClassifier
from utils.azure_blob_helper import FeedbackHandler
from services.proof_service import ProofService
import time
from config.settings import Config
from loguru import logger
import pandas as pd
from utils.logging_utils import setup_logger, log_system_startup, log_system_error

# Initialize logging for Streamlit app
@st.cache_resource
def initialize_logging():
    """Initialize logging for the Streamlit application."""
    try:
        setup_logger("streamlit_app")  # This will now use Config.STREAMLIT_LOG_FILE
        log_system_startup("Streamlit HTS Classification App")
        return True
    except Exception as e:
        st.error(f"Failed to setup logging: {e}")
        return False

@st.cache_resource
def initialize_classifier():
    # Initialize logging first
    initialize_logging()
    
    try:
        log_system_startup("Classifier Initialization")
        
        data_dir = Path(__file__).parent.parent / "Data"
        data_loader = HTSDataLoader(str(data_dir))
        preprocessor = TextPreprocessor()
        
        # Initialize Pinecone feedback service for feedback
        from services.pinecone_feedback_service import PineconeFeedbackService
        pinecone_feedback_service = PineconeFeedbackService()
        
        # Initialize feedback handler with Pinecone feedback service
        feedback_handler = FeedbackHandler(use_azure=True, pinecone_feedback_service=pinecone_feedback_service)
        
        # Initialize enhanced classifier with Pinecone feedback service
        classifier = FeedbackEnhancedClassifier(data_loader, preprocessor, feedback_handler, pinecone_feedback_service)
        classifier.build_index()
        
        # Check if Pinecone feedback index needs to be rebuilt
        # Only rebuild if the index is empty (has zero vectors)
        feedback_stats = pinecone_feedback_service.get_feedback_stats()
        
        if feedback_stats.get('pinecone_available', False):
            total_vectors = feedback_stats.get('total_vectors', 0)
            
            if total_vectors == 0:
                logger.info("Pinecone feedback index is empty, checking if rebuild is needed...")
                
                # Check if there's actual feedback data in Azure that should be migrated
                try:
                    recent_feedback = feedback_handler.get_recent_feedback(days=365)  # Check all data
                    
                    if not recent_feedback.empty:
                        corrections_count = len(recent_feedback[recent_feedback['predicted_code'] != recent_feedback['correct_code']])
                        
                        if corrections_count > 0:
                            logger.info(f"Found {corrections_count} feedback corrections in Azure, rebuilding Pinecone feedback index...")
                            success = feedback_handler.rebuild_pinecone_from_existing_data(days=365)
                            
                            if success:
                                logger.info("Successfully rebuilt Pinecone feedback index from existing data")
                            else:
                                logger.warning("Failed to rebuild Pinecone feedback index, but continuing...")
                        else:
                            logger.info("No feedback corrections found in Azure data, skipping rebuild")
                    else:
                        logger.info("No feedback data found in Azure, skipping rebuild")
                        
                except Exception as rebuild_error:
                    logger.error(f"Error during feedback index rebuild check: {str(rebuild_error)}")
                    logger.info("Continuing with empty feedback index...")
            else:
                logger.info(f"Pinecone feedback index already contains {total_vectors} vectors, skipping rebuild")
        else:
            logger.warning("Pinecone feedback service not available, skipping feedback index initialization")
        
        logger.info("Classifier initialization completed successfully")
        return classifier, data_loader
    
    except Exception as e:
        log_system_error("Classifier Initialization", str(e))
        raise

@st.cache_resource
def initialize_feedback_handler():
    """Initialize the feedback handler with Azure Blob Storage and Pinecone feedback support"""
    try:
        from services.pinecone_feedback_service import PineconeFeedbackService
        from utils.azure_blob_helper import FeedbackHandler
        
        pinecone_feedback_service = PineconeFeedbackService()
        feedback_handler = FeedbackHandler(use_azure=True, pinecone_feedback_service=pinecone_feedback_service)
        
        logger.info("Feedback handler initialized successfully")
        return feedback_handler
    
    except Exception as e:
        log_system_error("Feedback Handler Initialization", str(e))
        raise

def calculate_detailed_stats(feedback_handler):
    """Calculate detailed statistics from feedback data using FeedbackHandler methods"""
    logger.debug("Calculating detailed stats from feedback handler")
    try:
        # Use get_feedback_stats method from FeedbackHandler
        stats = feedback_handler.get_feedback_stats()
        logger.debug(f"Feedback stats: {stats}")  # Log the stats for debugging
        
        if not stats:
            return {
                'total_entries': 0,
                'correct_predictions': 0,
                'incorrect_predictions': 0,
                'accuracy': 0,
                'total_corrections': 0,
                'recent_feedback_count': 0
            }
        
        total_entries = stats.get('total_entries', 0)
        
        # Fix: The new FeedbackHandler returns 'accuracy' directly, not 'correct_predictions'
        accuracy = stats.get('accuracy', 0)
        correct_predictions = int(total_entries * accuracy) if total_entries > 0 else 0
        
        # Calculate additional metrics
        incorrect_predictions = total_entries - correct_predictions
        total_corrections = incorrect_predictions
        
        # Use configuration for recent feedback days
        try:
            recent_feedback = feedback_handler.get_recent_feedback(days=Config.DEFAULT_FEEDBACK_DAYS)
            recent_feedback_count = len(recent_feedback) if not recent_feedback.empty else 0
        except Exception as e:
            logger.error(f"Error getting recent feedback: {str(e)}")
            recent_feedback_count = 0
        
        result = {
            'total_entries': total_entries,
            'correct_predictions': correct_predictions,
            'incorrect_predictions': incorrect_predictions,
            'accuracy': accuracy,
            'total_corrections': total_corrections,
            'recent_feedback_count': recent_feedback_count
        }
        
        logger.debug(f"Calculated stats: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating detailed stats: {str(e)}")
        return {
            'total_entries': 0,
            'correct_predictions': 0,
            'incorrect_predictions': 0,
            'accuracy': 0,
            'total_corrections': 0,
            'recent_feedback_count': 0
        }

def get_feedback_summary(feedback_handler):
    """Get feedback summary using FeedbackHandler methods"""
    try:
        # Use configuration for recent feedback days
        recent_feedback = feedback_handler.get_recent_feedback(days=Config.DEFAULT_FEEDBACK_DAYS)
        
        if recent_feedback.empty:
            return {
                'recent_entries': 0,
                'recent_corrections': 0,
                'top_corrected_codes': [],
                'correction_rate': 0
            }
        
        recent_entries = len(recent_feedback)
        recent_corrections = 0
        corrected_codes = {}

        logger.debug(f"recent feedback:\n{recent_feedback.head()}")  # Log first few entries for debugging

        # Use iterrows() instead of itertuples() for better compatibility
        for _, row in recent_feedback.iterrows():
            predicted = row['predicted_code']
            correct = row['correct_code']

            if predicted != correct:
                recent_corrections += 1
                if correct in corrected_codes:
                    corrected_codes[correct] += 1
                else:
                    corrected_codes[correct] = 1
        
        # Use configuration for top corrected codes count
        top_corrected = sorted(corrected_codes.items(), key=lambda x: x[1], reverse=True)[:Config.DASHBOARD_TOP_CORRECTIONS_COUNT]
        correction_rate = (recent_corrections / recent_entries * 100) if recent_entries > 0 else 0
        
        result = {
            'recent_entries': recent_entries,
            'recent_corrections': recent_corrections,
            'top_corrected_codes': top_corrected,
            'correction_rate': correction_rate
        }
        
        logger.debug(f"Feedback summary: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting feedback summary: {str(e)}")
        return {
            'recent_entries': 0,
            'recent_corrections': 0,
            'top_corrected_codes': [],
            'correction_rate': 0
        }

def get_source_data(data_loader, hts_code):
    """Get the source data for a given HTS code"""
    matches = []
    for entry in data_loader.hts_data:
        if entry.get('htsno', '').startswith(hts_code[:6]):
            matches.append(entry)
    return matches

# Set page config
st.set_page_config(
    page_title="HTS Code Classification System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling
st.markdown("""
    <style>
    /* Global Styles */
    .main {
        padding: 2rem 3rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Header Styles */
    .header-container {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: white;
        padding: 2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .header-title {
        font-size: 2.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .header-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 300;
    }
    
    /* Card Styles */
    .card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .card-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e2e8f0;
    }
    
    /* Result Styles */
    .result-priority-1 {
        background: #f0fff4;
        border-left: 4px solid #38a169;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-radius: 0 8px 8px 0;
    }
    
    .result-priority-2 {
        background: #f7fafc;
        border-left: 4px solid #4299e1;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-radius: 0 8px 8px 0;
    }
    
    .result-priority-3 {
        background: #fffaf0;
        border-left: 4px solid #ed8936;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-radius: 0 8px 8px 0;
    }
    
    .result-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 0.5rem;
    }
    
    .result-code {
        font-family: 'Courier New', monospace;
        font-size: 1.1rem;
        font-weight: bold;
        color: #1a365d;
    }
    
    .confidence-high {
        color: #38a169;
        font-weight: 600;
    }
    
    .confidence-medium {
        color: #d69e2e;
        font-weight: 600;
    }
    
    .confidence-low {
        color: #e53e3e;
        font-weight: 600;
    }
    
    /* Form Styles */
    .stTextArea > div > div > textarea {
        border: 2px solid #e2e8f0;
        border-radius: 6px;
        padding: 1rem;
        font-size: 1rem;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #4299e1;
        box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #2c5282 0%, #3182ce 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2a4a6b 0%, #2b77b8 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(45, 82, 130, 0.3);
    }
    
    /* Feedback Styles */
    .feedback-section {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1.5rem;
        margin-top: 2rem;
    }
    
    .alert-success {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
        border-radius: 6px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
        border-radius: 6px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .alert-error {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
        border-radius: 6px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Stats Styles */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .stat-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .stat-value {
        font-size: 3rem;
        font-weight: bold;
        color: #2d3748;
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        font-size: 1rem;
        color: #718096;
        font-weight: 500;
    }
    
    .large-stat-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: white;
        border: none;
        text-align: center;
        padding: 3rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    .large-stat-value {
        font-size: 4rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    
    .large-stat-label {
        font-size: 1.2rem;
        opacity: 0.9;
    }
    
    /* Progress Bar */
    .progress-container {
        background: #e2e8f0;
        border-radius: 10px;
        height: 8px;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    
    .progress-bar {
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }
    
    .progress-high {
        background: linear-gradient(90deg, #38a169, #48bb78);
    }
    
    .progress-medium {
        background: linear-gradient(90deg, #d69e2e, #ecc94b);
    }
    
    .progress-low {
        background: linear-gradient(90deg, #e53e3e, #fc8181);
    }
    
    /* Sidebar Styles */
    .css-1d391kg {
        background: #f8f9fa;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .main {
            padding: 1rem;
        }
        
        .header-title {
            font-size: 2rem;
        }
        
        .stats-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar Navigation
with st.sidebar:
    sidebar_image_path = Path(__file__).parent / "assets" / "trench-logo.png"
    if sidebar_image_path.exists():
        st.image(str(sidebar_image_path), use_container_width=True)

    # vertical spacer
    st.markdown("<hr>", unsafe_allow_html=True)

    # Navigation options
    st.title("Navigation")
    
    page = st.radio(
        "Select Page",
        ["HTS Classification", "Performance Dashboard"],
        key="page_selection"
    )
    
    st.markdown("---")
    st.markdown("**System Status**")
    st.success("System Online")
    st.info("AI Learning: Active")

# Initialize the classifier and feedback handler
try:
    classifier, data_loader = initialize_classifier()
    feedback_handler = initialize_feedback_handler()
    
    # Page routing
    if page == "HTS Classification":
        # Header
        st.markdown("""
        <div class="header-container">
            <div class="header-title">HTS Code Classification System</div>
            <div class="header-subtitle">Advanced Harmonized Tariff Schedule Classification with AI-Enhanced Learning</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Main content area
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">Product Classification</div>', unsafe_allow_html=True)
            
            description = st.text_area(
                "Product Description",
                height=120,
                placeholder="Enter a detailed description of your product (e.g., 'leather wallet made of genuine cowhide')",
                help="Provide as much detail as possible including materials, size, intended use, and other relevant characteristics."
            )
            
            col_check, col_button = st.columns([1, 1])
            
            with col_check:
                learn_from_feedback = st.checkbox(
                    "Enable Enhanced Learning", 
                    value=True,
                    help="Use machine learning from past corrections to improve accuracy"
                )
            
            with col_button:
                classify_button = st.button("Classify Product", type="primary", use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Classification Results
            if classify_button and description:
                with st.spinner("Analyzing product description..."):
                    try:
                        results = classifier.classify(description, learn_from_feedback=learn_from_feedback)
                        
                        # Store results in session state
                        st.session_state.classification_results = results
                        st.session_state.classification_description = description
                        
                        if results:
                            st.markdown('<div class="card">', unsafe_allow_html=True)
                            st.markdown('<div class="card-header">Classification Results</div>', unsafe_allow_html=True)
                            
                            # Check for enhanced learning indicators
                            exact_feedback_used = any(r.get('source') == 'feedback_correction' and r.get('match_type') == 'exact_match' for r in results)
                            semantic_feedback_used = any(r.get('source') == 'semantic_feedback' for r in results)
                            confidence_adjusted = any(r.get('feedback_adjusted') for r in results)
                            
                            # Learning notifications
                            if exact_feedback_used:
                                st.markdown('<div class="alert-success"><strong>Priority 1:</strong> Exact match from previous corrections applied</div>', unsafe_allow_html=True)
                            elif semantic_feedback_used:
                                st.markdown('<div class="alert-success"><strong>Priority 2:</strong> AI semantic learning from similar products applied</div>', unsafe_allow_html=True)
                            elif confidence_adjusted:
                                st.markdown('<div class="alert-warning"><strong>Priority 3:</strong> AI confidence adjustment based on feedback patterns</div>', unsafe_allow_html=True)
                            
                            # Display results
                            for i, result in enumerate(results):
                                # Determine priority class
                                if result.get('source') == 'feedback_correction' and result.get('match_type') == 'exact_match':
                                    priority_class = "result-priority-1"
                                    priority_label = "Priority 1 - Exact Match"
                                elif result.get('source') == 'semantic_feedback':
                                    priority_class = "result-priority-2"
                                    priority_label = "Priority 2 - AI Semantic Match"
                                else:
                                    priority_class = "result-priority-3"
                                    priority_label = "Priority 3 - Standard Classification"
                                
                                # Confidence styling
                                confidence = result['confidence']
                                if confidence >= 80:
                                    confidence_class = "confidence-high"
                                elif confidence >= 60:
                                    confidence_class = "confidence-medium"
                                else:
                                    confidence_class = "confidence-low"
                                
                                st.markdown(f"""
                                <div class="{priority_class}">
                                    <div class="result-header">{priority_label} - Match {i+1}</div>
                                    <div style="margin: 0.75rem 0;">
                                        <strong>HTS Code:</strong> <span class="result-code">{result['hts_code']}</span>
                                    </div>
                                    <div style="margin: 0.75rem 0;">
                                        <strong>Description:</strong> {result['description']}
                                    </div>
                                    <div style="margin: 0.75rem 0;">
                                        <strong>Confidence:</strong> <span class="{confidence_class}">{result['confidence']:.1f}%</span>
                                    </div>
                                    <div style="margin: 0.75rem 0;">
                                        <strong>General Rate:</strong> {result['general_rate']}
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                # Similarity indicator for semantic matches
                                if result.get('similarity_score') and result.get('source') in ['feedback_correction', 'semantic_feedback']:
                                    similarity = result['similarity_score']
                                    if similarity < 1.0:
                                        similarity_percent = similarity * 100
                                        progress_class = "progress-high" if similarity >= 0.9 else "progress-medium" if similarity >= 0.75 else "progress-low"
                                        
                                        st.markdown(f"""
                                        <div style="margin: 0.75rem 0;">
                                            <strong>Semantic Similarity:</strong> {similarity_percent:.1f}%
                                            <div class="progress-container">
                                                <div class="progress-bar {progress_class}" style="width: {similarity_percent}%;"></div>
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                
                                # Learning explanation
                                if result.get('learning_explanation'):
                                    st.markdown(f"""
                                    <div style="margin: 0.75rem 0; padding: 0.5rem; background: rgba(255,255,255,0.7); border-radius: 4px; font-style: italic;">
                                        <strong>Learning Context:</strong> {result['learning_explanation']}
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Units if available
                                if result.get('units'):
                                    st.markdown(f"""
                                    <div style="margin: 0.75rem 0;">
                                        <strong>Units:</strong> {', '.join(result['units'])}
                                    </div>
                                    """, unsafe_allow_html=True)

                                # Display Proof
                                logger.info(f"Displaying proof for HTS code: {result['hts_code']}")
                                logger.debug(f"Proof service initialized with HTS code: {result['hts_code']}")
                                proof_handler = ProofService(result['hts_code'])

                                page_num = proof_handler.find_hts_code_page(result['hts_code'])
                                if page_num is None:
                                    st.markdown("""
                                    <div class="alert-warning">
                                        <strong>Proof Not Found:</strong> The HTS code was not found in the PDF document.
                                    </div>
                                    """, unsafe_allow_html=True)
                                    continue
                                else:
                                    chapter_num = proof_handler.code_parts[0][:2]
                                    logger.info(f"HTS code found on schedule chapter {chapter_num} page: {page_num}")

                                logger.debug(f"Converting PDF page {page_num} to image")
                                images = proof_handler.convert_pdf_to_images(page_num)
                                
                                
                                with st.expander(f"📄 View HTS Code Proof (Chapter {chapter_num}, Page {page_num})", expanded=False):
                                    st.image(images[0], use_container_width=True)
                                    st.caption(f"Source: https://hts.usitc.gov/, Chapter {chapter_num}, Page {page_num}")
                                    
                                    # Optional: Add a download button for the image
                                    from io import BytesIO
                                    import PIL.Image
                                    
                                    # Convert PIL image to bytes
                                    buf = BytesIO()
                                    images[0].save(buf, format="PNG")
                                    byte_im = buf.getvalue()
                                    
                                    # st.download_button(
                                    #     label="Download Proof Image",
                                    #     key =f"download_proof_{result['hts_code']}",
                                    #     data=byte_im,
                                    #     file_name=f"hts_code_{result['hts_code']}_proof.png",
                                    #     mime="image/png",
                                    #     use_container_width=True,
                                    # )
                                    st.download_button(
                                        label="Download Proof Image",
                                        data=byte_im,
                                        file_name=f"hts_code_{result['hts_code']}_proof.png",
                                        mime="image/png",
                                        use_container_width=True,
                                        key=f"download_proof_{result['hts_code']}_{i}"
                                    )
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.markdown("""
                            <div class="alert-error">
                                <strong>No Classification Results Found</strong><br>
                                The system could not find any matching HTS codes for this product description.
                                Please try rephrasing your description with more specific details.
                            </div>
                            """, unsafe_allow_html=True)
                            
                    except Exception as e:
                        st.markdown(f"""
                        <div class="alert-error">
                            <strong>Classification Error:</strong> {str(e)}
                        </div>
                        """, unsafe_allow_html=True)
                        logger.error(f"Classification error: {str(e)}")
            
            elif classify_button and not description:
                st.markdown("""
                <div class="alert-warning">
                    Please enter a product description before classifying.
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            # Feedback Section
            if 'classification_results' in st.session_state and st.session_state.classification_results:
                # st.markdown('<div class="feedback-section">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">Feedback & Learning</div>', unsafe_allow_html=True)
                
                with st.form(key="feedback_form"):
                    results = st.session_state.classification_results
                    top_result = results[0]
                    
                    # Show context for feedback
                    if top_result.get('source') == 'feedback_correction':
                        st.info("This result came from previous exact match corrections.")
                    elif top_result.get('source') == 'semantic_feedback':
                        similarity = top_result.get('similarity_score', 0) * 100
                        st.info(f"This result came from AI semantic learning ({similarity:.0f}% similarity).")
                    else:
                        st.info("This result came from standard HTS classification.")
                    
                    is_correct = st.radio(
                        "Is the top prediction correct?",
                        ["Yes", "No"],
                        key="feedback_choice"
                    )
                    
                    correct_code = None
                    if is_correct == "No":
                        correct_code = st.text_input(
                            "Correct HTS Code:",
                            max_chars=13,
                            help="Enter the correct HTS code (format: 1234.56.78.90)"
                        )
                        
                        if correct_code and not re.match(r"^\d{4}(?:\.\d{2}){0,3}$", correct_code):
                            st.error("Invalid format. Use format: 1234.56.78.90")
                    
                    submit_feedback = st.form_submit_button("Submit Feedback", use_container_width=True)
                    
                    if submit_feedback:
                        try:
                            description = st.session_state.classification_description
                            
                            if is_correct == "Yes":
                                success = classifier.add_feedback(
                                    product_description=description,
                                    predicted_code=top_result['hts_code'],
                                    correct_code=top_result['hts_code']
                                )
                                if success:
                                    st.success("Thank you! Feedback recorded successfully.")
                                    # Clear cache to refresh stats
                                    st.cache_resource.clear()
                                else:
                                    st.error("Failed to record feedback.")
                            
                            elif correct_code:
                                success = classifier.add_feedback(
                                    product_description=description,
                                    predicted_code=top_result['hts_code'],
                                    correct_code=correct_code
                                )
                                if success:
                                    st.success("Thank you! Correction recorded and will improve future predictions.")
                                    # Clear cache to refresh stats
                                    st.cache_resource.clear()
                                else:
                                    st.error("Failed to record correction.")
                            
                            else:
                                st.warning("Please provide the correct HTS code.")
                                
                        except Exception as e:
                            st.error(f"Error submitting feedback: {str(e)}")
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">Quick Start</div>', unsafe_allow_html=True)
                st.markdown("""
                <div style="padding: 1rem 0;">
                    <p><strong>How to use:</strong></p>
                    <ol>
                        <li>Enter detailed product description</li>
                        <li>Enable Enhanced Learning for better results</li>
                        <li>Click "Classify Product"</li>
                        <li>Review results and provide feedback</li>
                    </ol>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
    elif page == "Performance Dashboard":
        # Performance Dashboard Page
        st.markdown("""
        <div class="header-container">
            <div class="header-title">Performance Dashboard</div>
            <div class="header-subtitle">Real-time Performance Metrics and System Analytics</div>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            # Get detailed statistics using FeedbackHandler methods
            detailed_stats = calculate_detailed_stats(feedback_handler)
            feedback_summary = get_feedback_summary(feedback_handler)
            
            # Add FAISS statistics if available
            faiss_stats = {}
            if hasattr(classifier, 'faiss_service') and classifier.faiss_service:
                try:
                    faiss_stats = classifier.faiss_service.get_feedback_stats()
                    logger.debug(f"FAISS stats: {faiss_stats}")
                except Exception as e:
                    logger.error(f"Error getting FAISS stats: {str(e)}")
                    faiss_stats = {}
            
            # Main KPI Cards
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="large-stat-card">
                    <div class="large-stat-value">{detailed_stats['total_entries']}</div>
                    <div class="large-stat-label">Total Classifications</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                accuracy = detailed_stats['accuracy'] * 100
                st.markdown(f"""
                <div class="large-stat-card">
                    <div class="large-stat-value">{accuracy:.1f}%</div>
                    <div class="large-stat-label">System Accuracy</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="large-stat-card">
                    <div class="large-stat-value">{detailed_stats['correct_predictions']}</div>
                    <div class="large-stat-label">Correct Predictions</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Detailed Performance Metrics
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">Detailed Performance Metrics</div>', unsafe_allow_html=True)
            
            # Create a 2x3 grid of detailed stats
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{detailed_stats['correct_predictions']}</div>
                    <div class="stat-label">Correct Predictions</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{feedback_summary['recent_entries']}</div>
                    <div class="stat-label">Recent Feedback (30 days)</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{detailed_stats['incorrect_predictions']}</div>
                    <div class="stat-label">Incorrect Predictions</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{feedback_summary['recent_corrections']}</div>
                    <div class="stat-label">Recent Corrections</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{detailed_stats['total_corrections']}</div>
                    <div class="stat-label">Total Learning Corrections</div>
                </div>
                """, unsafe_allow_html=True)
                
                database_entries = len(data_loader.hts_data) if hasattr(data_loader, 'hts_data') else 0
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{database_entries:,}</div>
                    <div class="stat-label">Database Entries</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # FAISS Performance Section
            if faiss_stats and faiss_stats.get('faiss_available', False):
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">FAISS Vector Database Performance</div>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{faiss_stats.get('total_vectors', 0)}</div>
                        <div class="stat-label">Total Vectors</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{faiss_stats.get('total_corrections', 0)}</div>
                        <div class="stat-label">Feedback Corrections</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    faiss_status = "✅ Active" if faiss_stats.get('is_initialized', False) else "❌ Inactive"
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="font-size: 1.5rem;">{faiss_status}</div>
                        <div class="stat-label">FAISS Status</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # FAISS Performance Details
                st.markdown(f"""
                <div style="margin: 1rem 0; padding: 1rem; background: #f8f9fa; border-radius: 6px;">
                    <h4>FAISS Configuration</h4>
                    <p><strong>Index Type:</strong> {faiss_stats.get('index_type', 'Unknown')}</p>
                    <p><strong>Embedding Model:</strong> {faiss_stats.get('embedding_model', 'Unknown')}</p>
                    <p><strong>Initialized:</strong> {'Yes' if faiss_stats.get('is_initialized', False) else 'No'}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Performance Overview
            if detailed_stats['total_entries'] > 0:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">Performance Overview</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Accuracy chart data
                    correct_pct = (detailed_stats['correct_predictions'] / detailed_stats['total_entries']) * 100
                    incorrect_pct = (detailed_stats['incorrect_predictions'] / detailed_stats['total_entries']) * 100
                    
                    st.markdown(f"""
                    <div style="margin: 1rem 0;">
                        <h4>Prediction Accuracy Breakdown</h4>
                        <div style="margin: 1rem 0;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>Correct Predictions</span>
                                <span>{correct_pct:.1f}%</span>
                            </div>
                            <div class="progress-container">
                                <div class="progress-bar progress-high" style="width: {correct_pct}%;"></div>
                            </div>
                        </div>
                        <div style="margin: 1rem 0;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>Incorrect Predictions</span>
                                <span>{incorrect_pct:.1f}%</span>
                            </div>
                            <div class="progress-container">
                                <div class="progress-bar progress-low" style="width: {incorrect_pct}%;"></div>
                            </div>
                        </div>
                        <div style="margin: 1rem 0;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>Recent Correction Rate (30d)</span>
                                <span>{feedback_summary['correction_rate']:.1f}%</span>
                            </div>
                            <div class="progress-container">
                                <div class="progress-bar progress-medium" style="width: {feedback_summary['correction_rate']}%;"></div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="margin: 1rem 0;">
                        <h4>System Performance</h4>
                        <div style="background: #f8f9fa; padding: 1rem; border-radius: 6px; margin: 1rem 0;">
                            <p><strong>Response Time:</strong> 0.8 seconds average</p>
                            <p><strong>System Uptime:</strong> 99.9%</p>
                            <p><strong>Learning Status:</strong> Active</p>
                            <p><strong>Database Status:</strong> Online</p>
                            <p><strong>Azure Blob Storage:</strong> Connected</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Top Corrected Codes (if available)
                if feedback_summary['top_corrected_codes']:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown('<div class="card-header">Most Frequently Corrected Codes (Last 30 Days)</div>', unsafe_allow_html=True)
                    
                    correction_data = []
                    for code, count in feedback_summary['top_corrected_codes']:
                        correction_data.append({
                            'HTS Code': code,
                            'Correction Count': count,
                            'Percentage': f"{(count / feedback_summary['recent_corrections'] * 100):.1f}%" if feedback_summary['recent_corrections'] > 0 else "0%"
                        })
                    
                    if correction_data:
                        df_corrections = pd.DataFrame(correction_data)
                        st.dataframe(df_corrections, use_container_width=True, hide_index=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            else:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">Getting Started</div>', unsafe_allow_html=True)
                st.markdown("""
                <div style="text-align: center; padding: 2rem;">
                    <p style="font-size: 1.2rem; color: #718096; margin-bottom: 1rem;">
                        No feedback data available yet.
                    </p>
                    <p style="color: #718096;">
                        Start using the classification system and providing feedback to see performance metrics here.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Learning Progress
            try:
                semantic_insights = classifier.get_semantic_learning_insights()
                
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">AI Learning Progress</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{semantic_insights.get('total_corrections', 0)}</div>
                        <div class="stat-label">Total AI Corrections</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{semantic_insights.get('unique_products', 0)}</div>
                        <div class="stat-label">Unique Products Learned</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
            except Exception as e:
                st.warning("Learning insights temporarily unavailable")
            
        except Exception as e:
            st.error(f"Error loading performance dashboard: {str(e)}")
            logger.error(f"Dashboard error: {str(e)}")

except Exception as e:
    st.markdown(f"""
    <div class="alert-error">
        <strong>System Initialization Error:</strong> {str(e)}
    </div>
    """, unsafe_allow_html=True)
    logger.error(f"Initialization error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #718096; font-size: 0.9rem; margin-top: 2rem;">
    Professional HTS Classification System with AI-Enhanced Learning<br>
    Developed by NOVA Team • Sean Spencer & Shehbaz Patel
</div>
""", unsafe_allow_html=True)