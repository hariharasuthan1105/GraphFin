"""
India Tax Provider — New Tax Regime AY 2026–27.
Official Sources: Income Tax Department India (incometax.gov.in)
"""
from typing import List, Dict, Any
from .base import BaseJurisdictionProvider
from ..models import (
    TaxCalculationRequest,
    TaxCalculationResponse,
    TaxBracketBreakdown,
    JurisdictionInfo,
    TaxRuleMetadata,
)

INDIAN_SLABS_AY2026_27 = [
    {"label": "Up to ₹4,00,000", "min": 0, "max": 400000, "rate": 0.00},
    {"label": "₹4,00,001 – ₹8,00,000", "min": 400000, "max": 800000, "rate": 0.05},
    {"label": "₹8,00,001 – ₹12,00,000", "min": 800000, "max": 1200000, "rate": 0.10},
    {"label": "₹12,00,001 – ₹16,00,000", "min": 1200000, "max": 1600000, "rate": 0.15},
    {"label": "₹16,00,001 – ₹20,00,000", "min": 1600000, "max": 2000000, "rate": 0.20},
    {"label": "₹20,00,001 – ₹24,00,000", "min": 2000000, "max": 2400000, "rate": 0.25},
    {"label": "Above ₹24,00,000", "min": 2400000, "max": None, "rate": 0.30},
]


class IndiaTaxProvider(BaseJurisdictionProvider):
    """India Income Tax Provider for Assessment Year 2026–27."""

    @property
    def jurisdiction_code(self) -> str:
        return "IN"

    @property
    def country_name(self) -> str:
        return "India"

    @property
    def default_currency(self) -> str:
        return "INR"

    @property
    def currency_symbol(self) -> str:
        return "₹"

    @property
    def supported_years(self) -> List[str]:
        return ["AY2026-27", "2026-27", "AY 2026-27", "2026"]

    def get_jurisdiction_info(self) -> JurisdictionInfo:
        return JurisdictionInfo(
            id="IN",
            name="India",
            supported_years=["AY 2026–27"],
            currency="INR",
            currency_symbol="₹",
            source="Income Tax Department, Government of India",
            source_url="https://www.incometax.gov.in",
            filing_statuses=["Individual (New Regime)"],
            regions=None,
        )

    def get_rule_metadata(self, tax_year: str) -> TaxRuleMetadata:
        return TaxRuleMetadata(
            jurisdiction="IN",
            country="India",
            tax_year="AY 2026–27",
            rule_version="IN-AY2026-27-v1",
            currency="INR",
            currency_symbol="₹",
            source="Income Tax Department, Government of India",
            source_url="https://www.incometax.gov.in",
            last_verified="2026-03-01",
            disclaimer=(
                "Indian Income Tax — AY 2026–27 calculations are estimates under the New Tax Regime. "
                "Calculations incorporate Section 87A rebate, high-income surcharge, and 4% Health & Education Cess. "
                "They are provided for analytical purposes and do not constitute tax or legal advice."
            ),
            brackets=[
                {
                    "label": slab["label"],
                    "min": slab["min"],
                    "max": slab["max"],
                    "rate_percent": slab["rate"] * 100,
                }
                for slab in INDIAN_SLABS_AY2026_27
            ],
            options={
                "standard_deduction": 75000,
                "sec_87a_threshold": 1200000,
                "sec_87a_max_rebate": 60000,
                "cess_rate_percent": 4.0,
            },
        )

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResponse:
        # Evaluate income
        gross_income = request.gross_income
        std_deduction = 75000.0 if gross_income is not None else 0.0

        if gross_income is not None:
            eval_taxable = max(0.0, gross_income - std_deduction - request.deductions)
        else:
            eval_taxable = max(0.0, request.taxable_income - request.deductions)

        # Calculate progressive bracket tax
        breakdown: List[TaxBracketBreakdown] = []
        tax_before_reliefs = 0.0
        marginal_rate = 0.0

        for slab in INDIAN_SLABS_AY2026_27:
            min_val = slab["min"]
            max_val = slab["max"]
            rate = slab["rate"]

            if eval_taxable > min_val:
                if max_val is None:
                    taxable_in_bracket = eval_taxable - min_val
                else:
                    taxable_in_bracket = min(eval_taxable, max_val) - min_val

                bracket_tax = taxable_in_bracket * rate
                tax_before_reliefs += bracket_tax

                if taxable_in_bracket > 0 and rate > 0:
                    marginal_rate = rate * 100.0

                breakdown.append(
                    TaxBracketBreakdown(
                        bracket_label=slab["label"],
                        min_income=float(min_val),
                        max_income=float(max_val) if max_val is not None else None,
                        taxable_amount_in_bracket=round(taxable_in_bracket, 2),
                        rate=rate,
                        tax_amount=round(bracket_tax, 2),
                    )
                )
            else:
                breakdown.append(
                    TaxBracketBreakdown(
                        bracket_label=slab["label"],
                        min_income=float(min_val),
                        max_income=float(max_val) if max_val is not None else None,
                        taxable_amount_in_bracket=0.0,
                        rate=rate,
                        tax_amount=0.0,
                    )
                )

        # Section 87A Rebate for AY 2026-27 under New Tax Regime
        # Threshold: ₹12,00,000 taxable income. Max rebate: ₹60,000
        rebate_87a = 0.0
        if eval_taxable <= 1200000.0:
            rebate_87a = min(tax_before_reliefs, 60000.0)
        elif eval_taxable > 1200000.0 and eval_taxable <= 1275000.0:
            # Marginal relief under Section 87A
            excess_income = eval_taxable - 1200000.0
            if tax_before_reliefs > excess_income:
                rebate_87a = tax_before_reliefs - excess_income

        tax_after_rebate = max(0.0, tax_before_reliefs - rebate_87a)

        # Surcharge logic
        surcharge_rate = 0.0
        if eval_taxable > 20000000.0:
            surcharge_rate = 0.25
        elif eval_taxable > 10000000.0:
            surcharge_rate = 0.15
        elif eval_taxable > 5000000.0:
            surcharge_rate = 0.10

        surcharge = tax_after_rebate * surcharge_rate

        # 4% Health & Education Cess
        cess = (tax_after_rebate + surcharge) * 0.04

        estimated_tax = round(tax_after_rebate + surcharge + cess, 2)
        effective_rate = round((estimated_tax / eval_taxable * 100.0) if eval_taxable > 0 else 0.0, 2)

        return TaxCalculationResponse(
            jurisdiction="IN",
            country="India",
            tax_year="AY 2026–27",
            currency="INR",
            currency_symbol="₹",
            taxable_income=round(eval_taxable, 2),
            gross_income=round(gross_income, 2) if gross_income is not None else round(eval_taxable + std_deduction, 2),
            allowances_and_deductions=round(std_deduction + request.deductions, 2),
            tax_before_reliefs=round(tax_before_reliefs, 2),
            reliefs=round(rebate_87a, 2),
            tax_after_reliefs=round(tax_after_rebate, 2),
            surcharge=round(surcharge, 2),
            cess_or_additional_tax=round(cess, 2),
            church_tax=0.0,
            estimated_tax=estimated_tax,
            effective_tax_rate=effective_rate,
            marginal_tax_rate=round(marginal_rate, 2),
            breakdown=breakdown,
            extra_details={
                "regime": "New Tax Regime (AY 2026–27)",
                "section_87a_rebate": round(rebate_87a, 2),
                "health_and_education_cess_4pct": round(cess, 2),
                "surcharge": round(surcharge, 2),
                "standard_deduction": round(std_deduction, 2),
            },
            rule_version="IN-AY2026-27-v1",
            source="Income Tax Department, Government of India",
            source_url="https://www.incometax.gov.in",
            last_verified="2026-03-01",
            disclaimer=(
                "Indian Income Tax — AY 2026–27 calculations are estimates for analytical purposes and are not "
                "tax, legal, or financial advice. Actual liability depends on complete taxpayer circumstances, "
                "applicable exemptions, residency, and final official assessments."
            ),
        )
