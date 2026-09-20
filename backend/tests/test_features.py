"""
Tests for behavioral, temporal, and fused graph feature extraction.
"""
from fastapi.testclient import TestClient


def test_user_analytics_extraction(client: TestClient, valid_csv_bytes: bytes):
    """Uploading transactions should compute behavioral and temporal features for the dataset."""
    files = {"file": ("transactions.csv", valid_csv_bytes, "text/csv")}
    upload_resp = client.post("/api/v1/transactions/upload", files=files)
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]

    response = client.get(f"/api/v1/analytics/{dataset_id}/users")
    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] == 3

    # Find USER_A
    user_a = next((u for u in data["users"] if u["user_id"] == "USER_A"), None)
    assert user_a is not None

    # Behavioral checks
    assert user_a["transaction_count"] == 3
    assert user_a["total_sent"] == 175.50
    assert user_a["total_received"] == 25.00
    assert user_a["net_flow"] == -150.50
    assert user_a["unique_receivers"] == 2  # USER_B, USER_C
    assert user_a["unique_senders"] == 1    # USER_C
    assert user_a["maximum_transaction_amount"] == 100.50

    # Temporal checks
    assert user_a["average_time_between_transactions"] > 0
    assert user_a["minimum_time_between_transactions"] > 0
    assert user_a["transactions_per_day"] > 0
    assert user_a["transactions_per_week"] > 0

    # Structural checks
    assert user_a["in_degree"] == 1
    assert user_a["out_degree"] == 2

    # ML Vector check
    assert user_a["feature_vector"] is not None
    assert len(user_a["feature_vector"]) == 19


def test_single_user_analytics(client: TestClient, valid_csv_bytes: bytes):
    """Single user detail endpoint works and returns 404 for unknown users in a dataset."""
    files = {"file": ("transactions.csv", valid_csv_bytes, "text/csv")}
    upload_resp = client.post("/api/v1/transactions/upload", files=files)
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]

    resp_found = client.get(f"/api/v1/analytics/{dataset_id}/users/USER_B")
    assert resp_found.status_code == 200
    assert resp_found.json()["user_id"] == "USER_B"

    resp_not_found = client.get(f"/api/v1/analytics/{dataset_id}/users/UNKNOWN_USER")
    assert resp_not_found.status_code == 404


def test_feature_schema_endpoint(client: TestClient):
    """Schema endpoint exposes ordered feature vector columns for ML integration (global)."""
    response = client.get("/api/v1/analytics/features/schema")
    assert response.status_code == 200
    data = response.json()
    assert data["feature_count"] == 19
    assert "in_degree" in data["features"]
    assert "betweenness_centrality" in data["features"]
    assert "total_sent" in data["features"]
    assert "average_time_between_transactions" in data["features"]
