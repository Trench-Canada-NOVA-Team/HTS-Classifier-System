from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from .hts_classifier import HTSClassifier
from utils.azure_blob_helper import FeedbackHandler
from utils.azure_blob_feedback_trainer import AzureFeedbackTrainer
from config.settings import Config  # Import the configuration


class FeedbackEnhancedClassifier(HTSClassifier):
    def __init__(self, data_loader, preprocessor, feedback_handler=None, faiss_service=None):
        """
        Initialize the FeedbackEnhancedClassifier with semantic learning capabilities.
        
        Args:
            data_loader: Data loader instance
            preprocessor: Text preprocessor instance (with OpenAI embeddings)
            feedback_handler: Optional feedback handler instance
            faiss_service: Optional FAISS service for feedback embeddings
        """
        # Initialize FAISS service first
        self.faiss_service = faiss_service
        if self.faiss_service:
            self.faiss_service.initialize_index()
            logger.info("FAISS service initialized for enhanced classifier")
        
        # Initialize parent with FAISS service
        super().__init__(data_loader, preprocessor, faiss_service)
        
        # Initialize feedback handler with FAISS service (no preprocessor parameter)
        if feedback_handler is None:
            from utils.azure_blob_helper import FeedbackHandler
            self.feedback_handler = FeedbackHandler(use_s3=True, faiss_service=self.faiss_service)
        else:
            self.feedback_handler = feedback_handler
        
        # Use configuration for semantic similarity settings
        self.semantic_threshold = Config.SEMANTIC_THRESHOLD
        self.high_confidence_threshold = Config.HIGH_CONFIDENCE_THRESHOLD
        self.very_high_confidence_threshold = Config.VERY_HIGH_CONFIDENCE_THRESHOLD
        
        # Performance optimization settings from config
        self.last_feedback_check = datetime.now()
        self.feedback_cache = {}
        self.cache_duration = Config.FEEDBACK_CACHE_DURATION
        
        # Initialize Azure trainer if available
        try:
            self.azure_trainer = AzureFeedbackTrainer(feedback_handler)
            self.auto_retrain_enabled = True
            logger.info("AzureFeedbackTrainer initialized successfully")
        except Exception as e:
            logger.warning(f"AzureFeedbackTrainer initialization failed: {str(e)}")
            self.azure_trainer = None
            self.auto_retrain_enabled = False
        
        logger.info("FeedbackEnhancedClassifier initialized with semantic learning capabilities")
    
    def classify(self, product_description: str, top_k: int = 3, country_code: str = None, 
                learn_from_feedback: bool = True) -> List[Dict]:
        """
        Enhanced classification with semantic feedback learning.
        
        Priority Order:
        1. Exact match from feedback data (HIGHEST PRIORITY)
        2. Semantic match from feedback data (HIGH PRIORITY) 
        3. Primary HTS classifier (NORMAL PRIORITY)
        
        Args:
            product_description: Product description to classify
            top_k: Number of top results to return
            country_code: Optional country code for specific rates
            learn_from_feedback: Whether to apply feedback corrections
            
        Returns:
            List of classification results with semantic feedback enhancements
        """
        try:
            logger.info(f"🔍 Starting enhanced classification for: '{product_description}'")
            logger.info(f"🧠 Learning enabled: {learn_from_feedback}")
            
            # STEP 1: Check for exact feedback matches first (HIGHEST PRIORITY)
            if learn_from_feedback:
                logger.info("🎯 STEP 1: Checking for exact feedback matches...")
                exact_match = self._check_exact_feedback_match(product_description)
                
                if exact_match:
                    logger.info("🎯 Found exact feedback match - using learned correction")
                    feedback_result = self._create_exact_feedback_result(exact_match)
                    return [feedback_result]  # Return only the exact match with highest confidence
            
             # STEP 2: Check for semantic feedback matches (HIGH PRIORITY)
            if learn_from_feedback:
                logger.info("🤖 STEP 2: Checking for semantic feedback matches...")
                semantic_matches = self._find_semantic_feedback_matches(product_description)
                
                if semantic_matches:
                    logger.info(f"🤖 Found {len(semantic_matches)} semantic matches")
                    best_semantic_match = semantic_matches[0]  # Highest similarity
                    
                    # If semantic match is very strong (88%+), prioritize it
                    if best_semantic_match['similarity_score'] >= self.very_high_confidence_threshold:
                        logger.info(f"🤖 Strong semantic match found (similarity: {best_semantic_match['similarity_score']:.1%})")
                        semantic_result = self._create_semantic_feedback_result(best_semantic_match, 'very_high')
                        return [semantic_result]  # Return only the semantic match
                    
                    # If semantic match is good (78%+), prioritize it or combine with primary
                    elif best_semantic_match['similarity_score'] >= self.high_confidence_threshold:
                        logger.info(f"🤖 Good semantic match found (similarity: {best_semantic_match['similarity_score']:.1%})")
                        semantic_result = self._create_semantic_feedback_result(best_semantic_match, 'high')
                        
                        # Get primary results as backup
                        logger.info("📊 Getting primary classification as backup...")
                        primary_results = super().classify(product_description, top_k-1, country_code)
                        
                        # Return semantic result first, then primary results (if any)
                        if primary_results:
                            return [semantic_result] + primary_results[:2]
                        else:
                            logger.info("📊 Primary classifier failed, using semantic match only")
                            return [semantic_result]  # Use semantic match when primary fails
                    
                    # ADDED: Handle medium confidence matches (70-78%) when primary fails
                    elif best_semantic_match['similarity_score'] >= self.semantic_threshold:
                        logger.info(f"🤖 Medium semantic match found (similarity: {best_semantic_match['similarity_score']:.1%})")
                        
                        # Try primary first
                        logger.info("📊 Getting primary classification...")
                        primary_results = super().classify(product_description, top_k, country_code)
                        
                        if primary_results:
                            # Apply pattern adjustments with semantic matches
                            enhanced_results = self._apply_semantic_pattern_adjustments(primary_results, semantic_matches)
                            return enhanced_results
                        else:
                            logger.info("📊 Primary classifier failed, using medium semantic match as fallback")
                            semantic_result = self._create_semantic_feedback_result(best_semantic_match, 'medium')
                            return [semantic_result]  # Use semantic match as fallback
            
            # STEP 3: Use primary HTS classifier (NORMAL PRIORITY)
            logger.info("📊 STEP 3: Using primary HTS classifier...")
            primary_results = super().classify(product_description, top_k, country_code)
            
            if primary_results:
                logger.info(f"📊 Primary classifier returned {len(primary_results)} results")
                # Apply confidence adjustments based on feedback patterns if learning is enabled
                if learn_from_feedback:
                    enhanced_results = self._apply_semantic_pattern_adjustments(primary_results, [])
                    return enhanced_results
                else:
                    return primary_results
            else:
                logger.warning("📊 Primary classifier returned no results")
                
                # ADDED: Final fallback - use any semantic matches if available
                if learn_from_feedback:
                    logger.info("🔄 Checking for any semantic matches as final fallback...")
                    semantic_matches = self._find_semantic_feedback_matches(product_description)
                    if semantic_matches:
                        best_match = semantic_matches[0]
                        logger.info(f"🔄 Using semantic fallback (similarity: {best_match['similarity_score']:.1%})")
                        semantic_result = self._create_semantic_feedback_result(best_match, 'fallback')
                        return [semantic_result]
                
                return []  # No results available
            
        except Exception as e:
            logger.error(f"Error in enhanced classification: {str(e)}")
            # Fallback to base classification
            try:
                logger.info("🔄 Falling back to base classification...")
                return super().classify(product_description, top_k, country_code)
            except Exception as fallback_error:
                logger.error(f"Fallback classification also failed: {str(fallback_error)}")
                return []
    
    def _check_exact_feedback_match(self, product_description: str) -> Optional[Dict]:
        """
        Check for exact matches in feedback data using Langchain FAISS first, then fallback.
        
        Args:
            product_description: Product description to check
            
        Returns:
            Dictionary with exact match data or None
        """
        try:
            # Try Langchain FAISS first if available
            if self.faiss_service:
                exact_match = self.faiss_service.check_exact_match(product_description)
                if exact_match:
                    logger.info("🎯 Found exact feedback match via Langchain FAISS")
                    return exact_match
            
            # Fallback to original method
            recent_feedback = self._get_recent_feedback_data()
            
            if recent_feedback.empty:
                logger.info("🎯 No feedback data available for exact matching")
                return None
            
            # Look for exact description match (case-insensitive)
            exact_matches = recent_feedback[
                recent_feedback['description'].str.lower().str.strip() == product_description.lower().strip()
            ]
            
            if not exact_matches.empty:
                # Get the most recent exact match
                latest_match = exact_matches.iloc[-1]
                
                logger.info(f"🎯 Found exact feedback match for product: {latest_match['correct_code']}")
                
                return {
                    'description': latest_match['description'],
                    'predicted_code': latest_match['predicted_code'],
                    'correct_code': latest_match['correct_code'],
                    'similarity_score': 1.0,  # Exact match
                    'timestamp': latest_match['timestamp']
                }
            
            logger.info("🎯 No exact matches found in feedback data")
            return None
            
        except Exception as e:
            logger.error(f"Error checking exact feedback matches: {str(e)}")
            return None
    
    def _find_semantic_feedback_matches(self, product_description: str) -> List[Dict]:
        """
        Find semantically similar products using Langchain FAISS first, then fallback to re-embedding.
        
        Args:
            product_description: Product description to find matches for
            
        Returns:
            List of similar feedback matches with similarity scores
        """
        try:
            # Try Langchain FAISS first if available
            if self.faiss_service:
                logger.info("🤖 Using Langchain FAISS for semantic feedback matching")
                
                # Search using Langchain FAISS (no manual embedding needed)
                semantic_matches = self.faiss_service.search_similar_feedback(
                    product_description, 
                    top_k=10, 
                    similarity_threshold=self.semantic_threshold
                )
                
                if semantic_matches:
                    # Add confidence scores
                    for match in semantic_matches:
                        match['confidence'] = self._calculate_semantic_confidence(match['similarity_score'])
                    
                    logger.info(f"🤖 Langchain FAISS found {len(semantic_matches)} semantic matches")
                    return semantic_matches
                else:
                    logger.info("🤖 No semantic matches found in Langchain FAISS")
            
            # Fallback to original re-embedding method
            logger.info("🤖 Falling back to re-embedding method for semantic matching")
            return self._find_semantic_feedback_matches_fallback(product_description)
            
        except Exception as e:
            logger.error(f"Error finding semantic feedback matches via Langchain: {str(e)}")
            # Fallback to original method
            return self._find_semantic_feedback_matches_fallback(product_description)
    
    def _find_semantic_feedback_matches_fallback(self, product_description: str) -> List[Dict]:
        """
        Original semantic matching method using re-embedding (fallback).
        """
        try:
            # Get recent feedback data
            recent_feedback = self._get_recent_feedback_data()
            
            if recent_feedback.empty:
                logger.info("🤖 No feedback data available for semantic matching")
                return []
            
            logger.info(f"🤖 Analyzing {len(recent_feedback)} feedback entries for semantic similarity...")
            
            # Generate embedding for input description using your existing preprocessor
            input_embedding = self.preprocessor.encode_text([product_description])[0]
            logger.info(f"🤖 Generated input embedding with shape: {input_embedding.shape}")
            
            # Get embeddings for all feedback descriptions
            feedback_descriptions = recent_feedback['description'].tolist()
            feedback_embeddings = self.preprocessor.encode_text(feedback_descriptions)
            logger.info(f"🤖 Generated {len(feedback_embeddings)} feedback embeddings")
            
            # Calculate semantic similarities using pure NumPy (no scikit-learn)
            semantic_matches = []
            for idx, feedback_embedding in enumerate(feedback_embeddings):
                
                # Calculate cosine similarity without scikit-learn
                similarity = self._calculate_cosine_similarity(input_embedding, feedback_embedding)
                
                if similarity >= self.semantic_threshold:
                    feedback_row = recent_feedback.iloc[idx]
                    
                    # Only include corrections (where predicted != correct)
                    if feedback_row['predicted_code'] != feedback_row['correct_code']:
                        semantic_matches.append({
                            'description': feedback_row['description'],
                            'predicted_code': feedback_row['predicted_code'],
                            'correct_code': feedback_row['correct_code'],
                            'similarity_score': float(similarity),
                            'timestamp': feedback_row['timestamp'],
                            'confidence': self._calculate_semantic_confidence(similarity)
                        })
                        logger.info(f"🤖 Found semantic match: {similarity:.1%} similarity - '{feedback_row['description'][:50]}...'")
            
            # Sort by similarity (highest first)
            semantic_matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            logger.info(f"🤖 Found {len(semantic_matches)} semantic matches above {self.semantic_threshold:.1%} threshold")
            return semantic_matches
            
        except Exception as e:
            logger.error(f"Error finding semantic feedback matches (fallback): {str(e)}")
            return []
    
    def _calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings using pure NumPy.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # Ensure embeddings are numpy arrays
            embedding1 = np.array(embedding1)
            embedding2 = np.array(embedding2)
            
            # Calculate norms
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity using dot product
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            # Ensure result is between 0 and 1 (handle floating point errors)
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
    
    def _calculate_semantic_confidence(self, similarity_score: float) -> float:
        """
        Calculate confidence based on semantic similarity score.
        
        Args:
            similarity_score: Cosine similarity score (0-1)
            
        Returns:
            Confidence percentage (70-95)
        """
        # Scale confidence based on similarity:
        # 75% similarity = 80% confidence
        # 85% similarity = 90% confidence  
        # 95% similarity = 95% confidence
        base_confidence = 70
        similarity_bonus = (similarity_score - self.semantic_threshold) * 100
        return min(95, base_confidence + similarity_bonus)
    
    # Update the _create_semantic_feedback_result method around line 320:

    def _create_semantic_feedback_result(self, semantic_match: Dict, confidence_level: str = 'medium') -> Dict:
        """
        Create a result based on semantic feedback match.
        
        Args:
            semantic_match: Semantic match data with similarity score
            confidence_level: 'very_high', 'high', 'medium', or 'fallback'
            
        Returns:
            Dictionary with semantic feedback-based result
        """
        try:
            # Get HTS data for the correct code
            hts_info = self._get_hts_info_for_code(semantic_match['correct_code'])
            
            similarity_percentage = semantic_match['similarity_score'] * 100
            
            # Determine match type and confidence based on similarity
            if confidence_level == 'very_high':
                match_type = 'ai_perfect_match'
                confidence = min(98, semantic_match['confidence'] + 5)
                explanation = f"AI found virtually identical product (similarity: {similarity_percentage:.1f}%): '{semantic_match['description'][:60]}...'"
            elif confidence_level == 'high':
                match_type = 'ai_smart_match'
                confidence = semantic_match['confidence']
                explanation = f"AI found very similar product (similarity: {similarity_percentage:.1f}%): '{semantic_match['description'][:60]}...'"
            elif confidence_level == 'fallback':
                match_type = 'ai_fallback_match'
                confidence = max(65, semantic_match['confidence'] - 10)  # Lower confidence for fallback
                explanation = f"AI fallback match (similarity: {similarity_percentage:.1f}%): '{semantic_match['description'][:60]}...' - Primary classifier unavailable"
            else:  # medium
                match_type = 'ai_similar_match'
                confidence = max(70, semantic_match['confidence'] - 5)
                explanation = f"AI found similar product (similarity: {similarity_percentage:.1f}%): '{semantic_match['description'][:60]}...'"
            
            result = {
                'hts_code': semantic_match['correct_code'],
                'description': hts_info.get('description', 'Result from semantic feedback learning'),
                'confidence': confidence,
                'general_rate': hts_info.get('general_rate', 'Contact for rate'),
                'units': hts_info.get('units', []),
                'source': 'semantic_feedback',
                'similarity_score': semantic_match['similarity_score'],
                'match_type': match_type,
                'feedback_description': semantic_match['description'],
                'learning_explanation': explanation
            }
            
            logger.info(f"🤖 Created semantic result: {match_type} with {confidence}% confidence")
            return result
            
        except Exception as e:
            logger.error(f"Error creating semantic feedback result: {str(e)}")
            # Return basic semantic result
            return {
                'hts_code': semantic_match['correct_code'],
                'description': 'Result from semantic feedback learning',
                'confidence': semantic_match['confidence'],
                'general_rate': 'Contact for rate',
                'units': [],
                'source': 'semantic_feedback',
                'similarity_score': semantic_match['similarity_score'],
                'match_type': 'ai_similar_match',
                'learning_explanation': f"Similar product match (similarity: {semantic_match['similarity_score']:.1%})"
            }
    
    def _apply_semantic_pattern_adjustments(self, base_results: List[Dict], semantic_matches: List[Dict]) -> List[Dict]:
        """
        Apply confidence adjustments based on semantic feedback patterns.
        
        Args:
            base_results: Original classification results
            semantic_matches: List of semantic feedback matches
            
        Returns:
            Results with confidence adjustments applied
        """
        enhanced_results = []
        
        for result in base_results:
            enhanced_result = result.copy()
            
            # Check if this HTS code category was corrected in similar products
            result_chapter = result['hts_code'][:2] if len(result['hts_code']) >= 2 else ''
            
            correction_count = 0
            total_similarity = 0
            correction_details = []
            
            for match in semantic_matches:
                match_predicted_chapter = match['predicted_code'][:2] if len(match['predicted_code']) >= 2 else ''
                match_correct_chapter = match['correct_code'][:2] if len(match['correct_code']) >= 2 else ''
                
                # If this chapter was corrected in similar products
                if (match_predicted_chapter == result_chapter and 
                    match_predicted_chapter != match_correct_chapter):
                    correction_count += 1
                    total_similarity += match['similarity_score']
                    correction_details.append({
                        'from_chapter': match_predicted_chapter,
                        'to_chapter': match_correct_chapter,
                        'similarity': match['similarity_score']
                    })
            
            # Apply confidence adjustment based on correction patterns
            if correction_count > 0:
                avg_similarity = total_similarity / correction_count
                confidence_reduction = min(30, correction_count * 10 * avg_similarity)  # Max 30% reduction
                
                enhanced_result['confidence'] = max(10, result['confidence'] - confidence_reduction)
                enhanced_result['feedback_adjusted'] = True
                enhanced_result['learning_explanation'] = (
                    f"Confidence adjusted based on {correction_count} similar product correction(s) "
                    f"(avg. similarity: {avg_similarity:.1%})"
                )
                
                logger.info(f"🔧 Applied semantic pattern adjustment to {result['hts_code']} "
                          f"(reduced confidence by {confidence_reduction:.1f}%)")
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _get_recent_feedback_data(self, days: int = None) -> pd.DataFrame:
        """
        Get recent feedback data from the feedback handler with caching.
        
        Args:
            days: Number of days to retrieve (uses config default if not provided)
            
        Returns:
            DataFrame with recent feedback data
        """
        # Use configuration default if not provided
        days = days or Config.DEFAULT_FEEDBACK_DAYS
        
        try:
            # Check cache first
            cache_key = f"feedback_data_{days}d"
            if (cache_key in self.feedback_cache and 
                datetime.now() - self.last_feedback_check < timedelta(minutes=self.cache_duration)):
                logger.info(f"📊 Using cached feedback data ({len(self.feedback_cache[cache_key])} entries)")
                return self.feedback_cache[cache_key]
            
            logger.info(f"📊 Loading fresh feedback data (last {days} days)...")
            
            # Get fresh data from feedback handler
            if hasattr(self.feedback_handler, 'get_recent_feedback'):
                feedback_df = self.feedback_handler.get_recent_feedback(days=days)
            else:
                # Fallback to basic feedback data loading
                feedback_df = self.feedback_handler._load_feedback_data()
                if not feedback_df.empty:
                    # Filter to recent entries
                    feedback_df['timestamp'] = pd.to_datetime(feedback_df['timestamp'])
                    cutoff_date = datetime.now() - timedelta(days=days)
                    feedback_df = feedback_df[feedback_df['timestamp'] >= cutoff_date]
            
            logger.info(f"📊 Loaded {len(feedback_df)} feedback entries")
            ##############################
            logger.debug(feedback_df.head())
            ##############################
            
            # Cache the result
            self.feedback_cache[cache_key] = feedback_df
            self.last_feedback_check = datetime.now()
            
            return feedback_df
            
        except Exception as e:
            logger.error(f"Error getting recent feedback data: {str(e)}")
            return pd.DataFrame()
    
    def _get_hts_info_for_code(self, hts_code: str) -> Dict:
        """
        Get HTS information for a specific code.
        
        Args:
            hts_code: HTS code to look up
            
        Returns:
            Dictionary with HTS information
        """
        try:
            # Clean the HTS code
            if isinstance(hts_code, list):
                hts_code = str(hts_code[0]) if hts_code else ""
            hts_code = str(hts_code).strip()
            
            # Search in HTS data
            for entry in self.data_loader.hts_data:
                entry_code = entry.get('htsno', '')
                
                # Handle if entry_code is a list
                if isinstance(entry_code, list):
                    entry_code = str(entry_code[0]) if entry_code else ""
                entry_code = str(entry_code).strip()
                
                if entry_code.startswith(hts_code[:6]) or entry_code == hts_code:
                    # Handle description - could be string or list
                    description = entry.get('description', 'HTS Classification')
                    if isinstance(description, list):
                        description = ' '.join(str(d) for d in description)
                    
                    # Handle general_rate - could be string or list  
                    general_rate = entry.get('general_rate', 'Contact for rate')
                    if isinstance(general_rate, list):
                        general_rate = str(general_rate[0]) if general_rate else 'Contact for rate'
                    
                    # Handle units - ensure it's a list
                    units = entry.get('units', [])
                    if isinstance(units, str):
                        units = [units]
                    elif not isinstance(units, list):
                        units = [str(units)] if units else []
                    
                    return {
                        'description': str(description).strip(),
                        'general_rate': str(general_rate).strip(),
                        'units': units
                    }
            
            # Fallback if not found
            logger.warning(f"HTS code {hts_code} not found in data")
            return {
                'description': f'HTS Code {hts_code}',
                'general_rate': 'Contact for rate',
                'units': []
            }
            
        except Exception as e:
            logger.error(f"Error getting HTS info for code {hts_code}: {str(e)}")
            return {
                'description': f'HTS Code {hts_code}',
                'general_rate': 'Contact for rate',
                'units': []
            }
    
    def _create_exact_feedback_result(self, exact_match: Dict) -> Dict:
        """
        Create result from exact feedback match with highest priority.
        
        Args:
            exact_match: Exact match data
            
        Returns:
            Dictionary with exact feedback result
        """
        try:
            hts_info = self._get_hts_info_for_code(exact_match['correct_code'])
            
            result = {
                'hts_code': exact_match['correct_code'],
                'description': hts_info.get('description', 'Result from exact feedback match'),
                'confidence': 95.0,  # High confidence for exact matches
                'general_rate': hts_info.get('general_rate', 'Contact for rate'),
                'units': hts_info.get('units', []),
                'source': 'feedback_correction',
                'match_type': 'exact_match',
                'similarity_score': 1.0,  # Perfect match
                'learning_explanation': 'This result comes from an exact feedback correction for this product.',
                'feedback_description': exact_match['description']
            }
            
            logger.info(f"🎯 Created exact feedback result: {exact_match['correct_code']} with 95% confidence")
            return result
            
        except Exception as e:
            logger.error(f"Error creating exact feedback result: {str(e)}")
            return {
                'hts_code': exact_match['correct_code'],
                'description': 'Result from exact feedback match',
                'confidence': 95.0,
                'general_rate': 'Contact for rate',
                'units': [],
                'source': 'feedback_correction',
                'match_type': 'exact_match',
                'similarity_score': 1.0,
                'learning_explanation': 'Exact match from previous correction'
            }
    
    def add_feedback(self, product_description: str, predicted_code: str, correct_code: str) -> bool:
        """
        Add feedback and trigger immediate learning update including FAISS.
        
        Args:
            product_description: Product description
            predicted_code: Originally predicted HTS code
            correct_code: Correct HTS code provided by user
            
        Returns:
            True if feedback was successfully added and learning updated
        """
        try:
            logger.info(f"📝 Adding feedback: '{product_description}' | {predicted_code} → {correct_code}")
            
            # Add feedback using the feedback handler (which will also update FAISS)
            self.feedback_handler.add_feedback(
                description=product_description,
                predicted_code=predicted_code,
                correct_code=correct_code
            )
            
            # Analyze the correction
            correction_analysis = self._analyze_correction(predicted_code, correct_code)
            logger.info(f"📊 Correction analysis: {correction_analysis}")
            
            # Clear feedback cache to force fresh data on next classification
            self.feedback_cache.clear()
            self.last_feedback_check = datetime.now() - timedelta(hours=1)  # Force refresh
            
            logger.info(f"✅ Enhanced feedback recorded: {predicted_code} → {correct_code}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding feedback: {str(e)}")
            return False
    
    def _analyze_correction(self, predicted_code: str, correct_code: str) -> Dict:
        """
        Analyze the type and severity of a correction.
        
        Args:
            predicted_code: Originally predicted HTS code
            correct_code: Correct HTS code
            
        Returns:
            Dictionary with correction analysis
        """
        try:
            # Chapter level analysis
            pred_chapter = predicted_code[:2] if len(predicted_code) >= 2 else ''
            correct_chapter = correct_code[:2] if len(correct_code) >= 2 else ''
            
            # Heading level analysis
            pred_heading = predicted_code[:4] if len(predicted_code) >= 4 else ''
            correct_heading = correct_code[:4] if len(correct_code) >= 4 else ''
            
            if pred_chapter != correct_chapter:
                correction_type = 'chapter_change'
                severity = 'high'
            elif pred_heading != correct_heading:
                correction_type = 'heading_change'
                severity = 'medium'
            else:
                correction_type = 'subheading_change'
                severity = 'low'
            
            return {
                'correction_type': correction_type,
                'chapter_change': pred_chapter != correct_chapter,
                'severity': severity,
                'from_chapter': pred_chapter,
                'to_chapter': correct_chapter
            }
            
        except Exception as e:
            logger.error(f"Error analyzing correction: {str(e)}")
            return {'correction_type': 'unknown', 'severity': 'unknown'}
    
    def _check_and_retrain(self):
        """Check if retraining is needed and trigger it if necessary."""
        try:
            if self.s3_trainer and hasattr(self.s3_trainer, 'should_retrain'):
                if self.s3_trainer.should_retrain():
                    logger.info("🔄 Auto-retraining triggered based on feedback patterns")
                    # Note: Actual retraining would be triggered separately
                    # This is just a check to log when retraining would be beneficial
        except Exception as e:
            logger.error(f"Error checking retraining status: {str(e)}")
    
    def get_semantic_learning_insights(self, days: int = 30) -> Dict:
        """
        Get insights about semantic learning patterns.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with semantic learning insights
        """
        try:
            feedback_df = self._get_recent_feedback_data(days=days)
            
            if feedback_df.empty:
                return {
                    'total_corrections': 0,
                    'semantic_clusters': [],
                    'coverage_analysis': {},
                    'top_correction_patterns': []
                }
            
            # Analyze corrections
            corrections = feedback_df[feedback_df['predicted_code'] != feedback_df['correct_code']]
            
            insights = {
                'total_corrections': len(corrections),
                'semantic_clusters': [],
                'coverage_analysis': {},
                'top_correction_patterns': []
            }
            
            if len(corrections) > 0:
                # Find correction patterns
                pattern_counts = {}
                for _, row in corrections.iterrows():
                    pred_chapter = row['predicted_code'][:4] if len(row['predicted_code']) >= 4 else row['predicted_code']
                    correct_chapter = row['correct_code'][:4] if len(row['correct_code']) >= 4 else row['correct_code']
                    pattern = f"{pred_chapter} → {correct_chapter}"
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                
                # Get top patterns
                insights['top_correction_patterns'] = [
                    {'pattern': pattern, 'count': count}
                    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                ]
                
                # Coverage analysis
                total_feedback = len(feedback_df)
                insights['coverage_analysis'] = {
                    'total_feedback_entries': total_feedback,
                    'entries_with_corrections': len(corrections),
                    'correction_rate': len(corrections) / total_feedback * 100 if total_feedback > 0 else 0,
                    'semantic_learning_potential': len(corrections)
                }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting semantic learning insights: {str(e)}")
            return {
                'total_corrections': 0, 
                'semantic_clusters': [], 
                'coverage_analysis': {}, 
                'top_correction_patterns': []
            }