"""
FAISS service for handling feedback embeddings using Langchain framework.
"""
import numpy as np
import pickle
import json
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime
from loguru import logger
import pandas as pd

from langchain_community.vectorstores import FAISS
try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    # Fallback to deprecated import if new package not available
    from langchain_community.embeddings import OpenAIEmbeddings
    logger.warning("Using deprecated OpenAIEmbeddings. Consider upgrading: pip install langchain-openai")

from langchain.docstore.document import Document
from langchain.schema import BaseRetriever

from config.settings import Config

class FaissFeedbackService:
    """Service for handling feedback embeddings using Langchain FAISS."""
    
    def __init__(self, openai_api_key: str = None):
        """Initialize FAISS feedback service with Langchain."""
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
        self.faiss_available = True
        
        # Test FAISS availability first
        try:
            import faiss
            logger.info("FAISS library loaded successfully")
        except ImportError as e:
            logger.error(f"FAISS library not available: {str(e)}")
            self.faiss_available = False
            return
        except AttributeError as e:
            logger.error(f"FAISS NumPy compatibility issue: {str(e)}")
            logger.error("Please downgrade NumPy: pip install 'numpy<2.0.0'")
            self.faiss_available = False
            return
        
        # Initialize Langchain OpenAI embeddings
        try:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.openai_api_key,
                model=Config.OPENAI_EMBEDDING_MODEL
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {str(e)}")
            self.faiss_available = False
            return
        
        self.vectorstore = None
        self.metadata_store = []
        self.is_initialized = False
        
        # Use configuration for file paths
        self.faiss_index_path = Config.DATA_DIR / Config.FAISS_INDEX_NAME
        self.metadata_path = Config.DATA_DIR / Config.FAISS_METADATA_NAME
        
        logger.info("FaissFeedbackService initialized with Langchain framework")
    
    def initialize_index(self) -> bool:
        """Initialize or load existing Langchain FAISS index."""
        if not self.faiss_available:
            logger.warning("FAISS not available, skipping index initialization")
            return False
            
        try:
            if self._load_existing_index():
                logger.info(f"Loaded existing Langchain FAISS index")
                self.is_initialized = True
                return True
            else:
                logger.info("Creating new Langchain FAISS index")
                self._create_new_index()
                self.is_initialized = True
                return True
        except Exception as e:
            logger.error(f"Error initializing Langchain FAISS index: {str(e)}")
            # Set as initialized anyway to allow adding documents
            self.is_initialized = True
            return False
    
    def _create_new_index(self) -> None:
        """Create a new Langchain FAISS index."""
        # Create an empty FAISS index - we'll add documents later
        self.vectorstore = None
        self.metadata_store = []
        logger.info("Created new Langchain FAISS index (empty)")
    
    def _load_existing_index(self) -> bool:
        """Load existing Langchain FAISS index and metadata."""
        try:
            if self.faiss_index_path.exists() and self.metadata_path.exists():
                # Load FAISS index using Langchain
                self.vectorstore = FAISS.load_local(
                    str(self.faiss_index_path), 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                
                # Load metadata
                with open(self.metadata_path, 'rb') as f:
                    self.metadata_store = pickle.load(f)
                
                logger.info(f"Successfully loaded Langchain FAISS index with {len(self.metadata_store)} entries")
                return True
            else:
                logger.info("No existing Langchain FAISS index found")
                return False
        except Exception as e:
            logger.error(f"Error loading existing index: {str(e)}")
            return False
    
    def save_index(self) -> bool:
        """Save Langchain FAISS index and metadata to disk."""
        try:
            if not self.vectorstore:
                logger.warning("No vectorstore to save")
                return True  # Return True for empty index
            
            # Ensure directory exists
            self.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index using Langchain
            self.vectorstore.save_local(str(self.faiss_index_path))
            
            # Save metadata
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata_store, f)
            
            logger.info(f"Saved Langchain FAISS index with {len(self.metadata_store)} entries")
            return True
        except Exception as e:
            logger.error(f"Error saving Langchain FAISS index: {str(e)}")
            return False
    
    def add_feedback_embedding(self, feedback_entry: Dict) -> bool:
        """Add a new feedback embedding using Langchain."""
        if not self.faiss_available:
            logger.warning("FAISS not available, skipping embedding addition")
            return False
            
        try:
            if not self.is_initialized:
                self.initialize_index()
            
            # Create Langchain Document
            doc_content = feedback_entry['description']
            doc_metadata = {
                'id': len(self.metadata_store),
                'predicted_code': feedback_entry['predicted_code'],
                'correct_code': feedback_entry['correct_code'],
                'timestamp': feedback_entry.get('timestamp', datetime.now().isoformat()),
                'type': 'feedback'
            }
            
            document = Document(page_content=doc_content, metadata=doc_metadata)
            
            # Add to vectorstore
            if self.vectorstore is None:
                self.vectorstore = FAISS.from_documents([document], self.embeddings)
            else:
                self.vectorstore.add_documents([document])
            
            # Add to metadata store
            metadata_entry = {
                'id': len(self.metadata_store),
                'description': feedback_entry['description'],
                'predicted_code': feedback_entry['predicted_code'],
                'correct_code': feedback_entry['correct_code'],
                'timestamp': feedback_entry.get('timestamp', datetime.now().isoformat()),
                'added_to_faiss': datetime.now().isoformat()
            }
            self.metadata_store.append(metadata_entry)
            
            # Save to disk
            self.save_index()
            
            logger.info(f"Added feedback embedding via Langchain: {feedback_entry['description'][:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error adding feedback embedding via Langchain: {str(e)}")
            return False
    
    def batch_add_feedback_embeddings(self, feedback_entries: List[Dict]) -> bool:
        """Add multiple feedback embeddings using Langchain."""
        if not self.faiss_available:
            logger.warning("FAISS not available, skipping batch embedding addition")
            return False
            
        try:
            if not self.is_initialized:
                self.initialize_index()
            
            # Create Langchain Documents
            documents = []
            for i, feedback_entry in enumerate(feedback_entries):
                doc_content = feedback_entry['description']
                doc_metadata = {
                    'id': len(self.metadata_store) + i,
                    'predicted_code': feedback_entry['predicted_code'],
                    'correct_code': feedback_entry['correct_code'],
                    'timestamp': feedback_entry.get('timestamp', datetime.now().isoformat()),
                    'type': 'feedback'
                }
                
                document = Document(page_content=doc_content, metadata=doc_metadata)
                documents.append(document)
            
            # Add to vectorstore
            if self.vectorstore is None:
                self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            else:
                self.vectorstore.add_documents(documents)
            
            # Add to metadata store
            for feedback_entry in feedback_entries:
                metadata_entry = {
                    'id': len(self.metadata_store),
                    'description': feedback_entry['description'],
                    'predicted_code': feedback_entry['predicted_code'],
                    'correct_code': feedback_entry['correct_code'],
                    'timestamp': feedback_entry.get('timestamp', datetime.now().isoformat()),
                    'added_to_faiss': datetime.now().isoformat()
                }
                self.metadata_store.append(metadata_entry)
            
            # Save to disk
            self.save_index()
            
            logger.info(f"Batch added {len(feedback_entries)} feedback embeddings via Langchain")
            return True
            
        except Exception as e:
            logger.error(f"Error batch adding feedback embeddings via Langchain: {str(e)}")
            return False
    
    def search_similar_feedback(self, query: str, top_k: int = None, 
                              similarity_threshold: float = None) -> List[Dict]:
        """Search for similar feedback entries using Langchain FAISS."""
        # Use configuration defaults if not provided
        top_k = top_k or Config.FAISS_TOP_K_DEFAULT
        similarity_threshold = similarity_threshold or Config.FAISS_SIMILARITY_THRESHOLD
        
        if not self.faiss_available:
            logger.warning("FAISS not available, returning empty results")
            return []
            
        try:
            if not self.is_initialized or not self.vectorstore:
                logger.info("Langchain FAISS vectorstore not initialized or empty")
                return []
            
            # Use Langchain similarity search with scores
            docs_with_scores = self.vectorstore.similarity_search_with_score(
                query, k=min(top_k * 2, len(self.metadata_store))
            )
            
            # Filter results by similarity threshold and format
            results = []
            for doc, score in docs_with_scores:
                # Convert distance to similarity (FAISS returns distance, we want similarity)
                similarity_score = 1.0 / (1.0 + score) if score > 0 else 1.0
                
                if similarity_score >= similarity_threshold:
                    metadata = doc.metadata
                    
                    # Only include corrections (where predicted != correct)
                    if metadata['predicted_code'] != metadata['correct_code']:
                        results.append({
                            'description': doc.page_content,
                            'predicted_code': metadata['predicted_code'],
                            'correct_code': metadata['correct_code'],
                            'similarity_score': float(similarity_score),
                            'timestamp': metadata['timestamp'],
                            'faiss_id': metadata['id']
                        })
            
            # Sort by similarity score (highest first) and return top_k
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            logger.info(f"Langchain FAISS search found {len(results)} similar feedback entries")
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching Langchain FAISS feedback: {str(e)}")
            return []
    
    def get_retriever(self, search_kwargs: Dict[str, Any] = None) -> BaseRetriever:
        """Get Langchain retriever for the feedback vectorstore."""
        if not self.vectorstore:
            raise ValueError("Vectorstore not initialized")
        
        search_kwargs = search_kwargs or {"k": 5}
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)
    
    def check_exact_match(self, description: str) -> Optional[Dict]:
        """Check for exact description match in metadata."""
        try:
            description_lower = description.lower().strip()
            
            for metadata in self.metadata_store:
                if metadata['description'].lower().strip() == description_lower:
                    # Only return corrections
                    if metadata['predicted_code'] != metadata['correct_code']:
                        return {
                            'description': metadata['description'],
                            'predicted_code': metadata['predicted_code'],
                            'correct_code': metadata['correct_code'],
                            'similarity_score': 1.0,
                            'timestamp': metadata['timestamp'],
                            'faiss_id': metadata['id']
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking exact match: {str(e)}")
            return None
    
    def get_feedback_stats(self) -> Dict:
        """Get statistics about the Langchain FAISS feedback index."""
        try:
            if not self.faiss_available:
                return {
                    'total_vectors': 0, 
                    'total_corrections': 0,
                    'faiss_available': False,
                    'error': 'FAISS not available'
                }
            
            if not self.is_initialized:
                return {'total_vectors': 0, 'total_corrections': 0, 'faiss_available': True}
            
            total_vectors = len(self.metadata_store)
            total_corrections = sum(1 for m in self.metadata_store 
                                  if m['predicted_code'] != m['correct_code'])
            
            return {
                'total_vectors': total_vectors,
                'total_corrections': total_corrections,
                'index_type': 'Langchain FAISS',
                'embedding_model': Config.OPENAI_EMBEDDING_MODEL,
                'is_initialized': self.is_initialized,
                'faiss_available': self.faiss_available
            }
        except Exception as e:
            logger.error(f"Error getting Langchain FAISS stats: {str(e)}")
            return {'total_vectors': 0, 'total_corrections': 0, 'faiss_available': self.faiss_available}
    
    def rebuild_from_feedback_data(self, feedback_df: pd.DataFrame) -> bool:
        """Rebuild Langchain FAISS index from existing feedback data."""
        try:
            logger.info(f"Rebuilding Langchain FAISS index from {len(feedback_df)} feedback entries")
            
            # Create new index
            self._create_new_index()
            
            # Convert DataFrame to list of dicts
            feedback_entries = []
            for _, row in feedback_df.iterrows():
                feedback_entries.append({
                    'description': row['description'],
                    'predicted_code': row['predicted_code'],
                    'correct_code': row['correct_code'],
                    'timestamp': row['timestamp']
                })
            
            # Batch add all feedback entries
            success = self.batch_add_feedback_embeddings(feedback_entries)
            
            if success:
                logger.info("Successfully rebuilt Langchain FAISS index from feedback data")
            else:
                logger.error("Failed to rebuild Langchain FAISS index")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rebuilding Langchain FAISS index: {str(e)}")
            return False
