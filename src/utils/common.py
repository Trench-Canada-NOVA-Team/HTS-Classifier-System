"""
Common utility functions used across the HTS Classification System.
"""
import re
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

def format_hts_code(code: str) -> str:
    """Format HTS code with proper structure."""
    digits = ''.join(filter(str.isdigit, str(code)))[:12]
    sections = [digits[i:j] for i, j in [(0, 4), (4, 6), (6, 8), (8, 10)] if i < len(digits)]
    return '.'.join(sections)

def calculate_cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings using pure NumPy.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    try:
        embedding1 = np.array(embedding1)
        embedding2 = np.array(embedding2)
        
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return max(0.0, min(1.0, float(similarity)))
        
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {str(e)}")
        return 0.0

def clean_and_validate_data(data: Any) -> Any:
    """Clean and validate data that might be in list or string format."""
    if isinstance(data, list):
        return str(data[0]).strip() if data else ""
    return str(data).strip() if data else ""

def get_date_range(days: int) -> datetime:
    """Get cutoff date for filtering recent data."""
    return datetime.now() - timedelta(days=days)

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    return numerator / denominator if denominator != 0 else default

def exponential_backoff_delay(retry_count: int, base_delay: float = 1.0) -> float:
    """Calculate exponential backoff delay."""
    return base_delay * (2 ** retry_count)

def sanitize_string_input(input_str: str, max_length: int = 1000) -> str:
    """Sanitize and validate string input."""
    if not isinstance(input_str, str):
        input_str = str(input_str)
    
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', input_str)
    
    # Limit length
    return sanitized[:max_length].strip()

def extract_chapter_info(hts_code: str) -> Dict[str, str]:
    """Extract chapter and heading information from HTS code."""
    hts_code = str(hts_code).strip()
    return {
        'chapter': hts_code[:2] if len(hts_code) >= 2 else '',
        'heading': hts_code[:4] if len(hts_code) >= 4 else '',
        'subheading': hts_code[:6] if len(hts_code) >= 6 else ''
    }

def merge_dicts_safely(*dicts: Dict) -> Dict:
    """Safely merge multiple dictionaries."""
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result

def validate_hts_code_format(hts_code: str) -> bool:
    """Validate HTS code format."""
    if not hts_code:
        return False
    
    # Remove dots and check if it's numeric with proper length
    clean_code = hts_code.replace('.', '')
    return clean_code.isdigit() and 4 <= len(clean_code) <= 10
