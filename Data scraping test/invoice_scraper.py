import os
import re
from pathlib import Path
import pandas as pd
from typing import List, Dict

def extract_invoice_costs(text: str) -> List[Dict]:
    """
    Extract invoice cost data with BULLETPROOF EV extraction
    """
    
    print("DEBUG: Starting invoice cost extraction...")
    print(f"DEBUG: Text length: {len(text)} characters")
    
    # BULLETPROOF EV EXTRACTION - Check the very last line first
    lines = text.strip().split('\n')
    last_line_ev = None
    
    print(f"DEBUG: Last line of text: '{lines[-1] if lines else 'NO LINES'}'")
    
    # Check last line for EV pattern
    if lines:
        last_line = lines[-1].strip()
        ev_match = re.search(r'=EV\s+(.+)', last_line)
        if ev_match:
            last_line_ev = ev_match.group(1).strip()
            print(f"DEBUG: BULLETPROOF - Found EV on last line: '{last_line_ev}'")
        else:
            print(f"DEBUG: BULLETPROOF - No EV found on last line")
    results = []

    # Try primary pattern matching first
    print("DEBUG: Trying primary pattern...")
    results = extract_entry_data_primary(text)
    if results:
        print(f"DEBUG: Primary pattern found {len(results)} results")
    else:
        print("DEBUG: Primary pattern failed, trying alternative pattern...")
        results = alternative_pattern_search(text)
        if results:
            print(f"DEBUG: Alternative pattern found {len(results)} results")
        else:
            print("DEBUG: Alternative pattern failed, trying partial matches...")
            results = extract_partial_matches(text)
            print(f"DEBUG: Partial matches found {len(results)} results")
    
    # BULLETPROOF: Force add the EV to ALL results if we found it
    if last_line_ev and results:
        for result in results:
            if 'ev' not in result or not result['ev']:
                result['ev'] = last_line_ev
                print(f"DEBUG: BULLETPROOF - Force added EV '{last_line_ev}' to result")
    
    # BULLETPROOF: If no results but we have invoice data, create a minimal entry
    if not results and last_line_ev:
        # Look for any 001IV line
        for line in lines:
            invoice_match = re.search(r'\d{3}IV\s+(.+)', line.strip())
            if invoice_match:
                invoice_price = invoice_match.group(1).strip()
                results = [{
                    'invoice_price': invoice_price,
                    'ev': last_line_ev,
                    'frt_intl': None,
                    'brokerage': None
                }]
                print(f"DEBUG: BULLETPROOF - Created minimal entry with IV: '{invoice_price}' and EV: '{last_line_ev}'")
                break
    
    print(f"DEBUG: Final results count: {len(results)}")
    for i, result in enumerate(results):
        print(f"DEBUG: Final result {i}: {result}")
        
    return results

def extract_entry_data_primary(text: str) -> List[Dict]:
    """
    Extract entry data matching the COMPLETE pattern - without oth and dty columns
    """
    
    # Define the regex pattern - extract only the values after each identifier
    pattern = r'''
        \d{3}IV\s+(.+?)(?:\n|$)                 # Extract value after 001IV (not the 001IV itself)
        .*?-FRT,?\s*INTL\s+(.+?)(?:\n|$)        # -FRT, INTL XXXXX (any text)
        .*?-BROKERAGE\s+(.+?)(?:\n|$)           # -BROKERAGE XXXXX (any text)
        .*?=EV\s+(.+?)(?:\n|$)                  # =EV XXXXX (any text)
    '''
    
    # Compile regex with VERBOSE and DOTALL flags
    regex = re.compile(pattern, re.VERBOSE | re.DOTALL | re.IGNORECASE)
    
    # Find all matches
    matches = regex.findall(text)
    
    results = []
    for match in matches:
        try:
            results.append({
                'invoice_price': match[0].strip(),     # The value after 001IV
                'frt_intl': match[1].strip(),
                'brokerage': match[2].strip(),
                'ev': match[3].strip()
            })
        except IndexError as e:
            print(f"Error parsing match {match}: {e}")
            continue
    
    return results

def alternative_pattern_search(text: str) -> List[Dict]:
    """
    Line-wise pattern matching - ALWAYS check last line for EV
    """
    
    # Split text into lines for easier processing
    lines = text.split('\n')
    
    results = []
    current_entry = {}
    
    # HARD-CODED: Check the very last line for EV first
    last_line_ev = None
    for line in reversed(lines):  # Check from the end
        line = line.strip()
        if line:  # First non-empty line from the end
            ev_match = re.search(r'=EV\s+(.+)', line)
            if ev_match:
                last_line_ev = ev_match.group(1).strip()
                print(f"DEBUG: Found EV on last line: '{last_line_ev}'")
                break
            else:
                break  # Stop at first non-empty line that doesn't match EV
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Look for invoice price - extract only the value after 001IV
        invoice_match = re.search(r'\d{3}IV\s+(.+)', line)
        if invoice_match:
            # If we have a previous entry with invoice data, save it
            if current_entry and 'invoice_price' in current_entry:
                # HARD-CODED: Always add the last line EV if we found one
                if last_line_ev and 'ev' not in current_entry:
                    current_entry['ev'] = last_line_ev
                results.append(current_entry.copy())
            
            # Start new entry - only store the value, not the ID
            current_entry = {
                'invoice_price': invoice_match.group(1).strip()
            }
            continue
        
        # Look for FRT, INTL - capture everything after it
        frt_match = re.search(r'-FRT,?\s*INTL\s+(.+)', line)
        if frt_match and 'invoice_price' in current_entry:
            current_entry['frt_intl'] = frt_match.group(1).strip()
            continue
        
        # Look for BROKERAGE - capture everything after it
        brokerage_match = re.search(r'-BROKERAGE\s+(.+)', line)
        if brokerage_match and 'invoice_price' in current_entry:
            current_entry['brokerage'] = brokerage_match.group(1).strip()
            continue
        
        # Look for EV - capture everything after it
        ev_match = re.search(r'=EV\s+(.+)', line)
        if ev_match and 'invoice_price' in current_entry:
            current_entry['ev'] = ev_match.group(1).strip()
            continue
    
    # Don't forget the last entry - HARD-CODED: Always add last line EV
    if current_entry and 'invoice_price' in current_entry:
        if last_line_ev and 'ev' not in current_entry:
            current_entry['ev'] = last_line_ev
            print(f"DEBUG: Added last line EV to final entry: '{last_line_ev}'")
        results.append(current_entry)
    
    return results

def extract_partial_matches(text: str) -> List[Dict]:
    """
    Extract even partial matches - HARD-CODED EV from last line
    """
    
    lines = text.split('\n')
    
    # HARD-CODED: Get EV from the very last non-empty line
    last_line_ev = None
    for line in reversed(lines):
        line = line.strip()
        if line:  # First non-empty line from the end
            ev_match = re.search(r'=EV\s+(.+)', line)
            if ev_match:
                last_line_ev = ev_match.group(1).strip()
                print(f"DEBUG: Partial matches - Found EV on last line: '{last_line_ev}'")
                break
            else:
                break
    
    results = []
    current_entry = {}
    
    for line in lines:
        line = line.strip()
        
        # Look for invoice price - extract only the value
        invoice_match = re.search(r'\d{3}IV\s+(.+)', line)
        if invoice_match:
            # Save previous entry if it has at least 1 field
            if current_entry and len(current_entry) >= 1:
                # HARD-CODED: Always add last line EV if found
                if last_line_ev and 'ev' not in current_entry:
                    current_entry['ev'] = last_line_ev
                results.append(current_entry.copy())
            
            # Start new entry - only the value
            current_entry = {
                'invoice_price': invoice_match.group(1).strip()
            }
            continue
        
        # Check for pattern lines
        patterns = [
            (r'-FRT,?\s*INTL\s+(.+)', 'frt_intl'),
            (r'-BROKERAGE\s+(.+)', 'brokerage'),
            (r'=EV\s+(.+)', 'ev')
        ]
        
        for pattern, field_name in patterns:
            match = re.search(pattern, line)
            if match and 'invoice_price' in current_entry:
                current_entry[field_name] = match.group(1).strip()
                if field_name == 'ev':
                    print(f"DEBUG: Found EV during pattern matching: {current_entry[field_name]}")
                break
    
    # Save the last entry - HARD-CODED: Always add last line EV
    if current_entry and len(current_entry) >= 1:
        if last_line_ev and 'ev' not in current_entry:
            current_entry['ev'] = last_line_ev
            print(f"DEBUG: Added last line EV to final partial entry: '{last_line_ev}'")
        results.append(current_entry)
    
    return results

def extract_hs_codes_and_duties(text: str) -> List[Dict]:
    """
    Extract HS codes and duty information from lines like:
    8504.21.0020 XXXX KG XXX NO XXXX FREE FREE
    8504.33.0040 XXXX KG XXX NO XXXX 1.60 % 7,183.30
    
    Returns list of dictionaries with hs_code, general_duty (no special_duty)
    """
    
    lines = text.split('\n')
    hs_data = []
    
    for line in lines:
        line = line.strip()
        
        # Look for HS code pattern first
        if not re.match(r'^\S*\d{4}\.\d{2}\.\d{4}', line):
            continue
            
        # Split the line into parts
        parts = line.split()
        
        if len(parts) < 3:  # Need at least HS code and duty value
            continue
            
        # Extract HS code (first part, removing any prefix like 'S')
        hs_code_match = re.search(r'(\d{4}\.\d{2}\.\d{4})', parts[0])
        if not hs_code_match:
            continue
            
        hs_code = hs_code_match.group(1)
        
        # Find quantity and unit (look for number followed by unit)
        quantity = ""
        unit = ""
        
        for i in range(1, len(parts)-2):  # Skip HS code and last duty field
            if re.match(r'^\d+(\.\d+)?$', parts[i].replace(',', '')):  # Found a number
                quantity = parts[i].replace(',', '')
                if i+1 < len(parts)-2:  # Check if next part could be unit
                    next_part = parts[i+1]
                    if next_part in ['KG', 'NO', 'LB', 'MT', 'PCS', 'EA']:  # Common units
                        unit = next_part
                break
        
        # Extract duty - handle both "FREE" and "XX.XX %" formats
        # Look for the duty value (general duty only)
        if len(parts) >= 2:
            # Check if we have percentage format (number followed by %)
            if len(parts) >= 3 and parts[-2] == '%':
                # Format: ... 1.60 % 7,183.30
                general_duty = parts[-3] + " " + parts[-2]  # "1.60 %"
            elif len(parts) >= 2 and parts[-1] == 'FREE':
                # Format: ... FREE FREE or ... FREE
                general_duty = "FREE"
            else:
                # Try to find percentage pattern anywhere in the line
                found_percentage = False
                for i in range(len(parts)-1):
                    if parts[i+1] == '%' and re.match(r'^\d+(\.\d+)?$', parts[i]):
                        general_duty = parts[i] + " %"
                        found_percentage = True
                        break
                
                if not found_percentage:
                    # Default to second-to-last part
                    general_duty = parts[-2] if len(parts) >= 2 else ""
        else:
            general_duty = ""
        
        hs_data.append({
            'hs_code': hs_code,
            'quantity': quantity,
            'unit': unit,
            'general_duty': general_duty,
            'full_line': line
        })
    
    return hs_data

def process_invoice_section_file(file_path: str) -> tuple[List[Dict], List[Dict]]:
    """
    Process a single invoice section text file and extract both invoice costs and HS code data
    Returns: (invoice_costs, hs_codes)
    """
    
    print(f"Processing: {file_path}")
    
    try:
        # Read the invoice section text file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip the header lines and get the actual invoice section
        lines = content.split('\n')
        invoice_section = ""

        # Find the line that starts with "=" and take everything after it
        header_end_found = False
        for i, line in enumerate(lines):
            if "=" in line and len(line.strip()) > 10:  # Header separator line
                header_end_found = True
                continue
            if header_end_found:
                invoice_section += line + "\n"

        # If no header separator found, use the whole content
        if not header_end_found:
            invoice_section = content
        
        if not invoice_section.strip():
            print(f"No invoice section content found in {file_path}")
            return [], []
        
        # Extract invoice costs
        invoice_costs = extract_invoice_costs(invoice_section)
        
        # Extract HS codes and duties
        hs_codes = extract_hs_codes_and_duties(invoice_section)
        
        # Add source file to results
        source_file = Path(file_path).stem.replace('_invoice_section', '')
        
        for cost in invoice_costs:
            cost['source_file'] = source_file
        
        for hs in hs_codes:
            hs['source_file'] = source_file
        
        print(f"Extracted {len(invoice_costs)} invoice entries and {len(hs_codes)} HS codes from {source_file}")
        
        return invoice_costs, hs_codes
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return [], []


def scrape_invoice_sections_folder(folder_path: str = "invoice_sections") -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process all invoice section text files in the folder and return DataFrames for costs and HS codes
    Returns: (costs_df, hs_codes_df)
    """
    
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        raise FileNotFoundError(f"Invoice sections folder not found: {folder_path}")
    
    # Find all text files in the invoice_sections folder
    txt_files = list(folder_path.glob("*_invoice_section.txt"))
    
    if not txt_files:
        print(f"No invoice section text files found in {folder_path}")
        return pd.DataFrame(), pd.DataFrame()
    
    print(f"Found {len(txt_files)} invoice section files to process")
    
    all_costs = []
    all_hs_codes = []
    
    for txt_file in txt_files:
        try:
            costs, hs_codes = process_invoice_section_file(str(txt_file))
            all_costs.extend(costs)
            all_hs_codes.extend(hs_codes)
        except Exception as e:
            print(f"Error processing {txt_file}: {e}")
    
    # Convert to DataFrames
    costs_df = pd.DataFrame(all_costs) if all_costs else pd.DataFrame()
    hs_codes_df = pd.DataFrame(all_hs_codes) if all_hs_codes else pd.DataFrame()
    
    print(f"\nTotal extracted:")
    print(f"  - Invoice entries: {len(costs_df)}")
    print(f"  - HS codes: {len(hs_codes_df)}")
    
    return costs_df, hs_codes_df

def save_results(costs_df: pd.DataFrame, hs_codes_df: pd.DataFrame, 
                costs_output: str = "Data scraping test\invoice_costs.csv", 
                hs_output: str = "Data scraping test\hs_codes_duties.csv"):
    """Save both DataFrames to CSV files"""
    
    if not costs_df.empty:
        costs_df.to_csv(costs_output, index=False)
        print(f"Invoice costs saved to: {costs_output}")
    else:
        print("No invoice cost data to save")
    
    if not hs_codes_df.empty:
        hs_codes_df.to_csv(hs_output, index=False)
        print(f"HS codes and duties saved to: {hs_output}")
    else:
        print("No HS code data to save")


def test_extraction():
    """Test EV extraction from the very last line"""
    
    # Test with EV as the very last line
    sample_text = """001 LIQ DIELEC TRANSF, N/O 50KVA N
8504.21.0020 1,972 KG 9.00 NO 69,300 FREE FREE
C 1
499 MERCHANDISE PROCESSING FEE 0.3464 % 240.06
001IV 69,300.00
Other Fee Summary (for Block 39) 35. Total Entered Value CBP USE ONLY TOTALS
=EV 69,300"""

    print("Testing EV extraction from last line...")
    print("Sample text (last few lines):")
    lines = sample_text.strip().split('\n')
    for i, line in enumerate(lines[-3:], len(lines)-2):
        print(f"  Line {i}: '{line}'")
    
    print(f"\nLast line: '{lines[-1]}'")
    
    # Test extraction
    costs = extract_invoice_costs(sample_text)
    print(f"\nExtracted {len(costs)} entries:")
    for i, cost in enumerate(costs):
        print(f"Entry {i+1}:")
        print(f"  invoice_price: '{cost.get('invoice_price', 'MISSING')}'")
        print(f"  ev: '{cost.get('ev', 'MISSING')}'")
        if 'ev' in cost:
            print(f"  ✓ EV FOUND: {cost['ev']}")
        else:
            print(f"  ✗ EV NOT FOUND!")

    
# Main execution
if __name__ == "__main__":
    # Test the extraction first
    print("Testing extraction...")
    test_extraction()
    
    # Process the invoice sections folder
    invoice_sections_folder = "invoice_sections"
    
    try:
        # Scrape all invoice section files
        costs_df, hs_codes_df = scrape_invoice_sections_folder(invoice_sections_folder)
        
        # Save individual results to CSV
        save_results(costs_df, hs_codes_df)

        
        # Display individual results
        if not costs_df.empty:
            print("\nINVOICE COSTS DATA:")
            print(costs_df.to_string(index=False))
            
            # Check if EV column exists and has data
            if 'ev' in costs_df.columns:
                print(f"\nEV values found: {costs_df['ev'].notna().sum()} out of {len(costs_df)} entries")
                print(f"Sample EV values: {costs_df['ev'].dropna().head().tolist()}")
            else:
                print("\nWARNING: EV column not found in results!")
        
        if not hs_codes_df.empty:
            print(f"\nHS CODES AND DUTIES DATA:")
            print(hs_codes_df.to_string(index=False))

        
    except Exception as e:
        print(f"Error: {e}")