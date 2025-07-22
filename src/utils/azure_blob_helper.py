import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from loguru import logger
from azure.storage.blob import BlobServiceClient, BlobClient
from io import StringIO, BytesIO
from typing import Dict, Optional
from config.settings import Config
from utils.common import format_hts_code

class AzureBlobHelper:  # Renamed from S3Helper
    """Helper class for Azure Blob Storage operations."""
    
    def __init__(self):
        """Initialize Azure Blob helper with configuration."""
        self.container_name = Config.AZURE_CONTAINER_NAME
        self.feedback_blob_key = "feedback-data-canada.csv"
        
        # Initialize using connection string
        self.blob_service_client = BlobServiceClient.from_connection_string(
            Config.AZURE_STORAGE_CONNECTION_STRING
        )
        self.azure_client = self.blob_service_client.get_blob_client(
            container=self.container_name, 
            blob=self.feedback_blob_key
        )

    def initialize_container(self) -> bool:
        """Initialize Azure Blob container and test connection."""
        try:
            # Test connection by listing blobs
            container_client = self.blob_service_client.get_container_client(self.container_name)
            list(container_client.list_blobs())
            logger.info("Azure Blob Storage connection test successful")
            return True
        except Exception as e:
            logger.error(f"Azure Blob Storage connection test failed: {str(e)}")
            return False
    
    def read_feedback(self) -> pd.DataFrame:
        """Read feedback data from Azure Blob Storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=self.feedback_blob_key
            )
            blob_data = blob_client.download_blob()
            content = blob_data.content_as_text()
            return pd.read_csv(StringIO(content))
        except Exception as e:
            if 'BlobNotFound' in str(e) or '404' in str(e):
                logger.info("Feedback file not found in Azure Blob Storage, creating empty DataFrame")
                return pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
            else:
                logger.error(f"Error reading from Azure Blob Storage: {str(e)}")
                raise

    def upload_feedback(self, df: pd.DataFrame) -> None:
        """Upload feedback DataFrame to Azure Blob Storage."""
        try:
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=self.feedback_blob_key
            )
            
            blob_client.upload_blob(
                csv_buffer.getvalue(),
                overwrite=True
            )
            logger.info("Successfully saved feedback data to Azure Blob Storage")
        except Exception as e:
            logger.error(f"Error saving to Azure Blob Storage: {str(e)}")
            raise


    def upload_faiss_index(self, index_path: Path, metadata_path: Path) -> bool:
        """Upload FAISS index and metadata to Azure Blob Storage."""
        try:
            # Upload FAISS index file
            index_blob_key = 'feedback/faiss_index.index'
            with open(index_path, 'rb') as f:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=index_blob_key
                )
                blob_client.upload_blob(f.read(), overwrite=True)
            
            # Upload metadata file
            metadata_blob_key = 'feedback/faiss_metadata.pkl'
            with open(metadata_path, 'rb') as f:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=metadata_blob_key
                )
                blob_client.upload_blob(f.read(), overwrite=True)
            
            logger.info("Successfully uploaded FAISS index and metadata to Azure Blob Storage")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading FAISS index to Azure Blob Storage: {str(e)}")
            return False
        
    def download_faiss_index(self, local_index_path: Path, local_metadata_path: Path) -> bool:
        """Download FAISS index and metadata from Azure Blob Storage."""
        try:
            # Download FAISS index file
            index_blob_key = 'feedback/faiss_index.index'
            try:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=index_blob_key
                )
                with open(local_index_path, 'wb') as f:
                    blob_data = blob_client.download_blob()
                    f.write(blob_data.readall())
            except Exception as e:
                if 'BlobNotFound' in str(e):
                    logger.info("FAISS index not found in Azure Blob Storage")
                    return False
                raise
            
            # Download metadata file
            metadata_blob_key = 'feedback/faiss_metadata.pkl'
            try:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=metadata_blob_key
                )
                with open(local_metadata_path, 'wb') as f:
                    blob_data = blob_client.download_blob()
                    f.write(blob_data.readall())
            except Exception as e:
                if 'BlobNotFound' in str(e):
                    logger.info("FAISS metadata not found in Azure Blob Storage")
                    return False
                raise
            
            logger.info("Successfully downloaded FAISS index and metadata from Azure Blob Storage")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading FAISS index from Azure Blob Storage: {str(e)}")
            return False
    
    def upload_faiss_langchain_index(self, local_faiss_path: Path, local_metadata_path: Path) -> bool:
        """Upload Langchain FAISS index directory and metadata to Azure Blob."""
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
                    self.azure_client.upload_blob(
                        container_name=self.container_name,
                        blob_name=index_key,
                        data=f.read()
                    )
            
            # Clean up temporary file
            Path(tmp_zip.name).unlink()
            
            # Upload metadata file
            metadata_key = 'feedback/langchain_faiss_metadata.pkl'
            with open(local_metadata_path, 'rb') as f:
                self.azure_client.upload_blob(
                    container_name=self.container_name,
                    blob_name=metadata_key,
                    data=f.read()
                )

            logger.info("Successfully uploaded Langchain FAISS index and metadata to Azure Blob Storage")
            return True

        except Exception as e:
            logger.error(f"Error uploading Langchain FAISS index to Azure Blob Storage: {str(e)}")
            return False
 
    
    def download_faiss_langchain_index(self, local_faiss_path: Path, local_metadata_path: Path) -> bool:
        """Download Langchain FAISS index and metadata from Azure Blob Storage."""
        try:
            import zipfile
            import tempfile
            
            # Download FAISS index zip file
            index_key = 'feedback/langchain_faiss_index.zip'
            try:
                response = self.azure_client.get_blob(
                    container_name=self.container_name,
                    blob_name=index_key
                )

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
                    logger.info("Langchain FAISS index not found in Azure Blob Storage")
                    return False
                raise
            
            # Download metadata file
            metadata_key = 'feedback/langchain_faiss_metadata.pkl'
            try:
                response = self.azure_client.get_blob(
                    container_name=self.container_name,
                    blob_name=metadata_key
                )
                local_metadata_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_metadata_path, 'wb') as f:
                    f.write(response['Body'].read())
            except Exception as e:
                if 'NoSuchKey' in str(e):
                    logger.info("Langchain FAISS metadata not found in Azure Blob Storage")
                    return False
                raise

            logger.info("Successfully downloaded Langchain FAISS index and metadata from Azure Blob Storage")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading Langchain FAISS index from S3: {str(e)}")
            return False
    
class FeedbackHandler:
    def __init__(self, use_azure=True, faiss_service=None):  # Changed from use_s3
        """Initialize the feedback handler.
        
        Args:
            use_azure (bool): Whether to use Azure Blob Storage. Defaults to True.
            faiss_service: Optional Langchain FaissFeedbackService instance for vector storage
        """
        self.use_azure = use_azure  # Changed from use_s3
        self.azure_available = False  # Changed from s3_available
        self.faiss_service = faiss_service
        
        # Initialize FAISS service if available
        if self.faiss_service:
            self.faiss_service.initialize_index()
            logger.info("Langchain FAISS service initialized for feedback handler")
        
        if self.use_azure:
            try:
                self.azure_helper = AzureBlobHelper()  # Changed from S3Helper
                self.azure_helper.initialize_container()  # Changed method name
                self.azure_available = True
                self._initialize_azure_blob_feedback_file()  # Changed method name
                logger.info("Azure Blob Storage initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure Blob Storage: {str(e)}")
                logger.info("Falling back to local storage")
                self.use_azure = False
                self.azure_available = False
        
        if not self.azure_available:
            self.feedback_file = Config.DATA_DIR / "feedback_data.csv"
            self._initialize_feedback_file()

    def _initialize_azure_blob_feedback_file(self):
        """Create feedback file in Azure Blob Storage if it doesn't exist."""
        if not self.azure_available:
            return
            
        try:
            # Check if file exists in Azure Blob Storage
            try:
                self.azure_helper.azure_client.get_blob_properties()
                logger.info(f"Feedback file found in Azure Blob Storage: {self.azure_helper.feedback_blob_key}")
            except Exception as e:
                if '404' in str(e) or 'The specified blob does not exist.' in str(e):
                    # File doesn't exist, create it
                    logger.info(f"Feedback file not found in Azure Blob Storage, creating: {self.azure_helper.feedback_blob_key}")
                    df = pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 'correct_code'])
                    self.azure_helper.upload_feedback(df)
                    logger.info(f"Created new feedback file in Azure Blob Storage: {self.azure_helper.feedback_blob_key}")
                else:
                    raise
        except Exception as e:
            logger.error(f"Error initializing Azure Blob Storage feedback file: {str(e)}")
            self.use_azure = False
            self.azure_available = False
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
            if self.use_azure:
                return self.azure_helper.read_feedback()
            else:
                return pd.read_csv(self.feedback_file)
        except Exception as e:
            logger.warning(f"Error reading feedback data: {str(e)}. Creating new one.")
            return pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 
                                      'correct_code'])
    
    def _save_feedback_data(self, df):
        """Save feedback data."""
        if self.use_azure:
            self.azure_helper.upload_feedback(df)
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

            storage_location = "Azure Blob Storage" if (self.use_azure and self.azure_available) else "local file"
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
                    "storage_location": "Azure Blob Storage" if (self.use_azure and self.azure_available) else "local file"
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
                "storage_location": "Azure Blob Storage" if (self.use_azure and self.azure_available) else "local file"
            }
            
            logger.debug(f"Returning feedback stats: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting feedback stats: {str(e)}")
            raise