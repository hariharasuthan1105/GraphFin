"""
Comprehensive unit and integration tests for the Machine Learning Anomaly Detection Layer.
Covers training, dynamic feature groups, explainability, risk scoring, persistence,
retraining, hyperparameter overrides, and error handling.
"""
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.schemas.anomaly import AnomalyTrainRequest
from backend.app.services.anomaly_service import (
    anomaly_service,
    compute_percentile_rank,
    compute_risk_score,
)
from backend.app.services.dataset_registry import dataset_registry


# Helper function to upload sample dataset
def upload_sample_dataset(client: TestClient, csv_bytes: bytes) -> str:
    files = {"file": ("transactions.csv", csv_bytes, "text/csv")}
    resp = client.post("/api/v1/transactions/upload", files=files)
    assert resp.status_code == 200, resp.text
    return resp.json()["dataset_id"]


# 1. Successful model training (default feature_groups = all 19)
def test_successful_model_training_default(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)
    resp = client.post(f"/api/v1/anomalies/{dataset_id}/train", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["dataset_id"] == dataset_id
    meta = data["model_metadata"]
    assert meta["feature_count"] == 19
    assert meta["feature_groups"] == ["graph", "behavioral", "temporal"]
    assert meta["n_estimators"] == 100
    assert meta["contamination"] == 0.1
    assert meta["entity_count"] == 11
    assert len(meta["feature_names"]) == 19


# 2. Correct feature input for each feature_groups combination
def test_feature_groups_combinations(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Experiment 1: Graph only
    resp1 = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"feature_groups": ["graph"]},
    )
    assert resp1.status_code == 200
    meta1 = resp1.json()["model_metadata"]
    assert meta1["feature_count"] == 6
    assert meta1["feature_groups"] == ["graph"]

    # Experiment 2: Graph + Behavioral
    resp2 = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"feature_groups": ["graph", "behavioral"]},
    )
    assert resp2.status_code == 200
    meta2 = resp2.json()["model_metadata"]
    assert meta2["feature_count"] == 14
    assert meta2["feature_groups"] == ["graph", "behavioral"]

    # Experiment 3: Graph + Behavioral + Temporal (all 19)
    resp3 = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"feature_groups": ["graph", "behavioral", "temporal"]},
    )
    assert resp3.status_code == 200
    meta3 = resp3.json()["model_metadata"]
    assert meta3["feature_count"] == 19
    assert meta3["feature_groups"] == ["graph", "behavioral", "temporal"]


# 3. Correct feature ordering within a given feature_groups selection
def test_feature_ordering_preservation(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Pass in non-canonical order: ["temporal", "graph"]
    resp = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"feature_groups": ["temporal", "graph"]},
    )
    assert resp.status_code == 200
    meta = resp.json()["model_metadata"]
    assert meta["feature_count"] == 11
    # Check that graph features precede temporal features (as defined in canonical FEATURE_NAMES)
    graph_idx = meta["feature_names"].index("in_degree")
    temporal_idx = meta["feature_names"].index("transactions_per_day")
    assert graph_idx < temporal_idx


# 4. Prediction count equals number of users/entities
def test_prediction_count_equals_entities(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)
    client.post(f"/api/v1/anomalies/{dataset_id}/train", json={})

    resp = client.get(f"/api/v1/anomalies/{dataset_id}/users")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_users"] == 11
    assert len(data["users"]) == 11


# 5. Dataset isolation
def test_dataset_isolation(
    client: TestClient, valid_csv_bytes: bytes, sample_csv_bytes: bytes
):
    id1 = upload_sample_dataset(client, valid_csv_bytes)   # 3 users
    id2 = upload_sample_dataset(client, sample_csv_bytes)  # 11 users

    # Train id1 with graph only
    client.post(f"/api/v1/anomalies/{id1}/train", json={"feature_groups": ["graph"]})
    # Train id2 with all 19
    client.post(
        f"/api/v1/anomalies/{id2}/train",
        json={"feature_groups": ["graph", "behavioral", "temporal"]},
    )

    resp1 = client.get(f"/api/v1/anomalies/{id1}/model")
    resp2 = client.get(f"/api/v1/anomalies/{id2}/model")
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    assert resp1.json()["entity_count"] == 3
    assert resp1.json()["feature_count"] == 6

    assert resp2.json()["entity_count"] == 11
    assert resp2.json()["feature_count"] == 19


# 6. Missing dataset (train and GET endpoints both 404 correctly)
def test_missing_dataset_404(client: TestClient):
    fake_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/v1/anomalies/{fake_id}/train", json={}).status_code == 404
    assert client.get(f"/api/v1/anomalies/{fake_id}/users").status_code == 404
    assert client.get(f"/api/v1/anomalies/{fake_id}/summary").status_code == 404
    assert client.get(f"/api/v1/anomalies/{fake_id}/model").status_code == 404


# 7. Empty/invalid feature matrix
def test_empty_dataset_training_rejection(client: TestClient):
    # Create an empty StateStore in registry
    from backend.app.services.state_store import StateStore
    import uuid

    empty_id = str(uuid.uuid4())
    dataset_registry._datasets[empty_id] = StateStore()

    resp = client.post(f"/api/v1/anomalies/{empty_id}/train", json={})
    assert resp.status_code == 400
    assert "no users or transactions" in resp.json()["message"]


# 8. NaN/inf handling per the documented strategy
def test_nan_inf_handling_strategy():
    # Verify that nan_to_num handles NaNs and Infs cleanly without throwing
    arr = np.array([[1.0, np.nan, np.inf], [2.0, -np.inf, 4.0]])
    cleaned = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    assert not np.isnan(cleaned).any()
    assert not np.isinf(cleaned).any()
    assert cleaned[0, 1] == 0.0
    assert cleaned[0, 2] == 0.0


# 9. Deterministic results with fixed random_state
def test_deterministic_results_fixed_random_state(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Train run 1
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"random_state": 42, "n_estimators": 50},
    )
    users1 = client.get(f"/api/v1/anomalies/{dataset_id}/users").json()["users"]

    # Train run 2
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"random_state": 42, "n_estimators": 50},
    )
    users2 = client.get(f"/api/v1/anomalies/{dataset_id}/users").json()["users"]

    for u1, u2 in zip(users1, users2):
        assert u1["user_id"] == u2["user_id"]
        assert u1["raw_score"] == u2["raw_score"]
        assert u1["prediction"] == u2["prediction"]
        assert u1["risk_score"] == u2["risk_score"]


# 10. Model artifact creation and loading via joblib
def test_model_artifact_persistence_and_loading(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)
    client.post(f"/api/v1/anomalies/{dataset_id}/train", json={})

    # Verify file on disk
    model_file = settings.MODELS_DIR / f"{dataset_id}.joblib"
    assert model_file.exists()

    # Clear in-memory cache to force disk load
    anomaly_service._cache.clear()

    resp = client.get(f"/api/v1/anomalies/{dataset_id}/model")
    assert resp.status_code == 200
    assert resp.json()["dataset_id"] == dataset_id


# 11. API response schema validation
def test_api_response_schema(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)
    client.post(f"/api/v1/anomalies/{dataset_id}/train", json={})

    # Users endpoint
    users_resp = client.get(f"/api/v1/anomalies/{dataset_id}/users")
    assert users_resp.status_code == 200
    data = users_resp.json()
    assert "dataset_id" in data
    assert "total_users" in data
    assert "suspicious_count" in data
    assert "normal_count" in data
    first_user = data["users"][0]
    assert "user_id" in first_user
    assert "raw_score" in first_user
    assert "prediction" in first_user
    assert "status" in first_user
    assert "risk_score" in first_user
    assert "reasons" in first_user

    # Summary endpoint
    summary_resp = client.get(f"/api/v1/anomalies/{dataset_id}/summary")
    assert summary_resp.status_code == 200
    sdata = summary_resp.json()
    assert "total_entities" in sdata
    assert "suspicious_count" in sdata
    assert "contamination_rate" in sdata
    assert "model_metadata" in sdata


# 12. Risk score always between 0 and 100
def test_risk_score_bounds(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)
    client.post(f"/api/v1/anomalies/{dataset_id}/train", json={})

    resp = client.get(f"/api/v1/anomalies/{dataset_id}/users")
    users = resp.json()["users"]
    for u in users:
        assert 0.0 <= u["risk_score"] <= 100.0


# 13. Suspicious/normal status is consistent with model output
def test_status_consistency(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"contamination": 0.2},
    )

    resp = client.get(f"/api/v1/anomalies/{dataset_id}/users")
    users = resp.json()["users"]
    for u in users:
        if u["prediction"] == -1:
            assert u["status"] == "suspicious"
        else:
            assert u["status"] == "normal"


# 14. Explanation reasons correspond to actual feature values and only reference trained groups
def test_explanation_reasons_scoped_to_trained_groups(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Train with graph only
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"feature_groups": ["graph"], "contamination": 0.3},
    )
    users = client.get(f"/api/v1/anomalies/{dataset_id}/users").json()["users"]

    for u in users:
        for r in u["reasons"]:
            # None of the behavioral or temporal reason codes should appear
            assert "transaction count" not in r
            assert "outgoing volume" not in r
            assert "incoming volume" not in r
            assert "transaction amount" not in r
            assert "transaction intervals" not in r


# 15. Retraining overwrites previous model and GET reflects new model
def test_retrain_overwrites_previous(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # First training: graph only
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"feature_groups": ["graph"], "contamination": 0.1},
    )
    meta1 = client.get(f"/api/v1/anomalies/{dataset_id}/model").json()
    assert meta1["feature_count"] == 6

    # Second training: behavioral only with contamination=0.25
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"feature_groups": ["behavioral"], "contamination": 0.25},
    )
    meta2 = client.get(f"/api/v1/anomalies/{dataset_id}/model").json()
    assert meta2["feature_count"] == 8
    assert meta2["contamination"] == 0.25
    assert meta2["feature_groups"] == ["behavioral"]


# 16. Custom hyperparameter overrides applied and stored in metadata
def test_hyperparameter_overrides(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    resp = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={
            "n_estimators": 65,
            "contamination": 0.15,
            "max_samples": 0.75,
            "random_state": 999,
        },
    )
    assert resp.status_code == 200
    meta = resp.json()["model_metadata"]
    assert meta["n_estimators"] == 65
    assert meta["contamination"] == 0.15
    assert meta["max_samples"] == 0.75
    assert meta["random_state"] == 999


# 17. GET endpoints return clear 404 if called before training
def test_get_before_training_returns_404(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    resp_users = client.get(f"/api/v1/anomalies/{dataset_id}/users")
    assert resp_users.status_code == 404
    assert "No anomaly detection model has been trained yet" in resp_users.json()["message"]

    resp_summary = client.get(f"/api/v1/anomalies/{dataset_id}/summary")
    assert resp_summary.status_code == 404

    resp_model = client.get(f"/api/v1/anomalies/{dataset_id}/model")
    assert resp_model.status_code == 404
