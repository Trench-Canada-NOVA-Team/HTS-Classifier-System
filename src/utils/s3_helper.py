import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from loguru import logger
import boto3
from io import StringIO
from typing import Dict, Optional
from config.settings import Config

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

class FeedbackHandler:
    def __init__(self, use_s3=True):
        """Initialize the feedback handler.
        
        Args:
            use_s3 (bool): Whether to use S3 storage. Defaults to True.
        """
        self.use_s3 = use_s3
        
        if self.use_s3:
            try:
                self.s3_helper = S3Helper()
                self.s3_helper.initialize_bucket()
            except Exception as e:
                logger.error(f"Failed to initialize S3: {str(e)}")
                self.use_s3 = False
        
        if not self.use_s3:
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
            
            storage_location = "S3" if self.use_s3 else "local file"
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