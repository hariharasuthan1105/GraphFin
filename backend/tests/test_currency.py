"""
Tests for dataset-level currency support.

Covers:
  (a) Omitting currency defaults to USD — all pre-existing test assertions unchanged.
  (b) Providing currency="INR" at upload is stored and returned correctly
      in upload response, /summary, and /status.
  (c) Currency field never affects any computed feature value, graph metric,
      or anomaly score — only its label changes.
"""
import pytest
from fastapi.testclient import TestClient


# ── Shared fixture ────────────────────────────────────────────────────────────
MINIMAL_CSV = (
    "transaction_id,sender_id,receiver_id,amount,timestamp\n"
    "TX_1,USER_A,USER_B,10000.00,2026-01-01 10:00:00\n"
    "TX_2,USER_B,USER_C,5000.00,2026-01-01 11:00:00\n"
    "TX_3,USER_A,USER_C,2500.00,2026-01-01 12:00:00\n"
).encode("utf-8")


def _upload(client: TestClient, currency: str | None = None) -> dict:
    """Helper: upload MINIMAL_CSV with optional currency param."""
    url = "/api/v1/transactions/upload"
    if currency is not None:
        url += f"?currency={currency}"
    resp = client.post(url, files={"file": ("tx.csv", MINIMAL_CSV, "text/csv")})
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── (a) Default USD behaviour ─────────────────────────────────────────────────
class TestCurrencyDefault:
    def test_upload_without_currency_defaults_to_usd(self, client: TestClient):
        """Omitting currency must default to USD — backward compat guarantee."""
        data = _upload(client)
        assert data["currency"] == "USD"
        assert data["summary"]["currency"] == "USD"

    def test_status_without_currency_defaults_to_usd(self, client: TestClient):
        data = _upload(client)
        dataset_id = data["dataset_id"]
        status_resp = client.get(f"/api/v1/transactions/{dataset_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["currency"] == "USD"

    def test_summary_without_currency_defaults_to_usd(self, client: TestClient):
        data = _upload(client)
        dataset_id = data["dataset_id"]
        summary_resp = client.get(f"/api/v1/transactions/{dataset_id}/summary")
        assert summary_resp.status_code == 200
        assert summary_resp.json()["currency"] == "USD"

    def test_existing_field_assertions_still_pass(self, client: TestClient):
        """All pre-existing response fields remain unchanged."""
        data = _upload(client)
        assert data["status"] == "complete"
        assert data["valid_transactions"] == 3
        assert data["invalid_rows_count"] == 0
        assert data["summary"]["transactions"] == 3
        # Total: 10000 + 5000 + 2500 = 17500
        assert data["summary"]["total_amount"] == 17500.00


# ── (b) INR roundtrip ─────────────────────────────────────────────────────────
class TestCurrencyINR:
    def test_upload_with_inr_stored_in_upload_response(self, client: TestClient):
        data = _upload(client, currency="INR")
        assert data["currency"] == "INR"

    def test_inr_returned_in_summary_endpoint(self, client: TestClient):
        data = _upload(client, currency="INR")
        dataset_id = data["dataset_id"]
        summary_resp = client.get(f"/api/v1/transactions/{dataset_id}/summary")
        assert summary_resp.status_code == 200
        assert summary_resp.json()["currency"] == "INR"

    def test_inr_returned_in_status_endpoint(self, client: TestClient):
        data = _upload(client, currency="INR")
        dataset_id = data["dataset_id"]
        status_resp = client.get(f"/api/v1/transactions/{dataset_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["currency"] == "INR"

    def test_lowercase_inr_normalised(self, client: TestClient):
        """Currency code should be normalised to uppercase."""
        data = _upload(client, currency="inr")
        assert data["currency"] == "INR"

    def test_inr_stored_in_summary_response_nested(self, client: TestClient):
        """Upload response summary sub-object must also reflect the currency."""
        data = _upload(client, currency="INR")
        assert data["summary"]["currency"] == "INR"


# ── (c) Currency label does NOT affect computed values ────────────────────────
class TestCurrencyIsolation:
    """
    Upload the IDENTICAL csv twice: once as USD, once as INR.
    Every numeric field (amounts, graph metrics, feature values) must be identical.
    Only the currency label differs.
    """

    def test_amounts_identical_regardless_of_currency(self, client: TestClient):
        usd_data = _upload(client, currency="USD")
        inr_data = _upload(client, currency="INR")

        # Summary amounts: identical
        assert usd_data["summary"]["total_amount"] == inr_data["summary"]["total_amount"]
        assert usd_data["summary"]["average_amount"] == inr_data["summary"]["average_amount"]
        assert usd_data["summary"]["min_amount"] == inr_data["summary"]["min_amount"]
        assert usd_data["summary"]["max_amount"] == inr_data["summary"]["max_amount"]
        assert usd_data["summary"]["transactions"] == inr_data["summary"]["transactions"]
        assert usd_data["summary"]["users"] == inr_data["summary"]["users"]

        # Only the label differs
        assert usd_data["currency"] == "USD"
        assert inr_data["currency"] == "INR"

    def test_graph_metrics_identical_regardless_of_currency(self, client: TestClient):
        usd_data = _upload(client, currency="USD")
        inr_data = _upload(client, currency="INR")

        usd_graph = client.get(f"/api/v1/graph/{usd_data['dataset_id']}/summary").json()
        inr_graph = client.get(f"/api/v1/graph/{inr_data['dataset_id']}/summary").json()

        assert usd_graph["nodes"] == inr_graph["nodes"]
        assert usd_graph["edges"] == inr_graph["edges"]
        assert abs(usd_graph["density"] - inr_graph["density"]) < 1e-10

    def test_user_feature_values_identical_regardless_of_currency(self, client: TestClient):
        usd_data = _upload(client, currency="USD")
        inr_data = _upload(client, currency="INR")

        usd_analytics = client.get(
            f"/api/v1/analytics/{usd_data['dataset_id']}/users?limit=100"
        ).json()
        inr_analytics = client.get(
            f"/api/v1/analytics/{inr_data['dataset_id']}/users?limit=100"
        ).json()

        # Same entity count
        assert usd_analytics["total_users"] == inr_analytics["total_users"]

        # Build maps by user_id for comparison
        usd_by_id = {u["user_id"]: u for u in usd_analytics["users"]}
        inr_by_id = {u["user_id"]: u for u in inr_analytics["users"]}

        monetary_fields = [
            "total_sent", "total_received", "net_flow",
            "average_transaction_amount", "maximum_transaction_amount",
            "weighted_in_degree", "weighted_out_degree",
        ]
        for uid in usd_by_id:
            usd_user = usd_by_id[uid]
            inr_user = inr_by_id.get(uid)
            assert inr_user is not None, f"User {uid} missing from INR dataset"
            for field in monetary_fields:
                usd_val = usd_user.get(field, 0)
                inr_val = inr_user.get(field, 0)
                assert abs(usd_val - inr_val) < 1e-6, (
                    f"Feature '{field}' for user '{uid}' differs between USD and INR datasets: "
                    f"USD={usd_val}, INR={inr_val}"
                )

    def test_two_datasets_with_different_currencies_are_independent(self, client: TestClient):
        """Uploading a second dataset with a different currency doesn't contaminate the first."""
        usd_data = _upload(client, currency="USD")
        inr_data = _upload(client, currency="INR")

        # Verify each dataset still reports its own currency
        usd_summary = client.get(f"/api/v1/transactions/{usd_data['dataset_id']}/summary").json()
        inr_summary = client.get(f"/api/v1/transactions/{inr_data['dataset_id']}/summary").json()

        assert usd_summary["currency"] == "USD"
        assert inr_summary["currency"] == "INR"

    def test_unsupported_currency_falls_back_to_usd(self, client: TestClient):
        """Unknown currency codes are silently normalised to USD."""
        data = _upload(client, currency="XYZ")
        assert data["currency"] == "USD"


# ── EUR and GBP supported ─────────────────────────────────────────────────────
@pytest.mark.parametrize("code", ["EUR", "GBP"])
def test_supported_currencies_roundtrip(client: TestClient, code: str):
    data = _upload(client, currency=code)
    assert data["currency"] == code
    summary_resp = client.get(f"/api/v1/transactions/{data['dataset_id']}/summary")
    assert summary_resp.json()["currency"] == code
