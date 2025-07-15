import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from loguru import logger
import boto3
from io import StringIO
from typing import Dict, Optional
from config.settings import Config
from utils.common import format_hts_code

class S3Helper:
    """Helper class for S3 operations."""
    
    def __init__(self):
        """Initialize S3 helper with configuration."""
        self.bucket_name = Config.AWS_BUCKET_NAME
        self.s3_key = Config.S3_FEEDBACK_KEY
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
    
    def initialize_bucket(self) -> bool:
        """Initialize S3 bucket and test connection."""
        try:
            self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            logger.info("S3 connection test successful")
            return True
        except Exception as e:
            logger.error(f"S3 connection test failed: {str(e)}")
            return False
    
    def read_feedback(self) -> pd.DataFrame:
        """Read feedback data from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self.s3_key)
            content = response['Body'].read().decode('utf-8')
            return pd.read_csv(StringIO(content))
        except Exception as e:
            if 'NoSuchKey' in str(e) or '404' in str(e):
                logger.info("Feedback file not found in S3, creating empty DataFrame")
                return pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
            else:
                logger.error(f"Error reading from S3: {str(e)}")
                raise
    
    def upload_feedback(self, df: pd.DataFrame) -> None:
        """Upload feedback DataFrame to S3."""
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

    def upload_faiss_index(self, index_path: Path, metadata_path: Path) -> bool:
        """Upload FAISS index and metadata to S3."""
        try:
            # Upload FAISS index file
            index_key = 'feedback/faiss_index.index'
            with open(index_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=index_key,
                    Body=f.read()
                )
            
            # Upload metadata file
            metadata_key = 'feedback/faiss_metadata.pkl'
            with open(metadata_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=metadata_key,
                    Body=f.read()
                )
            
            logger.info("Successfully uploaded FAISS index and metadata to S3")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading FAISS index to S3: {str(e)}")
            return False
    
    def download_faiss_index(self, local_index_path: Path, local_metadata_path: Path) -> bool:
        """Download FAISS index and metadata from S3."""
        try:
            # Download FAISS index file
            index_key = 'feedback/faiss_index.index'
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=index_key)
                with open(local_index_path, 'wb') as f:
                    f.write(response['Body'].read())
            except Exception as e:
                if 'NoSuchKey' in str(e):
                    logger.info("FAISS index not found in S3")
                    return False
                raise
            
            # Download metadata file
            metadata_key = 'feedback/faiss_metadata.pkl'
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                with open(local_metadata_path, 'wb') as f:
                    f.write(response['Body'].read())
            except Exception as e:
                if 'NoSuchKey' in str(e):
                    logger.info("FAISS metadata not found in S3")
                    return False
                raise
            
            logger.info("Successfully downloaded FAISS index and metadata from S3")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading FAISS index from S3: {str(e)}")
            return False

    def upload_faiss_langchain_index(self, local_faiss_path: Path, local_metadata_path: Path) -> bool:
        """Upload Langchain FAISS index directory and metadata to S3."""
        try:
            import zipfile
            import tempfile
            
            # Create a temporary zip file containing the FAISS index
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
                with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add all files from the FAISS directory
                    if local_faiss_path.exists():
                        for file_path in local_faiss_path.rglob('*'):
                            if file_path.is_file():
                                arcname = str(file_path.relative_to(local_faiss_path))
                                zipf.write(str(file_path), arcname)
                
                # Upload the zip file to S3
                index_key = 'feedback/langchain_faiss_index.zip'
                with open(tmp_zip.name, 'rb') as f:
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=index_key,
                        Body=f.read()
                    )
            
            # Clean up temporary file
            Path(tmp_zip.name).unlink()
            
            # Upload metadata file
            metadata_key = 'feedback/langchain_faiss_metadata.pkl'
            with open(local_metadata_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=metadata_key,
                    Body=f.read()
                )
            
            logger.info("Successfully uploaded Langchain FAISS index and metadata to S3")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading Langchain FAISS index to S3: {str(e)}")
            return False
    
    def download_faiss_langchain_index(self, local_faiss_path: Path, local_metadata_path: Path) -> bool:
        """Download Langchain FAISS index and metadata from S3."""
        try:
            import zipfile
            import tempfile
            
            # Download FAISS index zip file
            index_key = 'feedback/langchain_faiss_index.zip'
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=index_key)
                
                # Create temporary file for the zip
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
                    tmp_zip.write(response['Body'].read())
                
                # Extract zip to the target directory
                local_faiss_path.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(tmp_zip.name, 'r') as zipf:
                    zipf.extractall(str(local_faiss_path))
                
                # Clean up temporary file
                Path(tmp_zip.name).unlink()
                
            except Exception as e:
                if 'NoSuchKey' in str(e):
                    logger.info("Langchain FAISS index not found in S3")
                    return False
                raise
            
            # Download metadata file
            metadata_key = 'feedback/langchain_faiss_metadata.pkl'
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                local_metadata_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_metadata_path, 'wb') as f:
                    f.write(response['Body'].read())
            except Exception as e:
                if 'NoSuchKey' in str(e):
                    logger.info("Langchain FAISS metadata not found in S3")
                    return False
                raise
            
            logger.info("Successfully downloaded Langchain FAISS index and metadata from S3")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading Langchain FAISS index from S3: {str(e)}")
            return False

class FeedbackHandler:
    def __init__(self, use_s3=True, faiss_service=None):
        """Initialize the feedback handler.
        
        Args:
            use_s3 (bool): Whether to use S3 storage. Defaults to True.
            faiss_service: Optional Langchain FaissFeedbackService instance for vector storage
        """
        self.use_s3 = use_s3
        self.s3_available = False
        self.faiss_service = faiss_service
        
        # Initialize FAISS service if available
        if self.faiss_service:
            self.faiss_service.initialize_index()
            logger.info("Langchain FAISS service initialized for feedback handler")
        
        if self.use_s3:
            try:
                self.s3_helper = S3Helper()
                self.s3_helper.initialize_bucket()
                self.s3_available = True
                self._initialize_s3_feedback_file()
                logger.info("S3 storage initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize S3: {str(e)}")
                logger.info("Falling back to local storage")
                self.use_s3 = False
                self.s3_available = False
        
        if not self.s3_available:
            self.feedback_file = Config.DATA_DIR / "feedback_data.csv"
            self._initialize_feedback_file()
    
    def _initialize_s3_feedback_file(self):
        """Create feedback file in S3 if it doesn't exist."""
        if not self.s3_available:
            return
            
        try:
            # Check if file exists in S3
            try:
                self.s3_helper.s3_client.head_object(Bucket=self.s3_helper.bucket_name, Key=self.s3_helper.s3_key)
                logger.info(f"Feedback file found in S3: {self.s3_helper.s3_key}")
            except Exception as e:
                if '404' in str(e) or 'NoSuchKey' in str(e):
                    # File doesn't exist, create it
                    logger.info(f"Feedback file not found in S3, creating: {self.s3_helper.s3_key}")
                    df = pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
                    self.s3_helper.upload_feedback(df)
                    logger.info(f"Created new feedback file in S3: {self.s3_helper.s3_key}")
                else:
                    raise
        except Exception as e:
            logger.error(f"Error initializing S3 feedback file: {str(e)}")
            self.use_s3 = False
            self.s3_available = False
            self.feedback_file = Config.DATA_DIR / "feedback_data.csv"
            self._initialize_feedback_file()

    def _initialize_feedback_file(self):
        """Create feedback file if it doesn't exist (local storage only)."""
        if not self.feedback_file.exists():
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            # Create CSV with headers
            df = pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 
                                     'correct_code'])
            df.to_csv(self.feedback_file, index=False)
            logger.info(f"Created new feedback file at {self.feedback_file}")
    
    def _load_feedback_data(self):
        """Load existing feedback data."""
        try:
            if self.use_s3:
                return self.s3_helper.read_feedback()
            else:
                return pd.read_csv(self.feedback_file)
        except Exception as e:
            logger.warning(f"Error reading feedback data: {str(e)}. Creating new one.")
            return pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 
                                      'correct_code'])
    
    def _save_feedback_data(self, df):
        """Save feedback data."""
        if self.use_s3:
            self.s3_helper.upload_feedback(df)
        else:
            df.to_csv(self.feedback_file, index=False)
    
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

    def get_recent_feedback(self, days: int = None) -> pd.DataFrame:
        """Get recent feedback data as DataFrame."""
        # Use configuration default if not provided
        days = days or Config.DEFAULT_FEEDBACK_DAYS
        
        try:
            # Load all feedback data directly
            df = self._load_feedback_data()
            
            if df.empty:
                logger.info("No feedback data available")
                return pd.DataFrame()
            
            # Convert timestamp column
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter by days
            cutoff_date = datetime.now() - pd.Timedelta(days=days)
            recent_df = df[df['timestamp'] >= cutoff_date]
            
            logger.info(f"Retrieved {len(recent_df)} recent feedback records from last {days} days")
            return recent_df
            
        except Exception as e:
            logger.error(f"Error getting recent feedback: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    def format_hs_code(code):
        """Format HTS code with proper structure."""
        # Use the centralized format_hts_code function
        return format_hts_code(code)

    def get_feedback_stats(self):
        """Get statistics about collected feedback."""
        logger.info("Getting feedback statistics...")
        try:
            df = self._load_feedback_data()
            
            if len(df) == 0:
                return {
                    "total_entries": 0,
                    "accuracy": 0,
                    "correct_predictions": 0,
                    "recent_entries": [],
                    "storage_location": "S3" if (self.use_s3 and self.s3_available) else "local file"
                }
            
            total = len(df)
            correct = sum(df['predicted_code'] == df['correct_code'])
            accuracy = correct / total if total > 0 else 0
            
            logger.debug(f"Total entries: {total}, Correct predictions: {correct}, Accuracy: {accuracy}")
            
            # Use configuration for recent entries count
            recent_count = Config.DASHBOARD_RECENT_ENTRIES_COUNT
            recent_entries = []
            for _, row in df.tail(recent_count).iterrows():
                recent_entries.append({
                    'timestamp': row['timestamp'],
                    'description': row['description'],
                    'predicted_code': row['predicted_code'],
                    'correct_code': row['correct_code'],
                })
            
            result = {
                "total_entries": total,
                "correct_predictions": correct,
                "accuracy": accuracy,
                "recent_entries": recent_entries,
                "storage_location": "S3" if (self.use_s3 and self.s3_available) else "local file"
            }
            
            logger.debug(f"Returning feedback stats: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting feedback stats: {str(e)}")
            raise