"""HTS Classification System package."""
# from .s3_feedback_trainer import S3FeedbackTrainer

# __all__ = ['S3FeedbackTrainer']
"""HTS Classification System package."""

# Safe import for S3FeedbackTrainer
try:
    from .utils.s3_feedback_trainer import S3FeedbackTrainer
    S3_TRAINER_AVAILABLE = True
except ImportError:
    S3FeedbackTrainer = None
    S3_TRAINER_AVAILABLE = False

# Safe import for FeedbackHandler
try:
    from .feedback_handler import FeedbackHandler
    FEEDBACK_HANDLER_AVAILABLE = True
except ImportError:
    FeedbackHandler = None
    FEEDBACK_HANDLER_AVAILABLE = False

__all__ = ['S3FeedbackTrainer', 'FeedbackHandler', 'S3_TRAINER_AVAILABLE', 'FEEDBACK_HANDLER_AVAILABLE']