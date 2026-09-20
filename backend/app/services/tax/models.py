"""
Data models and schemas for the GraphFin Tax Analytics Module.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TaxBracketBreakdown(BaseModel):
    """Breakdown of tax liability within a specific progressive bracket."""
    bracket_label: str = Field(..., description="Human readable bracket label (e.g. '₹4,00,001 - ₹8,00,000')")
    min_income: float = Field(..., description="Minimum income threshold for bracket")
    max_income: Optional[float] = Field(None, description="Maximum income threshold for bracket (None for uncapped top bracket)")
    taxable_amount_in_bracket: float = Field(..., description="Amount of income taxed in this bracket")
    rate: float = Field(..., description="Marginal rate for this bracket (e.g. 0.05 for 5%)")
    tax_amount: float = Field(..., description="Tax levied in this bracket")


class TaxCalculationRequest(BaseModel):
    """Input payload for tax estimation."""
    jurisdiction: str = Field(..., description="Explicit jurisdiction code: IN, US, GB, DE, FR")
    tax_year: str = Field(..., description="Tax year / Assessment year e.g. 'AY2026-27', '2026', '2026-27'")
    taxable_income: Optional[float] = Field(0.0, ge=0, description="Explicit taxable income amount")
    currency: Optional[str] = Field(None, description="Local currency code (e.g. INR, USD, GBP, EUR)")
    gross_income: Optional[float] = Field(None, description="Gross income before deductions/allowances if known")
    filing_status: Optional[str] = Field("single", description="US filing status: 'single', 'married_joint', 'married_separate', 'head_of_household'")
    region: Optional[str] = Field("england", description="UK region: 'england', 'wales', 'northern_ireland', 'scotland'")
    age: Optional[int] = Field(None, description="Taxpayer age")
    residency_status: Optional[str] = Field("resident", description="Residency status e.g. 'resident'")
    deductions: float = Field(0.0, ge=0, description="Additional explicit eligible deductions")
    taxable_capital_gains: float = Field(0.0, ge=0, description="Taxable capital gains income")
    dividend_income: float = Field(0.0, ge=0, description="Dividend income")
    interest_income: float = Field(0.0, ge=0, description="Interest income")
    church_tax: bool = Field(False, description="Germany: Church tax applicability (Kirchensteuer)")
    church_tax_rate: float = Field(0.08, description="Germany: Church tax rate (0.08 or 0.09)")
    parts: float = Field(1.0, ge=1.0, description="France: Quotient familial parts (default 1.0)")


class TaxCalculationResponse(BaseModel):
    """Output summary for tax estimation."""
    jurisdiction: str = Field(..., description="Jurisdiction code (IN, US, GB, DE, FR)")
    country: str = Field(..., description="Full country name")
    tax_year: str = Field(..., description="Tax year evaluated")
    currency: str = Field(..., description="Currency ISO code")
    currency_symbol: str = Field(..., description="Currency symbol (₹, $, £, €)")
    taxable_income: float = Field(..., description="Evaluated taxable income after allowances")
    gross_income: Optional[float] = Field(None, description="Gross income evaluated if provided or derived")
    allowances_and_deductions: float = Field(0.0, description="Total allowances or deductions applied")
    tax_before_reliefs: float = Field(..., description="Base tax calculated from brackets before rebates/credits")
    reliefs: float = Field(0.0, description="Total rebates or tax relief applied (e.g. Sec 87A rebate)")
    tax_after_reliefs: float = Field(..., description="Tax liability after rebates")
    surcharge: float = Field(0.0, description="High-income surcharge applied if any")
    cess_or_additional_tax: float = Field(0.0, description="Cess or additional surcharge (e.g. Health & Education Cess, Solidarity Surcharge)")
    church_tax: float = Field(0.0, description="Church tax if applicable (Germany)")
    estimated_tax: float = Field(..., description="Final estimated total tax liability")
    effective_tax_rate: float = Field(..., description="Effective rate percentage (0 - 100)")
    marginal_tax_rate: float = Field(..., description="Highest marginal bracket rate percentage (0 - 100)")
    breakdown: List[TaxBracketBreakdown] = Field(default_factory=list, description="Bracket-by-bracket breakdown")
    extra_details: Dict[str, Any] = Field(default_factory=dict, description="Jurisdiction specific calculation metadata")
    rule_version: str = Field(..., description="Tax rule version code")
    source: str = Field(..., description="Official tax authority source name")
    source_url: str = Field(..., description="Official source URL")
    last_verified: str = Field(..., description="ISO date of last rule verification")
    disclaimer: str = Field(..., description="Mandatory tax estimation disclaimer")


class JurisdictionInfo(BaseModel):
    """Metadata describing a supported jurisdiction."""
    id: str = Field(..., description="Jurisdiction code (IN, US, GB, DE, FR)")
    name: str = Field(..., description="Country display name")
    supported_years: List[str] = Field(..., description="Supported tax years")
    currency: str = Field(..., description="Local currency ISO code")
    currency_symbol: str = Field(..., description="Currency symbol")
    source: str = Field(..., description="Primary official source")
    source_url: str = Field(..., description="Primary official source URL")
    filing_statuses: Optional[List[str]] = Field(None, description="Available filing status options if applicable")
    regions: Optional[List[str]] = Field(None, description="Available regional options if applicable")


class TaxRuleMetadata(BaseModel):
    """Detailed tax rule metadata for a jurisdiction and tax year."""
    jurisdiction: str
    country: str
    tax_year: str
    rule_version: str
    currency: str
    currency_symbol: str
    source: str
    source_url: str
    last_verified: str
    disclaimer: str
    brackets: List[Dict[str, Any]]
    options: Dict[str, Any] = Field(default_factory=dict)
