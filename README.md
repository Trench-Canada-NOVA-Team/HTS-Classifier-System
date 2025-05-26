# HTS Code Classification System

An AI-powered system for classifying products into US Harmonized Tariff Schedule (HTS) codes using natural language processing and machine learning.

## Features

- Natural language product description input
- Semantic similarity-based classification
- Confidence scoring for predictions
- Interactive web interface using Streamlit
- HTS code hierarchy visualization
- Example classifications
- Detailed result explanations

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the Streamlit web interface:

```bash
cd src
streamlit run app.py
```

The application will be available at http://localhost:8501

## Project Structure

```
hts-classifier/
├── src/
│   ├── data_loader/      # HTS data loading and processing
│   ├── preprocessor/     # Text preprocessing
│   ├── classifier/       # Classification logic
│   └── app.py           # Streamlit web interface
├── Data/                 # HTS JSON data files
└── logs/                 # Application logs
```

## System Components

### Data Loader

- Loads HTS data from JSON files
- Creates efficient lookup structures
- Handles hierarchical HTS code relationships

### Text Preprocessor

- Cleans and normalizes product descriptions
- Converts text to embeddings using BERT
- Optimizes text for similarity matching

### HTS Classifier

- Uses semantic similarity for classification
- Calculates confidence scores
- Returns top matches with metadata

### Web Interface

- User-friendly Streamlit application
- Interactive example showcase
- Detailed result visualization
- HTS code hierarchy breakdown

## Tips for Better Results

- Provide detailed product descriptions
- Include material composition when relevant
- Specify product usage or purpose
- Mention specific characteristics (size, weight, etc.)
- Include industry-specific terminology

## License

MIT
