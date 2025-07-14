from typing import Dict, List, Optional
import json
import glob
from pathlib import Path
from loguru import logger
import re

class HTSDataLoader:
    def __init__(self, data_dir: str):
        """Initialize the HTS data loader."""
        self.data_dir = Path(data_dir)
        self.hts_data = []
        self.hts_code_map = {}
        
        # Initialize product mappings
        self.product_mappings = {
            # Leather goods (Chapter 42)
            ('wallet', 'leather'): ['4202.31', '4202.32'],  # Wallets and similar items
            ('handbag', 'leather'): ['4202.21', '4202.22'],  # Handbags
            ('briefcase', 'leather'): ['4202.11', '4202.12'],  # Briefcases
            ('suitcase', 'leather'): ['4202.11', '4202.12'],  # Suitcases
            
            # Aluminum building components (Chapter 76)
            ('window', 'aluminum'): ['7610.10'],  # Windows and frames
            ('door', 'aluminum'): ['7610.10'],    # Doors and frames
            ('frame', 'aluminum'): ['7610.10'],   # Frames
            
            # Apparel (Chapter 61)
            ('t-shirt', 'cotton'): ['6109.10'],   # Cotton t-shirts
            ('t-shirt', 'knit'): ['6109.90'],     # Other t-shirts
            ('sweater', 'cotton'): ['6110.20'],   # Cotton sweaters
            ('sweater', 'wool'): ['6110.11'],     # Wool sweaters
            
            # Electronics (Chapter 85)
            ('solar panel', ''): ['8541.43'],     # Solar panels
            ('coffee maker', ''): ['8516.71'],    # Coffee makers
            ('robot', 'industrial'): ['8428.70']  # Industrial robots
        }
        
        
        self.load_all_chapters()
        
    def load_all_chapters(self) -> List[Dict]:
        """Load all HTS chapter data from JSON files."""
        try:
            # Load all JSON files in sorted order
            for file_path in sorted(self.data_dir.glob("htsdata*.json")):
                with open(file_path, 'r', encoding='utf-8') as f:
                    chapter_data = json.load(f)
                    self.process_chapter_data(chapter_data)
            
            logger.info(f"Loaded {len(self.hts_data)} HTS entries")
            return self.hts_data
        except Exception as e:
            logger.error(f"Error loading HTS data: {str(e)}")
            raise

    def hts_code_backwalk(self, hts_code: str) -> Optional[str]:
        """Backwalk an HTS code to return a list of parent codes."""
        data_path = self.data_dir / "combined_data.json"
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                combined_data = json.load(f)
            
            # Find the item with the given HTS code
            target_item = None
            target_index = -1
            for i, item in enumerate(combined_data):
                if item.get('htsno') == hts_code:
                    target_item = item
                    target_index = i
                    break
            
            if not target_item:
                logger.warning(f"HTS code {hts_code} not found in combined data")
                return None
            
            # Get the indent level of the target HTS code
            target_indent = int(target_item.get('indent', 0))
            
            # Find hierarchical parents by walking backwards through the data
            parent_items = []
            current_indent = target_indent
            
            # Walk backwards from the target item to find parents
            for i in range(target_index - 1, -1, -1):
                item = combined_data[i]
                item_indent = int(item.get('indent', 0))
                
                # If we find an item with lower indent, it's a parent
                if item_indent < current_indent and item.get('htsno') and hts_code.startswith(item.get('htsno')):
                    parent_items.append(item)
                    current_indent = item_indent
                    
                    # Stop when we reach the top level (indent 0)
                    if item_indent < 0:
                        break
            
            # Reverse to get correct hierarchical order (highest level first)
            parent_items.reverse()
            
            # Build the result string with parent descriptions
            result = []
            for parent in parent_items:
                result.append(f"{parent.get('description', 'No description')}")
                
            result.append(f"{target_item.get('description', 'No description')}")  # Include the target item

            return " >> ".join(result) if result else None
        
        except Exception as e:
            logger.error(f"Error in hts_code_backwalk: {str(e)}")
            return None
    
            
    def process_chapter_data(self, chapter_data: List[Dict]):
        """Process and store HTS data from a chapter."""
        for item in chapter_data:
            # Skip entries that are just section headers or have no HTS code
            if not item.get('htsno') or item.get('superior'):
                continue
                
            # Clean and validate the HTS code
            hts_code = item['htsno'].strip()
            if not hts_code:
                continue

            # Store complete item in hts_data
            self.hts_data.append(item)
            
            # Create mapping for quick lookups with cleaned values
            self.hts_code_map[hts_code] = {
                'description': item['description'].strip(),
                'indent': str(item.get('indent', '0')),
                'general': item.get('general', '').strip(),
                'units': [u.strip() for u in item.get('units', []) if u.strip()],
                'special': item.get('special', '').strip(),
                'other': item.get('other', '').strip(),
                'footnotes': item.get('footnotes', [])
            }
    

    def get_hts_code_info(self, hts_code: str) -> Dict:
        """Get detailed information for a specific HTS code.
        
        Args:
            hts_code (str): The HTS code to look up
            
        Returns:
            Dict containing the HTS code information with cleaned values
        """
        info = self.hts_code_map.get(hts_code, {})
        # logger.debug(f"HTS Code: {hts_code}, Info: {info}")
        if info and not info.get('general'):
            info['general'] = 'N/A'
        return info
    
    def get_chapter_heading(self, hts_code: str) -> Optional[str]:
        """Get the chapter heading for an HTS code."""
        if len(hts_code) >= 4:
            chapter = hts_code[:2]
            heading = hts_code[:4]
            
            # Search for chapter/heading description
            for entry in self.hts_data:
                if entry.get('htsno') == chapter or entry.get('htsno') == heading:
                    return entry.get('description')
        
        return None
    
    def find_matching_codes(self, product_desc: str) -> List[str]:
        """Find matching HTS codes based on product description."""
        product_desc = product_desc.lower()
        matching_codes = set()
        
        # Check each product mapping against the description
        for (keyword, material), codes in self.product_mappings.items():
            if keyword in product_desc and (not material or material in product_desc):
                matching_codes.update(codes)
        
        return list(matching_codes)