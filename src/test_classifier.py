from pathlib import Path
from loguru import logger
from data_loader.json_loader import HTSDataLoader
from preprocessor.text_processor import TextPreprocessor
from classifier.hts_classifier import HTSClassifier
from utils.logging_utils import setup_logger, log_system_startup, log_system_error

def setup_test_logger():
    """Setup logger specifically for testing."""
    try:
        setup_logger("test_classifier")
        log_system_startup("HTS Classifier Test Suite")
        return True
    except Exception as e:
        print(f"Failed to setup test logging: {e}")
        return False

def test_classification():
    """Test the HTS classification system with sample products."""
    # Initialize logging
    if not setup_test_logger():
        print("Warning: Test logging setup failed, continuing without proper logging")
    
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
        
        logger.info("Test initialization completed successfully")
        
        # Test cases - representing different product categories
        test_cases = [
            "Pure-bred breeding horses",
            "Steel screws for wood, thread diameter 6mm",
            "Fresh Atlantic salmon, whole",
            "Men's cotton t-shirts, knitted",
            "Industrial robot for welding",
            "Stainless steel kitchen sink, 60cm x 45cm",
            "Electric coffee maker, 1000W capacity",
            "Leather wallet for men, made of genuine cowhide",
            "Solar panel modules, 400W output",
            "Aluminum window frames, anodized"
        ]
        
        logger.info(f"Starting test classification with {len(test_cases)} test cases")
        
        # Run tests
        for i, description in enumerate(test_cases, 1):
            print(f"\nTesting {i}/{len(test_cases)}: {description}")
            print("-" * 80)
            
            try:
                logger.info(f"Test {i}: Processing '{description}'")
                results = classifier.classify(description, top_k=3)
                
                logger.info(f"Test {i}: Returned {len(results)} results")
                
                for j, result in enumerate(results, 1):
                    print(f"{j}. HTS Code: {result['hts_code']}")
                    if result.get('chapter_context'):
                        print(f"   Chapter: {result['chapter_context']}")
                    print(f"   Description: {result['description']}")
                    print(f"   Confidence: {result['confidence']}%")
                    print(f"   General Rate: {result['general_rate']}")
                    if result['units']:
                        print(f"   Units: {', '.join(result['units'])}")
                    print("-" * 40)
                    
            except Exception as e:
                log_system_error(f"Test {i}", str(e))
                print(f"Error: {str(e)}")
        
        logger.info("Test suite completed successfully")
        
    except Exception as e:
        log_system_error("Test Suite", str(e))
        print(f"Test initialization error: {str(e)}")

if __name__ == "__main__":
    test_classification()