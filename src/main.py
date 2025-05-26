import os
from pathlib import Path
from loguru import logger
from src.data_loader.json_loader import HTSDataLoader
from src.preprocessor.text_processor import TextPreprocessor
from src.classifier.hts_classifier import HTSClassifier

def setup_logger():
    """Configure logging settings."""
    log_path = Path(__file__).parent.parent / "logs"
    log_path.mkdir(exist_ok=True)
    logger.add(log_path / "hts_classifier.log", rotation="500 MB")

def main():
    """Main entry point for HTS classification system."""
    setup_logger()
    
    try:
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
        
        # Interactive classification loop
        print("\nHTS Code Classification System")
        print("Enter 'quit' to exit")
        print("Enter 'stats' to view feedback statistics\n")
        
        while True:
            description = input("Enter product description: ").strip()
            
            if description.lower() == 'quit':
                break
                
            if description.lower() == 'stats':
                stats = classifier.get_feedback_stats()
                print("\nClassification Feedback Statistics:")
                print(f"Total entries: {stats['total_entries']}")
                print(f"Accuracy: {stats['accuracy']*100:.1f}%")
                print("\nRecent entries:")
                for entry in stats['recent_entries']:
                    print(f"Description: {entry['description']}")
                    print(f"Predicted: {entry['predicted_code']} -> Actual: {entry['correct_code']}")
                    print(f"Confidence: {entry['confidence_score']}%")
                    print("-" * 40)
                continue
                
            if not description:
                print("Please enter a valid description")
                continue
                
            try:
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
                
                # Get feedback from user
                while True:
                    feedback = input("\nIs the top prediction correct? (y/n): ").strip().lower()
                    if feedback in ['y', 'n']:
                        break
                    print("Please enter 'y' for yes or 'n' for no")
                
                if feedback == 'n':
                    correct_code = input("Please enter the correct HTS code: ").strip()
                    if correct_code:
                        classifier.add_feedback(
                            product_description=description,
                            predicted_code=results[0]['hts_code'],
                            correct_code=correct_code,
                            confidence_score=results[0]['confidence']
                        )
                        print("Thank you for your feedback!")
                        
            except Exception as e:
                print(f"Error processing request: {str(e)}")
                logger.error(f"Classification error: {str(e)}")
                
    except Exception as e:
        logger.error(f"System initialization error: {str(e)}")
        print(f"Error initializing system: {str(e)}")

if __name__ == "__main__":
    main()