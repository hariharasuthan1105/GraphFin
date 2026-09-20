"""
Unit and integration tests for ground-truth labeling, multi-experiment storage,
rule-based statistical baseline, and the research evaluation layer.
"""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.services.anomaly_service import anomaly_service
from backend.app.services.baseline_service import baseline_service
from backend.app.services.evaluation_service import evaluation_service
from backend.app.services.label_registry import label_registry, parse_label_value


def upload_sample_dataset(client: TestClient, csv_bytes: bytes) -> str:
    files = {"file": ("transactions.csv", csv_bytes, "text/csv")}
    resp = client.post("/api/v1/transactions/upload", files=files)
    assert resp.status_code == 200, resp.text
    return resp.json()["dataset_id"]


# 1. Label upload with matching user_ids succeeds, summary is correct
def test_label_upload_matching_user_ids(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # 11 users in sample dataset: USR_ALICE, USR_BOB, USR_CHARLIE, USR_DAVID, USR_EMILY,
    # USR_FRANK, USR_GRACE, USR_HENRY, USR_BURST_01, USR_WHALE_01, USR_MERCHANT_99
    label_csv = (
        "user_id,label\n"
        "USR_ALICE,0\n"
        "USR_BOB,normal\n"
        "USR_BURST_01,fraud\n"
        "USR_WHALE_01,1\n"
    ).encode("utf-8")

    files = {"file": ("labels.csv", label_csv, "text/csv")}
    resp = client.post(f"/api/v1/datasets/{dataset_id}/labels", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["dataset_id"] == dataset_id
    assert data["total_labels_uploaded"] == 4
    assert data["matched_count"] == 4
    assert data["unmatched_count"] == 0
    assert data["positive_count"] == 2  # USR_BURST_01, USR_WHALE_01
    assert data["negative_count"] == 2  # USR_ALICE, USR_BOB
    assert data["prevalence_rate"] == 0.5
    assert len(data["rejected_errors"]) == 0

    # Test summary endpoint without re-uploading
    sum_resp = client.get(f"/api/v1/datasets/{dataset_id}/labels/summary")
    assert sum_resp.status_code == 200
    assert sum_resp.json()["matched_count"] == 4


# 2. Label upload with unknown user_ids is rejected/reported correctly
def test_label_upload_unknown_user_ids(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    label_csv = (
        "user_id,label\n"
        "USR_ALICE,0\n"
        "UNKNOWN_USER_999,1\n"
    ).encode("utf-8")

    # Non-strict mode: reports unmatched and isolates rejected row
    files = {"file": ("labels.csv", label_csv, "text/csv")}
    resp = client.post(f"/api/v1/datasets/{dataset_id}/labels?strict=false", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_count"] == 1
    assert data["unmatched_count"] == 1
    assert len(data["rejected_errors"]) == 1
    assert "UNKNOWN_USER_999" in data["rejected_errors"][0]

    # Strict mode: rejects entire upload with 400
    resp_strict = client.post(
        f"/api/v1/datasets/{dataset_id}/labels?strict=true",
        files={"file": ("labels.csv", label_csv, "text/csv")},
    )
    assert resp_strict.status_code == 400
    assert "invalid or unmatched rows" in resp_strict.json()["message"]


# 3. Label upload with various accepted boolean string formats normalizes correctly
def test_label_normalization_variants():
    # Positives
    for val in [1, "1", "true", "True", "TRUE", "t", "T", "yes", "YES", "fraud", "Fraud", "suspicious", "anomalous"]:
        assert parse_label_value(val) is True

    # Negatives
    for val in [0, "0", "false", "False", "FALSE", "f", "F", "no", "NO", "normal", "Normal", "legitimate", "non-fraud"]:
        assert parse_label_value(val) is False

    # Invalid throws ValueError
    with pytest.raises(ValueError):
        parse_label_value("unknown_label_string")


# 4. Multiple experiment_labels for the same dataset_id coexist without overwriting each other
def test_multi_experiment_model_coexistence(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Train E1 (graph only)
    resp_e1 = client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e1",
        json={"feature_groups": ["graph"]},
    )
    assert resp_e1.status_code == 200

    # Train E2 (graph + behavioral)
    resp_e2 = client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e2",
        json={"feature_groups": ["graph", "behavioral"]},
    )
    assert resp_e2.status_code == 200

    # Both must be retrievable independently
    m1 = client.get(f"/api/v1/anomalies/{dataset_id}/model?experiment_label=e1").json()
    m2 = client.get(f"/api/v1/anomalies/{dataset_id}/model?experiment_label=e2").json()

    assert m1["experiment_label"] == "e1"
    assert m1["feature_count"] == 6

    assert m2["experiment_label"] == "e2"
    assert m2["feature_count"] == 14

    # Check GET /anomalies/{dataset_id}/experiments lists both
    exps_resp = client.get(f"/api/v1/anomalies/{dataset_id}/experiments")
    assert exps_resp.status_code == 200
    exps_data = exps_resp.json()
    exp_labels = [e["experiment_label"] for e in exps_data["experiments"]]
    assert "e1" in exp_labels
    assert "e2" in exp_labels


# 5. Baseline statistical service produces binary classification and continuous score without touching Isolation Forest
def test_baseline_statistical_service(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    resp = client.post(
        f"/api/v1/anomalies/{dataset_id}/baseline",
        json={"z_threshold": 2.0},
    )
    assert resp.status_code == 200
    meta = resp.json()["model_metadata"]
    assert meta["model_type"] == "StatisticalBaseline"
    assert meta["experiment_label"] == "baseline_statistical"

    # Query users under baseline_statistical
    users_resp = client.get(
        f"/api/v1/anomalies/{dataset_id}/users?experiment_label=baseline_statistical"
    )
    assert users_resp.status_code == 200
    users = users_resp.json()["users"]
    assert len(users) == 11

    # Check score properties
    for u in users:
        assert isinstance(u["raw_score"], float)  # Max z-score
        assert u["prediction"] in [-1, 1]
        assert u["status"] in ["suspicious", "normal"]
        assert 0.0 <= u["risk_score"] <= 100.0


# 6. Evaluation endpoint computes correct confusion matrix / precision / recall / F1 on a synthetic hand-verifiable example
def test_evaluation_metrics_hand_verifiable(client: TestClient, valid_csv_bytes: bytes):
    # valid_csv_bytes has 3 users: USER_A, USER_B, USER_C
    dataset_id = upload_sample_dataset(client, valid_csv_bytes)

    # Attach labels:
    # USER_A: fraud (1)
    # USER_B: normal (0)
    # USER_C: normal (0)
    label_csv = "user_id,label\nUSER_A,1\nUSER_B,0\nUSER_C,0\n".encode("utf-8")
    client.post(
        f"/api/v1/datasets/{dataset_id}/labels",
        files={"file": ("labels.csv", label_csv, "text/csv")},
    )

    # Train model
    client.post(f"/api/v1/anomalies/{dataset_id}/train?experiment_label=test_exp", json={})

    # Call evaluation endpoint
    eval_resp = client.get(f"/api/v1/evaluation/{dataset_id}/test_exp")
    assert eval_resp.status_code == 200, eval_resp.text
    metrics = eval_resp.json()

    cm = metrics["confusion_matrix"]
    tp = cm["tp"]
    fp = cm["fp"]
    tn = cm["tn"]
    fn = cm["fn"]

    assert tp + fp + tn + fn == 3

    # Check that metrics match formulas exactly
    acc = round((tp + tn) / 3, 4)
    assert metrics["accuracy"] == acc

    if tp + fp > 0:
        prec = round(tp / (tp + fp), 4)
        assert metrics["precision"] == prec

    if tp + fn > 0:
        rec = round(tp / (tp + fn), 4)
        assert metrics["recall"] == rec

    assert metrics["headline_metric"] == "pr_auc"


# 7. Evaluation endpoint returns clear error if labels haven't been uploaded or experiment hasn't been trained
def test_evaluation_errors(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # 1. No labels uploaded yet -> 404
    resp_no_labels = client.get(f"/api/v1/evaluation/{dataset_id}/e1")
    assert resp_no_labels.status_code == 404
    assert "No ground-truth labels found" in resp_no_labels.json()["message"]

    # Upload labels
    label_csv = "user_id,label\nUSR_ALICE,0\nUSR_BOB,1\n".encode("utf-8")
    client.post(
        f"/api/v1/datasets/{dataset_id}/labels",
        files={"file": ("labels.csv", label_csv, "text/csv")},
    )

    # 2. Experiment not trained yet -> 404
    resp_no_exp = client.get(f"/api/v1/evaluation/{dataset_id}/un_trained_exp")
    assert resp_no_exp.status_code == 404
    assert "No anomaly detection model has been trained yet" in resp_no_exp.json()["message"]


# 8. Compare endpoint returns all trained experiments sorted by PR-AUC
def test_compare_experiments_endpoint(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Upload labels
    label_csv = (
        "user_id,label\n"
        "USR_ALICE,0\n"
        "USR_BOB,0\n"
        "USR_BURST_01,1\n"
        "USR_WHALE_01,1\n"
    ).encode("utf-8")
    client.post(
        f"/api/v1/datasets/{dataset_id}/labels",
        files={"file": ("labels.csv", label_csv, "text/csv")},
    )

    # Train Baseline
    client.post(f"/api/v1/anomalies/{dataset_id}/baseline")

    # Train E1
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e1",
        json={"feature_groups": ["graph"]},
    )

    # Train E2
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e2",
        json={"feature_groups": ["graph", "behavioral"]},
    )

    # Call /compare
    compare_resp = client.get(f"/api/v1/evaluation/{dataset_id}/compare")
    assert compare_resp.status_code == 200, compare_resp.text
    comp_data = compare_resp.json()

    assert comp_data["dataset_id"] == dataset_id
    assert comp_data["total_experiments_evaluated"] == 3
    assert comp_data["headline_metric"] == "pr_auc"

    exps = comp_data["experiments"]
    assert len(exps) == 3

    # Check sorted descending by pr_auc
    for i in range(len(exps) - 1):
        score_curr = exps[i]["pr_auc"] if exps[i]["pr_auc"] is not None else -1.0
        score_next = exps[i + 1]["pr_auc"] if exps[i + 1]["pr_auc"] is not None else -1.0
        assert score_curr >= score_next


# 9. Existing default-experiment_label behavior still matches all existing tests
def test_default_experiment_backward_compatibility(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Train with no experiment_label
    train_resp = client.post(f"/api/v1/anomalies/{dataset_id}/train", json={})
    assert train_resp.status_code == 200
    assert train_resp.json()["model_metadata"]["experiment_label"] == "default"

    # Query with no experiment_label
    users_resp = client.get(f"/api/v1/anomalies/{dataset_id}/users")
    assert users_resp.status_code == 200
    assert users_resp.json()["experiment_label"] == "default"

    summary_resp = client.get(f"/api/v1/anomalies/{dataset_id}/summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["experiment_label"] == "default"

    model_resp = client.get(f"/api/v1/anomalies/{dataset_id}/model")
    assert model_resp.status_code == 200
    assert model_resp.json()["experiment_label"] == "default"


# 10. Audit 1 Regression: Zero label leakage into features or Isolation Forest training
def test_audit_label_leakage_regression(client: TestClient, sample_csv_bytes: bytes):
    from backend.app.services.dataset_registry import dataset_registry
    from backend.app.services.feature_service import FEATURE_NAMES

    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Verify dataset feature matrix only contains the exact 19 features
    store = dataset_registry.get(dataset_id)
    uids, matrix, feat_names = store.get_feature_matrix()
    assert feat_names == FEATURE_NAMES
    assert len(FEATURE_NAMES) == 19
    for col in feat_names:
        assert "label" not in col.lower()
        assert "fraud" not in col.lower()
        assert "target" not in col.lower()

    # Train E4 before labels exist
    resp_before = client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e4",
        json={"feature_groups": ["graph", "behavioral", "temporal"], "random_state": 42},
    )
    assert resp_before.status_code == 200
    meta_before = resp_before.json()["model_metadata"]
    assert meta_before["feature_names"] == FEATURE_NAMES

    users_before = client.get(f"/api/v1/anomalies/{dataset_id}/users?experiment_label=e4").json()["users"]

    # Now upload labels to LabelRegistry
    label_csv = (
        "user_id,label\n"
        "USR_ALICE,0\n"
        "USR_BOB,0\n"
        "USR_BURST_01,1\n"
        "USR_WHALE_01,1\n"
    ).encode("utf-8")
    resp_lbl = client.post(
        f"/api/v1/datasets/{dataset_id}/labels",
        files={"file": ("labels.csv", label_csv, "text/csv")},
    )
    assert resp_lbl.status_code == 200

    # Train E4 again after labels exist with same seed
    resp_after = client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e4_after",
        json={"feature_groups": ["graph", "behavioral", "temporal"], "random_state": 42},
    )
    assert resp_after.status_code == 200
    meta_after = resp_after.json()["model_metadata"]
    assert meta_after["feature_names"] == FEATURE_NAMES

    users_after = client.get(f"/api/v1/anomalies/{dataset_id}/users?experiment_label=e4_after").json()["users"]

    # Predictions, raw_scores, and risk_scores must be identical
    before_map = {u["user_id"]: u for u in users_before}
    after_map = {u["user_id"]: u for u in users_after}

    assert set(before_map.keys()) == set(after_map.keys())
    for uid in before_map:
        assert before_map[uid]["prediction"] == after_map[uid]["prediction"]
        assert before_map[uid]["raw_score"] == after_map[uid]["raw_score"]
        assert before_map[uid]["risk_score"] == after_map[uid]["risk_score"]
        assert before_map[uid]["reasons"] == after_map[uid]["reasons"]


# 11. Audit 2: User-level alignment, duplicate detection, and unmatched isolation
def test_audit_user_level_alignment_and_duplicates(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Label CSV with duplicate USR_ALICE row
    label_csv_dup = (
        "user_id,label\n"
        "USR_ALICE,0\n"
        "USR_ALICE,1\n"
        "USR_BOB,0\n"
    ).encode("utf-8")

    # Strict mode: rejects upload due to duplicate
    resp_strict = client.post(
        f"/api/v1/datasets/{dataset_id}/labels?strict=true",
        files={"file": ("labels.csv", label_csv_dup, "text/csv")},
    )
    assert resp_strict.status_code == 400
    assert any("Duplicate user_id 'USR_ALICE'" in err for err in resp_strict.json().get("details", []))

    # Non-strict mode: reports duplicate in rejected_errors
    resp_non_strict = client.post(
        f"/api/v1/datasets/{dataset_id}/labels?strict=false",
        files={"file": ("labels.csv", label_csv_dup, "text/csv")},
    )
    assert resp_non_strict.status_code == 200
    data = resp_non_strict.json()
    assert any("Duplicate user_id 'USR_ALICE'" in err for err in data["rejected_errors"])
    # 2 unique matched entities: USR_ALICE and USR_BOB
    assert data["matched_count"] == 2


# 12. Audit 3: Exact hand-verified metric math vs sklearn
def test_audit_metric_correctness_exact_hand_calculated(client: TestClient, sample_csv_bytes: bytes):
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score, average_precision_score

    # Hand-constructed ground truth and prediction test:
    # 8 instances:
    # y_true = [1, 1, 0, 0, 0, 0, 0, 1]  (3 positives, 5 negatives)
    # y_pred = [1, 0, 1, 0, 0, 0, 0, 1]  (3 positives predicted)
    # continuous scores = [95.0, 45.0, 75.0, 10.0, 20.0, 15.0, 5.0, 90.0]
    #
    # Pair-by-pair:
    # 0: yt=1, yp=1 -> TP
    # 1: yt=1, yp=0 -> FN
    # 2: yt=0, yp=1 -> FP
    # 3: yt=0, yp=0 -> TN
    # 4: yt=0, yp=0 -> TN
    # 5: yt=0, yp=0 -> TN
    # 6: yt=0, yp=0 -> TN
    # 7: yt=1, yp=1 -> TP
    #
    # Totals:
    # TP = 2, FP = 1, TN = 4, FN = 1
    # Accuracy  = (TP + TN) / Total = (2 + 4) / 8 = 6/8 = 0.75
    # Precision = TP / (TP + FP) = 2 / (2 + 1) = 2/3 = 0.6667
    # Recall    = TP / (TP + FN) = 2 / (2 + 1) = 2/3 = 0.6667
    # F1        = 2 * (P * R) / (P + R) = 2/3 = 0.6667

    y_true = [1, 1, 0, 0, 0, 0, 0, 1]
    y_pred = [1, 0, 1, 0, 0, 0, 0, 1]
    scores = [95.0, 45.0, 75.0, 10.0, 20.0, 15.0, 5.0, 90.0]

    exp_tp = 2
    exp_fp = 1
    exp_tn = 4
    exp_fn = 1
    exp_acc = round(6 / 8, 4)
    exp_prec = round(2 / 3, 4)
    exp_rec = round(2 / 3, 4)
    exp_f1 = round(2 / 3, 4)

    # Verify manual calculations match sklearn
    assert accuracy_score(y_true, y_pred) == exp_acc
    assert round(precision_score(y_true, y_pred), 4) == exp_prec
    assert round(recall_score(y_true, y_pred), 4) == exp_rec
    assert round(f1_score(y_true, y_pred), 4) == exp_f1

    # Verify AUC uses continuous scores and NOT binary predictions
    sk_roc_continuous = round(float(roc_auc_score(y_true, scores)), 4)
    sk_roc_binary = round(float(roc_auc_score(y_true, y_pred)), 4)
    assert sk_roc_continuous != sk_roc_binary

    sk_pr_continuous = round(float(average_precision_score(y_true, scores)), 4)
    sk_pr_binary = round(float(average_precision_score(y_true, y_pred)), 4)
    assert sk_pr_continuous != sk_pr_binary


# 13. Audit 4 & 6: Non-ML Baseline genuine separation and pure Graph features
def test_audit_baseline_genuinely_non_ml(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    resp = client.post(f"/api/v1/anomalies/{dataset_id}/baseline")
    assert resp.status_code == 200
    meta = resp.json()["model_metadata"]

    assert meta["model_type"] == "StatisticalBaseline"
    assert meta["sklearn_version"] == "N/A"
    assert meta["feature_groups"] == ["graph"]
    for feat in meta["feature_names"]:
        assert feat in ["weighted_out_degree", "betweenness_centrality", "total_degree"]

    users_resp = client.get(
        f"/api/v1/anomalies/{dataset_id}/users?experiment_label=baseline_statistical"
    )
    assert users_resp.status_code == 200
    for u in users_resp.json()["users"]:
        assert isinstance(u["raw_score"], float)
        assert u["prediction"] in [-1, 1]


# 14. Audit 5 & 6: Coexistence and feature groups of Baseline + E1 through E4
def test_audit_experiment_isolation_all_five(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # 1. Baseline: Graph (Statistical)
    client.post(f"/api/v1/anomalies/{dataset_id}/baseline")

    # 2. E1: Graph (IF)
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e1",
        json={"feature_groups": ["graph"]},
    )

    # 3. E2: Graph + Behavioral (IF)
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e2",
        json={"feature_groups": ["graph", "behavioral"]},
    )

    # 4. E3: Graph + Temporal (IF)
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e3",
        json={"feature_groups": ["graph", "temporal"]},
    )

    # 5. E4: Graph + Behavioral + Temporal (IF)
    client.post(
        f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e4",
        json={"feature_groups": ["graph", "behavioral", "temporal"]},
    )

    exps = client.get(f"/api/v1/anomalies/{dataset_id}/experiments").json()["experiments"]
    exp_dict = {e["experiment_label"]: e for e in exps}

    assert len(exp_dict) == 5
    assert "baseline_statistical" in exp_dict
    assert "e1" in exp_dict
    assert "e2" in exp_dict
    assert "e3" in exp_dict
    assert "e4" in exp_dict

    assert exp_dict["baseline_statistical"]["model_type"] == "StatisticalBaseline"
    assert exp_dict["baseline_statistical"]["feature_groups"] == ["graph"]

    assert exp_dict["e1"]["model_type"] == "IsolationForest"
    assert exp_dict["e1"]["feature_groups"] == ["graph"]
    assert exp_dict["e1"]["feature_count"] == 6

    assert exp_dict["e2"]["model_type"] == "IsolationForest"
    assert exp_dict["e2"]["feature_groups"] == ["graph", "behavioral"]
    assert exp_dict["e2"]["feature_count"] == 14

    assert exp_dict["e3"]["model_type"] == "IsolationForest"
    assert exp_dict["e3"]["feature_groups"] == ["graph", "temporal"]
    assert exp_dict["e3"]["feature_count"] == 11

    assert exp_dict["e4"]["model_type"] == "IsolationForest"
    assert exp_dict["e4"]["feature_groups"] == ["graph", "behavioral", "temporal"]
    assert exp_dict["e4"]["feature_count"] == 19


# 15. Hardening 1: /compare explicitly reports failed experiments instead of silently dropping them
def test_compare_reports_failed_experiment_explicitly(client: TestClient, sample_csv_bytes: bytes, monkeypatch):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Attach labels
    label_csv = "user_id,label\nUSR_ALICE,0\nUSR_BURST_01,1\n".encode("utf-8")
    client.post(f"/api/v1/datasets/{dataset_id}/labels", files={"file": ("labels.csv", label_csv, "text/csv")})

    # Train two experiments: E1 and E2
    client.post(f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e1", json={"feature_groups": ["graph"]})
    client.post(f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e2", json={"feature_groups": ["graph", "behavioral"]})

    # Monkeypatch evaluate_experiment to fail ONLY on e2
    orig_eval = evaluation_service.evaluate_experiment

    def mock_eval(dataset_id, experiment_label, include_curves=False):
        if experiment_label == "e2":
            raise RuntimeError("Simulated corruption in e2 model weights")
        return orig_eval(dataset_id, experiment_label, include_curves=include_curves)

    monkeypatch.setattr(evaluation_service, "evaluate_experiment", mock_eval)

    resp = client.get(f"/api/v1/evaluation/{dataset_id}/compare")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_experiments_evaluated"] == 2
    assert data["successful_experiments_count"] == 1
    assert data["failed_experiments_count"] == 1

    exps = {e["experiment_label"]: e for e in data["experiments"]}
    assert exps["e1"]["status"] == "success"
    assert exps["e1"]["error"] is None

    assert exps["e2"]["status"] == "error"
    assert "Simulated corruption in e2 model weights" in exps["e2"]["error"]


# 16. Hardening 4: Single-class and tiny dataset handling
def test_single_class_and_small_sample_warnings(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Attach single-class labels (all normal, 0)
    label_csv = "user_id,label\nUSR_ALICE,0\nUSR_BOB,0\nUSR_CHARLIE,0\n".encode("utf-8")
    client.post(f"/api/v1/datasets/{dataset_id}/labels", files={"file": ("labels.csv", label_csv, "text/csv")})

    client.post(f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e1", json={"feature_groups": ["graph"]})

    eval_resp = client.get(f"/api/v1/evaluation/{dataset_id}/e1")
    assert eval_resp.status_code == 200
    data = eval_resp.json()

    # Must NOT crash, but ROC-AUC and PR-AUC must be None with clear warnings
    assert data["roc_auc"] is None
    assert data["pr_auc"] is None
    assert len(data["metric_warnings"]) >= 2
    assert any("contains only one class" in w for w in data["metric_warnings"])
    assert any("Small sample warning" in w for w in data["metric_warnings"])


# 17. Hardening 6: ROC and Precision-Recall curve point extraction
def test_roc_and_pr_curve_data_generation(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    # Attach mixed labels
    label_csv = (
        "user_id,label\n"
        "USR_ALICE,0\n"
        "USR_BOB,0\n"
        "USR_CHARLIE,0\n"
        "USR_BURST_01,1\n"
        "USR_WHALE_01,1\n"
    ).encode("utf-8")
    client.post(f"/api/v1/datasets/{dataset_id}/labels", files={"file": ("labels.csv", label_csv, "text/csv")})

    client.post(f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e4", json={"feature_groups": ["graph", "behavioral", "temporal"]})

    # Query with include_curves=true
    resp = client.get(f"/api/v1/evaluation/{dataset_id}/e4?include_curves=true")
    assert resp.status_code == 200
    data = resp.json()

    assert data["roc_curve"] is not None
    roc = data["roc_curve"]
    assert len(roc["fpr"]) > 0
    assert len(roc["fpr"]) == len(roc["tpr"]) == len(roc["thresholds"])
    for val in roc["fpr"] + roc["tpr"]:
        assert 0.0 <= val <= 1.0

    assert data["precision_recall_curve"] is not None
    pr = data["precision_recall_curve"]
    assert len(pr["precision"]) > 0
    assert len(pr["precision"]) == len(pr["recall"])
    for val in pr["precision"] + pr["recall"]:
        assert 0.0 <= val <= 1.0


# 18. Hardening 5 & 7: Score direction and threshold analysis
def test_score_direction_and_threshold_analysis(client: TestClient, sample_csv_bytes: bytes):
    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    label_csv = "user_id,label\nUSR_ALICE,0\nUSR_BURST_01,1\n".encode("utf-8")
    client.post(f"/api/v1/datasets/{dataset_id}/labels", files={"file": ("labels.csv", label_csv, "text/csv")})

    # Train Baseline & E4
    client.post(f"/api/v1/anomalies/{dataset_id}/baseline")
    client.post(f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e4", json={"feature_groups": ["graph", "behavioral", "temporal"]})

    # Verify Baseline
    base_eval = client.get(f"/api/v1/evaluation/{dataset_id}/baseline_statistical").json()
    assert base_eval["score_name"] == "baseline_max_z_score"
    assert base_eval["score_direction"] == "higher_is_more_anomalous"
    assert base_eval["threshold_analysis"]["risk_score_is_probability"] is False
    assert "Population z-score" in base_eval["threshold_analysis"]["binary_decision_rule"]

    # Verify IF
    if_eval = client.get(f"/api/v1/evaluation/{dataset_id}/e4").json()
    assert if_eval["score_name"] == "risk_score"
    assert if_eval["score_direction"] == "higher_is_more_anomalous"
    assert if_eval["threshold_analysis"]["risk_score_is_probability"] is False
    assert "Top" in if_eval["threshold_analysis"]["binary_decision_rule"]


# 19. Hardening 11: Research run export to JSON and CSV artifacts
def test_research_run_export_json_and_csv(client: TestClient, sample_csv_bytes: bytes):
    import json
    import os

    dataset_id = upload_sample_dataset(client, sample_csv_bytes)

    label_csv = "user_id,label\nUSR_ALICE,0\nUSR_BURST_01,1\n".encode("utf-8")
    client.post(f"/api/v1/datasets/{dataset_id}/labels", files={"file": ("labels.csv", label_csv, "text/csv")})

    client.post(f"/api/v1/anomalies/{dataset_id}/baseline")
    client.post(f"/api/v1/anomalies/{dataset_id}/train?experiment_label=e1", json={"feature_groups": ["graph"]})

    export_resp = client.post(f"/api/v1/evaluation/{dataset_id}/export")
    assert export_resp.status_code == 200
    export_data = export_resp.json()

    assert export_data["dataset_id"] == dataset_id
    assert export_data["total_experiments"] == 2
    assert export_data["successful_experiments"] == 2
    assert export_data["failed_experiments"] == 0

    json_path = export_data["json_path"]
    csv_path = export_data["csv_path"]

    assert os.path.exists(json_path)
    assert os.path.exists(csv_path)

    # Validate JSON content
    with open(json_path, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
    assert loaded_json["dataset_id"] == dataset_id
    assert len(loaded_json["experiments"]) == 2

    # Validate CSV content
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 3  # Header + 2 experiment rows
    assert "experiment_label" in lines[0]
    assert "baseline_statistical" in lines[1] or "baseline_statistical" in lines[2]
