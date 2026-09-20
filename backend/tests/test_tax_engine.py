"""
Unit tests for GraphFin Tax Engine & Jurisdiction Providers.
"""
import pytest
from backend.app.services.tax.engine import tax_engine
from backend.app.services.tax.models import TaxCalculationRequest
from backend.app.services.tax.registry import tax_registry


def test_jurisdictions_list():
    """Verify that all 5 required jurisdictions are listed."""
    jurisdictions = tax_engine.list_jurisdictions()
    codes = [j.id for j in jurisdictions]
    assert "IN" in codes
    assert "US" in codes
    assert "GB" in codes
    assert "DE" in codes
    assert "FR" in codes


# ==========================================
# INDIA AY 2026-27 TESTS
# ==========================================

def test_india_zero_income():
    req = TaxCalculationRequest(
        jurisdiction="IN",
        tax_year="AY2026-27",
        taxable_income=0,
    )
    res = tax_engine.calculate_tax(req)
    assert res.estimated_tax == 0.0
    assert res.effective_tax_rate == 0.0
    assert res.currency == "INR"
    assert res.currency_symbol == "₹"


def test_india_below_first_threshold():
    # Below ₹4,00,000
    req = TaxCalculationRequest(
        jurisdiction="IN",
        tax_year="AY2026-27",
        taxable_income=350000,
    )
    res = tax_engine.calculate_tax(req)
    assert res.estimated_tax == 0.0
    assert res.tax_before_reliefs == 0.0


def test_india_exactly_at_threshold():
    # Exactly ₹4,00,000
    req = TaxCalculationRequest(
        jurisdiction="IN",
        tax_year="AY2026-27",
        taxable_income=400000,
    )
    res = tax_engine.calculate_tax(req)
    assert res.estimated_tax == 0.0


def test_india_sec_87a_rebate():
    # ₹12,00,000 taxable income -> Tax before rebate: 5% of 4L (20k) + 10% of 4L (40k) = ₹60,000.
    # Sec 87A rebate = ₹60,000 => Net estimated tax = 0.0!
    req = TaxCalculationRequest(
        jurisdiction="IN",
        tax_year="AY2026-27",
        taxable_income=1200000,
    )
    res = tax_engine.calculate_tax(req)
    assert res.tax_before_reliefs == 60000.0
    assert res.reliefs == 60000.0
    assert res.tax_after_reliefs == 0.0
    assert res.estimated_tax == 0.0


def test_india_middle_bracket():
    # ₹15,00,000 taxable income
    # Up to 4L: 0
    # 4L-8L (4L @ 5%): 20,000
    # 8L-12L (4L @ 10%): 40,000
    # 12L-15L (3L @ 15%): 45,000
    # Total tax before rebate = 1,05,000
    # Rebate (income > 12.75L) = 0
    # Cess 4% = 4,200
    # Estimated tax = 1,09,200
    req = TaxCalculationRequest(
        jurisdiction="IN",
        tax_year="AY2026-27",
        taxable_income=1500000,
    )
    res = tax_engine.calculate_tax(req)
    assert res.tax_before_reliefs == 105000.0
    assert res.cess_or_additional_tax == 4200.0
    assert res.estimated_tax == 109200.0
    assert res.marginal_tax_rate == 15.0


def test_india_highest_bracket_and_surcharge():
    # ₹60,00,000 taxable income (triggers 10% surcharge)
    req = TaxCalculationRequest(
        jurisdiction="IN",
        tax_year="AY2026-27",
        taxable_income=6000000,
    )
    res = tax_engine.calculate_tax(req)
    assert res.surcharge > 0
    assert res.marginal_tax_rate == 30.0


# ==========================================
# US TAX YEAR 2026 TESTS
# ==========================================

def test_us_single_filing_status():
    # Gross $100,000 single
    # Standard deduction: $16,100 -> Taxable: $83,900
    # 0 - 12,400 @ 10% = 1,240
    # 12,400 - 50,400 @ 12% = 4,560
    # 50,400 - 83,900 (33,500 @ 22%) = 7,370
    # Base tax = 13,170
    req = TaxCalculationRequest(
        jurisdiction="US",
        tax_year="2026",
        gross_income=100000,
        filing_status="single",
    )
    res = tax_engine.calculate_tax(req)
    assert res.allowances_and_deductions == 16100.0
    assert res.taxable_income == 83900.0
    assert res.tax_before_reliefs == 13170.0
    assert res.estimated_tax == 13170.0
    assert res.extra_details["state_tax"] == "Not calculated"


def test_us_married_joint_filing_status():
    # Gross $100,000 married joint
    # Standard deduction: $32,200 -> Taxable: $67,800
    req = TaxCalculationRequest(
        jurisdiction="US",
        tax_year="2026",
        gross_income=100000,
        filing_status="married_joint",
    )
    res = tax_engine.calculate_tax(req)
    assert res.allowances_and_deductions == 32200.0
    assert res.taxable_income == 67800.0
    assert res.estimated_tax < 13170.0  # Lower than single filing tax


def test_us_head_of_household():
    req = TaxCalculationRequest(
        jurisdiction="US",
        tax_year="2026",
        gross_income=100000,
        filing_status="head_of_household",
    )
    res = tax_engine.calculate_tax(req)
    assert res.allowances_and_deductions == 24150.0


# ==========================================
# UK & SCOTLAND TAX YEAR 2026-27 TESTS
# ==========================================

def test_uk_england_basic_and_higher_rate():
    # Gross £80,000 (England)
    # Personal allowance: £12,570 -> Taxable: £67,430
    # Basic rate (£0 - £37,700 @ 20%) = £7,540
    # Higher rate (£37,700 - £67,430 @ 40%) = £11,892
    # Total tax = £19,432
    req = TaxCalculationRequest(
        jurisdiction="GB",
        tax_year="2026-27",
        gross_income=80000,
        region="england",
    )
    res = tax_engine.calculate_tax(req)
    assert res.taxable_income == 67430.0
    assert res.estimated_tax == 19432.0


def test_uk_scotland_bands():
    # Gross £80,000 (Scotland)
    req = TaxCalculationRequest(
        jurisdiction="GB",
        tax_year="2026-27",
        gross_income=80000,
        region="scotland",
    )
    res = tax_engine.calculate_tax(req)
    assert res.country == "UK — Scotland Income Tax"
    assert res.estimated_tax != 19432.0  # Scottish bands differ from rUK


def test_uk_personal_allowance_tapering():
    # Gross £115,000
    # Excess over £100,000 = £15,000. Taper reduction = £7,500.
    # Effective Personal Allowance = £12,570 - £7,500 = £5,070.
    req = TaxCalculationRequest(
        jurisdiction="GB",
        tax_year="2026-27",
        gross_income=115000,
        region="england",
    )
    res = tax_engine.calculate_tax(req)
    assert res.extra_details["personal_allowance_applied"] == 5070.0
    assert res.extra_details["personal_allowance_tapered"] is True


# ==========================================
# GERMANY TAX YEAR 2026 TESTS
# ==========================================

def test_germany_grundfreibetrag():
    # €10,000 income (below €12,096 Grundfreibetrag)
    req = TaxCalculationRequest(
        jurisdiction="DE",
        tax_year="2026",
        taxable_income=10000,
    )
    res = tax_engine.calculate_tax(req)
    assert res.estimated_tax == 0.0


def test_germany_with_church_tax():
    req = TaxCalculationRequest(
        jurisdiction="DE",
        tax_year="2026",
        taxable_income=50000,
        church_tax=True,
    )
    res = tax_engine.calculate_tax(req)
    assert res.church_tax > 0.0
    assert res.extra_details["church_tax_selected"] is True


# ==========================================
# FRANCE TAX YEAR 2026 TESTS
# ==========================================

def test_france_progressive_brackets():
    # €60,000 taxable income, parts = 1
    req = TaxCalculationRequest(
        jurisdiction="FR",
        tax_year="2026",
        taxable_income=60000,
        parts=1.0,
    )
    res = tax_engine.calculate_tax(req)
    assert res.estimated_tax > 0.0
    assert res.currency == "EUR"


def test_france_quotient_familial():
    # €60,000 taxable income, parts = 2 -> lower tax per part
    req1 = TaxCalculationRequest(jurisdiction="FR", tax_year="2026", taxable_income=60000, parts=1.0)
    req2 = TaxCalculationRequest(jurisdiction="FR", tax_year="2026", taxable_income=60000, parts=2.0)
    
    res1 = tax_engine.calculate_tax(req1)
    res2 = tax_engine.calculate_tax(req2)
    assert res2.estimated_tax < res1.estimated_tax


# ==========================================
# EDGE CASES AND UNSUPPORTED ERROR TESTS
# ==========================================

def test_unsupported_jurisdiction():
    req = TaxCalculationRequest(
        jurisdiction="INVALID_COUNTRY",
        tax_year="2026",
        taxable_income=50000,
    )
    with pytest.raises(ValueError) as exc:
        tax_engine.calculate_tax(req)
    assert "Unsupported jurisdiction" in str(exc.value)


def test_unsupported_tax_year():
    req = TaxCalculationRequest(
        jurisdiction="IN",
        tax_year="1999",
        taxable_income=50000,
    )
    with pytest.raises(ValueError) as exc:
        tax_engine.calculate_tax(req)
    assert "Tax rule unavailable for selected year" in str(exc.value)
