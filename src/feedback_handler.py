import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from loguru import logger

class FeedbackHandler:
    def __init__(self, feedback_file_path=None):
        """Initialize the feedback handler.
        
        Args:
            feedback_file_path (str, optional): Path to store feedback data.
                Defaults to 'Data/feedback_data.csv'.
        """
        if feedback_file_path is None:
            self.feedback_file = Path(__file__).parent.parent / "Data" / "feedback_data.csv"
        else:
            self.feedback_file = Path(feedback_file_path)
            
        self._initialize_feedback_file()
    
    def _initialize_feedback_file(self):
        """Create feedback file if it doesn't exist."""
        if not self.feedback_file.exists():
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            # Create CSV with headers
            df = pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 
                                     'correct_code', 'confidence_score'])
            df.to_csv(self.feedback_file, index=False)
            logger.info(f"Created new feedback file at {self.feedback_file}")
    
    def _load_feedback_data(self):
        """Load existing feedback data."""
        try:
            return pd.read_csv(self.feedback_file)
        except Exception as e:
            logger.warning(f"Error reading feedback file: {str(e)}. Creating new one.")
            return pd.DataFrame(columns=['timestamp', 'description', 'predicted_code', 
                                      'correct_code', 'confidence_score'])
    
    def _save_feedback_data(self, df):
        """Save feedback data to CSV file."""
        df.to_csv(self.feedback_file, index=False)
    
    def add_feedback(self, description, predicted_code, correct_code, confidence_score):
        """Add new feedback entry.
        
        Args:
            description (str): Original product description
            predicted_code (str): HTS code predicted by the classifier
            correct_code (str): Correct HTS code provided by user
            confidence_score (float): Confidence score of the prediction
        """
        df = self._load_feedback_data()
        
        new_entry = pd.DataFrame([{
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "predicted_code": predicted_code,
            "correct_code": correct_code,
            "confidence_score": confidence_score
        }])
        
        # Append new entry to existing data
        df = pd.concat([df, new_entry], ignore_index=True)
        self._save_feedback_data(df)
        logger.info(f"Added new feedback entry for HTS code: {correct_code}")
    
    def get_feedback_stats(self):
        """Get statistics about collected feedback."""
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
                'confidence_score': row['confidence_score']
            })
        
        return {
            "total_entries": total,
            "accuracy": correct / total if total > 0 else 0,
            "recent_entries": recent_entries
        }
