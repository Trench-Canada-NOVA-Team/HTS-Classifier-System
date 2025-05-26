import re
from typing import List
import numpy as np
from loguru import logger
from openai import OpenAI
import os
from dotenv import load_dotenv

class TextPreprocessor:
    def __init__(self):
        """Initialize the text preprocessor with OpenAI."""
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Common HTS-specific replacements
        self.material_replacements = {
            r'stainless\s+steel': 'ss',
            r'carbon\s+steel': 'cs',
            r'aluminum': 'al',
            r'aluminium': 'al',
            r'polyethylene': 'pe',
            r'polypropylene': 'pp',
            r'polyvinyl\s+chloride': 'pvc',
            r'poly\s*vinyl\s*chloride': 'pvc'
        }
        
        self.accessory_keywords = {
            'wallet': 'article of leather wallet coin purse billfold',
            'handbag': 'article of leather handbag purse shoulder bag',
            'briefcase': 'article of leather briefcase attache case',
            'belt': 'article of leather belt waist strap',
            'glove': 'article of leather glove mitten',
            'watch strap': 'article of leather watch band strap'
        }
        
        self.material_keywords = {
            'leather': 'leather cowhide bovine animal hide genuine leather',
            'cotton': 'cotton textile fabric woven knit',
            'steel': 'steel iron metal ferrous alloy',
            'aluminum': 'aluminum aluminium metal alloy',
            'plastic': 'plastic polymer synthetic resin',
            'wood': 'wood timber hardwood softwood'
        }
        
        self.measurement_replacements = {
            r'kilogram[s]?\b': 'kg',
            r'gram[s]?\b': 'g',
            r'milligram[s]?\b': 'mg',
            r'meter[s]?\b': 'm',
            r'metre[s]?\b': 'm',
            r'cent[i]?meter[s]?\b': 'cm',
            r'mill[i]?meter[s]?\b': 'mm',
            r'lit[re|er][s]?\b': 'l',
            r'inch[es]?\b': 'in',
            r'foot|feet\b': 'ft',
            r'pound[s]?\b': 'lb',
            r'ounce[s]?\b': 'oz',
            r'gallon[s]?\b': 'gal',
            r'cubic\s+cent[i]?meters?\b': 'cc',
            r'square\s+meters?\b': 'm2',
            r'cubic\s+meters?\b': 'm3'
        }
        
        self.state_replacements = {
            r'new\b': 'n',
            r'used\b': 'u',
            r'refurbished\b': 'ref',
            r'remanufactured\b': 'reman'
        }
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize product description text."""
        # Convert to lowercase
        text = text.lower()
        
        # Product category mappings for better matching
        category_keywords = {
            # Leather goods (Chapter 42)
            'wallet': 'leather articles wallet billfold purse small leather goods 4202',
            'handbag': 'leather articles handbag purse shoulder bag tote 4202',
            'briefcase': 'leather articles briefcase attache business case 4202',
            'suitcase': 'leather articles suitcase luggage travel goods 4202',
            
            # Apparel (Chapters 61-62)
            't-shirt': 'knitted cotton t-shirt tshirt singlet tank top 6109',
            'shirt': 'cotton shirt apparel garment 61',
            'sweater': 'knitted sweater pullover jersey 6110',
            'jacket': 'apparel jacket coat outerwear 61',
            
            # Metal products (Chapters 73, 76)
            'window frame': 'aluminum window frame door frame building component 7610',
            'door frame': 'aluminum door frame window frame building component 7610',
            'sink': 'stainless steel sink basin wash basin sanitary ware 7324',
            'screw': 'metal screw bolt fastener iron steel 7318',
            
            # Electronics (Chapter 85)
            'solar panel': 'photovoltaic solar panel module cell 8541',
            'coffee maker': 'electric coffee maker appliance heating 8516',
            'appliance': 'electric appliance household 85'
        }
        
        # Expand product category keywords
        for key, expanded in category_keywords.items():
            if key in text:
                text = f"{text} {expanded}"
        
        # Expand accessory keywords
        for key, expanded in self.accessory_keywords.items():
            if key in text:
                text = f"{text} {expanded}"
                
        # Expand material keywords
        for key, expanded in self.material_keywords.items():
            if key in text:
                text = f"{text} {expanded}"
        
        # Replace material terms
        for pattern, replacement in self.material_replacements.items():
            text = re.sub(pattern, replacement, text)
            
        # Replace measurement terms
        for pattern, replacement in self.measurement_replacements.items():
            text = re.sub(pattern, replacement, text)
            
        # Replace state/condition terms
        for pattern, replacement in self.state_replacements.items():
            text = re.sub(pattern, replacement, text)
        
        # Handle special product formats
        text = re.sub(r'(\d+)\s*k\s*gold', r'\1k-gold', text)     # Gold karat
        text = re.sub(r'(\d+)\s*v\b', r'\1v', text)               # Voltage
        text = re.sub(r'(\d+)\s*w\b', r'\1w', text)               # Wattage
        text = re.sub(r'(\d+)\s*hz\b', r'\1hz', text)             # Frequency
        text = re.sub(r'(\d+)\s*mm?\b', r'\1mm', text)            # Millimeters
        text = re.sub(r'(\d+)\s*cm?\b', r'\1cm', text)            # Centimeters
        text = re.sub(r'(\d+)\s*x\s*(\d+)', r'\1x\2', text)       # Dimensions
        
        # Standardize percentages
        text = re.sub(r'(\d+)\s*percent\b', r'\1%', text)
        text = re.sub(r'(\d+)\s*pct\b', r'\1%', text)
        
        # Remove special characters but keep hyphens, numbers, %, and basic units
        text = re.sub(r'[^a-z0-9\s\-%\/]', ' ', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def encode_text(self, texts: List[str]) -> np.ndarray:
        """Encode text descriptions using OpenAI embeddings."""
        try:
            embeddings = []
            batch_size = 100  # Process in batches to avoid rate limits
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch,
                    encoding_format="float"
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Error encoding text with OpenAI: {str(e)}")
            raise
            
    def preprocess_descriptions(self, descriptions: List[str]) -> List[str]:
        """Preprocess a list of product descriptions."""
        return [self.clean_text(desc) for desc in descriptions]