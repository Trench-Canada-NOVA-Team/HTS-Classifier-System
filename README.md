# HTS Code Classification System and Tariff Calculator

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

## Tariff Calculator

The system includes a Tariff & Net Value Calculator (located in `TariffCalculator Research/experiment1.py`) that helps users calculate:
- Net value
- Associated tariff costs
- Other import-related fees

### Calculator Features

- Interactive Streamlit interface
- Real-time calculations
- Support for:
  - Invoice value calculations
  - Brokerage fees
  - Freight costs
  - Duty percentages
  - Merchandise Processing Fee (MPF)
  - Harbor Maintenance Fee (HMF)
  - Tariff percentages

### Formula Used

The calculator uses the following formula:

$$\begin{align}
  \Large \text{Net Value} = \Large \frac{\text{Invoice Value} - \text{Brokerage} - \text{Freight}}{1 + \frac{1}{100} \cdot (\text{Duty%} + \text{MPF%} + \text{HMF%} + \text{Tariff%})} \\
  \\
  \Large \text{Tariff Amount} = \Large \text{Tariff%} \times \text{Net Value}
\end{align}$$

Where:
- Duty and Tariff rates are given in percent (%)
- MPF is the Merchandise Processing Fee percentage (0.3464%)
- HMF is the Harbour Maintenance Fee percentage (0.125%)

```
Net Value = (Invoice Value - Brokerage - Freight) / (1 + Duty% + MPF% + HMF% + Tariff%)
Tariff Cost = Net Value × Tariff%
```

### Default Values
- MPF: 0.3464%
- HMF: 0.125%

### Usage Example

1. Enter the invoice value in USD
2. Input brokerage and freight costs
3. Specify duty and tariff percentages
4. Click "Calculate" to get:
   - Net Value
   - Tariff Cost

## License

MIT
