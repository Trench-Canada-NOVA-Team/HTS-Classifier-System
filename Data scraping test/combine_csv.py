import pandas as pd

def combine_csv(file1, file2, join_column, output_file, how='inner'):
    # Read the CSV files
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)
    
    # Merge the DataFrames on the specified column
    combined = pd.merge(df1, df2, on=join_column, how=how)
    
    # Save the combined DataFrame to a new CSV file
    combined.to_csv(output_file, index=False)
    print(f"Combined CSV saved to {output_file}")

def clean_csv(file_path, output_file):
    df = pd.read_csv(file_path)

    for col in df.columns[:-1]:
        if col.lower() == 'duty':
            # Remove last character and strip whitespace
            df[col] = df[col].astype(str).str[:-1].str.strip()
        else:
            # Take only the first chunk of text (split by whitespace/newline), strip whitespace
            df[col] = df[col].astype(str).str.split().str[0].str.strip()
            # Try to convert to float if possible
            df[col] = df[col].str.replace(',', '', regex=False)  # Remove commas for numeric conversion
            df[col] = pd.to_numeric(df[col], errors='ignore')

    df.to_csv(output_file, index=False)
    print(f"Cleaned CSV saved to {output_file}")

if __name__ == "__main__":
    # Combining scraped data with HS codes and duties
    file1 = 'Data scraping test\extracted_entry_data.csv'
    file2 = 'Data scraping test\hs_codes_duties.csv'
    join_column = 'source_file'  # Change to your join column
    output_file = 'Data scraping test\entry_data\combined.csv'
    combine_csv(file1, file2, join_column, output_file)
    clean_csv(output_file, 'Data scraping test\entry_data\cleaned_combined.csv')