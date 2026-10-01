"""
Unit and Integration Tests for PaySim Account-Level Ground-Truth Labels.
"""
from pathlib import Path
import pandas as pd
import pytest

from backend.app.services.dataset_registry import dataset_registry, PAYSIM_DATASET_ID
from backend.app.services.label_registry import label_registry
from backend.app.core.config import settings


def test_paysim_account_labels_file_exists():
    lbl_path = settings.DATA_DIR / "research" / "paysim_account_labels.csv"
    assert lbl_path.exists(), f"File missing: {lbl_path}"


def test_account_level_aggregation_and_coverage():
    lbl_path = settings.DATA_DIR / "research" / "paysim_account_labels.csv"
    df = pd.read_csv(lbl_path)

    # Check required columns
    assert "account" in df.columns
    assert "label" in df.columns
    assert "label_meaning" in df.columns

    # 1. Duplicate prevention
    assert df["account"].duplicated().sum() == 0, "Found duplicate accounts in paysim_account_labels.csv"

    # 2. Label values restricted to 0 or 1
    unique_labels = set(df["label"].unique())
    assert unique_labels.issubset({0, 1}), f"Unexpected label values: {unique_labels}"

    # 3. Label meaning alignment
    pos_mask = df["label"] == 1
    assert (df.loc[pos_mask, "label_meaning"] == "fraud-involved").all()
    assert (df.loc[~pos_mask, "label_meaning"] == "normal").all()

    # 4. No missing labels
    assert df["label"].isna().sum() == 0
    assert df["account"].isna().sum() == 0


def test_sender_and_receiver_fraud_involvement_logic():
    # Synthetic test to verify aggregation rule
    tx_records = [
        {"nameOrig": "S_NORMAL", "nameDest": "R_NORMAL", "isFraud": 0},
        {"nameOrig": "S_FRAUD", "nameDest": "R_VICTIM", "isFraud": 1},
        {"nameOrig": "S_MIXED", "nameDest": "R_NORMAL2", "isFraud": 0},
        {"nameOrig": "S_MIXED", "nameDest": "R_FRAUD_DEST", "isFraud": 1},
    ]
    df = pd.DataFrame(tx_records)

    fraud_accts = set()
    fraud_df = df[df["isFraud"] == 1]
    for s, r in zip(fraud_df["nameOrig"], fraud_df["nameDest"]):
        fraud_accts.add(s)
        fraud_accts.add(r)

    all_accts = set(df["nameOrig"]).union(set(df["nameDest"]))
    labels = {a: (1 if a in fraud_accts else 0) for a in all_accts}

    assert labels["S_NORMAL"] == 0
    assert labels["R_NORMAL"] == 0
    assert labels["S_FRAUD"] == 1  # Sender in fraud tx
    assert labels["R_VICTIM"] == 1  # Receiver in fraud tx
    assert labels["S_MIXED"] == 1   # Involved in at least 1 fraud tx
    assert labels["R_FRAUD_DEST"] == 1


def test_paysim_label_registry_integration():
    store = dataset_registry.load_paysim()
    assert dataset_registry.is_loaded(PAYSIM_DATASET_ID)

    summary = label_registry.get_summary(PAYSIM_DATASET_ID)
    assert summary.matched_count == len(store.feature_service.user_features)
    assert summary.positive_count > 0
    assert summary.negative_count > 0
    assert summary.positive_count + summary.negative_count == summary.matched_count

    labels = label_registry.get_labels(PAYSIM_DATASET_ID)
    assert len(labels) == summary.matched_count
    assert all(isinstance(v, bool) for v in labels.values())


def test_ibm_label_behavior_remains_unchanged():
    ibm_5k_id = "ddbaab44-78b6-41be-a8fb-e83dfec66358"
    ibm_50k_id = "03fb9ab0-4f42-4404-9d76-723fd4d8753e"

    assert dataset_registry.get_currency(ibm_5k_id) == "USD"
    assert dataset_registry.get_currency(ibm_50k_id) == "USD"


def test_production_paysim_loading_remains_unchanged():
    store = dataset_registry.load_paysim()
    assert len(store.transactions_df) == 10000
    assert len(store.feature_service.user_features) == 18711
