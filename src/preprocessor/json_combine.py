import json
import os

"""
This script concatenates all JSON files containing HTS data into a single JSON file.
"""


# Directory containing the JSON files
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', '..', 'Data')
data_dir = os.path.abspath(data_dir)
output_file = os.path.join(data_dir, 'combined_data.json')

# Store all loaded data
all_data = []

# # Include the first file (htsdata.json)
# first_file = os.path.join(data_dir, 'htsdata.json')
# try:
#     with open(first_file, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#         if isinstance(data, list):
#             all_data.extend(data)
#         else:
#             all_data.append(data)
# except Exception as e:
#     print(f"Error reading htsdata.json: {e}")

# Loop through the numbered files from htsdata(1).json to htsdata(99).json
for i in range(1, 100):
    filename = f'htsdata ({i}).json'
    filepath = os.path.join(data_dir, filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                all_data.extend(data)
            else:
                all_data.append(data)
    except Exception as e:
        print(f"Error reading {filename}: {e}")

# Write all data to a single JSON file
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, indent=2)

print(f"Concatenated {len(all_data)} entries into {output_file}")
