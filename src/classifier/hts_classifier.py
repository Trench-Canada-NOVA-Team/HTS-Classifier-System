from typing import Dict, List, Tuple
import numpy as np
import pickle
import time
from loguru import logger
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from data_loader.json_loader import HTSDataLoader
from preprocessor.text_processor import TextPreprocessor
from feedback_handler import FeedbackHandler

class HTSClassifier:
    def __init__(self, data_loader: HTSDataLoader, preprocessor: TextPreprocessor):
        """Initialize the HTS classifier."""
        self.data_loader = data_loader
        self.preprocessor = preprocessor
        self.descriptions = []
        self.hts_codes = []
        self.cache_dir = Path(__file__).parent.parent.parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize feedback handler
        self.feedback_handler = FeedbackHandler()
        
        # Initialize OpenAI client
        load_dotenv()
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=openai_api_key)
        
        # Initialize Pinecone client
        pinecone_api_key = os.getenv('PINECONE_API_KEY')
        if not pinecone_api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index_name = "hts-codes"
        
    def _get_cache_path(self) -> Path:
        """Get the path for the embeddings cache file."""
        return self.cache_dir / "embeddings_cache.pkl"
        
    def _load_cached_embeddings(self) -> Tuple[np.ndarray, List[str], List[str]]:
        """Load embeddings from cache if available."""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    cache_data = pickle.load(f)
                logger.info("Loaded embeddings from cache")
                return cache_data['embeddings'], cache_data['descriptions'], cache_data['hts_codes']
            except Exception as e:
                logger.warning(f"Failed to load cache: {str(e)}")
        return None, None, None
        
    def _save_cached_embeddings(self, embeddings: np.ndarray, descriptions: List[str], hts_codes: List[str]):
        """Save embeddings to cache."""
        cache_path = self._get_cache_path()
        try:
            cache_data = {
                'embeddings': embeddings,
                'descriptions': descriptions,
                'hts_codes': hts_codes
            }
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.info("Saved embeddings to cache")
        except Exception as e:
            logger.warning(f"Failed to save cache: {str(e)}")
    
    def build_index(self):
        """Build the Pinecone index for similarity search."""
        try:
            # Try to load from cache first for local embeddings
            embeddings, cached_descriptions, cached_codes = self._load_cached_embeddings()
            
            if embeddings is None:
                # Cache miss - generate new embeddings
                logger.info("Cache miss - generating new embeddings")
                
                # Get all HTS data
                hts_data = self.data_loader.hts_data
                
                # Extract descriptions and codes
                valid_entries = [(item['description'], item['htsno']) 
                               for item in hts_data 
                               if item.get('description') and item.get('htsno')]
                
                if not valid_entries:
                    raise ValueError("No valid HTS entries found")
                    
                self.descriptions, self.hts_codes = zip(*valid_entries)
                
                # Preprocess and encode descriptions
                clean_descriptions = self.preprocessor.preprocess_descriptions(self.descriptions)
                embeddings = self.preprocessor.encode_text(clean_descriptions)
                
                # Save to cache
                self._save_cached_embeddings(embeddings, self.descriptions, self.hts_codes)
            else:
                # Cache hit - use cached data
                self.descriptions = cached_descriptions
                self.hts_codes = cached_codes
            
            # Create Pinecone index if it doesn't exist
            if self.index_name not in self.pc.list_indexes().names():
                logger.info("Creating new Pinecone index...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=embeddings.shape[1],
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
            
            # Get the index
            index = self.pc.Index(self.index_name)
            
            # Check if vectors already exist in Pinecone
            stats = index.describe_index_stats()
            if stats.total_vector_count == 0:
                logger.info("Uploading vectors to Pinecone...")
                # Create vector data with IDs and metadata
                vectors = []
                for i, (embedding, description, hts_code) in enumerate(zip(embeddings, self.descriptions, self.hts_codes)):
                    vectors.append({
                        'id': str(i),
                        'values': embedding.tolist(),
                        'metadata': {
                            'description': description,
                            'hts_code': hts_code
                        }
                    })
                
                # Upsert vectors in batches
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i + batch_size]
                    index.upsert(vectors=batch)
                logger.info("Successfully uploaded vectors to Pinecone")
            else:
                logger.info(f"Using existing Pinecone index with {stats.total_vector_count} vectors")
            
        except Exception as e:
            logger.error(f"Error building index: {str(e)}")
            raise

    def classify(self, product_description: str, top_k: int = 3, country_code: str = None) -> List[Dict]:
        """Classify a product description into HTS codes with country-specific rates."""
        try:
            # First check explicit product mappings
            matching_codes = self.data_loader.find_matching_codes(product_description)
            logger.debug(f"Matching codes found: {matching_codes}")
            results = []
            
            # if matching_codes:
            #     for code in matching_codes:
            #         # Find the most specific matching code in our data
            #         specific_codes = [hts for hts in self.hts_codes if hts.startswith(code)]
            #         if specific_codes:
            #             # Sort by length to get most specific match
            #             specific_code = sorted(specific_codes, key=len, reverse=True)[0]
                        
            #             hts_info = self.data_loader.get_hts_code_info(specific_code)
            #             hts_info['hts_code'] = specific_code

            #             # Get country-specific rate information
            #             rate_info = {}
            #             if country_code:
            #                 rate_info = self.data_loader.get_country_specific_rate(specific_code, country_code)
                        
            #             # Validate with GPT for confidence score
            #             confidence = self.validate_with_gpt(product_description, hts_info)
                        
            #             if confidence > 80:  # Higher threshold for mapped codes
            #                 result = {
            #                     'hts_code': specific_code,
            #                     'description': hts_info.get('description', ''),
            #                     'confidence': round(confidence, 2),
            #                     'general_rate': hts_info.get('general', 'N/A'),
            #                     'units': hts_info.get('units', []),
            #                     'chapter_context': self.get_chapter_context(specific_code)
            #                 }
                            
            #                 # Add country-specific rate information if available
            #                 if rate_info:
            #                     result.update({
            #                         'country_specific_rate': rate_info.get('rate'),
            #                         'trade_agreement': rate_info.get('trade_agreement'),
            #                         'country_name': rate_info.get('country_name')
            #                     })
                            
            #                 results.append(result)
            
            if results:
                # Sort by confidence and return top matches
                results.sort(key=lambda x: x['confidence'], reverse=True)
                return results[:top_k]
            
            # If no mapping matches or not enough results, use similarity search
            clean_query = self.preprocessor.clean_text(product_description)
            query_embedding = self.preprocessor.encode_text([clean_query])
            
            # Get Pinecone index
            index = self.pc.Index(self.index_name)
            
            # Search index with more candidates
            k_multiplier = 5
            search_results = index.query(
                vector=query_embedding[0].tolist(),
                top_k=top_k * k_multiplier,
                include_metadata=True
            )
            
            # Prepare results with GPT validation
            seen_chapters = set()
            
            # Dynamic threshold based on product type
            clean_query_lower = clean_query.lower()
            base_threshold = 20
            category_42_threshold = 10
            apparel_threshold = 15
            aluminum_threshold = 15
            
            for match in search_results.matches:
                hts_code = match.metadata['hts_code']
                chapter = hts_code[:2] if len(hts_code) >= 2 else ""

                full_description = self.data_loader.hts_code_backwalk(hts_code)

                if chapter in seen_chapters and len(results) >= top_k:
                    continue
                
                # Determine confidence threshold
                threshold = base_threshold
                if "leather" in clean_query_lower and chapter == "42":
                    threshold = category_42_threshold
                elif any(word in clean_query_lower for word in ["t-shirt", "shirt", "sweater"]) and chapter in ["61", "62"]:
                    threshold = apparel_threshold
                elif "window" in clean_query_lower and "aluminum" in clean_query_lower and chapter == "76":
                    threshold = aluminum_threshold
                
                hts_info = self.data_loader.get_hts_code_info(hts_code)
                hts_info['hts_code'] = hts_code
                
                # Get country-specific rate information
                rate_info = {}
                if country_code:
                    rate_info = self.data_loader.get_country_specific_rate(hts_code, country_code)
                
                confidence = self.validate_with_gpt(full_description, hts_info)
                
                if confidence > threshold:
                    result = {
                        'hts_code': hts_code,
                        'description': full_description if full_description else hts_info.get('description', ''),
                        'confidence': round(confidence, 2),
                        'general_rate': hts_info.get('general', 'N/A'),
                        'units': hts_info.get('units', []),
                        'chapter_context': self.get_chapter_context(hts_code)
                    }
                    
                    # Add country-specific rate information if available
                    if rate_info:
                        result.update({
                            'country_specific_rate': rate_info.get('rate'),
                            'trade_agreement': rate_info.get('trade_agreement'),
                            'country_name': rate_info.get('country_name')
                        })
                    
                    results.append(result)
                    seen_chapters.add(chapter)
            
            # Sort by confidence and return top_k
            results.sort(key=lambda x: x['confidence'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in classification: {str(e)}")
            raise

    def get_chapter_context(self, hts_code: str) -> str:
        """Get the context of the HTS chapter and subchapter for better classification."""
        if len(hts_code) >= 4:
            chapter = hts_code[:2]
            subchapter = hts_code[:4]
            
            chapter_contexts = {
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
            
            subchapter_contexts = {
                # Leather goods and accessories
                "4202": "Trunks, suitcases, handbags, wallets, similar containers",
                "4203": "Articles of apparel and accessories of leather",
                "4205": "Other articles of leather or composition leather",
                # Apparel and textiles
                "6109": "T-shirts, singlets, tank tops, knitted or crocheted",
                "6110": "Sweaters, pullovers, sweatshirts, knitted or crocheted",
                "6205": "Men's or boys' shirts, not knitted or crocheted",
                # Metals and structures
                "7318": "Screws, bolts, nuts, washers of iron or steel",
                "7324": "Sanitary ware and parts of iron or steel",
                "7610": "Aluminum structures and parts (doors, windows, frames)",
                # Electronics and machinery
                "8516": "Electric heating equipment and appliances",
                "8541": "Semiconductor devices, LEDs, solar cells",
                "8428": "Lifting, handling, loading machinery; industrial robots"
            }
            
            context = chapter_contexts.get(chapter, "")
            subcontext = subchapter_contexts.get(subchapter, "")
            
            if context and subcontext:
                return f"{context} - {subcontext}"
            return context or subcontext
        
        return ""

    def validate_with_gpt(self, product_description: str, hts_info: Dict, max_retries: int = 3) -> float:
        """Use GPT to validate the match and calculate confidence score with retry logic."""
        retry_count = 0
        base_delay = 1  # Base delay in seconds

        while retry_count < max_retries:
            try:
                # Prepare the rate information
                general_rate = hts_info.get('general_rate', 'N/A')
                if not general_rate:
                    general_rate = 'N/A'

                # Get chapter context for better validation
                chapter_context = self.get_chapter_context(hts_info['hts_code'])
                context_info = f"\nProduct Category: {chapter_context}" if chapter_context else ""

                # Enhanced prompt with specific category guidance
                prompt = f"""As an expert in US Harmonized Tariff Schedule (HTS) classification, analyze the following product-code match.

                            Product Description: {product_description}{context_info}

                            Candidate HTS Classification:
                            - Code: {hts_info['hts_code']}
                            - Official Description: {hts_info['description']}
                            - Duty Rate: {general_rate}
                            - Units of Measurement: {', '.join(hts_info.get('units', [])) if hts_info.get('units') else 'N/A'}

                            Important Category Guidelines:
                            1. Leather wallets, handbags, and similar containers belong in Chapter 42 (4202)
                            2. Aluminum doors, windows, and frames belong in heading 7610
                            3. T-shirts and similar garments belong in heading 6109
                            4. Industrial robots belong in heading 8428 or 8479

                            Evaluate the match considering:
                            1. Product Specificity: How precisely does the HTS description match the product details?
                            2. Category Alignment: Is this the correct category chapter/heading for this type of product?
                            3. Material & Characteristics: Do any specified materials or characteristics align?
                            4. Usage/Purpose: Does the intended use match the HTS category purpose?

                            Return only a number between 0 and 100 representing your confidence in this classification match.
                            Example confidence scores:
                            - 95-100: Perfect match with exact terminology
                            - 80-94: Very good match with minor variations
                            - 60-79: Good match but some details differ
                            - 40-59: Partial match with significant differences
                            - 0-39: Poor match or wrong category
                            """

                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert US HTS classification system. Analyze product descriptions and HTS codes, then return only a confidence score between 0-100."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=10
                )
                
                confidence = float(response.choices[0].message.content.strip())
                
                # Apply category-specific confidence adjustments
                code = hts_info['hts_code']
                desc_lower = product_description.lower()
                
                if 'wallet' in desc_lower and 'leather' in desc_lower:
                    if code.startswith('4202'):  # Proper heading for wallets
                        confidence = max(confidence, 90)  # Boost confidence for correct heading
                    elif not code.startswith('42'):  # Wrong chapter
                        confidence = min(confidence, 30)  # Reduce confidence
                        
                elif 'window frame' in desc_lower and 'aluminum' in desc_lower:
                    if code.startswith('7610'):  # Proper heading for aluminum structures
                        confidence = max(confidence, 90)
                    elif not code.startswith('76'):  # Wrong chapter
                        confidence = min(confidence, 30)
                
                return min(max(confidence, 0), 100)  # Ensure score is between 0 and 100
                
            except RateLimitError as e:
                retry_count += 1
                if retry_count < max_retries:
                    delay = base_delay * (2 ** retry_count)  # Exponential backoff
                    logger.warning(f"Rate limit hit, retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("Max retries reached for rate limit")
                    return 50.0
                    
            except APIError as e:
                logger.error(f"OpenAI API error: {str(e)}")
                return 50.0
                
            except Exception as e:
                logger.error(f"Error validating with GPT: {str(e)}")
                return 50.0

    def add_feedback(self, product_description: str, predicted_code: str, correct_code: str):
        """Add feedback for a classification prediction."""
        try:
            self.feedback_handler.add_feedback(
                description=product_description,
                predicted_code=predicted_code,
                correct_code=correct_code
            )
            logger.info(f"Feedback recorded: {predicted_code} -> {correct_code}")
        except Exception as e:
            logger.error(f"Error recording feedback: {str(e)}")

    def get_feedback_stats(self):
        """Get statistics about classification feedback."""
        return self.feedback_handler.get_feedback_stats()
    
    def format_hs_code(self, hts_code: str) -> str:
        """Format HTS code to standard 10-digit format."""
        return self.feedback_handler.format_hs_code(hts_code)