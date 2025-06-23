"""
Logging utilities for the HTS Classification System.
"""
from pathlib import Path
from loguru import logger
from config.settings import Config

def setup_logger(module_name: str = "hts_classifier") -> None:
    """
    Configure logging settings for the application.
    
    Args:
        module_name: Name of the module for log file naming
    """
    Config.LOGS_DIR.mkdir(exist_ok=True)
    log_file = Config.LOGS_DIR / f"{module_name}.log"
    
    logger.add(
        log_file,
        rotation=Config.LOG_ROTATION,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        level="INFO"
    )
    
    logger.info(f"Logger initialized for {module_name}")

def log_classification_attempt(description: str, learn_from_feedback: bool = True) -> None:
    """Log classification attempt with standardized format."""
    logger.info(f"🔍 Classification attempt: '{description[:50]}...' | Learning: {learn_from_feedback}")

def log_feedback_addition(predicted_code: str, correct_code: str, success: bool) -> None:
    """Log feedback addition with standardized format."""
    status = "✅" if success else "❌"
    logger.info(f"{status} Feedback: {predicted_code} → {correct_code}")

def log_performance_metrics(total_entries: int, accuracy: float, storage_type: str) -> None:
    """Log performance metrics with standardized format."""
    logger.info(f"📊 Metrics: {total_entries} entries | {accuracy:.1%} accuracy | Storage: {storage_type}")
