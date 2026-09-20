"""
Integration tests for Tax Analytics API Endpoints.
"""
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_jurisdictions_endpoint():
    response = client.get("/api/v1/tax/jurisdictions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    codes = [j["id"] for j in data]
    assert "IN" in codes
    assert "US" in codes
    assert "GB" in codes
    assert "DE" in codes
    assert "FR" in codes


def test_get_tax_rules_endpoint():
    response = client.get("/api/v1/tax/rules/IN/AY2026-27")
    assert response.status_code == 200
    data = response.json()
    assert data["jurisdiction"] == "IN"
    assert data["rule_version"] == "IN-AY2026-27-v1"
    assert len(data["brackets"]) > 0


def test_calculate_tax_endpoint_india():
    payload = {
        "jurisdiction": "IN",
        "tax_year": "AY2026-27",
        "taxable_income": 1500000,
        "currency": "INR",
    }
    response = client.post("/api/v1/tax/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["jurisdiction"] == "IN"
    assert data["currency"] == "INR"
    assert data["taxable_income"] == 1500000
    assert data["estimated_tax"] == 109200.0


def test_calculate_tax_endpoint_us():
    payload = {
        "jurisdiction": "US",
        "tax_year": "2026",
        "taxable_income": 100000,
        "filing_status": "single",
    }
    response = client.post("/api/v1/tax/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["jurisdiction"] == "US"
    assert data["currency"] == "USD"
    assert data["estimated_tax"] > 0


def test_calculate_tax_endpoint_unsupported_jurisdiction():
    payload = {
        "jurisdiction": "XX",
        "tax_year": "2026",
        "taxable_income": 100000,
    }
    response = client.post("/api/v1/tax/calculate", json=payload)
    assert response.status_code == 400
    assert "Unsupported jurisdiction" in response.json()["detail"]


def test_calculate_tax_endpoint_unsupported_year():
    payload = {
        "jurisdiction": "IN",
        "tax_year": "1980",
        "taxable_income": 100000,
    }
    response = client.post("/api/v1/tax/calculate", json=payload)
    assert response.status_code == 400
    assert "Tax rule unavailable" in response.json()["detail"]
