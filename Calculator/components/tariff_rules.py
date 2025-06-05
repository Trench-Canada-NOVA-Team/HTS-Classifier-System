"""
Modular tariff rules configuration
Easy to modify when business rules change
"""

# USMCA Eligible Countries
USMCA_COUNTRIES = ["canada", "mexico"]

# Steel & Aluminum HTS Code Mappings
STEEL_ALUMINUM_CODES = {
    # Steel codes
    "7208": {"type": "steel", "tariff": 25, "description": "Hot-rolled steel"},
    "7209": {"type": "steel", "tariff": 25, "description": "Cold-rolled steel"},
    "7210": {"type": "steel", "tariff": 25, "description": "Plated/coated steel"},
    "7211": {"type": "steel", "tariff": 25, "description": "Hot-rolled steel bars"},
    "7212": {"type": "steel", "tariff": 25, "description": "Cold-rolled steel bars"},
    
    # Aluminum codes  
    "7601": {"type": "aluminum", "tariff": 10, "description": "Unwrought aluminum"},
    "7602": {"type": "aluminum", "tariff": 10, "description": "Aluminum waste/scrap"},
    "7603": {"type": "aluminum", "tariff": 10, "description": "Aluminum powders/flakes"},
    "7604": {"type": "aluminum", "tariff": 10, "description": "Aluminum bars/rods"},
    "7605": {"type": "aluminum", "tariff": 10, "description": "Aluminum wire"},
}

# IEEPA Countries (subject to reciprocal tariffs)
IEEPA_COUNTRIES = ["china"]

# Tariff Rate Configurations (%)
TARIFF_RATES = {
    "ieepa_reciprocal": 10,
    "ieepa_ca_tariff": 25,
    "steel_alum_232_tariff": 50
}

# Review Period Days
REVIEW_PERIODS = {
    "ieepa_reciprocal": 90,
    "steel_aluminum": 365
}