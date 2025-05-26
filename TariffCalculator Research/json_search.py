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
    returns a dictionary with general (success, duty percentage float), special, 
    other duties (success, duty percentage float) and description.
    If the HS code is not found, raises a ValueError.

    """
    for entry in json_data:
        if entry.get("htsno") == hs_code:
            return {
                "general": (format_duty(entry.get("general"))),

                "special": entry.get("special"),

                "other": (format_duty(entry.get("other"))),

                "description": entry.get("description")
            }
        
    print(f"HS code {hs_code} not found in the data.")
    raise ValueError(f"HS code {hs_code} not found in Tariff Schedule data.")

