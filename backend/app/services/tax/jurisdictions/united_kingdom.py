"""
United Kingdom & Scotland Income Tax Provider — Tax Year 2026–27.
Official Sources: HM Revenue & Customs (HMRC) (gov.uk) & Scottish Government (gov.scot)
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

RUK_BRACKETS_2026_27 = [
    {"label": "Personal Allowance (£0 – £12,570)", "min": 0, "max": 12570, "rate": 0.00},
    {"label": "Basic rate (£12,571 – £50,270)", "min": 12570, "max": 50270, "rate": 0.20},
    {"label": "Higher rate (£50,271 – £125,140)", "min": 50270, "max": 125140, "rate": 0.40},
    {"label": "Additional rate (Above £125,140)", "min": 125140, "max": None, "rate": 0.45},
]

SCOTLAND_BRACKETS_2026_27 = [
    {"label": "Personal Allowance (£0 – £12,570)", "min": 0, "max": 12570, "rate": 0.00},
    {"label": "Starter rate (£12,571 – £14,876)", "min": 12570, "max": 14876, "rate": 0.19},
    {"label": "Basic rate (£14,877 – £26,561)", "min": 14876, "max": 26561, "rate": 0.20},
    {"label": "Intermediate rate (£26,562 – £43,662)", "min": 26561, "max": 43662, "rate": 0.21},
    {"label": "Higher rate (£43,663 – £75,000)", "min": 43662, "max": 75000, "rate": 0.42},
    {"label": "Advanced rate (£75,001 – £125,140)", "min": 75000, "max": 125140, "rate": 0.45},
    {"label": "Top rate (Above £125,140)", "min": 125140, "max": None, "rate": 0.48},
]


class UKTaxProvider(BaseJurisdictionProvider):
    """United Kingdom Income Tax Provider (England, Wales, NI, Scotland) for Tax Year 2026–27."""

    @property
    def jurisdiction_code(self) -> str:
        return "GB"

    @property
    def country_name(self) -> str:
        return "United Kingdom"

    @property
    def default_currency(self) -> str:
        return "GBP"

    @property
    def currency_symbol(self) -> str:
        return "£"

    @property
    def supported_years(self) -> List[str]:
        return ["2026-27", "2026", "AY2026-27"]

    def get_jurisdiction_info(self) -> JurisdictionInfo:
        return JurisdictionInfo(
            id="GB",
            name="United Kingdom",
            supported_years=["2026–27"],
            currency="GBP",
            currency_symbol="£",
            source="HM Revenue & Customs (HMRC)",
            source_url="https://www.gov.uk/income-tax-rates",
            filing_statuses=None,
            regions=["england", "wales", "northern_ireland", "scotland"],
        )

    def get_rule_metadata(self, tax_year: str) -> TaxRuleMetadata:
        return TaxRuleMetadata(
            jurisdiction="GB",
            country="United Kingdom",
            tax_year="2026–27",
            rule_version="GB-2026-27-v1",
            currency="GBP",
            currency_symbol="£",
            source="HM Revenue & Customs (HMRC) & Scottish Government",
            source_url="https://www.gov.uk/income-tax-rates",
            last_verified="2026-03-01",
            disclaimer=(
                "UK Income Tax — Tax Year 2026–27 calculations reflect official HMRC rates and Personal Allowance taper logic. "
                "Scottish tax rates apply when Scotland is explicitly selected. "
                "Calculations are estimates for analytical purposes and do not constitute professional tax advice."
            ),
            brackets=[
                {
                    "label": b["label"],
                    "min": b["min"],
                    "max": b["max"],
                    "rate_percent": b["rate"] * 100,
                }
                for b in RUK_BRACKETS_2026_27
            ],
            options={
                "personal_allowance": 12570,
                "taper_threshold": 100000,
                "regions": ["england", "wales", "northern_ireland", "scotland"],
            },
        )

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResponse:
        region = (request.region or "england").lower()
        is_scotland = region == "scotland"

        gross_income = request.gross_income if request.gross_income is not None else request.taxable_income

        # Personal Allowance Tapering:
        # Reduce Personal Allowance by £1 for every £2 of income above £100,000
        base_allowance = 12570.0
        if gross_income > 100000.0:
            excess = gross_income - 100000.0
            reduction = min(base_allowance, excess / 2.0)
            effective_allowance = max(0.0, base_allowance - reduction)
        else:
            effective_allowance = base_allowance

        eval_taxable = max(0.0, gross_income - effective_allowance - request.deductions)

        # Select bracket structure
        # When evaluating against taxable income after tapered allowance:
        if is_scotland:
            # Scottish Bands (amounts above effective allowance)
            scottish_taxable_bands = [
                {"label": "Starter rate (19%)", "min": 0, "max": 2306, "rate": 0.19},
                {"label": "Basic rate (20%)", "min": 2306, "max": 13991, "rate": 0.20},
                {"label": "Intermediate rate (21%)", "min": 13991, "max": 31092, "rate": 0.21},
                {"label": "Higher rate (42%)", "min": 31092, "max": 62430, "rate": 0.42},
                {"label": "Advanced rate (45%)", "min": 62430, "max": 125140, "rate": 0.45},
                {"label": "Top rate (48%)", "min": 125140, "max": None, "rate": 0.48},
            ]
            bands = scottish_taxable_bands
            display_title = "UK — Scotland Income Tax"
        else:
            # England / Wales / NI Bands (amounts above effective allowance)
            ruk_taxable_bands = [
                {"label": "Basic rate (20%)", "min": 0, "max": 37700, "rate": 0.20},
                {"label": "Higher rate (40%)", "min": 37700, "max": 125140, "rate": 0.40},
                {"label": "Additional rate (45%)", "min": 125140, "max": None, "rate": 0.45},
            ]
            bands = ruk_taxable_bands
            display_title = "UK Income Tax — Tax Year 2026–27"

        breakdown: List[TaxBracketBreakdown] = []

        # Add Personal Allowance row in breakdown for transparency
        breakdown.append(
            TaxBracketBreakdown(
                bracket_label=f"Personal Allowance (£0 – £{effective_allowance:,.0f})",
                min_income=0.0,
                max_income=effective_allowance,
                taxable_amount_in_bracket=min(gross_income, effective_allowance),
                rate=0.0,
                tax_amount=0.0,
            )
        )

        tax_before_reliefs = 0.0
        marginal_rate = 0.0

        for b in bands:
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
        effective_rate = round((estimated_tax / gross_income * 100.0) if gross_income > 0 else 0.0, 2)

        return TaxCalculationResponse(
            jurisdiction="GB",
            country=display_title,
            tax_year="2026–27",
            currency="GBP",
            currency_symbol="£",
            taxable_income=round(eval_taxable, 2),
            gross_income=round(gross_income, 2),
            allowances_and_deductions=round(effective_allowance + request.deductions, 2),
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
                "region": region,
                "display_title": display_title,
                "personal_allowance_applied": round(effective_allowance, 2),
                "personal_allowance_tapered": effective_allowance < base_allowance,
            },
            rule_version="GB-2026-27-v1",
            source="HM Revenue & Customs (HMRC) & Scottish Government",
            source_url="https://www.gov.uk/income-tax-rates",
            last_verified="2026-03-01",
            disclaimer=(
                "UK Income Tax calculations reflect official HMRC / Scottish Government rates for 2026–27. "
                "National Insurance contributions, student loan repayments, and pension relief are not included. "
                "Calculations are for analytical purposes and do not constitute tax or legal advice."
            ),
        )
