"""
Tax Analytics API Routes.
Provides endpoints for tax estimation, jurisdiction metadata, and tax rule inspection.
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
from ...services.tax.engine import tax_engine
from ...services.tax.models import (
    TaxCalculationRequest,
    TaxCalculationResponse,
    JurisdictionInfo,
    TaxRuleMetadata,
)

router = APIRouter(prefix="/tax", tags=["tax"])


@router.post(
    "/calculate",
    response_model=TaxCalculationResponse,
    summary="Calculate estimated income tax liability for specified jurisdiction and tax year",
    description=(
        "Calculates progressive income tax liability for India (AY 2026-27), United States (2026), "
        "United Kingdom (2026-27), Germany (2026), and France (2026). "
        "Does NOT infer taxable income from transaction volume. Requires explicit taxable income or gross income inputs."
    ),
)
def calculate_tax(request: TaxCalculationRequest) -> TaxCalculationResponse:
    try:
        return tax_engine.calculate_tax(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during tax calculation: {str(e)}",
        )


@router.get(
    "/jurisdictions",
    response_model=List[JurisdictionInfo],
    summary="List all supported tax jurisdictions",
)
def get_jurisdictions() -> List[JurisdictionInfo]:
    return tax_engine.list_jurisdictions()


@router.get(
    "/rules/{jurisdiction}/{tax_year}",
    response_model=TaxRuleMetadata,
    summary="Retrieve official tax rule metadata and bracket definition",
)
def get_tax_rules(jurisdiction: str, tax_year: str) -> TaxRuleMetadata:
    try:
        return tax_engine.get_rule_metadata(jurisdiction, tax_year)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tax rules: {str(e)}",
        )
