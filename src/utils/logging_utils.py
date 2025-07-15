"""
Logging utilities for the HTS Classification System.
"""
from pathlib import Path
from loguru import logger
from config.settings import Config
import sys

def setup_logger(module_name: str = "hts_classifier") -> None:
    """
    Configure logging settings for the application.
    
    Args:
        module_name: Name of the module for log file naming
    """
    # Remove default handler to avoid duplicate logs
    logger.remove()
    
    # Add console handler with INFO level
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level="INFO"
    )
    
    # Ensure logs directory exists
    Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Use configurable log file names based on module
    if module_name == "hts_classifier":
        log_filename = Config.MAIN_LOG_FILE
    elif module_name == "test_classifier":
        log_filename = Config.TEST_LOG_FILE
    elif module_name == "streamlit_app":
        log_filename = Config.STREAMLIT_LOG_FILE
    else:
        log_filename = f"{module_name}.log"
    
    log_file = Config.LOGS_DIR / log_filename
    
    # Add file handler with detailed format
    logger.add(
        log_file,
        rotation=Config.LOG_ROTATION,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        level="DEBUG",  # More detailed logging to file
        retention=Config.LOG_RETENTION_DAYS,
        compression=Config.LOG_COMPRESSION
    )
    
    logger.info(f"Logger initialized for {module_name}")
    logger.info(f"Log file: {log_file}")

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

def log_system_startup(component: str) -> None:
    """Log system component startup."""
    logger.info(f"🚀 Starting {component}")

def log_system_error(component: str, error: str) -> None:
    """Log system errors with standardized format."""
    logger.error(f"❌ {component} Error: {error}")

def log_system_success(component: str, message: str) -> None:
    """Log system success with standardized format."""
    logger.success(f"✅ {component}: {message}")

def log_model_training_start(model_name: str) -> None:
    """Log the start of the model training process."""
    logger.info(f"📚 Training started for model: {model_name}")

def log_model_training_end(model_name: str, success: bool) -> None:
    """Log the end of the model training process."""
    status = "✅" if success else "❌"
    logger.info(f"{status} Training ended for model: {model_name}")

def log_data_loading(file_path: str, success: bool) -> None:
    """Log data loading events."""
    status = "✅" if success else "❌"
    logger.info(f"{status} Data loading {'succeeded' if success else 'failed'} for file: {file_path}")

def log_prediction_inference(model_name: str, sample_data: dict) -> None:
    """Log details about prediction inference."""
    logger.info(f"🔮 Inference by {model_name} on data: {sample_data}")

def log_results_saving(file_path: str, success: bool) -> None:
    """Log the results saving events."""
    status = "✅" if success else "❌"
    logger.info(f"{status} Results {'successfully' if success else 'unsuccessfully'} saved to: {file_path}")

def log_hyperparameter_tuning(model_name: str, params: dict) -> None:
    """Log hyperparameter tuning details."""
    logger.info(f"⚙️ Tuning hyperparameters for {model_name}: {params}")

def log_experiment_outcome(experiment_id: str, outcome: str) -> None:
    """Log the outcome of an experiment."""
    logger.info(f"🧪 Experiment {experiment_id} outcome: {outcome}")
