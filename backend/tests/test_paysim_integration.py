"""
Comprehensive test suite for PaySim dataset registration, schema validation, API routes, and ground-truth labels.
Designed for fast, reproducible unit and integration testing.
"""
from datetime import datetime, timedelta
import io
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.state_store import StateStore
from backend.app.services.dataset_registry import dataset_registry, PAYSIM_DATASET_ID
from backend.app.services.paysim_adapter import load_paysim_raw, derive_paysim_account_labels, convert_step_to_timestamp, FORBIDDEN_LEAKAGE_COLUMNS
from backend.app.services.feature_service import CANONICAL_TRANSFER_FEATURES, validate_19_feature_schema, FORBIDDEN_LEAKAGE_FEATURES

client = TestClient(app)


def test_paysim_step_to_timestamp():
    """Test deterministic step to timestamp conversion."""
    ts1 = convert_step_to_timestamp(1)
    ts24 = convert_step_to_timestamp(24)
    assert ts1 == "2023-01-01 01:00:00"
    assert ts24 == "2023-01-02 00:00:00"


def test_paysim_account_label_derivation():
    """Test any-involvement rule for account-level labels."""
    sample_df = pd.DataFrame([
        {"sender_id": "C100", "receiver_id": "M200", "is_fraud": 0},
        {"sender_id": "C100", "receiver_id": "M300", "is_fraud": 1},
        {"sender_id": "C400", "receiver_id": "M500", "is_fraud": 0},
    ])
    labels = derive_paysim_account_labels(sample_df)
    assert labels["C100"] == 1
    assert labels["M300"] == 1
    assert labels["M200"] == 0
    assert labels["C400"] == 0
    assert labels["M500"] == 0


def test_19_feature_schema_validation():
    """Test canonical 19-feature schema validation and leakage prevention."""
    valid_features = CANONICAL_TRANSFER_FEATURES + ["egonet_node_count", "egonet_edge_count", "egonet_density", "circular_flow_indicator"]
    assert validate_19_feature_schema(valid_features) is True

    # Less than 19 features fails
    with pytest.raises(ValueError, match="Expected at least 19"):
        validate_19_feature_schema(["in_degree", "out_degree"])

    # Wrong order fails
    invalid_order = list(valid_features)
    invalid_order[0], invalid_order[1] = invalid_order[1], invalid_order[0]
    with pytest.raises(ValueError, match="Feature schema validation failed"):
        validate_19_feature_schema(invalid_order)

    # Leakage column fails
    with pytest.raises(ValueError, match="leakage feature"):
        validate_19_feature_schema(valid_features + ["oldbalanceOrg"])


def test_paysim_raw_column_mapping_and_leakage_exclusion(tmp_path):
    """Test raw PaySim CSV loading, column mapping, and leakage column stripping."""
    raw_csv = tmp_path / "raw_paysim.csv"
    raw_df = pd.DataFrame([
        {
            "step": 1,
            "type": "PAYMENT",
            "amount": 150.0,
            "nameOrig": "C12345",
            "nameDest": "M67890",
            "oldbalanceOrg": 500.0,
            "newbalanceOrig": 350.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 150.0,
            "isFraud": 0,
            "isFlaggedFraud": 0,
        },
        {
            "step": 2,
            "type": "CASH_OUT",
            "amount": 1000.0,
            "nameOrig": "C99999",
            "nameDest": "C88888",
            "oldbalanceOrg": 1000.0,
            "newbalanceOrig": 0.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 1000.0,
            "isFraud": 1,
            "isFlaggedFraud": 0,
        },
    ])
    raw_df.to_csv(raw_csv, index=False)

    clean_df = load_paysim_raw(raw_csv)
    assert len(clean_df) == 2
    assert set(clean_df.columns) == {"transaction_id", "sender_id", "receiver_id", "amount", "timestamp", "transaction_type", "is_fraud"}
    for leakage_col in FORBIDDEN_LEAKAGE_COLUMNS:
        assert leakage_col not in clean_df.columns

    assert clean_df["timestamp"].iloc[0] == "2023-01-01 01:00:00"
    assert clean_df["timestamp"].iloc[1] == "2023-01-01 02:00:00"


def test_paysim_dataset_registration_and_api():
    """Test PaySim dataset registration, ID, and GET /api/v1/datasets endpoint."""
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "secondary_datasets" in data
    
    paysim_sec = next((d for d in data["secondary_datasets"] if d["id"] == PAYSIM_DATASET_ID), None)
    assert paysim_sec is not None
    assert paysim_sec["id"] == PAYSIM_DATASET_ID
    assert paysim_sec["name"] == "PaySim"
    assert paysim_sec["source_type"] == "raw_transaction"
    assert paysim_sec["entity_level"] == "account"
    assert paysim_sec["paper_reportable"] is False
    assert paysim_sec["is_locked"] is False


def test_paysim_fast_store_integration():
    """Test PaySim StateStore and API endpoints with a sample payload."""
    sample_df = pd.DataFrame([
        {"transaction_id": "TX_PS_001", "sender_id": "C10", "receiver_id": "C20", "amount": 100.0, "timestamp": "2023-01-01 01:00:00", "transaction_type": "PAYMENT"},
        {"transaction_id": "TX_PS_002", "sender_id": "C20", "receiver_id": "C30", "amount": 250.0, "timestamp": "2023-01-01 02:00:00", "transaction_type": "TRANSFER"},
    ])
    store = StateStore()
    store.load_transactions(sample_df)

    dataset_registry._datasets[PAYSIM_DATASET_ID] = store
    dataset_registry._currencies[PAYSIM_DATASET_ID] = "USD"

    # Test /transactions/paysim/summary
    tx_resp = client.get(f"/api/v1/transactions/{PAYSIM_DATASET_ID}/summary")
    assert tx_resp.status_code == 200
    assert tx_resp.json()["transactions"] == 2

    # Test /graph/paysim/summary
    graph_resp = client.get(f"/api/v1/graph/{PAYSIM_DATASET_ID}/summary")
    assert graph_resp.status_code == 200
    assert graph_resp.json()["nodes"] == 3

    # Test /analytics/paysim/users
    analytics_resp = client.get(f"/api/v1/analytics/{PAYSIM_DATASET_ID}/users?limit=10")
    assert analytics_resp.status_code == 200
    assert len(analytics_resp.json()["users"]) == 3
    features = analytics_resp.json()["users"][0]["feature_vector"]
    assert len(features) >= 19


def test_locked_ibm_datasets_remain_unchanged():
    """Verify locked IBM research benchmark dataset metadata and IDs remain untouched."""
    response = client.get("/api/v1/datasets/locked")
    assert response.status_code == 200
    locked_items = response.json()
    for item in locked_items:
        assert item["dataset_id"] in ["ddbaab44-78b6-41be-a8fb-e83dfec66358", "03fb9ab0-4f42-4404-9d76-723fd4d8753e"]
        assert item["dataset_id"] != PAYSIM_DATASET_ID
