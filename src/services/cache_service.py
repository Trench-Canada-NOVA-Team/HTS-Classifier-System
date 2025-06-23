"""
Centralized cache service for embeddings and other data.
"""
import pickle
import hashlib
from pathlib import Path
from typing import Tuple, Optional, List, Any
import numpy as np
from loguru import logger
from config.settings import Config

class CacheService:
    """Centralized service for caching embeddings and other data."""
    
    def __init__(self):
        """Initialize cache service."""
        self.cache_dir = Config.CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
    
    def generate_cache_key(self, data_items: List[str], prefix: str = "main") -> str:
        """Generate consistent cache key from data items."""
        # Create hash from first 100 items to ensure consistency
        sample_data = data_items[:100] if len(data_items) > 100 else data_items
        data_string = "||".join(sorted(sample_data))
        data_hash = hashlib.md5(data_string.encode()).hexdigest()[:8]
        return f"{prefix}_{len(data_items)}_{data_hash}"
    
    def cache_exists(self, cache_key: str) -> bool:
        """Check if cache file exists."""
        cache_path = self.cache_dir / f"{cache_key}_embeddings.pkl"
        return cache_path.exists()
    
    def load_embeddings_cache(self, cache_key: str) -> Tuple[Optional[np.ndarray], Optional[List[str]], Optional[List[str]]]:
        """Load embeddings from cache with consistent key."""
        cache_path = self.cache_dir / f"{cache_key}_embeddings.pkl"
        
        if not cache_path.exists():
            logger.info(f"Cache file not found: {cache_path}")
            return None, None, None
        
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Validate cache data structure
            required_keys = ['embeddings', 'descriptions', 'hts_codes']
            if not all(key in cache_data for key in required_keys):
                logger.warning("Invalid cache data structure, regenerating")
                return None, None, None
            
            logger.info(f"Loaded embeddings from cache: {len(cache_data['descriptions'])} entries")
            return cache_data['embeddings'], cache_data['descriptions'], cache_data['hts_codes']
            
        except Exception as e:
            logger.warning(f"Failed to load cache: {str(e)}")
            return None, None, None
    
    def save_embeddings_cache(self, cache_key: str, embeddings: np.ndarray, 
                            descriptions: List[str], hts_codes: List[str]) -> bool:
        """Save embeddings to cache with metadata."""
        cache_path = self.cache_dir / f"{cache_key}_embeddings.pkl"
        
        try:
            cache_data = {
                'embeddings': embeddings,
                'descriptions': descriptions,
                'hts_codes': hts_codes,
                'version': '1.0',
                'entry_count': len(descriptions)
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.info(f"Saved embeddings to cache: {cache_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")
            return False
    
    def clear_cache(self, cache_key: str = None) -> None:
        """Clear specific cache or all caches."""
        if cache_key:
            cache_path = self.cache_dir / f"{cache_key}_embeddings.pkl"
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared cache: {cache_key}")
        else:
            for cache_file in self.cache_dir.glob("*_embeddings.pkl"):
                cache_file.unlink()
            logger.info("Cleared all caches")
