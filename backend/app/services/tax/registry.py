"""
Tax Jurisdiction Provider Registry.
Manages deterministic tax calculation providers, version metadata, and rule lookup.
"""
from typing import Dict, List, Optional
from .jurisdictions import (
    BaseJurisdictionProvider,
    IndiaTaxProvider,
    USTaxProvider,
    UKTaxProvider,
    GermanyTaxProvider,
    FranceTaxProvider,
)
from .models import JurisdictionInfo, TaxRuleMetadata


class TaxRegistry:
    """Singleton registry for jurisdiction providers."""

    def __init__(self):
        self._providers: Dict[str, BaseJurisdictionProvider] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        """Register initial supported jurisdiction providers."""
        providers = [
            IndiaTaxProvider(),
            USTaxProvider(),
            UKTaxProvider(),
            GermanyTaxProvider(),
            FranceTaxProvider(),
        ]
        for p in providers:
            self.register_provider(p)

    def register_provider(self, provider: BaseJurisdictionProvider):
        """Register a new jurisdiction provider."""
        self._providers[provider.jurisdiction_code.upper()] = provider

    def get_provider(self, jurisdiction_code: str) -> BaseJurisdictionProvider:
        """Fetch provider by jurisdiction code. Raises ValueError if unsupported."""
        code = jurisdiction_code.upper().strip()
        if code not in self._providers:
            raise ValueError(f"Unsupported jurisdiction '{jurisdiction_code}'. Supported: {self.get_supported_codes()}")
        return self._providers[code]

    def get_supported_codes(self) -> List[str]:
        """Return list of supported two-letter jurisdiction codes."""
        return list(self._providers.keys())

    def list_jurisdictions(self) -> List[JurisdictionInfo]:
        """Return metadata for all registered jurisdictions."""
        return [p.get_jurisdiction_info() for p in self._providers.values()]

    def get_rule_metadata(self, jurisdiction_code: str, tax_year: str) -> TaxRuleMetadata:
        """Fetch rule metadata for given jurisdiction and tax year."""
        provider = self.get_provider(jurisdiction_code)
        
        # Verify tax year support
        year_normalized = tax_year.strip()
        supported = [y.lower() for y in provider.supported_years]
        if year_normalized.lower() not in supported and not any(year_normalized in y for y in provider.supported_years):
            raise ValueError(f"Tax rule unavailable for selected year '{tax_year}' in jurisdiction '{jurisdiction_code}'.")

        return provider.get_rule_metadata(tax_year)


# Global singleton instance
tax_registry = TaxRegistry()
