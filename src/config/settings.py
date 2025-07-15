"""
Centralized configuration settings for the HTS Classification System.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Main configuration class containing all system settings."""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "Data"
    LOGS_DIR = BASE_DIR / "logs"
    CACHE_DIR = BASE_DIR / "cache"
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
    OPENAI_CHAT_MODEL = "gpt-4"
    
    # Pinecone Configuration
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    PINECONE_INDEX_NAME = "hts-codes"
    PINECONE_CLOUD = "aws"
    PINECONE_REGION = "us-east-1"
    
    # AWS S3 Configuration
    AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-west-1')
    S3_FEEDBACK_KEY = 'feedback/feedback_data.csv'
    
    # Classification Settings
    SEMANTIC_THRESHOLD = 0.50
    HIGH_CONFIDENCE_THRESHOLD = 0.70
    VERY_HIGH_CONFIDENCE_THRESHOLD = 0.80
    BASE_CONFIDENCE_THRESHOLD = 20
    CATEGORY_42_THRESHOLD = 10
    APPAREL_THRESHOLD = 15
    ALUMINUM_THRESHOLD = 15
    
    # Feedback Settings
    FEEDBACK_CACHE_DURATION = 5  # minutes
    DEFAULT_FEEDBACK_DAYS = 30
    
    # FAISS Configuration
    FAISS_INDEX_NAME = "feedback_faiss_langchain"
    FAISS_METADATA_NAME = "feedback_metadata_langchain.pkl"
    FAISS_SIMILARITY_THRESHOLD = 0.5
    FAISS_TOP_K_DEFAULT = 5
    
    # System Settings
    BATCH_SIZE = 100
    MAX_RETRIES = 3
    BASE_DELAY = 1  # seconds
    LOG_ROTATION = "500 MB"
    
    # Dashboard Settings
    DASHBOARD_RECENT_ENTRIES_COUNT = 10
    DASHBOARD_TOP_CORRECTIONS_COUNT = 5
    PERFORMANCE_CACHE_DURATION = 300  # 5 minutes in seconds

class HTSMappings:
    """HTS-specific mappings and constants."""
    
    # Material replacements for text preprocessing
    MATERIAL_REPLACEMENTS = {
        r'stainless\s+steel': 'ss',
        r'carbon\s+steel': 'cs',
        r'aluminum': 'al',
        r'aluminium': 'al',
        r'polyethylene': 'pe',
        r'polypropylene': 'pp',
        r'polyvinyl\s+chloride': 'pvc',
        r'poly\s*vinyl\s*chloride': 'pvc'
    }
    
    # Product category mappings
    PRODUCT_MAPPINGS = {
        # Resale Products
        ('reactor', None): ['8504.50.80.00'],
        ('coil inductor', None): ['8504.50.80.00'],
        ('transformer', None): ['8504.21.00'],
        ('bushings', None): ['8535.90.80'],
        
        # Aluminum building components (Chapter 76)
        ('window', 'aluminum'): ['7610.10'],  # Windows and frames
        ('door', 'aluminum'): ['7610.10'],    # Doors and frames
        ('frame', 'aluminum'): ['7610.10'],   # Frames

        # =================== FOR TESTING =========================
        # Leather goods (Chapter 42)
        ('wallet', 'leather'): ['4202.31', '4202.32'],  # Wallets and similar items
        ('handbag', 'leather'): ['4202.21', '4202.22'],  # Handbags
        ('briefcase', 'leather'): ['4202.11', '4202.12'],  # Briefcases
        ('suitcase', 'leather'): ['4202.11', '4202.12'],  # Suitcases
        
        # Apparel (Chapter 61)
        ('t-shirt', 'cotton'): ['6109.10'],   # Cotton t-shirts
        ('t-shirt', 'knit'): ['6109.90'],     # Other t-shirts
        ('sweater', 'cotton'): ['6110.20'],   # Cotton sweaters
        ('sweater', 'wool'): ['6110.11'],     # Wool sweaters
        
        # Electronics (Chapter 85)
        ('solar panel', ''): ['8541.43'],     # Solar panels
        ('coffee maker', ''): ['8516.71'],    # Coffee makers
        ('robot', 'industrial'): ['8428.70']  # Industrial robots
        # ==========================================================
        }
    # Chapter contexts for classification
    CHAPTER_CONTEXTS = {
        "01": "Live animals",
        "02": "Meat and edible meat offal",
        "03": "Fish and crustaceans",
        "04": "Dairy, eggs, honey, and other edible animal products",
        "41": "Raw hides, skins and leather",
        "42": "Articles of leather; handbags, wallets, cases, similar containers",
        "43": "Furskins and artificial fur",
        "61": "Articles of apparel and clothing accessories, knitted or crocheted",
        "62": "Articles of apparel and clothing accessories, not knitted or crocheted",
        "63": "Other made up textile articles",
        "71": "Natural or cultured pearls, precious stones, precious metals",
        "72": "Iron and steel",
        "73": "Articles of iron or steel",
        "74": "Copper and articles thereof",
        "76": "Aluminum and articles thereof",
        "84": "Machinery and mechanical appliances",
        "85": "Electrical machinery and equipment"
    }
    
    # Subchapter contexts
    SUBCHAPTER_CONTEXTS = {
        "4202": "Trunks, suitcases, handbags, wallets, similar containers",
        "4203": "Articles of apparel and accessories of leather",
        "4205": "Other articles of leather or composition leather",
        "6109": "T-shirts, singlets, tank tops, knitted or crocheted",
        "6110": "Sweaters, pullovers, sweatshirts, knitted or crocheted",
        "6205": "Men's or boys' shirts, not knitted or crocheted",
        "7318": "Screws, bolts, nuts, washers of iron or steel",
        "7324": "Sanitary ware and parts of iron or steel",
        "7610": "Aluminum structures and parts (doors, windows, frames)",
        "8516": "Electric heating equipment and appliances",
        "8541": "Semiconductor devices, LEDs, solar cells",
        "8428": "Lifting, handling, loading machinery; industrial robots"
    }
