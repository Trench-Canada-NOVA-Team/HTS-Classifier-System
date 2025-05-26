from data_loader.json_loader import HTSDataLoader
import os
from pathlib import Path

def main():
    # Initialize the HTS Data Loader with the data directory
    data_dir = Path(__file__).parent.parent / "Data"
    loader = HTSDataLoader(str(data_dir))
    
    # Example 1: Looking up rates for a leather wallet from Canada (USMCA)
    print("Example 1: Leather wallet from Canada")
    hts_codes = loader.find_matching_codes("leather wallet")
    for hts_code in hts_codes:
        rate_info = loader.get_country_specific_rate(hts_code, "CA")
        print(f"\nHTS Code: {hts_code}")
        print(f"Description: {loader.get_hts_code_info(hts_code).get('description')}")
        print(f"Trade Agreement: {rate_info['trade_agreement']}")
        print(f"Rate: {rate_info['rate']}")
    
    # Example 2: Looking up rates for aluminum windows from Germany (EU)
    print("\nExample 2: Aluminum windows from Germany")
    hts_codes = loader.find_matching_codes("aluminum window")
    for hts_code in hts_codes:
        rate_info = loader.get_country_specific_rate(hts_code, "DE")
        print(f"\nHTS Code: {hts_code}")
        print(f"Description: {loader.get_hts_code_info(hts_code).get('description')}")
        print(f"Country: {rate_info['country_name']}")
        print(f"Trade Agreement: {rate_info['trade_agreement']}")
        print(f"Rate: {rate_info['rate']}")
    
    # Example 3: Looking up rates for cotton t-shirts from China (General Rate)
    print("\nExample 3: Cotton t-shirts from China")
    hts_codes = loader.find_matching_codes("cotton t-shirt")
    for hts_code in hts_codes:
        rate_info = loader.get_country_specific_rate(hts_code, "CN")
        print(f"\nHTS Code: {hts_code}")
        print(f"Description: {loader.get_hts_code_info(hts_code).get('description')}")
        print(f"Rate: {rate_info['rate']}")  # Will show general rate for non-preferential countries

if __name__ == "__main__":
    main()