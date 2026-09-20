"""
Tests for transaction upload, status, and dataset-scoped summary endpoints.
"""
import uuid
from fastapi.testclient import TestClient


def test_valid_csv_upload(client: TestClient, valid_csv_bytes: bytes):
    """Uploading a valid CSV should succeed, return dataset_id, and populate state."""
    files = {"file": ("transactions.csv", valid_csv_bytes, "text/csv")}
    response = client.post("/api/v1/transactions/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "dataset_id" in data
    dataset_id = data["dataset_id"]
    assert data["status"] == "complete"
    assert data["valid_transactions"] == 4
    assert data["invalid_rows_count"] == 0
    assert data["summary"]["transactions"] == 4
    assert data["summary"]["users"] == 3  # USER_A, USER_B, USER_C
    assert data["summary"]["total_amount"] == 250.75

    # Check that GET /transactions/{dataset_id}/summary reflects uploaded data
    summary_resp = client.get(f"/api/v1/transactions/{dataset_id}/summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["transactions"] == 4
    assert summary_resp.json()["total_amount"] == 250.75


def test_empty_csv_upload(client: TestClient, empty_csv_bytes: bytes):
    """Uploading an empty file should return 400 error."""
    files = {"file": ("empty.csv", empty_csv_bytes, "text/csv")}
    response = client.post("/api/v1/transactions/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "INVALID_TRANSACTION_DATA"
    assert "empty" in data["message"].lower()


def test_missing_columns_csv_upload(client: TestClient, missing_columns_csv_bytes: bytes):
    """Missing mandatory canonical headers should return 400 error."""
    files = {"file": ("missing.csv", missing_columns_csv_bytes, "text/csv")}
    response = client.post("/api/v1/transactions/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "INVALID_TRANSACTION_DATA"
    assert "Missing mandatory columns" in data["message"]


def test_invalid_amount_upload_strict_mode(client: TestClient, invalid_amount_csv_bytes: bytes):
    """Negative amount in strict mode should raise ValidationException."""
    files = {"file": ("bad_amount.csv", invalid_amount_csv_bytes, "text/csv")}
    response = client.post("/api/v1/transactions/upload?strict_mode=true", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "INVALID_TRANSACTION_DATA"
    assert "Amount must be greater than zero" in data["message"]


def test_duplicate_transaction_id_rejected(client: TestClient, duplicate_id_csv_bytes: bytes):
    """Duplicate transaction ID in dataset is caught and rejected."""
    files = {"file": ("duplicate.csv", duplicate_id_csv_bytes, "text/csv")}
    response = client.post("/api/v1/transactions/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    # One row is valid, one is rejected due to duplicate ID
    assert data["valid_transactions"] == 1
    assert data["invalid_rows_count"] == 1
    assert any("Duplicate transaction_id" in err for err in data["validation_errors"])


def test_self_transfer_rejected(client: TestClient, self_transfer_csv_bytes: bytes):
    """Self transfers (sender == receiver) are rejected."""
    files = {"file": ("self_transfer.csv", self_transfer_csv_bytes, "text/csv")}
    response = client.post("/api/v1/transactions/upload", files=files)
    # All rows fail so 400 is returned
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "INVALID_TRANSACTION_DATA"


def test_multiple_datasets_are_isolated(
    client: TestClient, valid_csv_bytes: bytes, second_valid_csv_bytes: bytes
):
    """Upload two different CSVs, confirm dataset_ids differ, and summaries reflect only their own data."""
    # Upload first dataset
    resp1 = client.post(
        "/api/v1/transactions/upload",
        files={"file": ("dataset1.csv", valid_csv_bytes, "text/csv")},
    )
    assert resp1.status_code == 200
    id1 = resp1.json()["dataset_id"]

    # Upload second dataset
    resp2 = client.post(
        "/api/v1/transactions/upload",
        files={"file": ("dataset2.csv", second_valid_csv_bytes, "text/csv")},
    )
    assert resp2.status_code == 200
    id2 = resp2.json()["dataset_id"]

    assert id1 != id2

    # Query summary for first dataset
    sum1 = client.get(f"/api/v1/transactions/{id1}/summary")
    assert sum1.status_code == 200
    assert sum1.json()["transactions"] == 4
    assert sum1.json()["total_amount"] == 250.75

    # Query summary for second dataset
    sum2 = client.get(f"/api/v1/transactions/{id2}/summary")
    assert sum2.status_code == 200
    assert sum2.json()["transactions"] == 1
    assert sum2.json()["total_amount"] == 999.00


def test_dataset_not_found(client: TestClient):
    """Calling summary, graph, or analytics with an unknown dataset_id returns 404."""
    bad_id = str(uuid.uuid4())

    resp_tx = client.get(f"/api/v1/transactions/{bad_id}/summary")
    assert resp_tx.status_code == 404
    assert f"Dataset '{bad_id}' not found" in resp_tx.json()["message"]

    resp_graph = client.get(f"/api/v1/graph/{bad_id}/summary")
    assert resp_graph.status_code == 404
    assert f"Dataset '{bad_id}' not found" in resp_graph.json()["message"]

    resp_analytics = client.get(f"/api/v1/analytics/{bad_id}/users")
    assert resp_analytics.status_code == 404
    assert f"Dataset '{bad_id}' not found" in resp_analytics.json()["message"]


def test_dataset_status_endpoint(client: TestClient, valid_csv_bytes: bytes):
    """Status endpoint returns 'complete' for valid dataset and 404 for bad id."""
    # Valid dataset
    resp = client.post(
        "/api/v1/transactions/upload",
        files={"file": ("transactions.csv", valid_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    dataset_id = resp.json()["dataset_id"]

    status_resp = client.get(f"/api/v1/transactions/{dataset_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["dataset_id"] == dataset_id
    assert status_data["status"] == "complete"

    # Bad dataset ID
    bad_id = str(uuid.uuid4())
    bad_status_resp = client.get(f"/api/v1/transactions/{bad_id}/status")
    assert bad_status_resp.status_code == 404


def test_soft_duplicate_warning(client: TestClient, soft_duplicate_csv_bytes: bytes):
    """
    Two rows with identical (sender_id, receiver_id, amount, timestamp) but different
    transaction_id are kept as valid transactions AND generate a duplicate warning.
    """
    resp = client.post(
        "/api/v1/transactions/upload",
        files={"file": ("soft_dup.csv", soft_duplicate_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid_transactions"] == 2
    assert data["invalid_rows_count"] == 0
    assert len(data["duplicate_warnings"]) == 1
    assert "duplicates the (sender, receiver, amount, timestamp)" in data["duplicate_warnings"][0]
    assert "Row 3 duplicates" in data["duplicate_warnings"][0]


