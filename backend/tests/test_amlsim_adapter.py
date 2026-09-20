"""
Unit and integration tests for AMLSimAdapter.
Tests transaction normalization, account universe resolution, ground-truth label construction,
memory-safe reading, and ensures strict decoupling from GraphFin 19-feature extraction.
"""
import gzip
import io
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from backend.app.services.amlsim_adapter import AMLSimAdapter
from backend.app.services.graph_service import GraphService
from backend.app.services.feature_service import FeatureService, FEATURE_NAMES
from backend.app.services.state_store import StateStore
from backend.app.services.label_registry import LabelRegistry
from backend.app.services.dataset_registry import dataset_registry


@pytest.fixture
def tiny_amlsim_dir(tmp_path: Path) -> Path:
    """Create a minimal synthetic AMLSim fixture with compressed CSV files."""
    data_dir = tmp_path / "bank_mixed"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. transactions.csv.gz
    tx_csv = (
        "tran_id,orig_acct,bene_acct,tx_type,base_amt,tran_timestamp,is_sar,alert_id\n"
        "1,1001,2001,TRANSFER,150.50,2017-01-01T10:00:00Z,False,-1\n"
        "2,2001,3001,TRANSFER,2750.00,2017-01-02T11:00:00Z,True,10\n"
        "3,3001,1001,TRANSFER,2740.00,2017-01-03T12:00:00Z,True,10\n"
        "4,4001,2001,TRANSFER,85.20,2017-01-04T13:00:00Z,False,-1\n"
    )
    with gzip.open(data_dir / "transactions.csv.gz", "wt", encoding="utf-8") as f:
        f.write(tx_csv)

    # 2. accounts.csv.gz
    acct_csv = (
        "acct_id,dsply_nm,type,acct_stat,acct_rptng_crncy,prior_sar_count,branch_id,open_dt,close_dt,initial_deposit,tx_behavior_id,bank_id\n"
        "1001,C_1001,SAV,A,USD,False,1,2017-01-01T00:00:00Z,4754-11-29T00:00:00Z,10000.0,1,bank_a\n"
        "2001,C_2001,SAV,A,USD,True,1,2017-01-01T00:00:00Z,4754-11-29T00:00:00Z,20000.0,1,bank_b\n"
        "3001,C_3001,SAV,A,USD,True,1,2017-01-01T00:00:00Z,4754-11-29T00:00:00Z,30000.0,1,bank_c\n"
        "4001,C_4001,SAV,A,USD,False,1,2017-01-01T00:00:00Z,4754-11-29T00:00:00Z,40000.0,1,bank_a\n"
    )
    with gzip.open(data_dir / "accounts.csv.gz", "wt", encoding="utf-8") as f:
        f.write(acct_csv)

    # 3. alert_accounts.csv.gz (with duplicate acct_id across multiple alerts to test deterministic aggregation)
    alert_csv = (
        "alert_id,alert_type,acct_id,acct_name,is_sar,model_id,start,end,schedule_id,bank_id\n"
        "10,cycle,2001,2001,True,1,0,1000000,0,bank_b\n"
        "10,cycle,3001,3001,True,1,0,1000000,0,bank_c\n"
        "99,gather_scatter,2001,2001,False,2,0,1000000,0,bank_b\n"  # Duplicate account with is_sar=False
    )
    with gzip.open(data_dir / "alert_accounts.csv.gz", "wt", encoding="utf-8") as f:
        f.write(alert_csv)

    # 4. alert_transactions.csv.gz
    alert_tx_csv = (
        "alert_id,alert_type,is_sar,tran_id,orig_acct,bene_acct,tx_type,base_amt,tran_timestamp\n"
        "10,cycle,True,2,2001,3001,TRANSFER,2750.00,2017-01-02T11:00:00Z\n"
        "10,cycle,True,3,3001,1001,TRANSFER,2740.00,2017-01-03T12:00:00Z\n"
    )
    with gzip.open(data_dir / "alert_transactions.csv.gz", "wt", encoding="utf-8") as f:
        f.write(alert_tx_csv)

    return data_dir


def test_transaction_column_mapping_and_normalization(tiny_amlsim_dir: Path):
    """Verify tran_id, orig_acct, bene_acct, base_amt, tran_timestamp map cleanly."""
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)
    df = adapter.load_transactions()

    assert len(df) == 4
    # Required normalized columns
    assert "transaction_id" in df.columns
    assert "source_user_id" in df.columns
    assert "destination_user_id" in df.columns
    assert "sender_id" in df.columns
    assert "receiver_id" in df.columns
    assert "amount" in df.columns
    assert "timestamp" in df.columns

    # Check values for row 0
    row0 = df.iloc[0]
    assert row0["transaction_id"] == "1"
    assert row0["source_user_id"] == "1001"
    assert row0["destination_user_id"] == "2001"
    assert row0["sender_id"] == "1001"
    assert row0["receiver_id"] == "2001"
    assert row0["amount"] == 150.50
    assert row0["transaction_type"] == "TRANSFER"

    # Metadata preserved
    assert bool(row0["is_sar"]) is False
    assert row0["alert_id"] == "-1"


def test_timestamp_parsing(tiny_amlsim_dir: Path):
    """Verify timestamps are parsed into UTC datetime objects."""
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)
    df = adapter.load_transactions()

    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    first_ts = df["timestamp"].iloc[0]
    assert first_ts.year == 2017
    assert first_ts.month == 1
    assert first_ts.day == 1
    assert first_ts.hour == 10


def test_amount_numeric_validation(tiny_amlsim_dir: Path):
    """Verify amounts are strictly positive floats."""
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)
    df = adapter.load_transactions()

    assert pd.api.types.is_float_dtype(df["amount"])
    assert (df["amount"] > 0).all()


def test_accounts_universe_loading(tiny_amlsim_dir: Path):
    """Verify accounts.csv.gz loads cleanly with acct_id as primary key."""
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)
    accounts = adapter.load_accounts()

    assert len(accounts) == 4
    assert set(accounts["acct_id"]) == {"1001", "2001", "3001", "4001"}
    assert "prior_sar_count" in accounts.columns


def test_account_labels_and_duplicate_handling(tiny_amlsim_dir: Path):
    """
    Verify account labels are correctly identified and multiple alert rows
    for the same account are deterministically aggregated (logical OR).
    """
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)

    # 1. Closed world (complete ground truth)
    closed_labels = adapter.load_account_labels(mode="closed_world")
    assert len(closed_labels) == 4

    labels_map = dict(zip(closed_labels["user_id"], closed_labels["label"]))
    # 2001 was in alert 10 (is_sar=True) and alert 99 (is_sar=False) -> should be 1
    assert labels_map["2001"] == 1
    assert labels_map["3001"] == 1
    assert labels_map["1001"] == 0
    assert labels_map["4001"] == 0

    # 2. Positives only (PU mode)
    pos_labels = adapter.load_account_labels(mode="positives_only")
    assert len(pos_labels) == 2
    assert set(pos_labels["user_id"]) == {"2001", "3001"}
    assert (pos_labels["label"] == 1).all()


def test_no_label_leakage_in_graphfin_feature_pipeline(tiny_amlsim_dir: Path):
    """
    CRITICAL: Verify that neither is_sar nor alert_id enters the 19 GraphFin
    feature definitions or feature matrix.
    """
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)
    df = adapter.load_transactions()

    graph_svc = GraphService()
    graph_svc.build_graph(df)

    feat_svc = FeatureService(graph_svc)
    feat_svc.extract_features(df)

    users, matrix, names = feat_svc.get_feature_matrix()

    # 1. Exactly GraphFin's 19 canonical features
    assert len(names) == 19
    assert names == FEATURE_NAMES
    assert "is_sar" not in names
    assert "alert_id" not in names
    assert "tx_type" not in names

    # 2. Feature matrix shape matches users x 19
    assert matrix.shape == (len(users), 19)
    assert not np.isnan(matrix).any()


def test_end_to_end_statestore_and_label_registry(tiny_amlsim_dir: Path):
    """
    Verify full GraphFin integration:
    - StateStore loads AMLSim transactions and constructs its OWN graph
    - Feature matrix contains only GraphFin features
    - LabelRegistry receives ground-truth labels separately without leakage
    """
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)
    df = adapter.load_transactions()

    # Create dataset in registry
    dataset_id = dataset_registry.create_dataset(df)
    store = dataset_registry.get(dataset_id)

    # Verify GraphFin constructs its OWN directed graph
    G = store.graph_service.graph
    assert G.number_of_nodes() == 4
    assert G.number_of_edges() == 4
    # Check edge weight is base_amt
    assert G["1001"]["2001"]["weight"] == 150.50
    assert G["2001"]["3001"]["weight"] == 2750.00

    # Verify separate ground-truth registration
    label_bytes = adapter.export_labels_csv_bytes(mode="closed_world")
    label_reg = LabelRegistry()
    summary = label_reg.store_labels_from_csv(
        dataset_id=dataset_id,
        csv_content=label_bytes,
        user_id_col="user_id",
        label_col="label",
    )

    assert summary.total_labels_uploaded == 4
    assert summary.matched_count == 4
    assert summary.positive_count == 2
    assert summary.negative_count == 2
    assert summary.unmatched_count == 0

    # Ensure feature matrix remains pure (19 features)
    _, matrix, fnames = store.get_feature_matrix()
    assert matrix.shape == (4, 19)
    assert fnames == FEATURE_NAMES


def test_chunked_reading_and_sample_size(tiny_amlsim_dir: Path):
    """Verify memory-safe chunked reading and sample_size parameter."""
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)

    # Sample size
    sample_df = adapter.load_transactions(sample_size=2)
    assert len(sample_df) == 2

    # Chunk generator
    chunks = list(adapter.load_transactions(chunksize=2))
    assert len(chunks) == 2
    assert len(chunks[0]) == 2
    assert len(chunks[1]) == 2


def test_audit_dataset_function(tiny_amlsim_dir: Path):
    """Verify audit_dataset returns all mandatory metrics without errors."""
    adapter = AMLSimAdapter(data_dir=tiny_amlsim_dir)
    audit = adapter.audit_dataset()

    assert audit["total_transactions"] == 4
    assert audit["unique_accounts"] == 4
    assert audit["unique_source_accounts"] == 4
    assert audit["unique_destination_accounts"] == 3  # 1001, 2001, 3001
    assert audit["total_labeled_accounts"] == 4
    assert audit["positive_accounts"] == 2
    assert audit["negative_accounts"] == 2
    assert audit["unlabeled_accounts"] == 0
    assert audit["duplicate_transaction_ids"] == 0
    assert audit["missing_required_values"]["tran_id"] == 0
    assert audit["transaction_time_range"]["start"] is not None
    assert audit["transaction_time_range"]["end"] is not None
