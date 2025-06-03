import os
import re
import PyPDF2
import pdfplumber
from pathlib import Path
import pandas as pd
from typing import List, Dict, Optional

def extract_text_with_pypdf2(pdf_path: str) -> str:
    """Extract text using PyPDF2 (fallback method)"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"PyPDF2 failed for {pdf_path}: {e}")
        return ""

def extract_text_with_pdfplumber(pdf_path: str) -> str:
    """Extract text using pdfplumber (preferred method)"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        print(f"pdfplumber failed for {pdf_path}: {e}")
        return ""

def extract_entry_data(text: str) -> List[Dict]:
    """
    Extract entry data matching the pattern:
    001IV XXXXX (extract only the value XXXXX)
    -FRT, INTL XXXXX
    -BROKERAGE XXXXX
    -OTH XXXXX
    /DTY XXXXX
    =EV XXXXX
    
    Where XXXXX can be any text, not just numbers.
    Accepts partial matches.
    """
    
    # Define the regex pattern - extract only the values after each identifier
    pattern = r'''
        \d{3}IV\s+(.+?)(?:\n|$)                 # Extract value after 001IV (not the 001IV itself)
        .*?-FRT,?\s*INTL\s+(.+?)(?:\n|$)        # -FRT, INTL XXXXX (any text)
        .*?-BROKERAGE\s+(.+?)(?:\n|$)           # -BROKERAGE XXXXX (any text)
        .*?-OTH\s+(.+?)(?:\n|$)                 # -OTH XXXXX (any text)
        .*?/DTY\s+(.+?)(?:\n|$)                 # /DTY XXXXX (any text)
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
                'oth': match[3].strip(),
                'dty': match[4].strip(),
                'ev': match[5].strip()
            })
        except IndexError as e:
            print(f"Error parsing match {match}: {e}")
            continue
    
    return results

def alternative_pattern_search(text: str) -> List[Dict]:
    """
    Line-wise pattern matching - accepts partial matches
    """
    
    # Split text into lines for easier processing
    lines = text.split('\n')
    
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
    
    results = []
    current_entry = {}
    
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
        
        # Look for OTH - capture everything after it
        oth_match = re.search(r'-OTH\s+(.+)', line)
        if oth_match and 'invoice_price' in current_entry:
            current_entry['oth'] = oth_match.group(1).strip()
            continue
        
        # Look for DTY - capture everything after it
        dty_match = re.search(r'/DTY\s+(.+)', line)
        if dty_match and 'invoice_price' in current_entry:
            current_entry['dty'] = dty_match.group(1).strip()
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
        
        # Check for any of the pattern lines
        patterns = [
            (r'-FRT,?\s*INTL\s+(.+)', 'frt_intl'),
            (r'-BROKERAGE\s+(.+)', 'brokerage'),
            (r'-OTH\s+(.+)', 'oth'),
            (r'/DTY\s+(.+)', 'dty'),
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

def extract_invoice_section(text: str) -> str:
    """
    Extract only the section between:
    * * * INVOICE # X, LINE XX * * *
    and
    "I declare that"
    
    Returns the lines in between (excluding the "I declare that" line)
    """
    lines = text.split('\n')
    invoice_sections = []
    
    capturing = False
    current_section = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check for invoice header pattern
        if re.search(r'\*\s*\*\s*\*\s*INVOICE\s*#\s*\d+,\s*LINE\s*\d+\s*\*\s*\*\s*\*', line_stripped, re.IGNORECASE):
            # If we were already capturing, save the previous section
            if capturing and current_section:
                invoice_sections.append('\n'.join(current_section))
            
            # Start capturing new section
            capturing = True
            current_section = []
            continue
        
        # Check for "I declare that" - stop capturing but don't include this line
        if line_stripped.startswith("CBP Form 7501 (05/22) Page 2 of 2"):
            if capturing and current_section:
                invoice_sections.append('\n'.join(current_section))
            capturing = False
            current_section = []
            continue
        
        # If we're capturing, add the line to current section
        if capturing:
            current_section.append(line)
    
    # If we were still capturing at the end, save the last section
    if capturing and current_section:
        invoice_sections.append('\n'.join(current_section))
    
    # Return all sections combined
    return '\n\n--- NEXT INVOICE SECTION ---\n\n'.join(invoice_sections)

def write_invoice_section_to_file(pdf_path: str, invoice_section: str, output_folder: str = "data_scraping\invoice_sections"):
    """Write only the invoice section to a plain text file"""
    
    # Create output folder if it doesn't exist
    Path(output_folder).mkdir(exist_ok=True)
    
    # Create filename based on PDF name
    pdf_name = Path(pdf_path).stem
    txt_filename = f"{pdf_name}_invoice_section.txt"
    txt_path = Path(output_folder) / txt_filename
    
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Invoice section from: {pdf_path}\n")
            f.write("=" * 80 + "\n\n")
            if invoice_section.strip():
                f.write(invoice_section)
            else:
                f.write("No invoice section found matching the pattern.")
        print(f"Invoice section saved to: {txt_path}")
    except Exception as e:
        print(f"Error saving invoice section for {pdf_path}: {e}")

def write_extracted_text_to_file(pdf_path: str, text: str, output_folder: str = "data_scraping\extracted_text"):
    """Write extracted text to a plain text file for verification"""
    
    # Create output folder if it doesn't exist
    Path(output_folder).mkdir(exist_ok=True)
    
    # Create filename based on PDF name
    pdf_name = Path(pdf_path).stem
    txt_filename = f"{pdf_name}_extracted.txt"
    txt_path = Path(output_folder) / txt_filename
    
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Extracted text from: {pdf_path}\n")
            f.write("=" * 80 + "\n\n")
            f.write(text)
        print(f"Extracted text saved to: {txt_path}")
    except Exception as e:
        print(f"Error saving extracted text for {pdf_path}: {e}")

def process_pdf(pdf_path: str) -> List[Dict]:
    """Process a single PDF file and extract entry data"""
    
    print(f"Processing: {pdf_path}")
    
    # Try pdfplumber first (usually better for text extraction)
    text = extract_text_with_pdfplumber(pdf_path)
    
    # Fallback to PyPDF2 if pdfplumber fails
    if not text.strip():
        print(f"pdfplumber failed, trying PyPDF2...")
        text = extract_text_with_pypdf2(pdf_path)
    
    if not text.strip():
        print(f"Could not extract text from {pdf_path}")
        return []
    
    # Extract only the invoice section
    invoice_section = extract_invoice_section(text)
    
    # Write both full text and invoice section to files for verification
    write_extracted_text_to_file(pdf_path, text)  # Full PDF text
    write_invoice_section_to_file(pdf_path, invoice_section)  # Invoice section only
    
    # Process the invoice section for data extraction
    if not invoice_section.strip():
        print(f"No invoice section found in {pdf_path}")
        return []
    
    # Try primary pattern matching first on the invoice section
    results = extract_entry_data(invoice_section)
    print(f"Primary pattern found {len(results)} complete matches")
    
    # Try alternative line-wise approach
    if not results:
        print(f"Trying line-wise approach...")
        results = alternative_pattern_search(invoice_section)
        print(f"Line-wise approach found {len(results)} matches")
    
    # Try partial matching as last resort
    if not results:
        print(f"Trying partial matching...")
        results = extract_partial_matches(invoice_section)
        print(f"Partial matching found {len(results)} matches")
    
    # Add source file to each result
    for result in results:
        result['source_file'] = os.path.basename(pdf_path)[:-4]  # Remove .pdf extension
        # Fill missing fields with None for partial matches
        for field in ['frt_intl', 'brokerage', 'oth', 'dty', 'ev']:
            if field not in result:
                result[field] = None
    
    return results

def scrape_entry_data_folder(folder_path: str) -> pd.DataFrame:
    """
    Scrape all PDFs in the entry data folder and return a DataFrame
    """
    
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    # Find all PDF files
    pdf_files = list(folder_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {folder_path}")
        return pd.DataFrame()
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    all_results = []
    
    for pdf_file in pdf_files:
        try:
            results = process_pdf(str(pdf_file))
            all_results.extend(results)
            print(f"Extracted {len(results)} entries from {pdf_file.name}")
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
    
    # Convert to DataFrame
    if all_results:
        df = pd.DataFrame(all_results)
        print(f"\nTotal entries extracted: {len(df)}")
        return df
    else:
        print("No entry data found in any PDF files")
        return pd.DataFrame()

def save_results(df: pd.DataFrame, output_path: str = "data_scraping\extracted_entry_data.csv"):
    """Save results to CSV file"""
    if not df.empty:
        df.to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")
    else:
        print("No data to save")


# Main execution
if __name__ == "__main__":
    
    # Set the path to your entry data folder
    entry_data_folder = r"data_scraping\entry_data"
    
    try:
        # Scrape the PDFs
        results_df = scrape_entry_data_folder(entry_data_folder)
        
        # Display results
        if not results_df.empty:
            print("\nExtracted Data:")
            print(results_df.to_string(index=False))
            
            # Save to CSV
            save_results(results_df)
            
            # Summary statistics
            print(f"\nSummary Statistics:")
            print(f"Total entries found: {len(results_df)}")
            
            # Try to show some sample values
            if 'invoice_price' in results_df.columns:
                print(f"Sample invoice prices: {results_df['invoice_price'].head().tolist()}")
            if 'ev' in results_df.columns:
                print(f"Sample EV values: {results_df['ev'].head().tolist()}")
        
    except Exception as e:
        print(f"Error: {e}")