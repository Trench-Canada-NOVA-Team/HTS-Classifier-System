import json
from typing import Dict 
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from loguru import logger
from dotenv import load_dotenv
import os
from io import StringIO
import boto3

class FeedbackHandler:
    def __init__(self, use_s3=True, feedback_file_path=None, faiss_service=None):
        """Initialize the feedback handler.
        
        Args:
            use_s3 (bool): Whether to use S3 storage. Defaults to True.
            feedback_file_path (str, optional): Path to store feedback data locally.
            faiss_service: Optional Langchain FaissFeedbackService instance for vector storage
        """
        load_dotenv()
        
        self.use_s3 = use_s3
        self.s3_available = False
        self.faiss_service = faiss_service
        
        # Initialize FAISS service if available
        if self.faiss_service:
            self.faiss_service.initialize_index()
            logger.info("Langchain FAISS service initialized for feedback handler")
        
        # Always set up local storage as fallback
        if feedback_file_path is None:
            self.feedback_file = Path(__file__).parent.parent / "Data" / "feedback_data.csv"
        else:
            self.feedback_file = Path(feedback_file_path)
        
        if self.use_s3:
            try:
                # S3 configuration
                self.bucket_name = os.getenv('AWS_BUCKET_NAME')
                self.s3_key = 'feedback/feedback_data.csv'
                
                # Initialize S3 client
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_REGION', 'us-east-1')
                )
                
                # Test S3 connection
                self._test_s3_connection()
                self.s3_available = True
                self._initialize_s3_feedback_file()
                logger.info("S3 storage initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize S3 storage: {str(e)}")
                logger.info("Falling back to local storage")
                self.use_s3 = False
                self.s3_available = False
        
        # Initialize local storage (either as primary or fallback)
        if not self.s3_available:
            self._initialize_feedback_file()
    
    def _test_s3_connection(self):
        """Test S3 connection and permissions."""
        try:
            self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            logger.info("S3 connection test successful")
        except Exception as e:
            logger.error(f"S3 connection test failed: {str(e)}")
            raise
    
    def _initialize_s3_feedback_file(self):
        """Create feedback file in S3 if it doesn't exist."""
        if not self.s3_available:
            return
            
        try:
            # Check if file exists in S3
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=self.s3_key)
                logger.info(f"Feedback file found in S3: {self.s3_key}")
            except Exception as e:
                if '404' in str(e) or 'NoSuchKey' in str(e):
                    # File doesn't exist, create it
                    logger.info(f"Feedback file not found in S3, creating: {self.s3_key}")
                    df = pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
                    self._save_to_s3(df)
                    logger.info(f"Created new feedback file in S3: {self.s3_key}")
                else:
                    raise
        except Exception as e:
            logger.error(f"Error initializing S3 feedback file: {str(e)}")
            self.use_s3 = False
            self.s3_available = False
            self._initialize_feedback_file()
    
    def _initialize_feedback_file(self):
        """Create feedback file if it doesn't exist (local storage only)."""
        if not self.feedback_file.exists():
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
            df.to_csv(self.feedback_file, index=False)
            logger.info(f"Created new feedback file at {self.feedback_file}")
    
    def _load_feedback_data(self):
        """Load existing feedback data."""
        try:
            if self.use_s3 and self.s3_available:
                return self._load_from_s3()
            else:
                if self.feedback_file.exists():
                    return pd.read_csv(self.feedback_file)
                else:
                    return pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
        except Exception as e:
            logger.warning(f"Error reading feedback data: {str(e)}. Creating new one.")
            return pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
    
    def _load_from_s3(self):
        """Load feedback data from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self.s3_key)
            content = response['Body'].read().decode('utf-8')
            return pd.read_csv(StringIO(content))
        except Exception as e:
            if 'NoSuchKey' in str(e) or '404' in str(e):
                logger.info("Feedback file not found in S3, creating empty DataFrame")
                return pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
            else:
                logger.error(f"Error loading from S3: {str(e)}")
                logger.info("Falling back to local storage")
                self.use_s3 = False
                self.s3_available = False
                return self._load_feedback_data()
    
    def _save_feedback_data(self, df):
        """Save feedback data."""
        try:
            if self.use_s3 and self.s3_available:
                self._save_to_s3(df)
            else:
                df.to_csv(self.feedback_file, index=False)
        except Exception as e:
            logger.error(f"Error saving to S3: {str(e)}")
            logger.info("Falling back to local storage")
            self.use_s3 = False
            self.s3_available = False
            df.to_csv(self.feedback_file, index=False)
    
    def _save_to_s3(self, df):
        """Save DataFrame to S3."""
        try:
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.s3_key,
                Body=csv_buffer.getvalue()
            )
            logger.info("Successfully saved feedback data to S3")
        except Exception as e:
            logger.error(f"Error saving to S3: {str(e)}")
            raise
    
    def add_feedback(self, description, predicted_code, correct_code):
        """Add new feedback entry and update Langchain FAISS index."""
        try:
            logger.info("Adding feedback...")
            df = self._load_feedback_data()
            
            new_entry = pd.DataFrame([{
                "timestamp": datetime.now().isoformat(),
                "description": description,
                "predicted_code": predicted_code,
                "correct_code": correct_code,
            }])
            
            df = pd.concat([df, new_entry], ignore_index=True)
            self._save_feedback_data(df)
            
            # Add to Langchain FAISS index if available
            if self.faiss_service:
                try:
                    # Add to Langchain FAISS (no manual embedding needed)
                    feedback_entry = {
                        'description': description,
                        'predicted_code': predicted_code,
                        'correct_code': correct_code,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    success = self.faiss_service.add_feedback_embedding(feedback_entry)
                    if success:
                        logger.info("Added feedback to Langchain FAISS index")
                    else:
                        logger.warning("Failed to add feedback to Langchain FAISS index")
                        
                except Exception as e:
                    logger.error(f"Error adding feedback to Langchain FAISS: {str(e)}")
            
            storage_location = "S3" if (self.use_s3 and self.s3_available) else "local file"
            logger.info(f"Added new feedback entry for HTS code: {correct_code} to {storage_location}")
            
        except Exception as e:
            logger.error(f"Error adding feedback: {str(e)}")
            raise

    def rebuild_faiss_from_existing_data(self, days: int = 365) -> bool:
        """Rebuild Langchain FAISS index from existing feedback data."""
        try:
            if not self.faiss_service:
                logger.warning("Langchain FAISS service not available")
                return False
            
            # Get existing feedback data
            feedback_df = self.get_recent_feedback(days=days)
            
            if feedback_df.empty:
                logger.info("No feedback data available for Langchain FAISS rebuild")
                return True
            
            logger.info(f"Rebuilding Langchain FAISS index from {len(feedback_df)} feedback entries")
            
            # Rebuild FAISS index using Langchain (no manual embeddings needed)
            success = self.faiss_service.rebuild_from_feedback_data(feedback_df)
            
            if success:
                logger.info("Successfully rebuilt Langchain FAISS index from existing feedback data")
            else:
                logger.error("Failed to rebuild Langchain FAISS index")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rebuilding Langchain FAISS from existing data: {str(e)}")
            return False

    def get_feedback_data_for_training(self) -> pd.DataFrame:
        """Get feedback data specifically for training purposes."""
        try:
            df = self._load_feedback_data()
            logger.info(f"Retrieved {len(df)} feedback records for training")
            return df
        except Exception as e:
            logger.error(f"Error getting feedback data for training: {str(e)}")
            return pd.DataFrame()

    def get_recent_feedback(self, days: int = 30) -> pd.DataFrame:
        """Get recent feedback data as DataFrame."""
        try:
            # Load all feedback data directly
            df = self._load_feedback_data()
            
            if df.empty:
                logger.info("No feedback data available")
                return pd.DataFrame()
        
            
            # Convert timestamp column
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter by days
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_df = df[df['timestamp'] >= cutoff_date]
            
            logger.info(f"Retrieved {len(recent_df)} recent feedback records from last {days} days")
            return recent_df
            
        except Exception as e:
            logger.error(f"Error getting recent feedback: {str(e)}")
            return pd.DataFrame()

    def get_correction_patterns(self, days: int = 30) -> Dict:
        """Get correction patterns from feedback data."""
        try:
            # Get recent feedback data
            recent_data = self.get_recent_feedback(days=days)
            
            if recent_data.empty:
                return {}
            
            # Get only corrections (where predicted != correct)
            corrections = recent_data[recent_data['predicted_code'] != recent_data['correct_code']]
            
            if corrections.empty:
                return {}
            
            patterns = {}
            
            # Group by chapter-level corrections
            for _, row in corrections.iterrows():
                pred_chapter = str(row['predicted_code'])[:2]
                correct_chapter = str(row['correct_code'])[:2]
                
                if pred_chapter != correct_chapter:
                    pattern_key = f"Chapter {pred_chapter} -> Chapter {correct_chapter}"
                    
                    if pattern_key not in patterns:
                        patterns[pattern_key] = []
                    
                    patterns[pattern_key].append({
                        'description': row['description'],
                        'predicted_code': row['predicted_code'],
                        'correct_code': row['correct_code'],
                        'timestamp': row['timestamp']
                    })
            
            logger.info(f"Found {len(patterns)} correction patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Error getting correction patterns: {str(e)}")
            return {}

    def get_feedback_quality_metrics(self, days: int = 30) -> Dict:
        """Get quality metrics for feedback data."""
        try:
            recent_data = self.get_recent_feedback(days=days)
            
            if recent_data.empty:
                return {
                    'total_entries': 0,
                    'total_corrections': 0,
                    'correction_rate': 0,
                    'data_freshness': 'No data'
                }
            
            # Calculate corrections
            corrections = recent_data[recent_data['predicted_code'] != recent_data['correct_code']]
            total_corrections = len(corrections)
            correction_rate = total_corrections / len(recent_data) if len(recent_data) > 0 else 0
            
            # Calculate data freshness
            latest_timestamp = pd.to_datetime(recent_data['timestamp']).max()
            data_age = (datetime.now() - latest_timestamp).days
            
            if data_age <= 1:
                freshness = 'Fresh'
            elif data_age <= 7:
                freshness = 'Recent'
            else:
                freshness = 'Stale'
            
            return {
                'total_entries': len(recent_data),
                'total_corrections': total_corrections,
                'correction_rate': correction_rate,
                'data_freshness': freshness,
                'latest_feedback': latest_timestamp.isoformat() if not pd.isna(latest_timestamp) else 'No data'
            }
            
        except Exception as e:
            logger.error(f"Error getting quality metrics: {str(e)}")
            return {
                'total_entries': 0,
                'total_corrections': 0,
                'correction_rate': 0,
                'data_freshness': 'Error',
                'error': str(e)
            }
    
    def get_feedback_stats(self):
        """Get statistics about collected feedback."""
        logger.info("Getting feedback statistics...")
        try:
            df = self._load_feedback_data()
            
            if len(df) == 0:
                return {
                    "total_entries": 0,
                    "accuracy": 0,
                    "recent_entries": []
                }
            
            total = len(df)
            correct = sum(df['predicted_code'] == df['correct_code'])
            logger.debug(f"Total entries: {total}, Correct predictions: {correct}")
            
            # Convert recent entries to dict format
            recent_entries = []
            for _, row in df.tail(10).iterrows():  # Get last 10 entries
                recent_entries.append({
                    'timestamp': row['timestamp'],
                    'description': row['description'],
                    'predicted_code': row['predicted_code'],
                    'correct_code': row['correct_code'],
                })
            
            return {
                "total_entries": total,
                "correct_predictions": correct,
                "accuracy": correct / total if total > 0 else 0,
                "recent_entries": recent_entries,
                "storage_location": "S3" if (self.use_s3 and self.s3_available) else "local file"
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback stats: {str(e)}")
            raise
        
    @staticmethod
    def format_hs_code(code):
        """Format HTS code with proper structure."""
        digits = ''.join(filter(str.isdigit, code))[:12]
        sections = [digits[i:j] for i, j in [(0, 4), (4, 6), (6, 8), (8, 10)] if i < len(digits)]
        return '.'.join(sections)