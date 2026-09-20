"""
France Income Tax Provider — Tax Year 2026 (FR-2026-v1).
Official Sources: Direction Générale des Finances Publiques (DGFiP) (impots.gouv.fr)
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

FR_BRACKETS_2026 = [
    {"label": "Jusqu'à 11 294 € (0 %)", "min": 0, "max": 11294, "rate": 0.00},
    {"label": "De 11 295 € à 28 797 € (11 %)", "min": 11294, "max": 28797, "rate": 0.11},
    {"label": "De 28 798 € à 82 341 € (30 %)", "min": 28797, "max": 82341, "rate": 0.30},
    {"label": "De 82 342 € à 177 106 € (41 %)", "min": 82341, "max": 177106, "rate": 0.41},
    {"label": "Au-delà de 177 106 € (45 %)", "min": 177106, "max": None, "rate": 0.45},
]


class FranceTaxProvider(BaseJurisdictionProvider):
    """France Income Tax Provider for Tax Year 2026."""

    @property
    def jurisdiction_code(self) -> str:
        return "FR"

    @property
    def country_name(self) -> str:
        return "France"

    @property
    def default_currency(self) -> str:
        return "EUR"

    @property
    def currency_symbol(self) -> str:
        return "€"

    @property
    def supported_years(self) -> List[str]:
        return ["2026", "TY2026", "2026-27"]

    def get_jurisdiction_info(self) -> JurisdictionInfo:
        return JurisdictionInfo(
            id="FR",
            name="France",
            supported_years=["2026"],
            currency="EUR",
            currency_symbol="€",
            source="Direction Générale des Finances Publiques (DGFiP)",
            source_url="https://www.impots.gouv.fr",
            filing_statuses=None,
            regions=None,
        )

    def get_rule_metadata(self, tax_year: str) -> TaxRuleMetadata:
        return TaxRuleMetadata(
            jurisdiction="FR",
            country="France",
            tax_year="2026",
            rule_version="FR-2026-v1",
            currency="EUR",
            currency_symbol="€",
            source="Direction Générale des Finances Publiques (DGFiP)",
            source_url="https://www.impots.gouv.fr",
            last_verified="2026-03-01",
            disclaimer=(
                "French Income Tax — Tax Year 2026 calculations evaluate basic progressive income tax (Barème de l'impôt sur le revenu) "
                "with Quotient Familial parts support. Social contributions (CSG/CRDS) and high-income surcharges are not included in this basic estimate. "
                "Calculations are for analytical purposes and do not constitute professional tax advice."
            ),
            brackets=[
                {
                    "label": b["label"],
                    "min": b["min"],
                    "max": b["max"],
                    "rate_percent": b["rate"] * 100,
                }
                for b in FR_BRACKETS_2026
            ],
            options={
                "quotient_familial_parts_default": 1.0,
            },
        )

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResponse:
        gross_income = request.gross_income if request.gross_income is not None else request.taxable_income
        eval_taxable = max(0.0, gross_income - request.deductions)

        parts = max(1.0, request.parts)
        income_per_part = eval_taxable / parts

        tax_per_part = 0.0
        marginal_rate = 0.0
        breakdown: List[TaxBracketBreakdown] = []

        for b in FR_BRACKETS_2026:
            min_val = b["min"]
            max_val = b["max"]
            rate = b["rate"]

            if income_per_part > min_val:
                if max_val is None:
                    taxable_in_bracket_part = income_per_part - min_val
                else:
                    taxable_in_bracket_part = min(income_per_part, max_val) - min_val

                bracket_tax_part = taxable_in_bracket_part * rate
                tax_per_part += bracket_tax_part

                if taxable_in_bracket_part > 0 and rate > 0:
                    marginal_rate = rate * 100.0

                breakdown.append(
                    TaxBracketBreakdown(
                        bracket_label=b["label"],
                        min_income=float(min_val),
                        max_income=float(max_val) if max_val is not None else None,
                        taxable_amount_in_bracket=round(taxable_in_bracket_part * parts, 2),
                        rate=rate,
                        tax_amount=round(bracket_tax_part * parts, 2),
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

        total_tax_before_reliefs = tax_per_part * parts
        estimated_tax = round(total_tax_before_reliefs, 2)
        effective_rate = round((estimated_tax / eval_taxable * 100.0) if eval_taxable > 0 else 0.0, 2)

        return TaxCalculationResponse(
            jurisdiction="FR",
            country="France",
            tax_year="2026",
            currency="EUR",
            currency_symbol="€",
            taxable_income=round(eval_taxable, 2),
            gross_income=round(gross_income, 2),
            allowances_and_deductions=round(request.deductions, 2),
            tax_before_reliefs=round(total_tax_before_reliefs, 2),
            reliefs=0.0,
            tax_after_reliefs=round(total_tax_before_reliefs, 2),
            surcharge=0.0,
            cess_or_additional_tax=0.0,
            church_tax=0.0,
            estimated_tax=estimated_tax,
            effective_tax_rate=effective_rate,
            marginal_tax_rate=round(marginal_rate, 2),
            breakdown=breakdown,
            extra_details={
                "barème": "Impôt sur le revenu 2026",
                "quotient_familial_parts": parts,
                "income_per_part": round(income_per_part, 2),
            },
            rule_version="FR-2026-v1",
            source="Direction Générale des Finances Publiques (DGFiP)",
            source_url="https://www.impots.gouv.fr",
            last_verified="2026-03-01",
            disclaimer=(
                "French Income Tax — Tax Year 2026 calculations evaluate basic progressive income tax (Barème de l'impôt sur le revenu). "
                "Social contributions (CSG/CRDS) and exceptional high-income surcharges are not included in this basic estimate. "
                "Calculations are for analytical purposes and do not constitute tax or legal advice."
            ),
        )
