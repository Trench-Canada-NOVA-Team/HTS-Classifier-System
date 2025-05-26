from pathlib import Path
from loguru import logger
from data_loader.json_loader import HTSDataLoader
from preprocessor.text_processor import TextPreprocessor
from classifier.hts_classifier import HTSClassifier

def setup_logger():
    log_path = Path(__file__).parent.parent / "logs"
    log_path.mkdir(exist_ok=True)
    logger.add(log_path / "test_classifier.log", rotation="500 MB")

def test_classification():
    """Test the HTS classification system with sample products."""
    setup_logger()
    
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
    
    # Run tests
    for description in test_cases:
        print(f"\nTesting: {description}")
        print("-" * 80)
        
        try:
            results = classifier.classify(description, top_k=3)
            
            for i, result in enumerate(results, 1):
                print(f"{i}. HTS Code: {result['hts_code']}")
                if result.get('chapter_context'):
                    print(f"   Chapter: {result['chapter_context']}")
                print(f"   Description: {result['description']}")
                print(f"   Confidence: {result['confidence']}%")
                print(f"   General Rate: {result['general_rate']}")
                if result['units']:
                    print(f"   Units: {', '.join(result['units'])}")
                print("-" * 40)
                
        except Exception as e:
            logger.error(f"Error processing '{description}': {str(e)}")
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_classification()