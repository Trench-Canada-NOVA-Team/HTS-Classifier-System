import json

def find_duty_by_hscode(json_data, hs_code):
    """
    Find duty information by HS code in the provided JSON data.
    returns a dictionary with general (duty percentage - float), special, 
    other duties (duty percentage - float) and description.
    If the HS code is not found, raises a ValueError.
    """
    for entry in json_data:
        if entry.get("htsno") == hs_code:
            return {
                "general": float(entry.get("general")[:-1] if isinstance(entry.get("general"), str) else entry.get("general")) if not None else 0.0,
                "special": entry.get("special"),
                "other": float(entry.get("other")[:-1] if isinstance(entry.get("general"), str) else entry.get("general")) if not None else 0.0,
                "description": entry.get("description")
            }
        
    print(f"HS code {hs_code} not found in the data.")
    raise ValueError(f"HS code {hs_code} not found in Tariff Schedule data.")

