"""
Embedding service for handling OpenAI embeddings and Pinecone operations.
"""
import numpy as np
import time
from typing import List, Tuple, Optional
from pathlib import Path
from openai import OpenAI, APIError, RateLimitError
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from loguru import logger

from config.settings import Config
from utils.common import exponential_backoff_delay
from .cache_service import CacheService

class EmbeddingService:
    """Service for handling embeddings and vector operations."""
    
    def __init__(self):
        """Initialize the embedding service."""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.pc = Pinecone(api_key=Config.PINECONE_API_KEY)
        self.index_name = Config.PINECONE_INDEX_NAME
        self.cache_service = CacheService()
    
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """Encode text descriptions using OpenAI embeddings."""
        try:
            embeddings = []
            for i in range(0, len(texts), Config.BATCH_SIZE):
                batch = texts[i:i + Config.BATCH_SIZE]
                response = self.client.embeddings.create(
                    model=Config.OPENAI_EMBEDDING_MODEL,
                    input=batch,
                    encoding_format="float"
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Error encoding text with OpenAI: {str(e)}")
            raise
    
    def get_cached_embeddings(self, descriptions: List[str], hts_codes: List[str]) -> Tuple[Optional[np.ndarray], Optional[List[str]], Optional[List[str]]]:
        """Load embeddings from cache using consistent cache key."""
        # Generate cache key from actual data
        cache_key = self.cache_service.generate_cache_key(descriptions, "embeddings")
        
        if self.cache_service.cache_exists(cache_key):
            embeddings, cached_descriptions, cached_codes = self.cache_service.load_embeddings_cache(cache_key)
            
            # Validate cache matches current data
            if (embeddings is not None and 
                len(cached_descriptions) == len(descriptions) and 
                len(cached_codes) == len(hts_codes)):
                logger.info(f"Cache hit: {cache_key}")
                return embeddings, cached_descriptions, cached_codes
        
        logger.info(f"Cache miss: {cache_key}")
        return None, None, None
    
    def save_embeddings_to_cache(self, descriptions: List[str], embeddings: np.ndarray, 
                                hts_codes: List[str]) -> None:
        """Save embeddings to cache with consistent key."""
        cache_key = self.cache_service.generate_cache_key(descriptions, "embeddings")
        self.cache_service.save_embeddings_cache(cache_key, embeddings, descriptions, hts_codes)
    
    def setup_pinecone_index(self, embeddings: np.ndarray, descriptions: List[str], 
                           hts_codes: List[str]) -> None:
        """Set up Pinecone index with embeddings."""
        try:
            # Create index if it doesn't exist
            if self.index_name not in self.pc.list_indexes().names():
                logger.info("Creating new Pinecone index...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=embeddings.shape[1],
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=Config.PINECONE_CLOUD,
                        region=Config.PINECONE_REGION
                    )
                )
            
            index = self.pc.Index(self.index_name)
            
            # Check if vectors already exist
            stats = index.describe_index_stats()
            if stats.total_vector_count == 0:
                logger.info("Uploading vectors to Pinecone...")
                self._upload_vectors_to_pinecone(index, embeddings, descriptions, hts_codes)
            else:
                logger.info(f"Using existing Pinecone index with {stats.total_vector_count} vectors")
                
        except Exception as e:
            logger.error(f"Error setting up Pinecone index: {str(e)}")
            raise
    
    def _upload_vectors_to_pinecone(self, index, embeddings: np.ndarray, 
                                  descriptions: List[str], hts_codes: List[str]) -> None:
        """Upload vectors to Pinecone in batches."""
        vectors = []
        for i, (embedding, description, hts_code) in enumerate(zip(embeddings, descriptions, hts_codes)):
            vectors.append({
                'id': str(i),
                'values': embedding.tolist(),
                'metadata': {
                    'description': description,
                    'hts_code': hts_code
                }
            })
        
        # Upload in batches
        for i in range(0, len(vectors), Config.BATCH_SIZE):
            batch = vectors[i:i + Config.BATCH_SIZE]
            index.upsert(vectors=batch)
        
        logger.info("Successfully uploaded vectors to Pinecone")
    
    def search_similar(self, query_embedding: np.ndarray, top_k: int) -> List:
        """Search for similar vectors in Pinecone."""
        try:
            index = self.pc.Index(self.index_name)
            return index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                include_metadata=True
            )
        except Exception as e:
            logger.error(f"Error searching Pinecone: {str(e)}")
            raise
            return index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                include_metadata=True
            )
        except Exception as e:
            logger.error(f"Error searching Pinecone: {str(e)}")
            raise
