"""
GPT service for HTS code validation and confidence scoring.
"""
import time
import re
from typing import Dict
from openai import OpenAI, APIError, RateLimitError
from loguru import logger

from config.settings import Config
from utils.common import exponential_backoff_delay

class GPTValidationService:
    """Service for GPT-based HTS validation."""
    
    def __init__(self):
        """Initialize the GPT service."""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def validate_hts_match(self, product_description: str, hts_info: Dict, 
                          chapter_context: str = "") -> float:
        """
        Use GPT to validate HTS match and calculate confidence score.
        
        Args:
            product_description: Product description to validate
            hts_info: HTS information dictionary
            chapter_context: Additional context about the HTS chapter
            
        Returns:
            Confidence score (0-100)
        """
        retry_count = 0
        
        while retry_count < Config.MAX_RETRIES:
            try:
                prompt = self._build_validation_prompt(
                    product_description, hts_info, chapter_context
                )
                
                response = self.client.chat.completions.create(
                    model=Config.OPENAI_CHAT_MODEL,  # ← Automatically uses your new setting
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert US HTS classification system. Analyze product descriptions and HTS codes, then return only a confidence score between 0-100."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=10
                )
                
                # Robust parsing for different response formats
                response_text = response.choices[0].message.content.strip()
                confidence = self._parse_confidence_score(response_text)
                
                # Apply category-specific adjustments
                adjusted_confidence = self._apply_category_adjustments(
                    confidence, product_description, hts_info['hts_code']
                )
                
                return min(max(adjusted_confidence, 0), 100)
                
            except RateLimitError:
                retry_count += 1
                if retry_count < Config.MAX_RETRIES:
                    delay = exponential_backoff_delay(retry_count, Config.BASE_DELAY)
                    logger.warning(f"Rate limit hit, retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("Max retries reached for rate limit")
                    return 50.0
                    
            except (APIError, ValueError) as e:
                logger.error(f"GPT validation error: {str(e)}")
                return 50.0
        
        return 50.0
    
    def _parse_confidence_score(self, response_text: str) -> float:
        """
        Parse confidence score from various response formats.
        
        Args:
            response_text: Raw response from GPT
            
        Returns:
            Parsed confidence score (0-100)
        """
        try:
            # Remove any extra whitespace
            response_text = response_text.strip()
            
            # Try multiple patterns to extract confidence score
            patterns = [
                r'confidence[:\s]*(\d+(?:\.\d+)?)',  # "Confidence: 95" or "Confidence 95"
                r'score[:\s]*(\d+(?:\.\d+)?)',       # "Score: 95" or "Score 95"
                r'(\d+(?:\.\d+)?)\s*%',              # "95%"
                r'^(\d+(?:\.\d+)?)$',                # Just "95" or "95.0"
                r'(\d+(?:\.\d+)?)'                   # Any number in the text (fallback)
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    score = float(match.group(1))
                    # Ensure score is within valid range
                    return min(max(score, 0.0), 100.0)
            
            # If no pattern matches, log the response and return default
            logger.warning(f"Could not parse confidence score from response: '{response_text}'")
            return 50.0
            
        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing confidence score from '{response_text}': {e}")
            return 50.0
    
    def _build_validation_prompt(self, product_description: str, hts_info: Dict, 
                               chapter_context: str) -> str:
        """Build the validation prompt for GPT."""
        general_rate = hts_info.get('general_rate', 'N/A') or 'N/A'
        context_info = f"\nProduct Category: {chapter_context}" if chapter_context else ""
        
        return f"""As an expert in US Harmonized Tariff Schedule (HTS) classification, analyze the following product-code match.

Product Description: {product_description}{context_info}

Candidate HTS Classification:
- Code: {hts_info['hts_code']}
- Official Description: {hts_info['description']}
- Duty Rate: {general_rate}
- Units of Measurement: {', '.join(hts_info.get('units', [])) if hts_info.get('units') else 'N/A'}

Important Category Guidelines:
1. Leather wallets, handbags, and similar containers belong in Chapter 42 (4202)
2. Aluminum doors, windows, and frames belong in heading 7610
3. T-shirts and similar garments belong in heading 6109
4. Industrial robots belong in heading 8428 or 8479

Evaluate the match considering:
1. Product Specificity: How precisely does the HTS description match the product details?
2. Category Alignment: Is this the correct category chapter/heading for this type of product?
3. Material & Characteristics: Do any specified materials or characteristics align?
4. Usage/Purpose: Does the intended use match the HTS category purpose?

Return only a number between 0 and 100 representing your confidence in this classification match.
Example confidence scores:
- 95-100: Perfect match with exact terminology
- 80-94: Very good match with minor variations
- 60-79: Good match but some details differ
- 40-59: Partial match with significant differences
- 0-39: Poor match or wrong category"""
    
    def _apply_category_adjustments(self, confidence: float, description: str, hts_code: str) -> float:
        """Apply category-specific confidence adjustments."""
        desc_lower = description.lower()
        
        # Wallet adjustments
        if 'wallet' in desc_lower and 'leather' in desc_lower:
            if hts_code.startswith('4202'):
                confidence = max(confidence, 90)
            elif not hts_code.startswith('42'):
                confidence = min(confidence, 30)
        
        # Window frame adjustments
        elif 'window frame' in desc_lower and 'aluminum' in desc_lower:
            if hts_code.startswith('7610'):
                confidence = max(confidence, 90)
            elif not hts_code.startswith('76'):
                confidence = min(confidence, 30)
        
        return confidence