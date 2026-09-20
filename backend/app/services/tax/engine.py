"""
Deterministic Tax Engine.
Serves as the main facade for tax calculation and rule inspection.
"""
from typing import List
from .registry import tax_registry
from .models import (
    TaxCalculationRequest,
    TaxCalculationResponse,
    JurisdictionInfo,
    TaxRuleMetadata,
)


class TaxEngine:
    """Facade service for tax calculations."""

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResponse:
        """Execute deterministic tax calculation for request payload."""
        provider = tax_registry.get_provider(request.jurisdiction)
        
        # Verify requested year is supported by provider
        supported = [y.lower() for y in provider.supported_years]
        req_year = request.tax_year.strip().lower()
        if req_year not in supported and not any(req_year in y for y in provider.supported_years):
            raise ValueError(
                f"Tax rule unavailable for selected year '{request.tax_year}' in jurisdiction '{request.jurisdiction}'."
            )

        return provider.calculate_tax(request)

    def list_jurisdictions(self) -> List[JurisdictionInfo]:
        """List all supported jurisdictions."""
        return tax_registry.list_jurisdictions()

    def get_rule_metadata(self, jurisdiction: str, tax_year: str) -> TaxRuleMetadata:
        """Get tax rule definition metadata for jurisdiction and tax year."""
        return tax_registry.get_rule_metadata(jurisdiction, tax_year)


# Global singleton instance
tax_engine = TaxEngine()
