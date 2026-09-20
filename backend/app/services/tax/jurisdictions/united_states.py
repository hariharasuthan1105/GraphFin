"""
United States Federal Income Tax Provider — Tax Year 2026.
Official Sources: Internal Revenue Service (IRS) (irs.gov)
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

US_STANDARD_DEDUCTIONS_2026 = {
    "single": 16100.0,
    "married_joint": 32200.0,
    "married_separate": 16100.0,
    "head_of_household": 24150.0,
}

US_BRACKETS_2026 = {
    "single": [
        {"label": "$0 – $12,400", "min": 0, "max": 12400, "rate": 0.10},
        {"label": "$12,400 – $50,400", "min": 12400, "max": 50400, "rate": 0.12},
        {"label": "$50,400 – $105,700", "min": 50400, "max": 105700, "rate": 0.22},
        {"label": "$105,700 – $201,775", "min": 105700, "max": 201775, "rate": 0.24},
        {"label": "$201,775 – $256,225", "min": 201775, "max": 256225, "rate": 0.32},
        {"label": "$256,225 – $640,600", "min": 256225, "max": 640600, "rate": 0.35},
        {"label": "Above $640,600", "min": 640600, "max": None, "rate": 0.37},
    ],
    "married_joint": [
        {"label": "$0 – $24,800", "min": 0, "max": 24800, "rate": 0.10},
        {"label": "$24,800 – $100,800", "min": 24800, "max": 100800, "rate": 0.12},
        {"label": "$100,800 – $211,400", "min": 100800, "max": 211400, "rate": 0.22},
        {"label": "$211,400 – $403,550", "min": 211400, "max": 403550, "rate": 0.24},
        {"label": "$403,550 – $512,450", "min": 403550, "max": 512450, "rate": 0.32},
        {"label": "$512,450 – $768,700", "min": 512450, "max": 768700, "rate": 0.35},
        {"label": "Above $768,700", "min": 768700, "max": None, "rate": 0.37},
    ],
    "married_separate": [
        {"label": "$0 – $12,400", "min": 0, "max": 12400, "rate": 0.10},
        {"label": "$12,400 – $50,400", "min": 12400, "max": 50400, "rate": 0.12},
        {"label": "$50,400 – $105,700", "min": 50400, "max": 105700, "rate": 0.22},
        {"label": "$105,700 – $201,775", "min": 105700, "max": 201775, "rate": 0.24},
        {"label": "$201,775 – $256,225", "min": 201775, "max": 256225, "rate": 0.32},
        {"label": "$256,225 – $384,350", "min": 256225, "max": 384350, "rate": 0.35},
        {"label": "Above $384,350", "min": 384350, "max": None, "rate": 0.37},
    ],
    "head_of_household": [
        {"label": "$0 – $17,700", "min": 0, "max": 17700, "rate": 0.10},
        {"label": "$17,700 – $67,450", "min": 17700, "max": 67450, "rate": 0.12},
        {"label": "$67,450 – $105,700", "min": 67450, "max": 105700, "rate": 0.22},
        {"label": "$105,700 – $201,750", "min": 105700, "max": 201750, "rate": 0.24},
        {"label": "$201,750 – $256,200", "min": 201750, "max": 256200, "rate": 0.32},
        {"label": "$256,200 – $640,600", "min": 256200, "max": 640600, "rate": 0.35},
        {"label": "Above $640,600", "min": 640600, "max": None, "rate": 0.37},
    ],
}


class USTaxProvider(BaseJurisdictionProvider):
    """US Federal Income Tax Provider for Tax Year 2026."""

    @property
    def jurisdiction_code(self) -> str:
        return "US"

    @property
    def country_name(self) -> str:
        return "United States"

    @property
    def default_currency(self) -> str:
        return "USD"

    @property
    def currency_symbol(self) -> str:
        return "$"

    @property
    def supported_years(self) -> List[str]:
        return ["2026", "TY2026", "2026-27"]

    def get_jurisdiction_info(self) -> JurisdictionInfo:
        return JurisdictionInfo(
            id="US",
            name="United States",
            supported_years=["2026"],
            currency="USD",
            currency_symbol="$",
            source="Internal Revenue Service (IRS)",
            source_url="https://www.irs.gov",
            filing_statuses=["single", "married_joint", "married_separate", "head_of_household"],
            regions=None,
        )

    def get_rule_metadata(self, tax_year: str) -> TaxRuleMetadata:
        status_brackets = US_BRACKETS_2026.get("single", [])
        return TaxRuleMetadata(
            jurisdiction="US",
            country="United States",
            tax_year="2026",
            rule_version="US-2026-v1",
            currency="USD",
            currency_symbol="$",
            source="Internal Revenue Service (IRS)",
            source_url="https://www.irs.gov",
            last_verified="2026-03-01",
            disclaimer=(
                "US Federal Income Tax — Tax Year 2026 calculations represent IRS Federal tax estimates only. "
                "State and local taxes are not included unless explicitly selected. "
                "Calculations are for analytical purposes and do not constitute professional tax advice."
            ),
            brackets=[
                {
                    "label": b["label"],
                    "min": b["min"],
                    "max": b["max"],
                    "rate_percent": b["rate"] * 100,
                }
                for b in status_brackets
            ],
            options={
                "standard_deductions_2026": US_STANDARD_DEDUCTIONS_2026,
                "filing_statuses": list(US_BRACKETS_2026.keys()),
            },
        )

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResponse:
        status = (request.filing_status or "single").lower()
        if status not in US_BRACKETS_2026:
            status = "single"

        std_deduction = US_STANDARD_DEDUCTIONS_2026.get(status, 16100.0)
        total_deductions = std_deduction + request.deductions

        gross_income = request.gross_income
        if gross_income is not None:
            eval_taxable = max(0.0, gross_income - total_deductions)
        else:
            # If taxable_income is given, treat as after standard deduction or apply if needed
            eval_taxable = max(0.0, request.taxable_income - request.deductions)

        brackets = US_BRACKETS_2026[status]
        breakdown: List[TaxBracketBreakdown] = []
        tax_before_reliefs = 0.0
        marginal_rate = 0.0

        for b in brackets:
            min_val = b["min"]
            max_val = b["max"]
            rate = b["rate"]

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
                        bracket_label=b["label"],
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
                        bracket_label=b["label"],
                        min_income=float(min_val),
                        max_income=float(max_val) if max_val is not None else None,
                        taxable_amount_in_bracket=0.0,
                        rate=rate,
                        tax_amount=0.0,
                    )
                )

        estimated_tax = round(tax_before_reliefs, 2)
        effective_rate = round((estimated_tax / eval_taxable * 100.0) if eval_taxable > 0 else 0.0, 2)

        return TaxCalculationResponse(
            jurisdiction="US",
            country="United States",
            tax_year="2026",
            currency="USD",
            currency_symbol="$",
            taxable_income=round(eval_taxable, 2),
            gross_income=round(gross_income, 2) if gross_income is not None else round(eval_taxable + std_deduction, 2),
            allowances_and_deductions=round(total_deductions, 2),
            tax_before_reliefs=round(tax_before_reliefs, 2),
            reliefs=0.0,
            tax_after_reliefs=round(tax_before_reliefs, 2),
            surcharge=0.0,
            cess_or_additional_tax=0.0,
            church_tax=0.0,
            estimated_tax=estimated_tax,
            effective_tax_rate=effective_rate,
            marginal_tax_rate=round(marginal_rate, 2),
            breakdown=breakdown,
            extra_details={
                "scope": "US Federal Income Tax — Tax Year 2026",
                "filing_status": status,
                "standard_deduction": std_deduction,
                "state_tax": "Not calculated",
            },
            rule_version="US-2026-v1",
            source="Internal Revenue Service (IRS)",
            source_url="https://www.irs.gov",
            last_verified="2026-03-01",
            disclaimer=(
                "US Federal Income Tax — Tax Year 2026 calculations represent IRS Federal tax estimates only. "
                "State and local taxes are not included unless explicitly selected. "
                "Calculations are for analytical purposes and do not constitute tax or legal advice."
            ),
        )
