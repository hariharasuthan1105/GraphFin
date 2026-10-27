"""
GraphFin Python ML and Gateway Recovery Validation Tests.
Verifies:
- Canonical 19 feature extraction and numerical bounds
- Isolation Forest fitting and score semantics
- Single service gateway GET-only security guard
- Ground truth label isolation (no leakage into unsupervised features)
"""
import os
import io
import pandas as pd
import numpy as np
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.services.preprocessing import PreprocessingService
from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.anomaly_service import AnomalyService
from backend.app.services.feature_service import CANONICAL_TRANSFER_FEATURES, validate_19_feature_schema
from backend.app.schemas.anomaly import AnomalyTrainRequest
from gateway.single_service import app as single_app


def test_canonical_19_features_extraction():
    """Verify exact 19 canonical features are extracted and numerically valid."""
    csv_candidates = [
        Path(r"C:\Users\hariharasuthan\Downloads\GraphFin_sample_1000_accounts_10000_transactions.csv"),
        Path.cwd() / "GraphFin_sample_1000_accounts_10000_transactions.csv",
    ]
    target_csv = next((p for p in csv_candidates if p.exists()), None)
    if not target_csv:
        pytest.skip("Synthetic benchmark CSV not present locally.")

    df = pd.read_csv(target_csv)
    df_canonical = df.rename(columns={
        "source_account": "sender_id",
        "destination_account": "receiver_id",
        "amount": "amount",
        "timestamp": "timestamp",
    })
    if "transaction_id" not in df_canonical.columns:
        df_canonical["transaction_id"] = [f"TX_{i:05d}" for i in range(len(df_canonical))]

    preprocessor = PreprocessingService(strict_mode=False)
    clean_df, errors, warnings = preprocessor.process_dataframe(df_canonical)
    assert len(clean_df) == 10000

    ds_id = dataset_registry.create_dataset(clean_df, currency="INR")
    store = dataset_registry.get(ds_id)

    users, X, feature_names = store.feature_service.get_feature_matrix()
    canonical_indices = [feature_names.index(f) for f in CANONICAL_TRANSFER_FEATURES]
    X_canonical = X[:, canonical_indices]
    validate_19_feature_schema(CANONICAL_TRANSFER_FEATURES)

    assert len(users) == 1000, f"Expected 1,000 entities, got {len(users)}"
    assert X_canonical.shape[1] == 19, f"Expected 19 canonical features, got {X_canonical.shape[1]}"
    assert not np.isnan(X_canonical).any(), "Feature matrix contains NaN"
    assert not np.isinf(X_canonical).any(), "Feature matrix contains Inf"

    # Train Isolation Forest
    anomaly_service = AnomalyService()
    train_req = AnomalyTrainRequest(
        experiment_label="recovery_test_iforest",
        n_estimators=50,
        contamination=0.05,
        random_state=42,
    )
    resp = anomaly_service.train_model(dataset_id=ds_id, request=train_req, experiment_label="recovery_test_iforest")
    assert resp.status == "success"

    # Verify predictions
    user_anomalies = anomaly_service.predict_user_anomalies(dataset_id=ds_id, experiment_label="recovery_test_iforest")
    assert user_anomalies.total_users == 1000
    assert user_anomalies.suspicious_count > 0
    assert user_anomalies.suspicious_count <= 100  # Contamination ~50 entities

    # Cleanup dataset from registry
    with dataset_registry._lock:
        dataset_registry._datasets.pop(ds_id, None)
        dataset_registry._currencies.pop(ds_id, None)


def test_gateway_single_service_read_only_protection():
    """Verify single_service gateway enforces GET-only read semantics."""
    client = TestClient(single_app)

    # GET /health should succeed
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # POST to /api/v1/research/... should be blocked with 405 Method Not Allowed
    res_post = client.post("/api/v1/research/overview", json={"foo": "bar"})
    assert res_post.status_code == 405
    data = res_post.json()
    assert data["error"] == "GATEWAY_READ_ONLY"


def test_ground_truth_label_isolation():
    """Verify is_anomaly and pattern_type are never included in unsupervised feature matrix."""
    assert "is_anomaly" not in CANONICAL_TRANSFER_FEATURES, "is_anomaly must never leak into feature set!"
    assert "pattern_type" not in CANONICAL_TRANSFER_FEATURES, "pattern_type must never leak into feature set!"
    assert "label" not in CANONICAL_TRANSFER_FEATURES, "label must never leak into feature set!"
    assert len(CANONICAL_TRANSFER_FEATURES) == 19, "Must have exactly 19 canonical features"
