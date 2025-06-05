import streamlit as st
import logging
from typing import Dict, Any, Tuple, Optional
from components.tariff_rules import *

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TariffDecisionEngine:
    """Modular tariff decision engine based on the flow diagram"""
    
    def __init__(self):
        self.decision_results = {}
    
    def check_country_origin(self, country: str) -> bool:
        """Check if country of Origin is Canada or elsewhere"""

        # CoO is Canada
        if country.lower().strip() == "canada":
            return True
        
        # CoO is not Canada (and not China)
        elif country.lower().strip() not in ["canada", "china"]:
            return False
        
        # CoO is China
        return NotImplementedError
    
    def check_usmca_eligibility(self, hs_code: str) -> Tuple[bool, str]:
        """Check USMCA eligibility - placeholder for actual logic"""
        # This would connect to your HTS database/API
        # For now, return a placeholder
        return False, "USMCA check not implemented yet"
    
    def check_steel_aluminum_content(self, hs_code: str) -> Tuple[bool, Dict]:
        """Check if product contains steel or aluminum derivatives"""
        # Steel & Aluminum HTS codes (placeholder)
        # Implement to check HTS code database
        
        return False, {}
    
    def apply_reciprocal_tariff(self, base_tariff: float) -> float:
        """Apply IEEPA reciprocal tariff (10% reduction)"""
        return base_tariff * 0.9  # 10% reduction
    
    def calculate_tariff(self, country: str, hs_code: str, product_type: str) -> Dict[str, Any]:
        """Main tariff calculation flow"""
        result = {
            "country": country,
            "hs_code": hs_code,
            "product_type": product_type,
            "final_tariff": 0,
            "additional_tariff": 0,
            "decision_path": [],
            "tariff_type": "Standard",
            "notes": []
        }

        logger.info(f"Country of Origin Check: {self.check_country_origin(country)}")
        
        # Step 1: Check if from Canada
        if self.check_country_origin(country):
            logger.info(f"Running Canada-specific logic for HS Code: {hs_code}")
            result["decision_path"].append("Country: Canada")
            
            # Check USMCA eligibility
            is_usmca, usmca_note = self.check_usmca_eligibility(hs_code)
            if is_usmca:
                logger.info("USMCA eligibility confirmed")
                result["decision_path"].append("USMCA Eligible")
                result["final_tariff"] = 0
                result["tariff_type"] = "USMCA Free"
                result["notes"].append("Eligible for USMCA duty-free treatment")

                # Check for steel & aluminum content
                has_steel_aluminum, steel_aluminum_info = self.check_steel_aluminum_content(hs_code)
                
                if has_steel_aluminum:
                    logger.info(f"Product contains steel/aluminum: {steel_aluminum_info}")
                    result["decision_path"].append(f"Contains {steel_aluminum_info.get('type', 'steel/aluminum')}")
                    additional_tariff = TARIFF_RATES["steel_alum_232_tariff"]
                    result["additional_tariff"] += additional_tariff
                    result["tariff_type"] = f"{steel_aluminum_info.get('type', 'Steel/Aluminum').title()} Tariff"
                    result["notes"].append(f"Additional {additional_tariff}% tariff for {steel_aluminum_info.get('type', 'steel/aluminum')}")
                
                return result
            
            else:
                logger.info("USMCA eligibility not confirmed")
                result["decision_path"].append("USMCA Not Eligible")
                result["notes"].append(usmca_note)

                # From Canada but not USMCA, apply IEEPA reciprocal tariff
                result["additional_tariff"] += TARIFF_RATES["ieepa_ca_tariff"]

        # Not from Canada and not USMCA, apply IEEPA reciprocal
        elif not self.check_country_origin(country):
            logger.info(f"Running Foreign logic for HS Code: {hs_code}")
            logger.info(f"Checking product type: {result['product_type']}")
            if result["product_type"] == "Resale":
                logger.info("Resale product, applying IEEPA tariff")
                result["decision_path"].append("IEEPA Reciprocal Applied")
                result["additional_tariff"] += TARIFF_RATES["ieepa_reciprocal"]

        # Final calculation
        logger.info(f"Final tariff calculation for HS Code: {hs_code}")
        result["final_tariff"] += result["additional_tariff"]
        
        return result

def render_tariff_decision_flow():
    """Render the tariff decision flow interface"""
    st.subheader("🎯 Tariff Decision Engine")
    
    engine = TariffDecisionEngine()
    
    # Get current values from session state
    country = st.session_state.get('country_of_origin', '')
    hs_codes = st.session_state.get('hs_code_list', [])
    
    if country and hs_codes:
        st.write("**Tariff Analysis Results:**")
        
        for idx, hs_item in enumerate(hs_codes):
            if isinstance(hs_item, dict):
                hs_code = hs_item.get('hs_code', '')
                product_type = st.session_state.hs_code_list[idx]['goods_type']
                
                # Calculate tariff using decision engine
                tariff_result = engine.calculate_tariff(country, hs_code, product_type)
                
                with st.expander(f"HS Code: {hs_code} - {tariff_result['tariff_type']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Additional Tariff:** {tariff_result['additional_tariff']}%")
                        st.write(f"**Total Tariff:** {tariff_result['final_tariff']}%")
                    
                    with col2:
                        st.write("**Decision Path:**")
                        for step in tariff_result['decision_path']:
                            st.write(f"• {step}")
                    
                    if tariff_result['notes']:
                        st.write("**Notes:**")
                        for note in tariff_result['notes']:
                            st.info(note)
                
                # Update the tariff in session state
                st.session_state.hs_code_list[idx]['calculated_tariff'] = tariff_result['final_tariff']
    
    else:
        st.info("Enter country of origin and HS codes to see tariff analysis")

def get_calculated_tariffs() -> float:
    """Get total calculated tariffs from decision engine"""
    hs_codes = st.session_state.get('hs_code_list', [])
    total_tariff = 0
    
    for hs_item in hs_codes:
        if isinstance(hs_item, dict):
            total_tariff += float(hs_item.get('calculated_tariff', hs_item.get('tariff_percent', 0)))
    
    return total_tariff