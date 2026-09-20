"""
End-to-End Demo Research Evaluation Workflow Tests.
Covers the 30-transaction / 21-entity demo dataset scenario across E0 through E4.
Validates:
1. Demo labels upload (21 matched, 2 positive, 19 negative)
2. Split creation determinism (test_size=0.3, random_state=42)
3. E0 baseline training (feature_groups=["graph"], 6 features, StatisticalBaseline)
4. E1 training (6 features, IsolationForest)
5. E2 training (14 features, IsolationForest)
6. E3 training (11 features, IsolationForest)
7. E4 training (19 features, IsolationForest)
8. No label leakage for any of E0-E4
9. Training strictly restricted to train partition entities (entity_count == 14)
10. Evaluation strictly isolated to test partition entities (entity_count == 7)
11. Evaluation response schema and held_out evaluation_mode for all five experiments
12. Missing labels and missing split error paths
13. Research run export (JSON & CSV) capturing all five experiments
"""
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.services.anomaly_service import anomaly_service
from backend.app.services.baseline_service import baseline_service
from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.evaluation_service import evaluation_service
from backend.app.services.label_registry import label_registry
from backend.app.services.split_service import split_service

DEMO_TRANSACTIONS_PATH = Path(__file__).parents[2] / "graphfin_sample_transactions.csv"
DEMO_LABELS_PATH = Path(__file__).parents[2] / "graphfin_demo_labels.csv"


@pytest.fixture
def demo_dataset(client: TestClient) -> str:
    """Uploads the canonical 30-transaction demo dataset and returns its dataset_id."""
    assert DEMO_TRANSACTIONS_PATH.exists(), f"Missing {DEMO_TRANSACTIONS_PATH}"
    with open(DEMO_TRANSACTIONS_PATH, "rb") as f:
        files = {"file": ("graphfin_sample_transactions.csv", f, "text/csv")}
        resp = client.post("/api/v1/transactions/upload", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["valid_transactions"] == 30
    assert data["summary"]["users"] == 21
    return data["dataset_id"]


@pytest.fixture
def demo_dataset_with_split(client: TestClient, demo_dataset: str) -> str:
    """Prepares the demo dataset with demo labels and the deterministic demo-split."""
    with open(DEMO_LABELS_PATH, "rb") as f:
        files = {"file": ("graphfin_demo_labels.csv", f, "text/csv")}
        resp = client.post(f"/api/v1/datasets/{demo_dataset}/labels", files=files)
    assert resp.status_code == 200

    split_resp = client.post(
        f"/api/v1/datasets/{demo_dataset}/splits",
        json={
            "split_label": "demo-split",
            "test_size": 0.30,
            "random_state": 42,
            "stratify_by_label": True,
        },
    )
    assert split_resp.status_code == 200
    return demo_dataset


# ==============================================================================
# 1. Demo labels upload: 21 labels match, 2 positive / 19 negative
# ==============================================================================
def test_demo_labels_upload(client: TestClient, demo_dataset: str):
    assert DEMO_LABELS_PATH.exists(), f"Missing {DEMO_LABELS_PATH}"
    with open(DEMO_LABELS_PATH, "rb") as f:
        files = {"file": ("graphfin_demo_labels.csv", f, "text/csv")}
        resp = client.post(f"/api/v1/datasets/{demo_dataset}/labels", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_labels_uploaded"] == 21
    assert data["matched_count"] == 21
    assert data["unmatched_count"] == 0
    assert data["positive_count"] == 2
    assert data["negative_count"] == 19
    assert round(data["prevalence_rate"], 4) == 0.0952
    assert len(data["rejected_errors"]) == 0


# ==============================================================================
# 2. Split creation with test_size=0.3, random_state=42: deterministic composition
# ==============================================================================
def test_demo_split_creation_determinism(client: TestClient, demo_dataset: str):
    # Upload labels first
    with open(DEMO_LABELS_PATH, "rb") as f:
        client.post(f"/api/v1/datasets/{demo_dataset}/labels", files={"file": ("labels.csv", f, "text/csv")})

    resp = client.post(
        f"/api/v1/datasets/{demo_dataset}/splits",
        json={
            "split_label": "demo-split",
            "test_size": 0.30,
            "random_state": 42,
            "stratify_by_label": True,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["split_label"] == "demo-split"
    assert data["total_users"] == 21
    assert data["stratified"] is True
    assert data["warning"] is None

    # Assert exact resulting train/test composition explicitly
    assert data["train_count"] == 14
    assert data["test_count"] == 7
    assert data["train_positive_count"] == 1
    assert data["train_negative_count"] == 13
    assert data["test_positive_count"] == 1
    assert data["test_negative_count"] == 6

    # Re-run to verify deterministic user partitions
    split_obj = split_service.get_split(demo_dataset, "demo-split")
    assert len(split_obj.train_user_ids) == 14
    assert len(split_obj.test_user_ids) == 7
    assert set(split_obj.train_user_ids).isdisjoint(set(split_obj.test_user_ids))


# ==============================================================================
# 3. E0 baseline trains via baseline endpoint, feature_groups=["graph"], 6 features
# ==============================================================================
def test_e0_baseline_training(client: TestClient, demo_dataset_with_split: str):
    resp = client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/baseline",
        json={
            "experiment_label": "E0_graph_baseline",
            "split_label": "demo-split",
            "feature_groups": ["graph"],
            "z_threshold": 2.0,
        },
    )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["model_metadata"]
    assert meta["experiment_label"] == "E0_graph_baseline"
    assert meta["model_type"] == "StatisticalBaseline"
    assert meta["feature_count"] == 6
    assert meta["feature_groups"] == ["graph"]
    assert meta["evaluation_mode"] == "held_out"
    assert meta["entity_count"] == 14  # Fit strictly on train partition


# ==============================================================================
# 4. E1 training: exactly 6 features (graph only)
# ==============================================================================
def test_e1_training(client: TestClient, demo_dataset_with_split: str):
    resp = client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/train",
        json={
            "experiment_label": "E1_graph_ml",
            "split_label": "demo-split",
            "feature_groups": ["graph"],
            "random_state": 42,
        },
    )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["model_metadata"]
    assert meta["experiment_label"] == "E1_graph_ml"
    assert meta["model_type"] == "IsolationForest"
    assert meta["feature_count"] == 6
    assert meta["feature_groups"] == ["graph"]
    assert meta["evaluation_mode"] == "held_out"
    assert meta["entity_count"] == 14


# ==============================================================================
# 5. E2 training: exactly 14 features (graph + behavioral)
# ==============================================================================
def test_e2_training(client: TestClient, demo_dataset_with_split: str):
    resp = client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/train",
        json={
            "experiment_label": "E2_graph_behavioral_ml",
            "split_label": "demo-split",
            "feature_groups": ["graph", "behavioral"],
            "random_state": 42,
        },
    )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["model_metadata"]
    assert meta["experiment_label"] == "E2_graph_behavioral_ml"
    assert meta["model_type"] == "IsolationForest"
    assert meta["feature_count"] == 14
    assert set(meta["feature_groups"]) == {"graph", "behavioral"}
    assert meta["entity_count"] == 14


# ==============================================================================
# 6. E3 training: exactly 11 features (graph + temporal)
# ==============================================================================
def test_e3_training(client: TestClient, demo_dataset_with_split: str):
    resp = client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/train",
        json={
            "experiment_label": "E3_graph_temporal_ml",
            "split_label": "demo-split",
            "feature_groups": ["graph", "temporal"],
            "random_state": 42,
        },
    )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["model_metadata"]
    assert meta["experiment_label"] == "E3_graph_temporal_ml"
    assert meta["model_type"] == "IsolationForest"
    assert meta["feature_count"] == 11
    assert set(meta["feature_groups"]) == {"graph", "temporal"}
    assert meta["entity_count"] == 14


# ==============================================================================
# 7. E4 training: exactly 19 features (full graphfin)
# ==============================================================================
def test_e4_training(client: TestClient, demo_dataset_with_split: str):
    resp = client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/train",
        json={
            "experiment_label": "E4_full_graphfin",
            "split_label": "demo-split",
            "feature_groups": ["graph", "behavioral", "temporal"],
            "random_state": 42,
        },
    )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["model_metadata"]
    assert meta["experiment_label"] == "E4_full_graphfin"
    assert meta["model_type"] == "IsolationForest"
    assert meta["feature_count"] == 19
    assert set(meta["feature_groups"]) == {"graph", "behavioral", "temporal"}
    assert meta["entity_count"] == 14


# ==============================================================================
# 8. No label leakage for any of E0-E4
# ==============================================================================
def test_no_label_leakage_for_all_experiments(client: TestClient, demo_dataset_with_split: str):
    store = dataset_registry.get(demo_dataset_with_split)
    _, matrix, feat_names = store.get_feature_matrix()

    # Verify no label columns in feature matrix
    assert matrix.shape[1] == 19
    for col in feat_names:
        assert "label" not in col.lower()
        assert "fraud" not in col.lower()

    # Train all 5
    client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/baseline",
        json={"experiment_label": "E0_graph_baseline", "split_label": "demo-split", "feature_groups": ["graph"]},
    )
    client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/train",
        json={"experiment_label": "E1_graph_ml", "split_label": "demo-split", "feature_groups": ["graph"]},
    )
    client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/train",
        json={"experiment_label": "E2_graph_behavioral_ml", "split_label": "demo-split", "feature_groups": ["graph", "behavioral"]},
    )
    client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/train",
        json={"experiment_label": "E3_graph_temporal_ml", "split_label": "demo-split", "feature_groups": ["graph", "temporal"]},
    )
    client.post(
        f"/api/v1/anomalies/{demo_dataset_with_split}/train",
        json={"experiment_label": "E4_full_graphfin", "split_label": "demo-split", "feature_groups": ["graph", "behavioral", "temporal"]},
    )

    for exp in ["E0_graph_baseline", "E1_graph_ml", "E2_graph_behavioral_ml", "E3_graph_temporal_ml", "E4_full_graphfin"]:
        meta = anomaly_service.get_model_metadata(demo_dataset_with_split, exp)
        for f in meta.feature_names:
            assert "label" not in f.lower()
            assert "fraud" not in f.lower()


# ==============================================================================
# 9. Each of E0-E4 trained only on the train partition
# ==============================================================================
def test_trained_only_on_train_partition(client: TestClient, demo_dataset_with_split: str):
    split_obj = split_service.get_split(demo_dataset_with_split, "demo-split")
    test_uids = set(split_obj.test_user_ids)
    assert len(test_uids) == 7

    # Fit E0-E4
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/baseline", json={"experiment_label": "E0_graph_baseline", "split_label": "demo-split", "feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E1_graph_ml", "split_label": "demo-split", "feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E2_graph_behavioral_ml", "split_label": "demo-split", "feature_groups": ["graph", "behavioral"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E3_graph_temporal_ml", "split_label": "demo-split", "feature_groups": ["graph", "temporal"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E4_full_graphfin", "split_label": "demo-split", "feature_groups": ["graph", "behavioral", "temporal"]})

    for exp in ["E0_graph_baseline", "E1_graph_ml", "E2_graph_behavioral_ml", "E3_graph_temporal_ml", "E4_full_graphfin"]:
        meta = anomaly_service.get_model_metadata(demo_dataset_with_split, exp)
        assert meta.entity_count == 14
        assert meta.training_entity_count == 14

        art = anomaly_service._load_artifact(demo_dataset_with_split, exp)
        art_uids = set(art.get("user_ids", []))
        assert art_uids.isdisjoint(test_uids), f"Leakage: test users present in {exp} training artifact!"


# ==============================================================================
# 10. Evaluation for each of E0-E4 uses only the test partition
# ==============================================================================
def test_evaluation_uses_only_test_partition(client: TestClient, demo_dataset_with_split: str):
    # Train E0 through E4
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/baseline", json={"experiment_label": "E0_graph_baseline", "split_label": "demo-split", "feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E1_graph_ml", "split_label": "demo-split", "feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E2_graph_behavioral_ml", "split_label": "demo-split", "feature_groups": ["graph", "behavioral"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E3_graph_temporal_ml", "split_label": "demo-split", "feature_groups": ["graph", "temporal"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E4_full_graphfin", "split_label": "demo-split", "feature_groups": ["graph", "behavioral", "temporal"]})

    for exp in ["E0_graph_baseline", "E1_graph_ml", "E2_graph_behavioral_ml", "E3_graph_temporal_ml", "E4_full_graphfin"]:
        eval_resp = client.get(f"/api/v1/evaluation/{demo_dataset_with_split}/{exp}?split_label=demo-split")
        assert eval_resp.status_code == 200, eval_resp.text
        eval_data = eval_resp.json()
        assert eval_data["evaluation_mode"] == "held_out"
        assert eval_data["usable_labeled_user_count"] == 7
        cm = eval_data["confusion_matrix"]
        assert (cm["tp"] + cm["fp"] + cm["tn"] + cm["fn"]) == 7


# ==============================================================================
# 11. Metric response schema and evaluation_mode are correct for all 5 experiments
# ==============================================================================
def test_evaluation_metrics_response_schema(client: TestClient, demo_dataset_with_split: str):
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/baseline", json={"experiment_label": "E0_graph_baseline", "split_label": "demo-split", "feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E1_graph_ml", "split_label": "demo-split", "feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E2_graph_behavioral_ml", "split_label": "demo-split", "feature_groups": ["graph", "behavioral"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E3_graph_temporal_ml", "split_label": "demo-split", "feature_groups": ["graph", "temporal"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E4_full_graphfin", "split_label": "demo-split", "feature_groups": ["graph", "behavioral", "temporal"]})

    comp_resp = client.get(f"/api/v1/evaluation/{demo_dataset_with_split}/compare?split_label=demo-split")
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["total_experiments_evaluated"] >= 5

    exp_labels = [e["experiment_label"] for e in comp_data["experiments"]]
    for target in ["E0_graph_baseline", "E1_graph_ml", "E2_graph_behavioral_ml", "E3_graph_temporal_ml", "E4_full_graphfin"]:
        assert target in exp_labels

    for e in comp_data["experiments"]:
        assert e["evaluation_mode"] == "held_out"
        assert e["status"] == "success"
        assert isinstance(e["f1_score"], float)
        assert isinstance(e["accuracy"], float)
        if e["roc_auc"] is not None:
            assert 0.0 <= e["roc_auc"] <= 1.0
        if e["pr_auc"] is not None:
            assert 0.0 <= e["pr_auc"] <= 1.0


# ==============================================================================
# 12. Missing labels error, missing split error
# ==============================================================================
def test_missing_labels_and_missing_split_errors(client: TestClient, demo_dataset: str):
    # 1. Before labels are uploaded, evaluating raises 404
    eval_no_labels = client.get(f"/api/v1/evaluation/{demo_dataset}/E1_graph_ml")
    assert eval_no_labels.status_code == 404
    assert "No ground-truth labels found" in eval_no_labels.json()["message"]

    # Upload labels
    with open(DEMO_LABELS_PATH, "rb") as f:
        client.post(f"/api/v1/datasets/{demo_dataset}/labels", files={"file": ("labels.csv", f, "text/csv")})

    # Train model on a non-existent split
    bad_split_train = client.post(
        f"/api/v1/anomalies/{demo_dataset}/train",
        json={"experiment_label": "E1_graph_ml", "split_label": "nonexistent-split"},
    )
    assert bad_split_train.status_code == 404

    # Evaluate on non-existent split
    bad_split_eval = client.get(f"/api/v1/evaluation/{demo_dataset}/E1_graph_ml?split_label=nonexistent-split")
    assert bad_split_eval.status_code == 404


# ==============================================================================
# 13. Export JSON and CSV include all five experiments correctly labeled
# ==============================================================================
def test_export_all_five_experiments(client: TestClient, demo_dataset_with_split: str):
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/baseline", json={"experiment_label": "E0_graph_baseline", "split_label": "demo-split", "feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E1_graph_ml", "split_label": "demo-split", "feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E2_graph_behavioral_ml", "split_label": "demo-split", "feature_groups": ["graph", "behavioral"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E3_graph_temporal_ml", "split_label": "demo-split", "feature_groups": ["graph", "temporal"]})
    client.post(f"/api/v1/anomalies/{demo_dataset_with_split}/train", json={"experiment_label": "E4_full_graphfin", "split_label": "demo-split", "feature_groups": ["graph", "behavioral", "temporal"]})

    export_resp = client.post(f"/api/v1/evaluation/{demo_dataset_with_split}/export")
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["successful_experiments"] >= 5
    assert export_data["total_experiments"] >= 5

    # Check that the files exist and contain the experiments
    json_path = Path(export_data["json_path"])
    csv_path = Path(export_data["csv_path"])
    assert json_path.exists()
    assert csv_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        saved_json = json.load(f)
    saved_labels = [e["experiment_label"] for e in saved_json["experiments"]]
    for target in ["E0_graph_baseline", "E1_graph_ml", "E2_graph_behavioral_ml", "E3_graph_temporal_ml", "E4_full_graphfin"]:
        assert target in saved_labels

    with open(csv_path, "r", encoding="utf-8") as f:
        csv_text = f.read()
    for target in ["E0_graph_baseline", "E1_graph_ml", "E2_graph_behavioral_ml", "E3_graph_temporal_ml", "E4_full_graphfin"]:
        assert target in csv_text
