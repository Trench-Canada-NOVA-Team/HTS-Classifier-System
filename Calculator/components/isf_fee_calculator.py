from typing import Dict, List, Optional

class ISFFeeCalculator:
    """Calculate ISF fees based on transportation mode - Logic only"""
    
    # ISF Fee structure based on flowchart
    FEE_STRUCTURE = {
        "Ocean": {
            "base_fee": 50.00,
            "isf_fee": 37.10,
            "total": 87.10,
            "description": "Base Fee + ISF Filing Fee",
            "requires_isf": True
        },
        "Air": {
            "base_fee": 25.00,
            "isf_fee": 0.00,
            "total": 25.00,
            "description": "Air Processing Fee",
            "requires_isf": False
        },
        "Highway": {
            "base_fee": 16.50,
            "isf_fee": 0.00,
            "total": 16.50,
            "description": "Highway Processing Fee",
            "requires_isf": False
        }
    }
    
    @classmethod
    def calculate_isf_fee(cls, freight_mode: str) -> Dict[str, float]:
        """Calculate ISF fees based on freight mode"""
        if freight_mode not in cls.FEE_STRUCTURE:
            return {
                "base_fee": 0.00,
                "isf_fee": 0.00,
                "total": 0.00,
                "description": "Unknown Mode",
                "requires_isf": False
            }
        return cls.FEE_STRUCTURE[freight_mode].copy()
    
    @classmethod
    def get_available_modes(cls) -> List[str]:
        """Get list of available transportation modes"""
        return list(cls.FEE_STRUCTURE.keys())
    
    @classmethod
    def get_total_fee(cls, freight_mode: str) -> float:
        """Get total ISF fee for a freight mode"""
        return cls.FEE_STRUCTURE.get(freight_mode, {}).get("total", 0.00)
    
    @classmethod
    def get_base_fee(cls, freight_mode: str) -> float:
        """Get base processing fee for a freight mode"""
        return cls.FEE_STRUCTURE.get(freight_mode, {}).get("base_fee", 0.00)
    
    @classmethod
    def get_isf_filing_fee(cls, freight_mode: str) -> float:
        """Get ISF filing fee for a freight mode"""
        return cls.FEE_STRUCTURE.get(freight_mode, {}).get("isf_fee", 0.00)
    
    @classmethod
    def requires_isf_filing(cls, freight_mode: str) -> bool:
        """Check if freight mode requires ISF filing"""
        return cls.FEE_STRUCTURE.get(freight_mode, {}).get("requires_isf", False)
    
    @classmethod
    def get_fee_description(cls, freight_mode: str) -> str:
        """Get description for freight mode fees"""
        return cls.FEE_STRUCTURE.get(freight_mode, {}).get("description", "Unknown Mode")
    
    @classmethod
    def is_valid_mode(cls, freight_mode: str) -> bool:
        """Check if freight mode is valid"""
        return freight_mode in cls.FEE_STRUCTURE
    
    @classmethod
    def get_all_fees_data(cls) -> Dict[str, Dict]:
        """Get complete fee structure data"""
        return cls.FEE_STRUCTURE.copy()