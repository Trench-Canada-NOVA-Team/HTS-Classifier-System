"""
Data models for HTS classification system.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class HTSEntry:
    """Model for HTS entry data."""
    hts_code: str
    description: str
    general_rate: str
    units: List[str]
    indent: int
    special: str = ""
    other: str = ""
    footnotes: List[str] = None
    
    def __post_init__(self):
        if self.footnotes is None:
            self.footnotes = []

@dataclass
class ClassificationResult:
    """Model for classification result."""
    hts_code: str
    description: str
    confidence: float
    general_rate: str
    units: List[str]
    source: str = "standard"
    similarity_score: Optional[float] = None
    match_type: Optional[str] = None
    learning_explanation: Optional[str] = None
    chapter_context: Optional[str] = None
    feedback_adjusted: bool = False

@dataclass
class FeedbackEntry:
    """Model for feedback data."""
    timestamp: datetime
    description: str
    predicted_code: str
    correct_code: str
    confidence_score: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackEntry':
        """Create FeedbackEntry from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']) if isinstance(data['timestamp'], str) else data['timestamp'],
            description=data['description'],
            predicted_code=data['predicted_code'],
            correct_code=data['correct_code'],
            confidence_score=data.get('confidence_score')
        )

@dataclass
class SemanticMatch:
    """Model for semantic feedback match."""
    description: str
    predicted_code: str
    correct_code: str
    similarity_score: float
    timestamp: datetime
    confidence: float

@dataclass
class FaissFeedbackEntry:
    """Model for FAISS feedback data with embedding info."""
    description: str
    predicted_code: str
    correct_code: str
    similarity_score: float
    timestamp: datetime
    faiss_id: int
    confidence: Optional[float] = None
    
    @classmethod
    def from_faiss_result(cls, result: Dict[str, Any]) -> 'FaissFeedbackEntry':
        """Create FaissFeedbackEntry from FAISS search result."""
        return cls(
            description=result['description'],
            predicted_code=result['predicted_code'],
            correct_code=result['correct_code'],
            similarity_score=result['similarity_score'],
            timestamp=datetime.fromisoformat(result['timestamp']) if isinstance(result['timestamp'], str) else result['timestamp'],
            faiss_id=result['faiss_id'],
            confidence=result.get('confidence')
        )

@dataclass
class LangchainFaissFeedbackEntry:
    """Model for Langchain FAISS feedback data with document integration."""
    description: str
    predicted_code: str
    correct_code: str
    similarity_score: float
    timestamp: datetime
    faiss_id: int
    confidence: Optional[float] = None
    
    @classmethod
    def from_langchain_result(cls, result: Dict[str, Any]) -> 'LangchainFaissFeedbackEntry':
        """Create LangchainFaissFeedbackEntry from Langchain FAISS search result."""
        return cls(
            description=result['description'],
            predicted_code=result['predicted_code'],
            correct_code=result['correct_code'],
            similarity_score=result['similarity_score'],
            timestamp=datetime.fromisoformat(result['timestamp']) if isinstance(result['timestamp'], str) else result['timestamp'],
            faiss_id=result['faiss_id'],
            confidence=result.get('confidence')
        )
