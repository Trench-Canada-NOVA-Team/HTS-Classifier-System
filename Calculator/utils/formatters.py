def format_hs_code(code):
    """Format HS code to XXXX.XX.XX.XX"""
    if not code:
        return None
    
    digits = ''.join(filter(str.isdigit, code))[:12]
    sections = [digits[i:j] for i, j in [(0, 4), (4, 6), (6, 8), (8, 10)] if i < len(digits)]
    return '.'.join(sections)

def format_currency(amount):
    """Format currency with proper comma separation"""
    return f"${amount:,.2f}"

def format_percentage(percent):
    """Format percentage with 2 decimal places"""
    return f"{percent:.2f}%"