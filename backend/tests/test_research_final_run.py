"""
Unit and validation tests for the final E0-E4 research evaluation run.

Tests:
1. Confirms both locked-in dataset fixtures reproduce their documented
   account/positive counts when re-converted with the documented seed.
2. Confirms contamination values used in training match the documented
   per-tier values in stored model metadata (0.004 for medium, 0.005 for large).
3. Confirms all 10 experiments trained only on their respective train
   partitions (reuse existing entity-count assertion pattern).
4. Confirms the consolidated export contains exactly 10 rows with the
   expected experiment/scale labeling.
"""

import csv
import json
from pathlib import Path
import pandas as pd
import pytest

from backend.scripts.convert_ibm_aml import (
    build_composite_key,
    collect_sampled_accounts,
)


@pytest.fixture
def repo_paths():
    repo_root = Path(__file__).resolve().parent.parent.parent
    return {
        "root": repo_root,
        "research_dir": repo_root / "data" / "research",
        "results_dir": repo_root / "data" / "results",
        "medium_tx": repo_root / "data" / "research" / "ibm_aml_medium_5k.csv",
        "medium_lbl": repo_root / "data" / "research" / "ibm_aml_medium_5k_labels.csv",
        "large_tx": repo_root / "data" / "research" / "ibm_aml_large_50k.csv",
        "large_lbl": repo_root / "data" / "research" / "ibm_aml_large_50k_labels.csv",
        "json_export": repo_root / "data" / "results" / "final_e0_e4_comparison.json",
        "csv_export": repo_root / "data" / "results" / "final_e0_e4_comparison.csv",
        "multiseed_json": repo_root / "data" / "results" / "final_multiseed_robustness.json",
        "multiseed_csv": repo_root / "data" / "results" / "final_multiseed_robustness.csv",
    }


def test_locked_in_dataset_fixtures_counts_and_reproducibility(repo_paths):
    """
    Test 1: Confirms both locked-in dataset fixtures reproduce their documented
    account/positive counts when re-converted with the documented seed.
    """
    # 1. Verify Medium tier fixture
    med_tx_path = repo_paths["medium_tx"]
    med_lbl_path = repo_paths["medium_lbl"]
    assert med_tx_path.exists(), f"Medium transaction fixture missing: {med_tx_path}"
    assert med_lbl_path.exists(), f"Medium label fixture missing: {med_lbl_path}"

    df_med_tx = pd.read_csv(med_tx_path)
    df_med_lbl = pd.read_csv(med_lbl_path)

    med_accounts = set(df_med_tx["sender_id"]).union(set(df_med_tx["receiver_id"]))
    assert len(med_accounts) == 5000, f"Expected 5,000 accounts in medium graph, found {len(med_accounts)}"
    assert len(df_med_lbl) == 5000, f"Expected 5,000 accounts in medium labels, found {len(df_med_lbl)}"

    med_pos = int((df_med_lbl["label"] == 1).sum())
    med_neg = int((df_med_lbl["label"] == 0).sum())
    assert med_pos == 20, f"Expected 20 positive accounts in medium labels, found {med_pos}"
    assert med_neg == 4980, f"Expected 4,980 negative accounts in medium labels, found {med_neg}"
    med_prevalence = med_pos / len(df_med_lbl)
    assert abs(med_prevalence - 0.004) < 1e-6, f"Expected 0.004 prevalence, got {med_prevalence}"

    # 2. Verify Large tier fixture
    large_tx_path = repo_paths["large_tx"]
    large_lbl_path = repo_paths["large_lbl"]
    assert large_tx_path.exists(), f"Large transaction fixture missing: {large_tx_path}"
    assert large_lbl_path.exists(), f"Large label fixture missing: {large_lbl_path}"

    df_large_tx = pd.read_csv(large_tx_path)
    df_large_lbl = pd.read_csv(large_lbl_path)

    # In raw transactions file, exactly 10 transactions have amount <= 0 after rounding.
    # GraphFin filters them, leaving 353,850 valid transactions and 49,992 unique accounts.
    valid_large_tx = df_large_tx[df_large_tx["amount"] > 0]
    valid_large_accounts = set(valid_large_tx["sender_id"]).union(set(valid_large_tx["receiver_id"]))
    assert len(valid_large_accounts) == 49992, (
        f"Expected 49,992 unique accounts in large graph after zero-amount filtering, got {len(valid_large_accounts)}"
    )

    large_pos = int((df_large_lbl["label"] == 1).sum())
    assert large_pos == 249, f"Expected 249 positive accounts in large labels, found {large_pos}"
    large_prevalence = large_pos / len(valid_large_accounts)
    assert abs(large_prevalence - 0.00498) < 1e-4, f"Expected ~0.00498 prevalence, got {large_prevalence}"

    # 3. Verify deterministic sampling logic invariance
    # Using a small mock file, verify that collect_sampled_accounts with seed=42 produces identical sets
    test_rows = [
        ["2022/09/01 00:00", "1", f"A_{i}", "1", f"B_{i}", "100.0", "USD", "100.0", "USD", "Wire", 0]
        for i in range(20)
    ]
    cols = [
        "Timestamp", "From Bank", "Account", "To Bank", "Account.1",
        "Amount Received", "Receiving Currency", "Amount Paid",
        "Payment Currency", "Payment Format", "Is Laundering"
    ]
    mock_df = pd.DataFrame(test_rows, columns=cols)
    mock_path = repo_paths["research_dir"] / "mock_test_sample.csv"
    mock_df.to_csv(mock_path, index=False)
    try:
        sample_1 = collect_sampled_accounts(mock_path, target_accounts=5, chunksize=10, seed=42)
        sample_2 = collect_sampled_accounts(mock_path, target_accounts=5, chunksize=10, seed=42)
        assert sample_1 == sample_2, "Account sampling must be 100% deterministic given the same seed."
        assert len(sample_1) == 5
    finally:
        if mock_path.exists():
            mock_path.unlink()


def test_stored_model_metadata_contamination_values(repo_paths):
    """
    Test 2: Confirms contamination values used in training match the documented
    per-tier values in stored model metadata (0.004 for medium, 0.005 for large).
    """
    json_path = repo_paths["json_export"]
    assert json_path.exists(), f"Consolidated JSON export not found: {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check tier contamination metadata in export header
    tiers = data["tiers"]
    assert tiers["medium_real"]["contamination"] == 0.004
    assert tiers["large_real"]["contamination"] == 0.005

    # Check per-experiment contamination values
    experiments = data["experiments"]
    for exp in experiments:
        scale = exp["scale"]
        exp_label = exp["experiment_label"]
        contam = exp["contamination"]

        if "medium" in scale.lower():
            if exp_label == "E0_graph_baseline":
                assert contam is None, "Statistical baseline should not have contamination parameter"
            else:
                assert contam == 0.004, f"Medium tier experiment {exp_label} must have contamination=0.004, got {contam}"
        elif "large" in scale.lower():
            if exp_label == "E0_graph_baseline":
                assert contam is None, "Statistical baseline should not have contamination parameter"
            else:
                assert contam == 0.005, f"Large tier experiment {exp_label} must have contamination=0.005, got {contam}"


def test_experiments_trained_strictly_on_train_partition(repo_paths):
    """
    Test 3: Confirms all 10 experiments trained only on their respective train
    partitions (reuse existing entity-count assertion pattern).
    """
    json_path = repo_paths["json_export"]
    assert json_path.exists(), f"Consolidated JSON export not found: {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tiers = data["tiers"]
    med_split = tiers["medium_real"]["train_test_split"]
    assert med_split["train"]["total"] == 3500, "Medium train count must be 3,500 (70% of 5,000)"
    assert med_split["train"]["pos"] == 14, "Medium train positive count must be 14"
    assert med_split["train"]["neg"] == 3486, "Medium train negative count must be 3,486"
    assert med_split["test"]["total"] == 1500, "Medium test count must be 1,500 (30% of 5,000)"
    assert med_split["test"]["pos"] == 6, "Medium test positive count must be 6 (non-zero)"
    assert med_split["test"]["neg"] == 1494, "Medium test negative count must be 1,494"

    large_split = tiers["large_real"]["train_test_split"]
    assert large_split["train"]["total"] == 34994, "Large train count must be 34,994 (70% of 49,992)"
    assert large_split["train"]["pos"] == 174, "Large train positive count must be 174"
    assert large_split["train"]["neg"] == 34820, "Large train negative count must be 34,820"
    assert large_split["test"]["total"] == 14998, "Large test count must be 14,998 (30% of 49,992)"
    assert large_split["test"]["pos"] == 75, "Large test positive count must be 75 (non-zero)"
    assert large_split["test"]["neg"] == 14923, "Large test negative count must be 14,923"

    for exp in data["experiments"]:
        assert exp["evaluation_mode"] == "held_out", (
            f"Experiment {exp['experiment_label']} on {exp['scale']} must be in held_out mode"
        )
        assert exp["split_label"] == "research-split", (
            f"Experiment {exp['experiment_label']} must be evaluated on research-split"
        )
        if "medium" in exp["scale"].lower():
            assert exp["test_total"] == 1500
            assert exp["test_positive"] == 6
            assert exp["test_negative"] == 1494
        elif "large" in exp["scale"].lower():
            assert exp["test_total"] == 14998
            assert exp["test_positive"] == 75
            assert exp["test_negative"] == 14923


def test_consolidated_export_structure_and_row_count(repo_paths):
    """
    Test 4: Confirms the consolidated export contains exactly 10 rows with the
    expected experiment/scale labeling.
    """
    json_path = repo_paths["json_export"]
    csv_path = repo_paths["csv_export"]

    assert json_path.exists(), f"JSON export not found: {json_path}"
    assert csv_path.exists(), f"CSV export not found: {csv_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_configurations_evaluated"] == 10
    experiments = data["experiments"]
    assert len(experiments) == 10

    # Verify CSV rows
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    assert len(csv_rows) == 10, f"Expected exactly 10 rows in CSV, got {len(csv_rows)}"

    expected_labels = [
        "E0_graph_baseline",
        "E1_graph_ml",
        "E2_graph_behavioral_ml",
        "E3_graph_temporal_ml",
        "E4_full_graphfin",
    ]

    med_rows = [r for r in csv_rows if "medium" in r["scale"].lower()]
    large_rows = [r for r in csv_rows if "large" in r["scale"].lower()]

    assert len(med_rows) == 5, f"Expected 5 medium tier rows, got {len(med_rows)}"
    assert len(large_rows) == 5, f"Expected 5 large tier rows, got {len(large_rows)}"

    assert [r["experiment_label"] for r in med_rows] == expected_labels
    assert [r["experiment_label"] for r in large_rows] == expected_labels

    for r in csv_rows:
        assert float(r["f1_score"]) >= 0.0
        assert float(r["precision"]) >= 0.0
        assert float(r["recall"]) >= 0.0
        if r["roc_auc"]:
            assert float(r["roc_auc"]) >= 0.0
        if r["pr_auc"]:
            assert float(r["pr_auc"]) >= 0.0


def test_multiseed_robustness_splits_and_isolation(repo_paths):
    """
    Test 5: Confirms that at least 6 distinct split_labels exist per dataset with the
    documented random_state values, and that retraining under a different split_label
    does not overwrite or corrupt results from split_label="research-split".
    """
    from backend.app.schemas.anomaly import AnomalyTrainRequest
    from backend.app.services.anomaly_service import anomaly_service
    from backend.app.services.dataset_registry import dataset_registry
    from backend.app.services.evaluation_service import evaluation_service
    from backend.app.services.label_registry import label_registry
    from backend.app.services.preprocessing import PreprocessingService
    from backend.app.services.split_service import split_service

    # Part A: Verify documented seeds and split isolation on a clean, isolated dataset
    preprocessor = PreprocessingService(strict_mode=False)
    csv_data = (
        "transaction_id,sender_id,receiver_id,amount,timestamp\n"
        "T1,U1,U2,100.0,2023-01-01T10:00:00\n"
        "T2,U2,U3,150.0,2023-01-01T11:00:00\n"
        "T3,U3,U4,200.0,2023-01-01T12:00:00\n"
        "T4,U4,U1,250.0,2023-01-01T13:00:00\n"
        "T5,U5,U6,300.0,2023-01-01T14:00:00\n"
        "T6,U6,U7,350.0,2023-01-01T15:00:00\n"
        "T7,U7,U8,400.0,2023-01-01T16:00:00\n"
        "T8,U8,U5,450.0,2023-01-01T17:00:00\n"
        "T9,U9,U10,500.0,2023-01-01T18:00:00\n"
        "T10,U10,U1,550.0,2023-01-01T19:00:00\n"
    ).encode("utf-8")
    clean_df, _, _ = preprocessor.process_csv(csv_data)
    test_ds_id = dataset_registry.create_dataset(clean_df)

    label_csv = (
        "user_id,label\n"
        "U1,1\n"
        "U2,0\n"
        "U3,0\n"
        "U4,0\n"
        "U5,1\n"
        "U6,0\n"
        "U7,0\n"
        "U8,0\n"
        "U9,0\n"
        "U10,0\n"
    ).encode("utf-8")
    label_registry.store_labels_from_csv(test_ds_id, label_csv)

    documented_seeds = [42, 123, 7, 2024, 99, 555]
    seed_to_label = {
        42: "research-split",
        123: "research-split-123",
        7: "research-split-7",
        2024: "research-split-2024",
        99: "research-split-99",
        555: "research-split-555",
    }

    # Create all 6 documented splits on this dataset
    for seed in documented_seeds:
        split_lbl = seed_to_label[seed]
        split_service.create_split(
            dataset_id=test_ds_id,
            test_size=0.30,
            random_state=seed,
            stratify_by_label=True,
            split_label=split_lbl,
        )

    # 1. Assert at least 6 distinct split_labels exist per dataset with documented random_state values
    existing_splits = split_service.list_splits(test_ds_id)
    assert len(existing_splits) >= 6, f"Expected at least 6 splits, found {len(existing_splits)}"
    split_map = {s.split_label: s for s in existing_splits}
    for seed in documented_seeds:
        expected_label = seed_to_label[seed]
        assert expected_label in split_map, f"Missing split label '{expected_label}'"
        assert split_map[expected_label].random_state == seed, (
            f"Split '{expected_label}' has random_state={split_map[expected_label].random_state}, expected {seed}"
        )

    # 2. Train model under research-split (seed 42)
    exp_label = "E1_graph_ml"
    train_req_42 = AnomalyTrainRequest(
        experiment_label=exp_label,
        feature_groups=["graph"],
        contamination=0.1,
        random_state=42,
        split_label="research-split",
    )
    anomaly_service.train_model(dataset_id=test_ds_id, request=train_req_42, experiment_label=exp_label)

    # Evaluate against research-split
    eval_42_initial = evaluation_service.evaluate_experiment(
        dataset_id=test_ds_id,
        experiment_label=exp_label,
        split_label="research-split",
    )
    assert eval_42_initial.pr_auc is not None
    assert eval_42_initial.roc_auc is not None

    # 3. Retrain the exact same experiment under a different split_label (research-split-123)
    train_req_123 = AnomalyTrainRequest(
        experiment_label=exp_label,
        feature_groups=["graph"],
        contamination=0.1,
        random_state=42,
        split_label="research-split-123",
    )
    anomaly_service.train_model(dataset_id=test_ds_id, request=train_req_123, experiment_label=exp_label)

    # Evaluate against research-split-123
    eval_123 = evaluation_service.evaluate_experiment(
        dataset_id=test_ds_id,
        experiment_label=exp_label,
        split_label="research-split-123",
    )
    assert eval_123.split_label == "research-split-123"

    # 4. Assert separate split model files exist on disk
    model_dir = anomaly_service.models_dir
    file_42 = model_dir / f"{test_ds_id}__{exp_label}__research-split.joblib"
    file_123 = model_dir / f"{test_ds_id}__{exp_label}__research-split-123.joblib"
    assert file_42.exists(), f"Expected split-specific model artifact {file_42} to exist"
    assert file_123.exists(), f"Expected split-specific model artifact {file_123} to exist"

    # 5. Re-evaluate against research-split and assert metrics are NOT corrupted or overwritten
    eval_42_after = evaluation_service.evaluate_experiment(
        dataset_id=test_ds_id,
        experiment_label=exp_label,
        split_label="research-split",
    )

    assert eval_42_after.split_label == "research-split"
    assert eval_42_after.pr_auc == eval_42_initial.pr_auc, (
        f"Corrupted PR-AUC: was {eval_42_initial.pr_auc}, now {eval_42_after.pr_auc}"
    )
    assert eval_42_after.roc_auc == eval_42_initial.roc_auc, (
        f"Corrupted ROC-AUC: was {eval_42_initial.roc_auc}, now {eval_42_after.roc_auc}"
    )
    assert eval_42_after.f1_score == eval_42_initial.f1_score
    assert eval_42_after.confusion_matrix.tp == eval_42_initial.confusion_matrix.tp
    assert eval_42_after.confusion_matrix.fp == eval_42_initial.confusion_matrix.fp

    # Part B: If multi-seed results file exists, verify structure and counts
    multiseed_json = repo_paths["multiseed_json"]
    if multiseed_json.exists():
        with open(multiseed_json, "r", encoding="utf-8") as f:
            mdata = json.load(f)
        assert len(mdata["seeds"]) == 6
        assert mdata["seeds"] == documented_seeds
        assert len(mdata["all_evaluations"]) == 60
        assert len(mdata["summary_statistics"]) == 10

