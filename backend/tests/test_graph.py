"""
Tests for NetworkX graph construction and structural metrics.
"""
from fastapi.testclient import TestClient


def test_graph_construction_and_summary(client: TestClient, valid_csv_bytes: bytes):
    """Uploading transactions constructs the directed weighted NetworkX graph for the dataset."""
    files = {"file": ("transactions.csv", valid_csv_bytes, "text/csv")}
    upload_resp = client.post("/api/v1/transactions/upload", files=files)
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]

    response = client.get(f"/api/v1/graph/{dataset_id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["nodes"] == 3
    assert data["edges"] == 4
    assert data["density"] > 0.0
    assert data["is_directed"] is True
    assert len(data["top_in_degree_nodes"]) > 0
    assert len(data["top_out_degree_nodes"]) > 0


def test_node_structural_metrics(client: TestClient, valid_csv_bytes: bytes):
    """Check structural metrics for a specific node in a dataset."""
    files = {"file": ("transactions.csv", valid_csv_bytes, "text/csv")}
    upload_resp = client.post("/api/v1/transactions/upload", files=files)
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]

    response = client.get(f"/api/v1/graph/{dataset_id}/nodes/USER_A")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "USER_A"
    # USER_A sent to B and C -> out_degree = 2
    assert data["out_degree"] == 2
    # USER_A received from C -> in_degree = 1
    assert data["in_degree"] == 1
    # USER_A weighted out = 100.50 + 75.0 = 175.50
    assert data["weighted_out_degree"] == 175.50
    # USER_A weighted in = 25.0
    assert data["weighted_in_degree"] == 25.0
    assert "betweenness_centrality" in data


def test_nonexistent_node_metrics(client: TestClient, valid_csv_bytes: bytes):
    """Querying metrics for an unknown node in a dataset returns 404."""
    files = {"file": ("transactions.csv", valid_csv_bytes, "text/csv")}
    upload_resp = client.post("/api/v1/transactions/upload", files=files)
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]

    response = client.get(f"/api/v1/graph/{dataset_id}/nodes/NON_EXISTENT_USER")
    assert response.status_code == 404
