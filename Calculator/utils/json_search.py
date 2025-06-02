import json

def format_duty(duty):
    """
    Format the duty percentage as a float.
    If the duty is a string, check the string for a percentage."""
    
    # duty is Free
    if duty == "Free" or duty == '':
        return 0, 0.0
    
    # check whether duty field contains a message or conditional
    try:
        # if duty is a percentage in a string format, convert it to float
        duty = float(duty.strip('%'))
        return 0, duty
    except ValueError:
        # if it cannot be converted, return 0.0
        return 1, duty
    


def find_duty_by_hscode(json_data, hs_code):
    """
    Find duty information by HS code in the provided JSON data.
    If duty is empty, search backwards from the found entry to find a valid duty.
    returns a dictionary with general (success, duty percentage float), special, 
    other duties (success, duty percentage float) and description.
    If the HS code is not found, raises a ValueError.
    """
    # First, find the target HS code and its index
    target_index = None
    target_entry = None
    
    for index, entry in enumerate(json_data):
        if entry.get("htsno") == hs_code:
            target_index = index
            target_entry = entry
            break
    
    if target_entry is None:
        print(f"HS code {hs_code} not found in the data.")
        raise ValueError(f"HS code {hs_code} not found in Tariff Schedule data.")
    
    # Function to search backwards for valid duty from the target entry
    def find_valid_duty_backwards(duty_field):
        current_duty = target_entry.get(duty_field, "")
        
        # If current duty is valid, return it
        if current_duty and current_duty != "":
            return format_duty(current_duty)
        
        # Search backwards from the target entry
        for i in range(target_index - 1, -1, -1):
            entry = json_data[i]
            duty = entry.get(duty_field, "")
            
            if duty and duty != "":
                return format_duty(duty)
        
        # If no valid duty found, return default
        return format_duty("")
    
    return {
        "general": find_valid_duty_backwards("general"),
        "special": target_entry.get("special"),
        "other": find_valid_duty_backwards("other"),
        "description": target_entry.get("description")
    }
