"""
Pinecone service for handling feedback embeddings.
"""
import numpy as np
import json
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
from loguru import logger
import pandas as pd

from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
try:
    from langchain_openai import AzureOpenAIEmbeddings
except ImportError:
    from langchain_community.embeddings import OpenAIEmbeddings as AzureOpenAIEmbeddings
    logger.warning("Using deprecated AzureOpenAIEmbeddings. Consider upgrading: pip install langchain-openai")

from config.settings import Config

class PineconeFeedbackService:
    """Service for handling feedback embeddings using Pinecone."""
    
    def __init__(self, openai_api_key: str = None):
        """Initialize Pinecone feedback service."""
        self.openai_api_key = openai_api_key or Config.AZURE_OPENAI_API_KEY
        self.pinecone_available = True
        
        # Test Pinecone availability first
        try:
            self.pc = Pinecone(api_key=Config.PINECONE_API_KEY)
            logger.info("Pinecone client initialized successfully")
        except Exception as e:
            logger.error(f"Pinecone client initialization failed: {str(e)}")
            self.pinecone_available = False
            return
        
        # Initialize Azure OpenAI embeddings
        try:
            self.embeddings = AzureOpenAIEmbeddings(
                openai_api_key=Config.AZURE_OPENAI_API_KEY,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                api_version=Config.AZURE_OPENAI_API_VERSION,
                model=Config.AZURE_OPENAI_EMBEDDING_MODEL
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI embeddings: {str(e)}")
            self.pinecone_available = False
            return
        
        self.index_name = Config.PINECONE_FEEDBACK_INDEX_NAME
        self.index = None
        self.is_initialized = False
        
        logger.info("PineconeFeedbackService initialized using Azure OpenAI")
    
    def initialize_index(self) -> bool:
        """Initialize or connect to existing Pinecone feedback index."""
        if not self.pinecone_available:
            logger.warning("Pinecone not available, skipping index initialization")
            return False
            
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes().names()
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone feedback index: {self.index_name}")
                
                # Get embedding dimension
                test_embedding = self.embeddings.embed_query("test")
                dimension = len(test_embedding)
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=Config.PINECONE_CLOUD,
                        region=Config.PINECONE_REGION
                    )
                )
                logger.info(f"Created Pinecone feedback index with dimension {dimension}")
            else:
                logger.info(f"Using existing Pinecone feedback index: {self.index_name}")
            
            # Connect to index
            self.index = self.pc.Index(self.index_name)
            self.is_initialized = True
            
            # Get current stats
            stats = self.index.describe_index_stats()
            logger.info(f"Pinecone feedback index connected. Total vectors: {stats.total_vector_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone feedback index: {str(e)}")
            self.is_initialized = False
            return False
    
    def add_feedback_embedding(self, feedback_entry: Dict) -> bool:
        """Add a new feedback embedding to Pinecone."""
        if not self.pinecone_available or not self.is_initialized:
            logger.warning("Pinecone feedback service not available or initialized")
            return False
            
        try:
            # Generate embedding for the description
            description = feedback_entry['description']
            embedding = self.embeddings.embed_query(description)
            
            # Create unique vector ID
            timestamp = feedback_entry.get('timestamp', datetime.now().isoformat())
            vector_id = f"feedback_{hash(description + timestamp)}_{datetime.now().microsecond}"
            
            # Prepare metadata
            metadata = {
                'description': description,
                'predicted_code': feedback_entry['predicted_code'],
                'correct_code': feedback_entry['correct_code'],
                'timestamp': timestamp,
                'type': 'feedback',
                'is_correction': feedback_entry['predicted_code'] != feedback_entry['correct_code']
            }
            
            # Upsert to Pinecone
            self.index.upsert(vectors=[{
                'id': vector_id,
                'values': embedding,
                'metadata': metadata
            }])
            
            logger.info(f"Added feedback embedding to Pinecone: {description[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error adding feedback embedding to Pinecone: {str(e)}")
            return False
    
    def batch_add_feedback_embeddings(self, feedback_entries: List[Dict]) -> bool:
        """Add multiple feedback embeddings to Pinecone."""
        if not self.pinecone_available or not self.is_initialized:
            logger.warning("Pinecone feedback service not available or initialized")
            return False
            
        try:
            # Prepare vectors for batch upsert
            vectors = []
            descriptions = [entry['description'] for entry in feedback_entries]
            embeddings = self.embeddings.embed_documents(descriptions)
            
            for i, (feedback_entry, embedding) in enumerate(zip(feedback_entries, embeddings)):
                timestamp = feedback_entry.get('timestamp', datetime.now().isoformat())
                vector_id = f"feedback_{hash(feedback_entry['description'] + timestamp)}_{i}"
                
                metadata = {
                    'description': feedback_entry['description'],
                    'predicted_code': feedback_entry['predicted_code'],
                    'correct_code': feedback_entry['correct_code'],
                    'timestamp': timestamp,
                    'type': 'feedback',
                    'is_correction': feedback_entry['predicted_code'] != feedback_entry['correct_code']
                }
                
                vectors.append({
                    'id': vector_id,
                    'values': embedding,
                    'metadata': metadata
                })
            
            # Batch upsert to Pinecone
            batch_size = 100  # Pinecone batch limit
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Batch added {len(feedback_entries)} feedback embeddings to Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Error batch adding feedback embeddings to Pinecone: {str(e)}")
            return False
    
    def search_similar_feedback(self, query: str, top_k: int = None, 
                              similarity_threshold: float = None) -> List[Dict]:
        """Search for similar feedback entries using Pinecone."""
        # Use configuration defaults if not provided
        top_k = top_k or Config.PINECONE_FEEDBACK_TOP_K_DEFAULT
        similarity_threshold = similarity_threshold or Config.PINECONE_FEEDBACK_SIMILARITY_THRESHOLD
        
        if not self.pinecone_available or not self.is_initialized:
            logger.warning("Pinecone feedback service not available, returning empty results")
            return []
            
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search in Pinecone with filter for corrections only
            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k * 2,  # Get more to filter
                filter={'is_correction': True},
                include_metadata=True
            )
            
            # Process and filter results
            results = []
            for match in search_results.matches:
                similarity_score = float(match.score)
                
                if similarity_score >= similarity_threshold:
                    metadata = match.metadata
                    
                    results.append({
                        'description': metadata['description'],
                        'predicted_code': metadata['predicted_code'],
                        'correct_code': metadata['correct_code'],
                        'similarity_score': similarity_score,
                        'timestamp': metadata['timestamp'],
                        'pinecone_id': match.id
                    })
            
            # Sort by similarity score (highest first) and return top_k
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            logger.info(f"Pinecone feedback search found {len(results)} similar feedback entries")
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching Pinecone feedback: {str(e)}")
            return []
    
    def check_exact_match(self, description: str) -> Optional[Dict]:
        """Check for exact description match in Pinecone metadata."""
        try:
            if not self.pinecone_available or not self.is_initialized:
                return None
            
            # Search with high top_k to find potential exact matches
            query_embedding = self.embeddings.embed_query(description)
            
            search_results = self.index.query(
                vector=query_embedding,
                top_k=50,
                filter={'is_correction': True},
                include_metadata=True
            )
            
            description_lower = description.lower().strip()
            
            # Look for exact match in metadata
            for match in search_results.matches:
                metadata = match.metadata
                if metadata['description'].lower().strip() == description_lower:
                    return {
                        'description': metadata['description'],
                        'predicted_code': metadata['predicted_code'],
                        'correct_code': metadata['correct_code'],
                        'similarity_score': 1.0,
                        'timestamp': metadata['timestamp'],
                        'pinecone_id': match.id
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking exact match in Pinecone: {str(e)}")
            return None
    
    def get_feedback_stats(self) -> Dict:
        """Get statistics about the Pinecone feedback index."""
        try:
            if not self.pinecone_available:
                return {
                    'total_vectors': 0, 
                    'total_corrections': 0,
                    'pinecone_available': False,
                    'error': 'Pinecone not available'
                }
            
            if not self.is_initialized:
                # Try to initialize if not already done
                if not self.initialize_index():
                    return {
                        'total_vectors': 0, 
                        'total_corrections': 0, 
                        'pinecone_available': True,
                        'is_initialized': False
                    }
            
            # Get index stats safely
            stats = self.index.describe_index_stats()
            total_vectors = stats.total_vector_count
            
            # For corrections count, we can use the total since we only store corrections
            # In a production environment, you might want to query with filters
            total_corrections = total_vectors
            
            return {
                'total_vectors': total_vectors,
                'total_corrections': total_corrections,
                'index_type': 'Pinecone',
                'embedding_model': Config.AZURE_OPENAI_EMBEDDING_MODEL,
                'is_initialized': self.is_initialized,
                'pinecone_available': self.pinecone_available,
                'index_name': self.index_name
            }
        except Exception as e:
            logger.error(f"Error getting Pinecone feedback stats: {str(e)}")
            return {
                'total_vectors': 0, 
                'total_corrections': 0, 
                'pinecone_available': self.pinecone_available,
                'error': str(e)
            }
    
    def has_existing_data(self) -> bool:
        """Check if the Pinecone feedback index already contains data."""
        try:
            if not self.pinecone_available or not self.is_initialized:
                return False
            
            stats = self.index.describe_index_stats()
            return stats.total_vector_count > 0
            
        except Exception as e:
            logger.error(f"Error checking if Pinecone feedback index has data: {str(e)}")
            return False
    
    def rebuild_from_feedback_data(self, feedback_df: pd.DataFrame) -> bool:
        """Rebuild Pinecone feedback index from existing feedback data."""
        try:
            logger.info(f"Rebuilding Pinecone feedback index from {len(feedback_df)} feedback entries")
            
            # Clear existing index (delete and recreate)
            if self.is_initialized:
                try:
                    self.pc.delete_index(self.index_name)
                    logger.info("Deleted existing Pinecone feedback index")
                except Exception as e:
                    logger.warning(f"Could not delete existing index: {str(e)}")
            
            # Reinitialize index
            self.is_initialized = False
            if not self.initialize_index():
                logger.error("Failed to reinitialize Pinecone feedback index")
                return False
            
            # Convert DataFrame to list of dicts
            feedback_entries = []
            for _, row in feedback_df.iterrows():
                # Only include corrections
                if row['predicted_code'] != row['correct_code']:
                    # Fix timestamp conversion
                    timestamp = row['timestamp']
                    if hasattr(timestamp, 'isoformat'):
                        timestamp_str = timestamp.isoformat()
                    else:
                        timestamp_str = str(timestamp)
                    
                    feedback_entries.append({
                        'description': str(row['description']),
                        'predicted_code': str(row['predicted_code']),
                        'correct_code': str(row['correct_code']),
                        'timestamp': timestamp_str
                    })
            
            if not feedback_entries:
                logger.info("No corrections found in feedback data")
                return True
            
            # Batch add all feedback entries
            success = self.batch_add_feedback_embeddings(feedback_entries)
            
            if success:
                logger.info("Successfully rebuilt Pinecone feedback index from feedback data")
            else:
                logger.error("Failed to rebuild Pinecone feedback index")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rebuilding Pinecone feedback index: {str(e)}")
            return False
    
    def delete_index(self) -> bool:
        """Delete the Pinecone feedback index."""
        try:
            if self.pinecone_available and self.index_name in self.pc.list_indexes().names():
                self.pc.delete_index(self.index_name)
                logger.info(f"Deleted Pinecone feedback index: {self.index_name}")
                self.is_initialized = False
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting Pinecone feedback index: {str(e)}")
            return False
