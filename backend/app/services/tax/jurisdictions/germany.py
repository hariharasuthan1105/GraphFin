"""
Germany Income Tax Provider — Tax Year 2026 (DE-2026-v1).
Official Sources: Federal Ministry of Finance (Bundesministerium der Finanzen) (bundesfinanzministerium.de)
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

DE_BRACKETS_2026 = [
    {"label": "Grundfreibetrag (€0 – €12,096)", "min": 0, "max": 12096, "rate": 0.00},
    {"label": "Progressionszone I (€12,097 – €17,005)", "min": 12096, "max": 17005, "rate": 0.14},
    {"label": "Progressionszone II (€17,006 – €66,760)", "min": 17005, "max": 66760, "rate": 0.24},
    {"label": "Proportionalzone I (€66,761 – €277,825)", "min": 66760, "max": 277825, "rate": 0.42},
    {"label": "Proportionalzone II / Reichensteuer (Above €277,825)", "min": 277825, "max": None, "rate": 0.45},
]


class GermanyTaxProvider(BaseJurisdictionProvider):
    """Germany Income Tax Provider for Tax Year 2026."""

    @property
    def jurisdiction_code(self) -> str:
        return "DE"

    @property
    def country_name(self) -> str:
        return "Germany"

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
            id="DE",
            name="Germany",
            supported_years=["2026"],
            currency="EUR",
            currency_symbol="€",
            source="Federal Ministry of Finance (Bundesministerium der Finanzen)",
            source_url="https://www.bundesfinanzministerium.de",
            filing_statuses=None,
            regions=None,
        )

    def get_rule_metadata(self, tax_year: str) -> TaxRuleMetadata:
        return TaxRuleMetadata(
            jurisdiction="DE",
            country="Germany",
            tax_year="2026",
            rule_version="DE-2026-v1",
            currency="EUR",
            currency_symbol="€",
            source="Federal Ministry of Finance (Bundesministerium der Finanzen)",
            source_url="https://www.bundesfinanzministerium.de",
            last_verified="2026-03-01",
            disclaimer=(
                "German Income Tax — Tax Year 2026 calculations incorporate Grundfreibetrag (€12,096), "
                "progressive Einkommensteuer formula, Solidarity Surcharge (Solidaritätszuschlag), and optional Church Tax (Kirchensteuer). "
                "Calculations are estimates for analytical purposes and do not constitute professional tax advice."
            ),
            brackets=[
                {
                    "label": b["label"],
                    "min": b["min"],
                    "max": b["max"],
                    "rate_percent": b["rate"] * 100,
                }
                for b in DE_BRACKETS_2026
            ],
            options={
                "grundfreibetrag": 12096,
                "solidarity_surcharge_rate_percent": 5.5,
                "church_tax_applicable": True,
            },
        )

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResponse:
        gross_income = request.gross_income if request.gross_income is not None else request.taxable_income
        eval_taxable = max(0.0, gross_income - request.deductions)

        # Standard German progressive calculation (Einkommensteuertarif 2026)
        # Grundfreibetrag: €12,096
        tax_before_reliefs = 0.0
        marginal_rate = 0.0
        breakdown: List[TaxBracketBreakdown] = []

        if eval_taxable <= 12096:
            tax_before_reliefs = 0.0
            marginal_rate = 0.0
        elif eval_taxable <= 17005:
            # Zone 2: Progressive 14% - 24%
            y = (eval_taxable - 12096) / 10000.0
            tax_before_reliefs = (993.62 * y + 1400) * y
            marginal_rate = (14.0 + (24.0 - 14.0) * (eval_taxable - 12096) / (17005 - 12096))
        elif eval_taxable <= 66760:
            # Zone 3: Progressive 24% - 42%
            z = (eval_taxable - 17005) / 10000.0
            tax_before_reliefs = (181.19 * z + 2397) * z + 1014.0
            marginal_rate = (24.0 + (42.0 - 24.0) * (eval_taxable - 17005) / (66760 - 17005))
        elif eval_taxable <= 277825:
            # Zone 4: 42%
            tax_before_reliefs = 0.42 * eval_taxable - 10636.0
            marginal_rate = 42.0
        else:
            # Zone 5: 45%
            tax_before_reliefs = 0.45 * eval_taxable - 18970.05
            marginal_rate = 45.0

        tax_before_reliefs = max(0.0, tax_before_reliefs)

        # Build bracket breakdown rows
        for b in DE_BRACKETS_2026:
            min_val = b["min"]
            max_val = b["max"]
            rate = b["rate"]

            if eval_taxable > min_val:
                if max_val is None:
                    taxable_in_bracket = eval_taxable - min_val
                else:
                    taxable_in_bracket = min(eval_taxable, max_val) - min_val

                bracket_tax = taxable_in_bracket * rate
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

        # Solidarity Surcharge (Solidaritätszuschlag): 5.5% on income tax if tax > €18,130
        soli = 0.0
        if tax_before_reliefs > 18130.0:
            soli = tax_before_reliefs * 0.055

        # Church Tax (Kirchensteuer): Only if explicitly requested by user
        church_tax_val = 0.0
        if request.church_tax:
            rate = request.church_tax_rate if request.church_tax_rate in (0.08, 0.09) else 0.08
            church_tax_val = tax_before_reliefs * rate

        estimated_tax = round(tax_before_reliefs + soli + church_tax_val, 2)
        effective_rate = round((estimated_tax / eval_taxable * 100.0) if eval_taxable > 0 else 0.0, 2)

        return TaxCalculationResponse(
            jurisdiction="DE",
            country="Germany",
            tax_year="2026",
            currency="EUR",
            currency_symbol="€",
            taxable_income=round(eval_taxable, 2),
            gross_income=round(gross_income, 2),
            allowances_and_deductions=round(request.deductions, 2),
            tax_before_reliefs=round(tax_before_reliefs, 2),
            reliefs=0.0,
            tax_after_reliefs=round(tax_before_reliefs, 2),
            surcharge=0.0,
            cess_or_additional_tax=round(soli, 2),
            church_tax=round(church_tax_val, 2),
            estimated_tax=estimated_tax,
            effective_tax_rate=effective_rate,
            marginal_tax_rate=round(marginal_rate, 2),
            breakdown=breakdown,
            extra_details={
                "grundfreibetrag": 12096,
                "solidaritätszuschlag": round(soli, 2),
                "kirchensteuer": round(church_tax_val, 2),
                "church_tax_selected": request.church_tax,
            },
            rule_version="DE-2026-v1",
            source="Federal Ministry of Finance (Bundesministerium der Finanzen)",
            source_url="https://www.bundesfinanzministerium.de",
            last_verified="2026-03-01",
            disclaimer=(
                "German Income Tax — Tax Year 2026 calculations incorporate Grundfreibetrag, progressive Einkommensteuer formula, "
                "Solidarity Surcharge (Solidaritätszuschlag), and optional Church Tax (Kirchensteuer). "
                "Calculations are estimates for analytical purposes and do not constitute professional tax advice."
            ),
        )
