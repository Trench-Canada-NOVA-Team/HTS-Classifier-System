import re
import streamlit as st
from pathlib import Path
from data_loader.json_loader import HTSDataLoader
from preprocessor.text_processor import TextPreprocessor
from classifier.feedback_enhanced_classifier import FeedbackEnhancedClassifier
from feedback_handler import FeedbackHandler
import time
from loguru import logger

@st.cache_resource
def initialize_classifier():
    data_dir = Path(__file__).parent.parent / "Data"
    data_loader = HTSDataLoader(str(data_dir))
    preprocessor = TextPreprocessor()
    feedback_handler = FeedbackHandler(use_s3=True)

    # Use FeedbackEnhancedClassifier instead of HTSClassifier
    classifier = FeedbackEnhancedClassifier(data_loader, preprocessor, feedback_handler)
    classifier.build_index()
    return classifier, data_loader

@st.cache_resource
def initialize_feedback_handler():
    """Initialize the feedback handler with S3 support"""
    return FeedbackHandler(use_s3=True)

def get_source_data(data_loader, hts_code):
    """Get the source data for a given HTS code"""
    matches = []
    for entry in data_loader.hts_data:
        if entry.get('htsno', '').startswith(hts_code[:6]):
            matches.append(entry)
    return matches

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

# Custom CSS (Enhanced with semantic learning styles)
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
    .learning-indicator {
        background-color: #E8F5E8;
        border-left: 4px solid #4CAF50;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .feedback-applied {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    /* Enhanced Semantic learning styles with priority indicators */
    .semantic-match {
        background-color: #F0F8FF;
        border-left: 4px solid #4169E1;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .exact-match {
        background-color: #F0FFF0;
        border-left: 4px solid #008000;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .ai-adjusted {
        background-color: #FFF8DC;
        border-left: 4px solid #FFD700;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .fallback-match {
        background-color: #FFF4E6;
        border-left: 4px solid #FF9800;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .priority-1 {
        background-color: #E8F5E8;
        border: 2px solid #4CAF50;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .priority-2 {
        background-color: #E3F2FD;
        border: 2px solid #2196F3;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .priority-2-fallback {
        background-color: #FFF4E6;
        border: 2px solid #FF9800;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .priority-3 {
        background-color: #F5F5F5;
        border: 2px solid #9E9E9E;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .no-results {
        background-color: #FFEBEE;
        border: 2px solid #F44336;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title("🔍 HTS Code Classifier")
st.markdown("""
This tool helps you find the correct Harmonized Tariff Schedule (HTS) code for your products.
Simply enter a product description, and the AI will suggest the most relevant HTS codes with **semantic learning**.
""")

# Initialize the classifier and feedback handler
try:
    classifier, data_loader = initialize_classifier()
    feedback_handler = initialize_feedback_handler()
    
    # Create two columns for layout (KEEPING YOUR ORIGINAL LAYOUT)
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Product Description")
        description = st.text_area("Enter your product description:", height=100, 
                                 placeholder="Example: leather wallet made of genuine cowhide")
        
        # Enhanced learning mode toggle
        learn_from_feedback = st.checkbox("🧠 Enable Semantic Feedback Learning", value=True, 
                                          help="Use past corrections and similar product feedback to improve predictions")
        
        if st.button("Classify", type="primary"):
            if description:
                with st.spinner("Analyzing product description with AI semantic learning..."):
                    try:
                        # Use enhanced classification with semantic feedback learning
                        results = classifier.classify(description, learn_from_feedback=learn_from_feedback)
                        
                        # Store results and description in session state
                        st.session_state.classification_results = results
                        st.session_state.classification_description = description
                        
                        # Display results with ENHANCED priority-based semantic learning indicators
                        st.subheader("Classification Results")
                        
                        # Handle case where no results are returned
                        if not results:
                            st.markdown("""
                            <div class="no-results">
                                ⚠️ <strong>No Classification Results Found</strong><br>
                                The system could not find any matching HTS codes for this product description.<br>
                                Please try rephrasing your description or contact support.
                            </div>
                            """, unsafe_allow_html=True)
                            # FIXED: Removed the 'return' statement that was causing the syntax error
                        else:
                            # Check if semantic feedback learning was applied
                            exact_feedback_used = any(r.get('source') == 'feedback_correction' and r.get('match_type') == 'exact_match' for r in results)
                            semantic_feedback_used = any(r.get('source') == 'semantic_feedback' for r in results)
                            fallback_used = any(r.get('match_type') == 'ai_fallback_match' for r in results)
                            confidence_adjusted = any(r.get('feedback_adjusted') for r in results)
                            
                            # Enhanced priority-based learning status indicators
                            if exact_feedback_used and learn_from_feedback:
                                st.markdown("""
                                <div class="exact-match">
                                    🎯 <strong>PRIORITY 1 - Exact Match Applied:</strong> Found identical product with previous correction!
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if semantic_feedback_used and learn_from_feedback and not fallback_used:
                                st.markdown("""
                                <div class="semantic-match">
                                    🤖 <strong>PRIORITY 2 - AI Semantic Learning Applied:</strong> Found similar products to improve predictions!
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if fallback_used and learn_from_feedback:
                                st.markdown("""
                                <div class="fallback-match">
                                    🔄 <strong>PRIORITY 2D - AI Fallback Applied:</strong> Primary classifier unavailable, using semantic learning as backup!
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if confidence_adjusted and learn_from_feedback and not exact_feedback_used and not semantic_feedback_used:
                                st.markdown("""
                                <div class="ai-adjusted">
                                    🔧 <strong>PRIORITY 3 - AI Confidence Adjustment:</strong> Scores adjusted based on similar product patterns!
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Display results with ENHANCED priority-based semantic indicators
                            for i, result in enumerate(results):
                                # Determine priority class and indicators
                                priority_class = "priority-3"  # Default
                                priority_badge = "🔍 PRIORITY 3"
                                feedback_indicator = ""
                                confidence_color = "black"
                                
                                # HIGHEST PRIORITY: Exact feedback match
                                if result.get('source') == 'feedback_correction' and result.get('match_type') == 'exact_match':
                                    priority_class = "priority-1"
                                    priority_badge = "🥇 PRIORITY 1"
                                    feedback_indicator = " 🎯 **EXACT MATCH** (Highest Priority)"
                                    confidence_color = "green"
                                    
                                # HIGH PRIORITY: Semantic feedback match  
                                elif result.get('source') == 'semantic_feedback':
                                    similarity_score = result.get('similarity_score', 1.0)
                                    match_type = result.get('match_type', 'ai_similar_match')
                                    
                                    if match_type == 'ai_perfect_match':
                                        priority_class = "priority-2"
                                        priority_badge = "🥈 PRIORITY 2A"
                                        feedback_indicator = f" 🤖 **AI PERFECT MATCH** ({similarity_score:.0%}) (High Priority)"
                                        confidence_color = "darkgreen"
                                    elif match_type == 'ai_smart_match':
                                        priority_class = "priority-2"
                                        priority_badge = "🥈 PRIORITY 2B"
                                        feedback_indicator = f" 🤖 **AI SMART MATCH** ({similarity_score:.0%}) (High Priority)"
                                        confidence_color = "blue"
                                    elif match_type == 'ai_fallback_match':
                                        priority_class = "priority-2-fallback"
                                        priority_badge = "🔄 PRIORITY 2D"
                                        feedback_indicator = f" 🔄 **AI FALLBACK MATCH** ({similarity_score:.0%}) (Backup)"
                                        confidence_color = "orange"
                                    else:
                                        priority_class = "priority-2"
                                        priority_badge = "🥉 PRIORITY 2C"
                                        feedback_indicator = f" 🔍 **AI SIMILAR MATCH** ({similarity_score:.0%}) (Medium Priority)"
                                        confidence_color = "darkblue"
                                        
                                # NORMAL PRIORITY: Primary HTS classifier
                                else:
                                    priority_badge = "🔍 PRIORITY 3"
                                    feedback_indicator = " 📊 **HTS CLASSIFICATION** (Standard)"
                                    confidence_color = "black"
                                    
                                    if result.get('feedback_adjusted'):
                                        feedback_indicator += " 🔧 **AI ADJUSTED**"
                                        confidence_color = "orange"
                                
                                # Display result with priority styling
                                with st.container():
                                    st.markdown(f"""
                                    <div class="{priority_class}">
                                    """, unsafe_allow_html=True)
                                    
                                    st.markdown(f"""
                                    ### {priority_badge} Match {i+1}{feedback_indicator}
                                    - **HTS Code:** {result['hts_code']}
                                    - **Description:** {result['description']}
                                    - **Confidence:** <span style="color:{confidence_color}; font-weight:bold;">{result['confidence']:.1f}%</span>
                                    - **General Rate:** {result['general_rate']}
                                    """, unsafe_allow_html=True)
                                    
                                    # Show semantic similarity progress bar for feedback matches
                                    if result.get('similarity_score') and result.get('source') in ['feedback_correction', 'semantic_feedback']:
                                        similarity_value = result['similarity_score']
                                        if similarity_value < 1.0:  # Don't show 100% bar for exact matches
                                            # Color-code the progress bar based on similarity
                                            if similarity_value >= 0.90:
                                                progress_color = "🟢"  # Green for high similarity
                                            elif similarity_value >= 0.80:
                                                progress_color = "🔵"  # Blue for good similarity
                                            elif similarity_value >= 0.70:
                                                progress_color = "🟡"  # Yellow for medium similarity
                                            else:
                                                progress_color = "🟠"  # Orange for lower similarity
                                            
                                            st.progress(similarity_value, text=f"{progress_color} Semantic Similarity: {similarity_value:.1%}")
                                        else:
                                            st.success("🎯 Perfect Match (100%)")
                                    
                                    if result.get('units'):
                                        st.markdown(f"- **Units:** {', '.join(result['units'])}")
                                    
                                    # Show enhanced learning explanation with priority context
                                    if result.get('learning_explanation'):
                                        # Determine the style based on the source and priority
                                        if result.get('match_type') == 'ai_fallback_match':
                                            explanation_class = "fallback-match"
                                            icon = "🔄"
                                            priority_context = "AI Fallback Learning"
                                        elif result.get('source') == 'semantic_feedback':
                                            explanation_class = "semantic-match"
                                            icon = "🤖"
                                            priority_context = "High Priority AI Learning"
                                        elif result.get('source') == 'feedback_correction':
                                            explanation_class = "exact-match"
                                            icon = "🎯"
                                            priority_context = "Highest Priority Exact Match"
                                        else:
                                            explanation_class = "feedback-applied"
                                            icon = "💡"
                                            priority_context = "Standard Classification"
                                        
                                        st.markdown(f"""
                                        <div class="{explanation_class}">
                                            {icon} <strong>{priority_context}:</strong> {result['learning_explanation']}
                                        </div>
                                        """, unsafe_allow_html=True)
                                    
                                    # Source data in expander (KEEPING YOUR ORIGINAL FEATURE)
                                    with st.expander(f"View Source Data for {result['hts_code']}"):
                                        source_matches = get_source_data(data_loader, result['hts_code'])
                                        if source_matches:
                                            for match in source_matches:
                                                st.markdown(f"""
                                                **Code:** {match.get('htsno', 'N/A')}  
                                                **Description:** {match.get('description', 'N/A')}
                                                ---
                                                """)
                                        else:
                                            st.info("No additional source data found for this code.")
                                    
                                    st.markdown("</div>", unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"An error occurred during classification: {str(e)}")
                        logger.error(f"Classification error: {str(e)}")
                        
                        # Show debug information
                        if hasattr(classifier, 'feedback_handler'):
                            try:
                                recent_feedback = classifier._get_recent_feedback_data()
                                st.info(f"📊 Debug: Found {len(recent_feedback)} feedback entries")
                            except Exception as debug_error:
                                st.warning(f"Debug info unavailable: {str(debug_error)}")
            else:
                st.warning("Please enter a product description.")
        
        # Feedback form (ENHANCED with priority context)
        if 'classification_results' in st.session_state and st.session_state.classification_results:
            with st.form(key="feedback_form"):
                st.subheader("📝 Provide Feedback")
                
                # Show what the top result was with enhanced priority information
                top_result = st.session_state.classification_results[0]
                priority_info = ""
                learning_impact = ""
                
                if top_result.get('source') == 'feedback_correction' and top_result.get('match_type') == 'exact_match':
                    priority_info = "🥇 This was a **Priority 1 Exact Match** from previous feedback."
                    learning_impact = "🔄 Your feedback will reinforce or update our exact match learning."
                elif top_result.get('source') == 'semantic_feedback':
                    similarity = top_result.get('similarity_score', 1.0)
                    match_type = top_result.get('match_type', 'ai_similar_match')
                    
                    if match_type == 'ai_fallback_match':
                        priority_info = f"🔄 This was a **Priority 2D AI Fallback Match** ({similarity:.0%} similarity) - primary classifier was unavailable."
                        learning_impact = "🛠️ Your feedback will help improve both semantic learning and primary classifier reliability."
                    else:
                        priority_info = f"🥈 This was a **Priority 2 AI Semantic Match** ({similarity:.0%} similarity)."
                        learning_impact = "🤖 Your feedback will improve our AI semantic matching for similar products."
                else:
                    priority_info = "🔍 This was a **Priority 3 Standard Classification**."
                    learning_impact = "🆕 Your feedback will create new learning data for semantic matching."
                
                st.info(priority_info)
                st.caption(learning_impact)
                
                # Define the regex pattern
                allowed_chars_pattern = r"^\d{4}(?:\.\d{2}){0,3}$"
                
                is_correct = st.radio(
                    "Is the top prediction correct?",
                    ["Yes", "No"],
                    key="feedback_choice"
                )
                
                # Show correct code input if "No" is selected
                correct_code = None
                if is_correct == "No":
                    correct_code = st.text_input(
                        "Please provide the correct HTS code:",
                        max_chars=13,
                        help="Enter the correct HTS code (up to 13 characters).",
                        key="correct_code_input"
                    )
                    
                    # Validation
                    if correct_code and not re.match(allowed_chars_pattern, correct_code):
                        st.error("Invalid Format: HS Code can only contain digits and periods (e.g., 1234.56.78.90)")
                    elif correct_code not in (None, ""):
                        st.success("Input format is valid.")
                
                # Submit button
                submit_feedback = st.form_submit_button("Submit Feedback")
                
                if submit_feedback:
                    logger.info("Submitting feedback...")
                    try:
                        # Get results and description from session state
                        results = st.session_state.classification_results
                        description = st.session_state.classification_description
                        
                        if is_correct == "Yes":
                            # Use enhanced classifier's feedback method
                            success = classifier.add_feedback(
                                product_description=description,
                                predicted_code=results[0]['hts_code'],
                                correct_code=results[0]['hts_code']
                            )
                            
                            if success:
                                st.success("✅ Thank you! Prediction marked as correct!")
                                st.info("🧠 This feedback will help improve future predictions for similar products!")
                                
                                # Show learning impact based on result type
                                if results[0].get('source') == 'feedback_correction':
                                    st.success("🎯 This reinforces our exact match learning!")
                                elif results[0].get('source') == 'semantic_feedback':
                                    if results[0].get('match_type') == 'ai_fallback_match':
                                        st.success("🔄 This validates our AI fallback system!")
                                    else:
                                        st.success("🤖 This validates our AI semantic matching!")
                                else:
                                    st.success("📊 This creates new learning data for semantic matching!")
                            else:
                                st.warning("⚠️ Feedback saved but couldn't update learning immediately.")
                            
                            # Clear session state
                            del st.session_state.classification_results
                            del st.session_state.classification_description
                            
                            time.sleep(1)
                            st.rerun()
                            
                        else:  # No - correction needed
                            if not correct_code:
                                st.error("⚠️ Please enter the correct HTS code.")
                            elif correct_code and not re.match(allowed_chars_pattern, correct_code):
                                st.error("⚠️ Invalid format: HS Code can only contain digits and periods.")
                            else:
                                # Format the correct code
                                formatted_correct_code = format_hs_code(correct_code)
                                
                                logger.info(f"Adding correction: {results[0]['hts_code']} -> {formatted_correct_code}")
                                
                                # Use enhanced classifier's feedback method
                                success = classifier.add_feedback(
                                    product_description=description,
                                    predicted_code=results[0]['hts_code'],
                                    correct_code=formatted_correct_code
                                )
                                
                                if success:
                                    st.success(f"✅ Thank you! Corrected to {formatted_correct_code}")
                                    st.info("🧠 This correction has been learned and will help classify similar products!")
                                    
                                    # Show learning impact based on previous result type
                                    if results[0].get('source') == 'feedback_correction':
                                        st.info("🔄 This updates our exact match learning data!")
                                    elif results[0].get('source') == 'semantic_feedback':
                                        if results[0].get('match_type') == 'ai_fallback_match':
                                            st.info("🛠️ This improves our AI fallback system and creates stronger learning data!")
                                        else:
                                            st.info("🤖 This improves our AI semantic matching patterns!")
                                    else:
                                        st.info("🆕 This creates new learning data for future semantic matching!")
                                else:
                                    st.warning("⚠️ Feedback saved but couldn't update learning immediately.")
                                
                                # Clear session state
                                del st.session_state.classification_results
                                del st.session_state.classification_description
                            
                                time.sleep(1)
                                st.rerun()
                                
                    except Exception as e:
                        logger.error(f"Error saving feedback: {str(e)}")
                        st.error(f"Error saving feedback: {str(e)}")
    
    # ENHANCED RIGHT COLUMN with semantic analytics
    with col2:
        st.subheader("Feedback Statistics")
        
        # Use enhanced stats if available
        try:
            if hasattr(classifier, 'get_semantic_learning_insights'):
                semantic_insights = classifier.get_semantic_learning_insights(days=30)
                stats = feedback_handler.get_feedback_stats()
            else:
                stats = feedback_handler.get_feedback_stats()
                semantic_insights = {}
        except Exception as e:
            logger.warning(f"Error getting enhanced stats: {str(e)}")
            stats = feedback_handler.get_feedback_stats()
            semantic_insights = {}
        
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            st.metric("Total Entries", stats['total_entries'])
            # Add semantic learning metrics
            if semantic_insights.get('total_corrections'):
                st.metric("AI Corrections", semantic_insights['total_corrections'])
        with col2_2:
            st.metric("Accuracy", f"{stats['accuracy']*100:.1f}%")
            # Add S3 storage indicator
            storage_location = stats.get('storage_location', 'Unknown')
            if storage_location == "S3":
                st.success("☁️ Cloud Storage")
            else:
                st.info("💾 Local Storage")
        
        # Enhanced learning status indicator with priority information
        st.subheader("🧠 AI Learning Status")
        try:
            if hasattr(classifier, 'auto_retrain_enabled') and classifier.auto_retrain_enabled:
                st.success("✅ Semantic Learning Active")
                st.caption("🥇 Priority 1: Exact matches")
                st.caption("🥈 Priority 2: AI semantic matches (70%+ similarity)")
                st.caption("🔄 Priority 2D: AI fallback (when primary fails)")
                st.caption("🔍 Priority 3: Standard HTS classification")
            else:
                st.info("⏸️ Learning Available")
            
            # Show semantic learning coverage if available
            if semantic_insights.get('coverage_analysis'):
                coverage = semantic_insights['coverage_analysis']
                correction_rate = coverage.get('correction_rate', 0)
                if correction_rate > 70:
                    st.success(f"🎯 High Learning Potential ({correction_rate:.0f}%)")
                elif correction_rate > 30:
                    st.info(f"📈 Good Learning Data ({correction_rate:.0f}%)")
                else:
                    st.warning(f"⚠️ Building Learning Data ({correction_rate:.0f}%)")
        except:
            st.info("📊 Feedback Collection Active")
        
        # Enhanced recent entries display with priority indicators
        if stats['recent_entries']:
            st.subheader("Recent Feedback")
            for entry in stats['recent_entries'][:5]:
                # Add enhanced learning indicators to recent entries
                learning_badge = ""
                priority_indicator = ""
                
                if entry['predicted_code'] != entry['correct_code']:
                    learning_badge = " 🧠"  # Correction that will help learning
                    priority_indicator = "🆕 Creates learning data"
                else:
                    learning_badge = " ✅"  # Confirmation
                    priority_indicator = "🔄 Reinforces learning"
                
                st.markdown(f"""
                ---
                **Description:** {entry['description'][:50]}...{learning_badge}  
                **Predicted:** {entry['predicted_code']}  
                **Actual:** {entry['correct_code']}  
                *{priority_indicator}*
                """)
        else:
            st.info("No feedback entries yet.")

    # ENHANCED Learning insights section with priority information
    st.markdown("---")

    with st.expander("📊 AI Learning Insights & Analytics", expanded=False):
        col_insights1, col_insights2 = st.columns(2)
        
        with col_insights1:
            st.subheader("🔍 Priority-Based Learning Patterns")
            
            try:
                # Show semantic learning patterns if available
                if semantic_insights.get('top_correction_patterns'):
                    st.write("**Top AI Learning Patterns:**")
                    for pattern_info in semantic_insights['top_correction_patterns'][:5]:
                        st.write(f"• {pattern_info['pattern']}: {pattern_info['count']} corrections")
                        st.caption("   🥈 Priority 2 semantic learning source")
                else:
                    # Fallback to regular correction patterns
                    if hasattr(classifier, 'feedback_handler'):
                        patterns = classifier.feedback_handler.get_correction_patterns(days=7)
                        
                        if patterns:
                            st.write("**Recent Correction Patterns:**")
                            pattern_count = 0
                            for pattern_key, corrections in patterns.items():
                                if pattern_count >= 5:
                                    break
                                st.write(f"• {pattern_key}: {len(corrections)} corrections")
                                st.caption("   🥇 Priority 1 exact match source")
                                pattern_count += 1
                        else:
                            st.info("No recent correction patterns found.")
                    else:
                        st.info("Learning analytics not available.")
            except Exception as e:
                st.info("Learning analytics not available.")
        
        with col_insights2:
            st.subheader("🎯 Training Actions")
            
            # Enhanced cache refresh for semantic learning
            if st.button("🔄 Refresh AI Learning Cache"):
                try:
                    # Clear semantic feedback cache
                    if hasattr(classifier, 'feedback_cache'):
                        classifier.feedback_cache.clear()
                    st.success("✅ AI learning cache refreshed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error refreshing cache: {str(e)}")
            
            # Manual retraining button
            if st.button("🔄 Retrain with Latest Feedback"):
                with st.spinner("Retraining classifier with latest feedback..."):
                    try:
                        # Clear cache and reinitialize
                        st.cache_resource.clear()
                        classifier, data_loader = initialize_classifier()
                        st.success("✅ Classifier retrained with latest feedback!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during retraining: {str(e)}")
                        logger.error(f"Retraining error: {str(e)}")
            
            # Show enhanced training status with thresholds
            try:
                if hasattr(classifier, 'semantic_threshold'):
                    st.caption(f"Semantic threshold: {classifier.semantic_threshold:.0%}")
                if hasattr(classifier, 'high_confidence_threshold'):
                    st.caption(f"High confidence: {classifier.high_confidence_threshold:.0%}")
                if hasattr(classifier, 'very_high_confidence_threshold'):
                    st.caption(f"Very high confidence: {classifier.very_high_confidence_threshold:.0%}")
                if hasattr(classifier, 'last_feedback_check'):
                    st.caption(f"Last check: {classifier.last_feedback_check.strftime('%H:%M:%S')}")
                else:
                    st.caption("Training status: Active")
            except:
                st.caption("Training status: Available")

    # ENHANCED Learning tips section with fallback information
    with st.expander("💡 How Enhanced Priority-Based Semantic Learning Works", expanded=False):
        st.markdown("""
        ### 🎯 Enhanced Priority-Based Learning System:
        
        #### 🥇 **PRIORITY 1 - Exact Match Learning (Highest)**
        - **100% Match**: Previous corrections for identical products are automatically applied
        - **95% Confidence**: Highest confidence scoring for exact matches
        - **Immediate Application**: Takes precedence over all other results
        
        #### 🥈 **PRIORITY 2 - AI Semantic Learning (High)**
        - **🤖 AI Perfect Match**: Virtually identical products (88%+ similarity)
        - **🤖 AI Smart Match**: Very similar products (78-88% similarity)
        - **🔍 AI Similar Match**: Similar products (70-78% similarity)
        - **🔄 AI Fallback Match**: Backup when primary classifier fails (70%+ similarity)
        - **Dynamic Confidence**: Confidence scaled based on similarity percentage
        
        #### 🔍 **PRIORITY 3 - Standard HTS Classification (Normal)**
        - **Primary Database**: Uses original HTS Pinecone vector search
        - **Pattern Adjustments**: Confidence modified by feedback patterns
        - **Fallback System**: Always available when no learning data exists
        
        ### 📈 What You'll See (Enhanced):
        
        - **🥇 PRIORITY 1**: Result from identical product correction (100% similarity)
        - **🥈 PRIORITY 2A**: AI Perfect Match (88%+ similarity)
        - **🥈 PRIORITY 2B**: AI Smart Match (78-88% similarity)  
        - **🥉 PRIORITY 2C**: AI Similar Match (70-78% similarity)
        - **🔄 PRIORITY 2D**: AI Fallback Match (70%+ similarity, primary unavailable)
        - **🔍 PRIORITY 3**: Standard HTS classification with optional AI adjustments
        
        ### 🎯 Learning Flow Examples:
        
        #### **Exact Match Scenario:**
        ```
        Input: "leather handbag"
        Previous Feedback: "leather handbag" → 4202.21.90.00
        Result: 🥇 PRIORITY 1 🎯 EXACT MATCH (95% confidence)
        ```
        
        #### **Semantic Match Scenario:**
        ```
        Input: "genuine leather purse"
        Similar Feedback: "leather handbag" → 4202.21.90.00 (82% similarity)
        Result: 🥈 PRIORITY 2B 🤖 AI SMART MATCH (82%)
        ```
        
        #### **Fallback Scenario:**
        ```
        Input: "women's leather wallet"
        Similar Feedback: "leather handbag" → 4202.21.90.00 (75% similarity)
        Primary Classifier: Failed/Unavailable
        Result: 🔄 PRIORITY 2D 🔄 AI FALLBACK MATCH (75%)
        ```
        
        #### **Standard Classification:**
        ```
        Input: "steel bolts" (no feedback data)
        Result: 🔍 PRIORITY 3 📊 HTS CLASSIFICATION
        ```
        
        ### 🚀 Enhanced Best Practices:
        
        - **Lowered Thresholds**: Now accepts 70%+ similarity (was 75%)
        - **Fallback Protection**: AI learning works even when primary fails
        - **Consistent Terminology**: Use similar terms for related products
        - **Detailed Descriptions**: More details = better semantic matching
        - **Priority Understanding**: Higher priority results are more reliable
        - **Feedback Impact**: Each correction creates learning opportunities
        - **System Resilience**: Multiple fallback layers ensure results
        
        ### 🧠 Technical Enhancement:
        
        - **Step 1**: Check for exact text matches in feedback data
        - **Step 2**: Calculate semantic similarity using OpenAI embeddings
        - **Step 3**: Apply cosine similarity with lowered thresholds (70/78/88%)
        - **Step 4**: Use semantic learning as fallback when primary fails
        - **Step 5**: Fallback to primary HTS classification system
        - **Priority Override**: Higher priority results override lower ones
        - **Graceful Degradation**: Always provides some result when possible
        """)
            
except Exception as e:
    st.error(f"Error initializing the classifier: {str(e)}")
    logger.error(f"Initialization error: {str(e)}")

# Footer (ENHANCED)
st.markdown("---")
st.markdown("""
*This is an AI-powered tool with enhanced priority-based semantic machine learning capabilities and intelligent fallback systems. 
The verification data is extracted directly from the official HTS database. 
Please verify the results with official HTS documentation for critical decisions.*
""")