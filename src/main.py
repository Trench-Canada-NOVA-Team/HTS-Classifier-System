import os
from pathlib import Path
from loguru import logger
from data_loader.json_loader import HTSDataLoader
from preprocessor.text_processor import TextPreprocessor
from classifier.hts_classifier import HTSClassifier
from utils.logging_utils import setup_logger, log_system_startup, log_system_error

def setup_logging():
    """Configure logging settings with proper initialization."""
    try:
        setup_logger("hts_classifier")
        log_system_startup("HTS Classification System")
        return True
    except Exception as e:
        print(f"Failed to setup logging: {e}")
        return False

def main():
    """Main entry point for HTS classification system."""
    # Initialize logging first
    if not setup_logging():
        print("Warning: Logging setup failed, continuing without proper logging")
    
    try:
        log_system_startup("System Initialization")
        
        # Initialize components
        current_dir = Path(__file__).parent.parent
        data_dir = current_dir / "Data"
        
        logger.info(f"Initializing HTS classifier with data from {data_dir}")
        data_loader = HTSDataLoader(data_dir)
        preprocessor = TextPreprocessor()
        classifier = HTSClassifier(data_loader, preprocessor)
        
        # Load data and build index
        logger.info("Loading HTS data...")
        data_loader.load_all_chapters()
        
        logger.info("Building search index...")
        classifier.build_index()
        
        logger.info("System initialization completed successfully")
        
        # Interactive classification loop
        print("\nHTS Code Classification System")
        print("Enter 'quit' to exit")
        print("Enter 'stats' to view feedback statistics\n")
        
        while True:
            description = input("Enter product description: ").strip()
            
            if description.lower() == 'quit':
                logger.info("User requested system shutdown")
                break
                
            if description.lower() == 'stats':
                try:
                    stats = classifier.get_feedback_stats()
                    logger.info("Feedback statistics requested")
                    print("\nClassification Feedback Statistics:")
                    print(f"Total entries: {stats['total_entries']}")
                    print(f"Accuracy: {stats['accuracy']*100:.1f}%")
                    print("\nRecent entries:")
                    for entry in stats['recent_entries']:
                        print(f"Description: {entry['description']}")
                        print(f"Predicted: {entry['predicted_code']} -> Actual: {entry['correct_code']}")
                        print("-" * 40)
                except Exception as e:
                    log_system_error("Statistics", str(e))
                    print("Error retrieving statistics")
                continue
                
            if not description:
                print("Please enter a valid description")
                continue
                
            try:
                logger.info(f"Processing classification request: {description[:100]}...")
                results = classifier.classify(description)
                
                print("\nTop matches:")
                print("-" * 80)
                for i, result in enumerate(results, 1):
                    print(f"{i}. HTS Code: {result['hts_code']}")
                    print(f"   Description: {result['description']}")
                    print(f"   Confidence: {result['confidence']}%")
                    print(f"   General Rate: {result['general_rate']}")
                    if result['units']:
                        print(f"   Units: {', '.join(result['units'])}")
                    print("-" * 80)
                
                logger.info(f"Classification completed - returned {len(results)} results")
                
                # Get feedback from user
                while True:
                    feedback = input("\nIs the top prediction correct? (y/n): ").strip().lower()
                    if feedback in ['y', 'n']:
                        break
                    print("Please enter 'y' for yes or 'n' for no")
                
                if feedback == 'n':
                    correct_code = input("Please enter the correct HTS code: ").strip()
                    if correct_code:
                        try:
                            classifier.add_feedback(
                                product_description=description,
                                predicted_code=results[0]['hts_code'],
                                correct_code=correct_code
                            )
                            print("Thank you for your feedback!")
                            logger.info(f"Feedback recorded: {results[0]['hts_code']} -> {correct_code}")
                        except Exception as e:
                            log_system_error("Feedback", str(e))
                            print("Error recording feedback")
                else:
                    logger.info("User confirmed prediction was correct")
                        
            except Exception as e:
                log_system_error("Classification", str(e))
                print(f"Error processing request: {str(e)}")
                
    except Exception as e:
        log_system_error("System", str(e))
        print(f"Error initializing system: {str(e)}")

if __name__ == "__main__":
    main()