"""
Unit and integration tests for entity-level held-out train/test split evaluation mode.
Tests all 8 required testing scenarios:
1. Split creation ratio & determinism
2. Stratification & graceful fallback with documented warning
3. No leakage in model fit (features fit strictly on train partition)
4. Held-out evaluation entity isolation (evaluates only test partition)
5. Coexistence of in-sample and held-out modes without cross-contamination
6. Backward compatibility (in_sample remains default when no split is specified)
7. Missing split lookup returns clear 404 error
8. Explanation reason-code percentiles computed only from train partition
"""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.services.anomaly_service import anomaly_service
from backend.app.services.baseline_service import baseline_service
from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.evaluation_service import evaluation_service
from backend.app.services.label_registry import label_registry
from backend.app.services.split_service import split_service


def upload_test_dataset(client: TestClient, csv_bytes: bytes) -> str:
    files = {"file": ("transactions.csv", csv_bytes, "text/csv")}
    resp = client.post("/api/v1/transactions/upload", files=files)
    assert resp.status_code == 200, resp.text
    return resp.json()["dataset_id"]


def upload_test_labels(client: TestClient, dataset_id: str, label_csv_str: str):
    files = {"file": ("labels.csv", label_csv_str.encode("utf-8"), "text/csv")}
    resp = client.post(f"/api/v1/datasets/{dataset_id}/labels", files=files)
    assert resp.status_code == 200, resp.text
    return resp.json()


# Helper: Sample 11 users with 3 frauds, 8 normals
SAMPLE_11_LABELS = (
    "user_id,label\n"
    "USR_ALICE,0\n"
    "USR_BOB,0\n"
    "USR_CHARLIE,0\n"
    "USR_DAVID,0\n"
    "USR_EMILY,0\n"
    "USR_FRANK,0\n"
    "USR_GRACE,0\n"
    "USR_HENRY,0\n"
    "USR_BURST_01,1\n"
    "USR_WHALE_01,1\n"
    "USR_MERCHANT_99,1\n"
)


# ==============================================================================
# 1. Split creation with default params produces requested test_size ratio & is deterministic
# ==============================================================================
def test_split_creation_ratio_and_determinism(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_test_dataset(client, sample_csv_bytes)
    upload_test_labels(client, dataset_id, SAMPLE_11_LABELS)

    # Create split with default test_size (0.3)
    resp = client.post(
        f"/api/v1/datasets/{dataset_id}/splits",
        json={"split_label": "default", "test_size": 0.3, "random_state": 42},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["dataset_id"] == dataset_id
    assert data["split_label"] == "default"
    assert data["total_users"] == 11
    # 11 * 0.3 = 3.3 -> test partition has 3 or 4 users; train has 8 or 7
    assert data["test_count"] in (3, 4)
    assert data["train_count"] + data["test_count"] == 11
    assert data["random_state"] == 42
    assert data["test_size"] == 0.3

    # Test GET summary endpoint
    get_resp = client.get(f"/api/v1/datasets/{dataset_id}/splits/default")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["train_count"] == data["train_count"]
    assert get_data["test_count"] == data["test_count"]

    # Determinism: creating the split again with the exact same seed yields identical assignment
    assignment_1 = split_service.get_split(dataset_id, "default")
    split_service.clear()
    assignment_2 = split_service.create_split(
        dataset_id=dataset_id, test_size=0.3, random_state=42, split_label="default"
    )

    assert assignment_1.train_user_ids == assignment_2.train_user_ids
    assert assignment_1.test_user_ids == assignment_2.test_user_ids


# ==============================================================================
# 2. Stratified split preserves similar prevalence; falls back gracefully when < 2 positives
# ==============================================================================
def test_stratified_split_and_graceful_fallback(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_test_dataset(client, sample_csv_bytes)

    # Scenario A: Adequate positives (3 positive out of 11 -> positive >= 2, negative >= 2)
    upload_test_labels(client, dataset_id, SAMPLE_11_LABELS)
    split_strat = split_service.create_split(
        dataset_id=dataset_id,
        test_size=0.3,
        random_state=42,
        stratify_by_label=True,
        split_label="strat_ok",
    )
    assert split_strat.stratified is True
    assert split_strat.warning is None
    # Both train and test should contain positive cases when stratified
    assert split_strat.train_positive_count >= 1
    assert split_strat.test_positive_count >= 1

    # Scenario B: Insufficient positives (only 1 positive case)
    # Clear and re-upload with only 1 positive
    label_registry.clear()
    split_service.clear()
    one_pos_labels = (
        "user_id,label\n"
        "USR_ALICE,0\n"
        "USR_BOB,0\n"
        "USR_CHARLIE,0\n"
        "USR_DAVID,0\n"
        "USR_EMILY,0\n"
        "USR_FRANK,0\n"
        "USR_GRACE,0\n"
        "USR_HENRY,0\n"
        "USR_BURST_01,0\n"
        "USR_WHALE_01,0\n"
        "USR_MERCHANT_99,1\n"
    )
    upload_test_labels(client, dataset_id, one_pos_labels)

    split_fallback = split_service.create_split(
        dataset_id=dataset_id,
        test_size=0.3,
        random_state=42,
        stratify_by_label=True,
        split_label="fallback_split",
    )
    assert split_fallback.stratified is False
    assert split_fallback.warning is not None
    assert "at least 2 members" in split_fallback.warning
    assert split_fallback.train_count + split_fallback.test_count == 11


# ==============================================================================
# 3. Training with split_label uses ONLY train partition users in fitted feature matrix
# ==============================================================================
def test_training_with_split_label_no_leakage(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_test_dataset(client, sample_csv_bytes)
    upload_test_labels(client, dataset_id, SAMPLE_11_LABELS)

    # Create split
    split_obj = split_service.create_split(
        dataset_id=dataset_id, test_size=0.3, random_state=42, split_label="held_out_split"
    )
    train_uids = set(split_obj.train_user_ids)
    test_uids = set(split_obj.test_user_ids)

    # Train Isolation Forest with split_label
    train_resp = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"experiment_label": "e4_heldout", "split_label": "held_out_split"},
    )
    assert train_resp.status_code == 200, train_resp.text
    meta = train_resp.json()["model_metadata"]

    # Assert directly on metadata
    assert meta["split_label"] == "held_out_split"
    assert meta["evaluation_mode"] == "held_out"
    assert meta["training_entity_count"] == len(train_uids)
    assert meta["entity_count"] == len(train_uids)

    # Assert directly on model artifact: training user_ids contains NO test users
    artifact = anomaly_service._load_artifact(dataset_id, "e4_heldout")
    artifact_uids = set(artifact["user_ids"])
    assert artifact_uids == train_uids
    assert artifact_uids.isdisjoint(test_uids), "Leakage detected: test users found in fitted model user_ids!"


# ==============================================================================
# 4. Evaluating a held-out-trained experiment only scores test partition users
# ==============================================================================
def test_evaluating_held_out_scores_only_test_partition(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_test_dataset(client, sample_csv_bytes)
    upload_test_labels(client, dataset_id, SAMPLE_11_LABELS)

    split_obj = split_service.create_split(
        dataset_id=dataset_id, test_size=0.3, random_state=42, split_label="eval_split"
    )

    # Train with split
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"experiment_label": "e1_heldout", "split_label": "eval_split"},
    )

    # Evaluate experiment
    eval_resp = client.get(f"/api/v1/evaluation/{dataset_id}/e1_heldout")
    assert eval_resp.status_code == 200, eval_resp.text
    eval_data = eval_resp.json()

    assert eval_data["evaluation_mode"] == "held_out"
    assert eval_data["split_label"] == "eval_split"
    # Usable labeled user count matches exactly the test partition count!
    assert eval_data["usable_labeled_user_count"] == len(split_obj.test_user_ids)
    assert eval_data["usable_labeled_user_count"] < 11


# ==============================================================================
# 5. Held-out evaluation metrics legitimately differ from in-sample metrics & coexist
# ==============================================================================
def test_held_out_and_in_sample_coexist(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_test_dataset(client, sample_csv_bytes)
    upload_test_labels(client, dataset_id, SAMPLE_11_LABELS)

    split_obj = split_service.create_split(
        dataset_id=dataset_id, test_size=0.3, random_state=42, split_label="coexist_split"
    )

    # 1. Train in-sample model
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"experiment_label": "e4_insample", "feature_groups": ["graph", "behavioral", "temporal"]},
    )

    # 2. Train held-out model
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={
            "experiment_label": "e4_heldout",
            "feature_groups": ["graph", "behavioral", "temporal"],
            "split_label": "coexist_split",
        },
    )

    # Evaluate both individually
    eval_in = client.get(f"/api/v1/evaluation/{dataset_id}/e4_insample").json()
    eval_out = client.get(f"/api/v1/evaluation/{dataset_id}/e4_heldout").json()

    assert eval_in["evaluation_mode"] == "in_sample"
    assert eval_in["usable_labeled_user_count"] == 11

    assert eval_out["evaluation_mode"] == "held_out"
    assert eval_out["usable_labeled_user_count"] == len(split_obj.test_user_ids)

    # Call compare endpoint
    comp_resp = client.get(f"/api/v1/evaluation/{dataset_id}/compare")
    assert comp_resp.status_code == 200, comp_resp.text
    comp_data = comp_resp.json()

    assert comp_data["by_evaluation_mode"] is not None
    assert "in_sample" in comp_data["by_evaluation_mode"]
    assert "held_out" in comp_data["by_evaluation_mode"]

    in_labels = [e["experiment_label"] for e in comp_data["by_evaluation_mode"]["in_sample"]]
    out_labels = [e["experiment_label"] for e in comp_data["by_evaluation_mode"]["held_out"]]

    assert "e4_insample" in in_labels
    assert "e4_heldout" in out_labels


# ==============================================================================
# 6. Backward compatibility: calls without split_label produce evaluation_mode "in_sample"
# ==============================================================================
def test_backward_compatibility_no_split(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_test_dataset(client, sample_csv_bytes)
    upload_test_labels(client, dataset_id, SAMPLE_11_LABELS)

    # Train without split_label
    train_resp = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"experiment_label": "legacy_exp"},
    )
    assert train_resp.status_code == 200
    meta = train_resp.json()["model_metadata"]
    assert meta["evaluation_mode"] == "in_sample"
    assert meta["split_label"] is None
    assert meta["entity_count"] == 11

    # Evaluate without split_label
    eval_resp = client.get(f"/api/v1/evaluation/{dataset_id}/legacy_exp")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["evaluation_mode"] == "in_sample"
    assert eval_data["split_label"] is None
    assert eval_data["usable_labeled_user_count"] == 11


# ==============================================================================
# 7. Missing split_label lookup returns a clear error, not a silent fallback
# ==============================================================================
def test_missing_split_label_error(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_test_dataset(client, sample_csv_bytes)
    upload_test_labels(client, dataset_id, SAMPLE_11_LABELS)

    # Training with non-existent split returns 404
    train_resp = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"experiment_label": "err_exp", "split_label": "non_existent_split_123"},
    )
    assert train_resp.status_code == 404
    assert "not found" in train_resp.json()["message"].lower()

    # GET non-existent split summary returns 404
    get_resp = client.get(f"/api/v1/datasets/{dataset_id}/splits/non_existent_split_123")
    assert get_resp.status_code == 404

    # Evaluating with non-existent split returns 404
    client.post(f"/api/v1/anomalies/{dataset_id}/train", json={"experiment_label": "default"})
    eval_resp = client.get(f"/api/v1/evaluation/{dataset_id}/default?split_label=non_existent_split_123")
    assert eval_resp.status_code == 404


# ==============================================================================
# 8. Reason-code percentiles for held-out-trained model are computed from train partition only
# ==============================================================================
def test_reason_code_percentiles_computed_from_train_partition_only(
    client: TestClient, sample_csv_bytes: bytes
):
    dataset_id = upload_test_dataset(client, sample_csv_bytes)
    upload_test_labels(client, dataset_id, SAMPLE_11_LABELS)

    split_obj = split_service.create_split(
        dataset_id=dataset_id, test_size=0.4, random_state=42, split_label="stats_split"
    )

    # Train held-out model
    train_resp = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={"experiment_label": "stats_exp", "split_label": "stats_split"},
    )
    meta = train_resp.json()["model_metadata"]
    feature_stats = meta["feature_stats"]

    # Verify directly: compute transaction_count percentiles on train partition vs full population
    store = dataset_registry.get(dataset_id)
    user_ids, full_matrix, _ = store.get_feature_matrix()
    from backend.app.services.feature_service import FEATURE_NAMES

    tc_idx = FEATURE_NAMES.index("transaction_count")
    full_tc = full_matrix[:, tc_idx]

    uid_to_idx = {uid: i for i, uid in enumerate(user_ids)}
    train_tc = full_matrix[[uid_to_idx[u] for u in split_obj.train_user_ids], tc_idx]

    # Stored p90 must match the train partition p90 exactly
    expected_train_p90 = float(round(np.percentile(train_tc, 90), 4))
    stored_p90 = feature_stats["transaction_count"]["p90"]

    assert stored_p90 == expected_train_p90
    assert meta["training_entity_count"] == len(split_obj.train_user_ids)
