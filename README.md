# HTS Classification System

An AI-powered Harmonized Tariff Schedule (HTS) classification system that automatically classifies products into appropriate trade codes using advanced machine learning and semantic feedback learning.

## 🚀 Features

- **AI-Powered Classification**: Uses OpenAI embeddings and GPT-4 for intelligent product classification
- **Semantic Learning**: Learns from user feedback to improve accuracy over time
- **Real-time Validation**: Provides confidence scores and explanations for each classification
- **Visual Proof**: Generates highlighted PDF proofs from official HTS documents
- **Performance Analytics**: Comprehensive dashboard for monitoring system performance
- **Cloud Integration**: AWS S3 storage for persistent learning data
- **Professional Interface**: Clean, intuitive web interface built with Streamlit

## 🏗️ Architecture

```
User Input → Text Processing → AI Classification → Feedback Learning → Results
     ↓              ↓                ↓                ↓              ↓
Streamlit → TextPreprocessor → EmbeddingService → FeedbackHandler → Dashboard
                              → GPTValidation   → S3Storage
                              → VectorSearch    → Cache
```

## 📁 Project Structure

```
TariffPilot/
├── src/
│   ├── config/                   # Configuration and settings
│   ├── services/                 # Core business logic
│   ├── models/                   # Data models
│   ├── utils/                    # Utility functions
│   ├── data_loader/             # Data loading
│   ├── preprocessor/            # Text preprocessing
│   ├── classifier/              # Classification logic
│   ├── feedback_handler.py      # Feedback management
│   └── app.py                   # Streamlit application
├── Data/                        # HTS data files
├── logs/                        # Application logs
├── cache/                       # Embedding cache
└── requirements.txt             # Dependencies
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- OpenAI API key
- Pinecone API key (optional, for vector search)
- AWS credentials (optional, for cloud storage)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd TariffPilot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Environment Variables**
```env
# Required
OPENAI_API_KEY=your_openai_api_key

# Optional (for enhanced features)
PINECONE_API_KEY=your_pinecone_api_key
AWS_BUCKET_NAME=your_s3_bucket
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-west-1
```

## 🚀 Usage

### Web Interface
```bash
# Start the Streamlit application
streamlit run src/app.py
```

### Command Line Interface
```bash
# Basic classification
python src/main.py

# Run tests
python src/test_classifier.py
```

### Python API
```python
from src.classifier.feedback_enhanced_classifier import FeedbackEnhancedClassifier
from src.data_loader.json_loader import HTSDataLoader
from src.preprocessor.text_processor import TextPreprocessor

# Initialize components
data_loader = HTSDataLoader("Data")
preprocessor = TextPreprocessor()
classifier = FeedbackEnhancedClassifier(data_loader, preprocessor)

# Build index
classifier.build_index()

# Classify product
results = classifier.classify("leather wallet", learn_from_feedback=True)
for result in results:
    print(f"HTS Code: {result['hts_code']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Description: {result['description']}")
```

## 🧠 AI & Machine Learning

### Classification Process
1. **Text Preprocessing**: Normalizes and enhances product descriptions
2. **Embedding Generation**: Converts text to vectors using OpenAI
3. **Similarity Search**: Finds similar products in vector database
4. **GPT Validation**: Validates matches and provides confidence scores
5. **Semantic Learning**: Applies feedback-based improvements

### Learning Mechanisms
- **Exact Match Learning**: Remembers identical product corrections
- **Semantic Similarity Learning**: Learns from similar product patterns
- **Pattern Recognition**: Identifies correction trends across categories
- **Confidence Calibration**: Adjusts confidence based on historical accuracy

## 📊 Performance Monitoring

### Key Metrics
- **Classification Accuracy**: Overall system accuracy percentage
- **Learning Effectiveness**: Improvement rate from feedback
- **Response Time**: Average classification speed
- **Feedback Quality**: User correction patterns

### Dashboard Features
- Real-time performance metrics
- Learning progress tracking
- Feedback analytics
- System health monitoring

## 🔧 Configuration

### Classification Settings
```python
# config/settings.py
class Config:
    SEMANTIC_THRESHOLD = 0.50           # Similarity matching threshold
    HIGH_CONFIDENCE_THRESHOLD = 0.70    # High confidence threshold
    BASE_CONFIDENCE_THRESHOLD = 20      # Base confidence threshold
    
    # Category-specific thresholds
    CATEGORY_42_THRESHOLD = 10          # Leather goods
    APPAREL_THRESHOLD = 15              # Clothing items
    ALUMINUM_THRESHOLD = 15             # Aluminum products
```

### Product Mappings
```python
# Custom product mappings for specific categories
PRODUCT_MAPPINGS = {
    ('wallet', 'leather'): ['4202.31', '4202.32'],
    ('handbag', 'leather'): ['4202.21', '4202.22'],
    ('t-shirt', 'cotton'): ['6109.10'],
    # ... more mappings
}
```

## 🧪 Testing

### Run Test Suite
```bash
# Test classification system
python src/test_classifier.py

# Test specific components
python -m pytest tests/
```

### Test Products
```python
test_cases = [
    "Pure-bred breeding horses",
    "Steel screws for wood, thread diameter 6mm", 
    "Fresh Atlantic salmon, whole",
    "Men's cotton t-shirts, knitted",
    "Industrial robot for welding"
]
```

## 📈 Performance Optimization

### Caching Strategy
- **Embedding Cache**: Stores computed embeddings to reduce API calls
- **Result Cache**: Caches classification results for repeated queries
- **Smart Invalidation**: Updates cache when underlying data changes

### API Optimization
- **Batch Processing**: Efficient handling of multiple requests
- **Rate Limiting**: Respects API rate limits and quotas
- **Connection Pooling**: Reuses connections for better performance

## 🔍 Troubleshooting

### Common Issues

#### API Connection Errors
```bash
# Test API connections
python -c "from src.services.embedding_service import EmbeddingService; EmbeddingService().test_connection()"
```

#### Cache Issues
```bash
# Clear cache
rm -rf cache/*
```

#### Classification Accuracy
- Provide more detailed product descriptions
- Use industry-standard terminology
- Enable semantic learning features
- Review and correct system suggestions

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Deployment

### Local Development
```bash
streamlit run src/app.py
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "src/app.py"]
```

### Cloud Deployment
- **AWS**: Deploy using EC2, ECS, or Lambda
- **Google Cloud**: Use Cloud Run or Compute Engine
- **Azure**: Deploy with Container Instances or App Service

## 📚 API Reference

### Core Classes

#### `HTSClassifier`
Base classification functionality
```python
classify(description, top_k=3, country_code=None)
build_index()
get_feedback_stats()
```

#### `FeedbackEnhancedClassifier`
Enhanced classifier with learning capabilities
```python
classify(description, learn_from_feedback=True)
add_feedback(description, predicted_code, correct_code)
get_semantic_learning_insights()
```

#### `FeedbackHandler`
Manages user feedback and learning data
```python
add_feedback(description, predicted_code, correct_code)
get_feedback_stats()
get_recent_feedback(days=30)
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings for public methods
- Include unit tests for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Team

- **Sean Spencer** - Lead Developer
- **Shehbaz Patel** - AI/ML Engineer
- **NOVA Team** - Development Team

## 📞 Support

For technical support or questions:
- Create an issue in the repository
- Contact the development team
- Review the troubleshooting section

---

**Note**: This system requires active internet connection for AI services and cloud storage features. Local fallbacks are available for offline usage.
