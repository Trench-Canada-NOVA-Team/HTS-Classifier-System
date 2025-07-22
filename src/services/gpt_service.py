"""
GPT service for HTS code validation and confidence scoring.
"""
import time
import re
from typing import Dict
from openai import AzureOpenAI, APIError, RateLimitError
from loguru import logger

from config.settings import Config
from utils.common import exponential_backoff_delay

class GPTValidationService:
    """Service for GPT-based HTS validation."""
    
    def __init__(self):
        """Initialize the GPT service."""
        self.client = AzureOpenAI(
            api_key=Config.AZURE_OPENAI_API_KEY,
            api_version=Config.AZURE_OPENAI_API_VERSION,
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
        )
    
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
                    model=Config.AZURE_OPENAI_CHAT_MODEL,
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert US HTS classification system for a company that designs and manufactures electrical transformers, reactors, and bushings, as well as related parts and subcomponents. Analyze product descriptions and HTS codes, then return only a confidence score between 0-100."
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
        
        return f"""You are an expert in US Harmonized Tariff Schedule (HTS) classification with experience in electrical components, transformers, bushings, reactors, and related subassemblies.

Please validate the following proposed HTS code classification.

---
Product Description:
{product_description}
{context_info}

Candidate HTS Classification:
- Code: {hts_info['hts_code']}
- Official Description: {hts_info['description']}
- Duty Rate: {general_rate}
- Units of Measurement: {', '.join(hts_info.get('units', [])) if hts_info.get('units') else 'N/A'}
---

Instructions:

1. **Product Specificity:**  
   - Assess how closely the HTS description matches the product details, **paying special attention to critical values such as voltage and power rating (e.g., kVA, kW, volts)**, as these frequently determine the correct subheading.
2. **Category Alignment:**  
   - Determine if this chapter/heading is appropriate for the product type.
3. **Material & Characteristics:**  
   - Check if the described materials and product characteristics, **including any specified electrical ratings (e.g., voltage, kVA, insulation class, frequency)**, align.
4. **Usage/Purpose:**  
   - Evaluate if the product's intended function fits the HTS code's intended use.

**Scoring:**  
Return only a single number between 0 and 100, representing your confidence in this classification match.  
Example confidence scores:
- 95-100: Perfect match with exact terminology and use
- 80-94: Very good match, minor differences only
- 60-79: Good match, but details differ or lack evidence
- 40-59: Partial match, significant differences
- 0-39: Poor match or wrong category

**Important Category Guidelines (for reference):**
- Electric transformers are generally classified in Chapter 85, heading 8504.21, **with subheadings often based on voltage and kVA ratings**. unless specified as a **part**, any description of a transformer should be treated as a **complete unit**.
- The stated voltage or kVA rating in the description is defined as **exactly that**, and **not exceeding** that value
- **If the power handling capacity (such as kVA, kW, or similar) in the product description does not exactly match the value stated in the HTS code description from the context, return only the subheading (the first 6-8 digits) as the code.**
- Bushings and similar insulating fittings often fall under 8546.20.
- Air core reactors fall within 8504.90, but review product specifics, especially electrical ratings.
- Electrical parts and subassemblies should be considered for headings 8504, 8546, or other relevant chapters, depending on their function and electrical properties.

**Additional Critical Instructions:**
- If you are not sure about the subheading (the 5th and 6th or 7th and 8th digits), or if there is insufficient evidence for a specific sub-classification (such as missing voltage or kVA rating), return only the preceding digits (e.g., "8504" or "8504.21") as the code.
- If your confidence score is below 80, or if the match is not strong, return the parent heading (the first 4 digits) to avoid over-specific classification.
- Be critical and conservative. When in doubt, prefer a broader heading to avoid misclassification.

**Format:**
Return only the confidence score (0-100).
"""

    
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