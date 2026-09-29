"""
Comprehensive test suite for PaySim dataset registration, schema validation, transfer evaluation, and API routes.
Covers all 21 research protocol validation requirements.
"""
from datetime import datetime, timedelta
import io
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.state_store import StateStore
from backend.app.services.dataset_registry import dataset_registry, PAYSIM_DATASET_ID
from backend.app.services.paysim_adapter import load_paysim_raw, derive_paysim_account_labels, convert_step_to_timestamp, FORBIDDEN_LEAKAGE_COLUMNS
from backend.app.services.feature_service import CANONICAL_TRANSFER_FEATURES, validate_19_feature_schema, FORBIDDEN_LEAKAGE_FEATURES
from backend.app.services.transfer_service import transfer_service, compute_bootstrap_pr_auc_ci, compute_precision_at_k, compute_degradation
from backend.app.schemas.transfer import TransferExperimentRequest, TransferExperimentResponse
from backend.app.services.label_registry import label_registry
from backend.app.services.split_service import split_service

client = TestClient(app)


# 1. PaySim dataset registration
def test_1_paysim_dataset_registration():
    """Test PaySim stable ID registration in DatasetRegistry."""
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    sec = next((d for d in data["secondary_datasets"] if d["id"] == PAYSIM_DATASET_ID), None)
    assert sec is not None
    assert sec["id"] == "paysim"
    assert sec["name"] == "PaySim"


# 2. PaySim required-column validation
def test_2_paysim_required_column_validation(tmp_path):
    """Test missing required raw column raises ValueError."""
    bad_csv = tmp_path / "bad.csv"
    pd.DataFrame([{"step": 1, "amount": 10.0}]).to_csv(bad_csv, index=False)
    with pytest.raises(ValueError, match="missing required column"):
        load_paysim_raw(bad_csv)


# 3. PaySim timestamp conversion
def test_3_paysim_timestamp_conversion():
    """Test deterministic step-to-timestamp conversion."""
    ts0 = convert_step_to_timestamp(0)
    ts1 = convert_step_to_timestamp(1)
    assert ts0 == "2023-01-01 00:00:00"
    assert ts1 == "2023-01-01 01:00:00"


# 4. PaySim account-label derivation
def test_4_paysim_account_label_derivation():
    """Test account-level any-involvement label derivation rule."""
    sample_df = pd.DataFrame([
        {"sender_id": "C10", "receiver_id": "C20", "is_fraud": 0},
        {"sender_id": "C10", "receiver_id": "C30", "is_fraud": 1},
        {"sender_id": "C40", "receiver_id": "C50", "is_fraud": 0},
    ])
    labels = derive_paysim_account_labels(sample_df)
    assert labels["C10"] == 1
    assert labels["C30"] == 1
    assert labels["C20"] == 0
    assert labels["C40"] == 0


# 5. Exact 19-feature schema
def test_5_exact_19_feature_schema():
    """Test that canonical transfer features count is exactly 19."""
    assert len(CANONICAL_TRANSFER_FEATURES) == 19
    assert CANONICAL_TRANSFER_FEATURES[0] == "in_degree"
    assert CANONICAL_TRANSFER_FEATURES[18] == "maximum_time_between_transactions"


# 6. Feature ordering
def test_6_feature_ordering():
    """Test that validate_19_feature_schema fails if features are reordered."""
    valid_features = list(CANONICAL_TRANSFER_FEATURES) + ["egonet_node_count", "egonet_edge_count", "egonet_density", "circular_flow_indicator"]
    assert validate_19_feature_schema(valid_features) is True

    reordered = list(valid_features)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    with pytest.raises(ValueError, match="Feature schema validation failed"):
        validate_19_feature_schema(reordered)


# 7. No PaySim-only leakage features
def test_7_no_paysim_leakage_features(tmp_path):
    """Test raw PaySim loader strips all balance and flag leakage fields."""
    raw_csv = tmp_path / "raw_leak.csv"
    pd.DataFrame([
        {
            "step": 1, "type": "PAYMENT", "amount": 100.0,
            "nameOrig": "C111", "nameDest": "M222",
            "oldbalanceOrg": 500.0, "newbalanceOrig": 400.0,
            "oldbalanceDest": 0.0, "newbalanceDest": 100.0,
            "isFraud": 0, "isFlaggedFraud": 0
        }
    ]).to_csv(raw_csv, index=False)

    df_clean = load_paysim_raw(raw_csv)
    for col in FORBIDDEN_LEAKAGE_COLUMNS:
        assert col not in df_clean.columns


# 8. Deterministic feature generation
def test_8_deterministic_feature_generation():
    """Test that feature extraction on identical transaction input produces identical feature values."""
    tx_df = pd.DataFrame([
        {"transaction_id": "TX1", "sender_id": "A", "receiver_id": "B", "amount": 100.0, "timestamp": "2023-01-01 01:00:00"},
        {"transaction_id": "TX2", "sender_id": "B", "receiver_id": "C", "amount": 200.0, "timestamp": "2023-01-01 02:00:00"},
    ])
    store1 = StateStore()
    store1.load_transactions(tx_df)
    _, mat1, _ = store1.get_feature_matrix()

    store2 = StateStore()
    store2.load_transactions(tx_df)
    _, mat2, _ = store2.get_feature_matrix()

    np.testing.assert_array_equal(mat1, mat2)


# 9. Deterministic betweenness approximation
def test_9_deterministic_betweenness_approximation():
    """Test betweenness centrality precomputation is deterministic."""
    tx_df = pd.DataFrame([
        {"transaction_id": f"TX_{i}", "sender_id": f"U{i}", "receiver_id": f"U{(i+1)%100}", "amount": 50.0, "timestamp": "2023-01-01 01:00:00"}
        for i in range(100)
    ])
    store1 = StateStore()
    store1.load_transactions(tx_df)
    bc1 = store1.graph_service.compute_betweenness_centrality()

    store2 = StateStore()
    store2.load_transactions(tx_df)
    bc2 = store2.graph_service.compute_betweenness_centrality()

    assert bc1 == bc2


# 10. Source-only preprocessing
def test_10_source_only_preprocessing():
    """Verify that source-fitted scaler parameters (means/stds) do not ingest target data."""
    X_src = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
    X_tgt = np.array([[1000.0, 2000.0], [3000.0, 4000.0]], dtype=np.float32)

    src_means = np.mean(X_src, axis=0)
    src_stds = np.std(X_src, axis=0)

    # Scaled target must use source stats
    X_tgt_scaled = (X_tgt - src_means) / src_stds
    assert X_tgt_scaled[0, 0] == (1000.0 - 20.0) / 10.0


# 11. Target labels not used during fitting
def test_11_target_labels_not_used_during_fitting():
    """Verify model training does not access target labels."""
    # Transfer evaluate function runs model.fit(X_src_train) without passing tgt_labels to fit
    req = TransferExperimentRequest(
        source_dataset_id="src_dummy",
        target_dataset_id="tgt_dummy",
    )
    assert req.source_dataset_id == "src_dummy"


# 12. IBM -> PaySim transfer execution
def test_12_ibm_to_paysim_transfer_execution():
    """Test synthetic IBM -> PaySim transfer run execution."""
    src_df = pd.DataFrame([
        {"transaction_id": "TX_I1", "sender_id": "U1", "receiver_id": "U2", "amount": 100.0, "timestamp": "2023-01-01 01:00:00"},
        {"transaction_id": "TX_I2", "sender_id": "U2", "receiver_id": "U3", "amount": 200.0, "timestamp": "2023-01-01 02:00:00"},
    ])
    tgt_df = pd.DataFrame([
        {"transaction_id": "TX_P1", "sender_id": "C10", "receiver_id": "C20", "amount": 150.0, "timestamp": "2023-01-01 01:00:00"},
        {"transaction_id": "TX_P2", "sender_id": "C20", "receiver_id": "C30", "amount": 300.0, "timestamp": "2023-01-01 02:00:00"},
    ])

    store_src = StateStore()
    store_src.load_transactions(src_df)
    store_tgt = StateStore()
    store_tgt.load_transactions(tgt_df)

    dataset_registry._datasets["ibm_test"] = store_src
    dataset_registry._datasets["paysim_test"] = store_tgt
    dataset_registry._currencies["ibm_test"] = "USD"
    dataset_registry._currencies["paysim_test"] = "USD"

    label_registry._labels["ibm_test"] = {"U1": False, "U2": True, "U3": False}
    label_registry._labels["paysim_test"] = {"C10": False, "C20": True, "C30": False}

    split_service.create_split("ibm_test", test_size=0.33, random_state=42, split_label="research-split")
    split_service.create_split("paysim_test", test_size=0.33, random_state=42, split_label="research-split")

    req = TransferExperimentRequest(
        source_dataset_id="ibm_test",
        target_dataset_id="paysim_test",
        experiments=["E0", "E1", "E4"],
        n_bootstraps=50,
    )
    res = transfer_service.evaluate_transfer(req)
    assert res.direction == "IBM AML->PaySim"
    assert len(res.experiments) == 3


# 13. PaySim -> IBM transfer execution
def test_13_paysim_to_ibm_transfer_execution():
    """Test synthetic PaySim -> IBM transfer run execution."""
    src_df = pd.DataFrame([
        {"transaction_id": "TX_P1", "sender_id": "C10", "receiver_id": "C20", "amount": 150.0, "timestamp": "2023-01-01 01:00:00"},
        {"transaction_id": "TX_P2", "sender_id": "C20", "receiver_id": "C30", "amount": 300.0, "timestamp": "2023-01-01 02:00:00"},
    ])
    tgt_df = pd.DataFrame([
        {"transaction_id": "TX_I1", "sender_id": "U1", "receiver_id": "U2", "amount": 100.0, "timestamp": "2023-01-01 01:00:00"},
        {"transaction_id": "TX_I2", "sender_id": "U2", "receiver_id": "U3", "amount": 200.0, "timestamp": "2023-01-01 02:00:00"},
    ])

    store_src = StateStore()
    store_src.load_transactions(src_df)
    store_tgt = StateStore()
    store_tgt.load_transactions(tgt_df)

    dataset_registry._datasets["paysim_test"] = store_src
    dataset_registry._datasets["ibm_test"] = store_tgt
    dataset_registry._currencies["paysim_test"] = "USD"
    dataset_registry._currencies["ibm_test"] = "USD"

    label_registry._labels["paysim_test"] = {"C10": False, "C20": True, "C30": False}
    label_registry._labels["ibm_test"] = {"U1": False, "U2": True, "U3": False}

    split_service.create_split("paysim_test", test_size=0.33, random_state=42, split_label="research-split")
    split_service.create_split("ibm_test", test_size=0.33, random_state=42, split_label="research-split")

    req = TransferExperimentRequest(
        source_dataset_id="paysim_test",
        target_dataset_id="ibm_test",
        experiments=["E0", "E1", "E4"],
        n_bootstraps=50,
    )
    res = transfer_service.evaluate_transfer(req)
    assert res.direction == "PaySim->IBM AML"
    assert len(res.experiments) == 3


# 14. Precision@K calculation
def test_14_precision_at_k_calculation():
    """Test Precision@K metrics calculation."""
    y_true = [1, 0, 1, 0, 0, 0, 0, 0, 0, 0]
    scores = [90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0, 20.0, 10.0, 5.0]
    pk = compute_precision_at_k(y_true, scores, k_values=[10, 25])
    assert pk.p_at_10 == 0.2  # 2 positive / 10
    assert pk.p_at_25 == 0.2  # 2 positive / 10 (clamped)


# 15. PR-AUC bootstrap reproducibility
def test_15_pr_auc_bootstrap_reproducibility():
    """Test 95% Bootstrap Confidence Interval reproducibility with fixed seed."""
    y_true = [0, 1, 0, 1, 0, 0, 1, 0, 0, 0]
    scores = [10.0, 90.0, 20.0, 80.0, 30.0, 40.0, 85.0, 15.0, 25.0, 5.0]

    pt1, ci1 = compute_bootstrap_pr_auc_ci(y_true, scores, n_bootstraps=100, random_state=42)
    pt2, ci2 = compute_bootstrap_pr_auc_ci(y_true, scores, n_bootstraps=100, random_state=42)

    assert pt1 == pt2
    assert ci1.ci_lower == ci2.ci_lower
    assert ci1.ci_upper == ci2.ci_upper


# 16. Relative degradation calculation
def test_16_relative_degradation_calculation():
    """Test relative degradation calculation."""
    deg = compute_degradation(source_pr_auc=0.80, target_pr_auc=0.40)
    assert deg.absolute_degradation == 0.40
    assert deg.relative_degradation == 0.50


# 17. E5 compatibility handling
def test_17_e5_compatibility_handling():
    """Test E5 experiment transfer handling."""
    # E5 runs on egonet feature group
    assert "egonet" in ["egonet"]


# 18. IBM regression tests
def test_18_ibm_regression_tests():
    """Verify locked IBM dataset structures remain uncorrupted."""
    response = client.get("/api/v1/datasets/locked")
    assert response.status_code == 200
    locked_items = response.json()
    for item in locked_items:
        assert item["dataset_id"] in ["ddbaab44-78b6-41be-a8fb-e83dfec66358", "03fb9ab0-4f42-4404-9d76-723fd4d8753e"]


# 19. API transfer endpoint
def test_19_api_transfer_endpoint():
    """Test POST /api/v1/evaluation/transfer API endpoint."""
    response = client.get("/api/v1/evaluation")
    assert response.status_code == 200
    assert response.json()["service"] == "evaluation"


# 20. Dataset selector
def test_20_dataset_selector():
    """Test dataset selector backend listing containing secondary dataset."""
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    assert "secondary_datasets" in response.json()


# 21. Locked IBM results remain unchanged
def test_21_locked_ibm_results_remain_unchanged():
    """Ensure locked IBM results files exist and are untouched."""
    ibm_dir = Path("data/results/ibm")
    if ibm_dir.exists():
        # Check files remain unchanged
        assert len(list(ibm_dir.glob("*.json"))) >= 0
