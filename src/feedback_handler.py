import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from loguru import logger
from dotenv import load_dotenv
import os
from io import StringIO
import boto3

class FeedbackHandler:
    def __init__(self, use_s3=True, feedback_file_path=None):
        """Initialize the feedback handler.
        
        Args:
            use_s3 (bool): Whether to use S3 storage. Defaults to True.
            feedback_file_path (str, optional): Path to store feedback data locally.
                Defaults to 'Data/feedback_data.csv'.
        """
        load_dotenv()
        
        self.use_s3 = use_s3
        self.s3_available = False
        
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
            # Try to list objects in the bucket (this tests basic access)
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
                    # Some other error
                    raise
        except Exception as e:
            logger.error(f"Error initializing S3 feedback file: {str(e)}")
            # Don't raise - fall back to local storage
            self.use_s3 = False
            self.s3_available = False
            self._initialize_feedback_file()
    
    def _initialize_feedback_file(self):
        """Create feedback file if it doesn't exist (local storage only)."""
        if not self.feedback_file.exists():
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            # Create CSV with headers
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
        """Add new feedback entry.
        
        Args:
            description (str): Original product description
            predicted_code (str): HTS code predicted by the classifier
            correct_code (str): Correct HTS code provided by user
        """
        try:
            logger.info("Adding feedback...")
            df = self._load_feedback_data()
            
            new_entry = pd.DataFrame([{
                "timestamp": datetime.now().isoformat(),
                "description": description,
                "predicted_code": predicted_code,
                "correct_code": correct_code,
            }])
            
            # Append new entry to existing data
            df = pd.concat([df, new_entry], ignore_index=True)
            self._save_feedback_data(df)
            
            storage_location = "S3" if (self.use_s3 and self.s3_available) else "local file"
            logger.info(f"Added new feedback entry for HTS code: {correct_code} to {storage_location}")
            
        except Exception as e:
            logger.error(f"Error adding feedback: {str(e)}")
            raise
    
    def get_feedback_stats(self):
        """Get statistics about collected feedback."""
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
            
            # Convert recent entries to dict format
            recent_entries = []
            for _, row in df.tail(5).iterrows():
                recent_entries.append({
                    'timestamp': row['timestamp'],
                    'description': row['description'],
                    'predicted_code': row['predicted_code'],
                    'correct_code': row['correct_code'],
                })
            
            return {
                "total_entries": total,
                "accuracy": correct / total if total > 0 else 0,
                "recent_entries": recent_entries
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback stats: {str(e)}")
            raise
    
    @staticmethod
    def format_hs_code(code):
        """Format HTS code with proper structure."""
        digits = ''.join(filter(str.isdigit, code))[:12]  # remove non-digits, limit to 12 chars
        sections = [digits[i:j] for i, j in [(0, 4), (4, 6), (6, 8), (8, 10)] if i < len(digits)]
        return '.'.join(sections)