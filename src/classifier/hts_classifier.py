from typing import Dict, List
import numpy as np
from loguru import logger

from config.settings import Config, HTSMappings
from services.embedding_service import EmbeddingService
from services.gpt_service import GPTValidationService
from models.hts_models import ClassificationResult
from utils.common import extract_chapter_info
from utils.logging_utils import log_classification_attempt, log_feedback_addition
from data_loader.json_loader import HTSDataLoader
from preprocessor.text_processor import TextPreprocessor

class HTSClassifier:
    def __init__(self, data_loader: HTSDataLoader, preprocessor: TextPreprocessor, pinecone_feedback_service=None):
        """Initialize the HTS classifier."""
        self.data_loader = data_loader
        self.preprocessor = preprocessor
        self.descriptions = []
        self.hts_codes = []
        
        # Initialize services
        self.embedding_service = EmbeddingService()
        self.gpt_service = GPTValidationService()
        
        # Import and initialize feedback handler with Pinecone feedback service
        from utils.azure_blob_helper import FeedbackHandler
        self.feedback_handler = FeedbackHandler(use_azure=True, pinecone_feedback_service=pinecone_feedback_service)
        
    def build_index(self):
        """Build the search index with improved caching."""
        try:
            # Prepare data
            hts_data = self.data_loader.hts_data
            valid_entries = [(item['description'], item['htsno']) 
                           for item in hts_data 
                           if item.get('description') and item.get('htsno')]
            
            if not valid_entries:
                raise ValueError("No valid HTS entries found")
                
            self.descriptions, self.hts_codes = zip(*valid_entries)
            
            # Try to load from cache with current data
            embeddings, cached_descriptions, cached_codes = self.embedding_service.get_cached_embeddings(
                self.descriptions, self.hts_codes
            )
            
            if embeddings is None:
                logger.info("Generating new embeddings...")
                clean_descriptions = self.preprocessor.preprocess_descriptions(self.descriptions)
                embeddings = self.embedding_service.encode_texts(clean_descriptions)
                
                # Save to cache
                self.embedding_service.save_embeddings_to_cache(self.descriptions, embeddings, self.hts_codes)
            
            # Setup Pinecone index for main production data
            self.embedding_service.setup_pinecone_index(embeddings, self.descriptions, self.hts_codes)
            
        except Exception as e:
            logger.error(f"Error building index: {str(e)}")
            raise

    def classify(self, product_description: str, top_k: int = 3, country_code: str = None) -> List[Dict]:
        """Classify a product description into HTS codes."""
        try:
            log_classification_attempt(product_description)
            
            # Check explicit product mappings first
            matching_codes = self.data_loader.find_matching_codes(product_description)
            results = []
            
            # If no mapping matches, use similarity search
            clean_query = self.preprocessor.clean_text(product_description)
            query_embedding = self.preprocessor.encode_text([clean_query])
            
            # Search using embedding service
            search_results = self.embedding_service.search_similar(query_embedding[0], top_k * 5)
            
            # Process results with dynamic thresholding
            seen_chapters = set()
            threshold = self._determine_confidence_threshold(clean_query)
            
            for match in search_results.matches:
                hts_code = match.metadata['hts_code']
                chapter_info = extract_chapter_info(hts_code)
                
                if chapter_info['chapter'] in seen_chapters and len(results) >= top_k:
                    continue
                
                hts_info = self.data_loader.get_hts_code_info(hts_code)
                hts_info['hts_code'] = hts_code
                
                # Get hierarchical description
                full_description = self.data_loader.hts_code_backwalk(hts_code)
                
                # Validate with GPT
                chapter_context = self.get_chapter_context(hts_code)
                confidence = self.gpt_service.validate_hts_match(
                    full_description or hts_info.get('description', ''), 
                    hts_info, 
                    chapter_context
                )
                
                if confidence > threshold:
                    result = ClassificationResult(
                        hts_code=hts_code,
                        description=full_description if full_description else hts_info.get('description', ''),
                        confidence=round(confidence, 2),
                        general_rate=hts_info.get('general', 'N/A'),
                        units=hts_info.get('units', []),
                        chapter_context=chapter_context
                    )
                    
                    results.append(result.__dict__)
                    seen_chapters.add(chapter_info['chapter'])
            
            # Sort by confidence and return top_k
            results.sort(key=lambda x: x['confidence'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in classification: {str(e)}")
            raise

    def _determine_confidence_threshold(self, clean_query: str) -> float:
        """Determine confidence threshold based on product type."""
        clean_query_lower = clean_query.lower()
        
        if "leather" in clean_query_lower:
            return Config.CATEGORY_42_THRESHOLD
        elif any(word in clean_query_lower for word in ["t-shirt", "shirt", "sweater"]):
            return Config.APPAREL_THRESHOLD
        elif "window" in clean_query_lower and "aluminum" in clean_query_lower:
            return Config.ALUMINUM_THRESHOLD
        else:
            return Config.BASE_CONFIDENCE_THRESHOLD

    def get_chapter_context(self, hts_code: str) -> str:
        """Get the context of the HTS chapter and subchapter."""
        chapter_info = extract_chapter_info(hts_code)
        
        context = HTSMappings.CHAPTER_CONTEXTS.get(chapter_info['chapter'], "")
        subcontext = HTSMappings.SUBCHAPTER_CONTEXTS.get(chapter_info['heading'], "")
        
        if context and subcontext:
            return f"{context} - {subcontext}"
        return context or subcontext

    def add_feedback(self, product_description: str, predicted_code: str, correct_code: str):
        """Add feedback for a classification prediction."""
        try:
            self.feedback_handler.add_feedback(
                description=product_description,
                predicted_code=predicted_code,
                correct_code=correct_code
            )
            log_feedback_addition(predicted_code, correct_code, True)
        except Exception as e:
            log_feedback_addition(predicted_code, correct_code, False)
            logger.error(f"Error recording feedback: {str(e)}")

    def get_feedback_stats(self):
        """Get statistics about classification feedback."""
        return self.feedback_handler.get_feedback_stats()
    
    def format_hs_code(self, hts_code: str) -> str:
        """Format HTS code to standard format."""
        return self.feedback_handler.format_hs_code(hts_code)