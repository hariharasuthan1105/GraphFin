"""
Abstract Base Class for Jurisdiction Tax Providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..models import TaxCalculationRequest, TaxCalculationResponse, JurisdictionInfo, TaxRuleMetadata


class BaseJurisdictionProvider(ABC):
    """Abstract base class for all country tax providers."""

    @property
    @abstractmethod
    def jurisdiction_code(self) -> str:
        """Two-letter jurisdiction code (IN, US, GB, DE, FR)."""
        pass

    @property
    @abstractmethod
    def country_name(self) -> str:
        """Full country display name."""
        pass

    @property
    @abstractmethod
    def default_currency(self) -> str:
        """Default ISO 4217 currency code."""
        pass

    @property
    @abstractmethod
    def currency_symbol(self) -> str:
        """Currency display symbol."""
        pass

    @property
    @abstractmethod
    def supported_years(self) -> List[str]:
        """List of supported tax year strings."""
        pass

    @abstractmethod
    def get_jurisdiction_info(self) -> JurisdictionInfo:
        """Return high-level metadata about this jurisdiction."""
        pass

    @abstractmethod
    def get_rule_metadata(self, tax_year: str) -> TaxRuleMetadata:
        """Return static rule definition for visualization and rule inspection."""
        pass

    @abstractmethod
    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResponse:
        """Execute deterministic progressive tax calculation for given request."""
        pass
