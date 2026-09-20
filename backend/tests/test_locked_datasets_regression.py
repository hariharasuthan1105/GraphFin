"""
Regression tests for Locked Research Datasets (IBM AML 5K and 50K tiers).

Validates:
1. Exact sha256 checksums and byte integrity of locked research artifacts
   (final_e0_e4_comparison.json and final_e0_e4_comparison.csv).
2. Backend resolvability of both locked dataset IDs:
   - ddbaab44-78b6-41be-a8fb-e83dfec66358 (5,000 accounts)
   - 03fb9ab0-4f42-4404-9d76-723fd4d8753e (49,992 accounts)
3. Experiment structure and metrics completeness (E0-E4 for each tier).
4. Complete isolation between custom evaluation workflows and locked benchmark files.
"""
import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings

# Frozen expected SHA-256 hashes (lowercase)
EXPECTED_JSON_SHA256 = "e16e2d5948b66f0cde493fadf43e1491fee219b582faa6a38eabfe53be786ad2"
EXPECTED_CSV_SHA256 = "ba89012faf612cfe96d9e5049a869c40596894d167d37bb26a1581d976efa40a"

LOCKED_JSON_PATH = settings.DATA_DIR / "results" / "final_e0_e4_comparison.json"
LOCKED_CSV_PATH = settings.DATA_DIR / "results" / "final_e0_e4_comparison.csv"

TIER_5K_ID = "ddbaab44-78b6-41be-a8fb-e83dfec66358"
TIER_50K_ID = "03fb9ab0-4f42-4404-9d76-723fd4d8753e"

EXPECTED_EXPERIMENTS = [
    "E0_graph_baseline",
    "E1_graph_ml",
    "E2_graph_behavioral_ml",
    "E3_graph_temporal_ml",
    "E4_full_graphfin",
]


@pytest.fixture
def client():
    return TestClient(app)


def compute_sha256(path: Path) -> str:
    assert path.exists(), f"File does not exist: {path}"
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest().lower()


def test_locked_benchmark_files_byte_integrity():
    """Verify final_e0_e4_comparison.json and .csv match their frozen cryptographic checksums."""
    json_hash = compute_sha256(LOCKED_JSON_PATH)
    csv_hash = compute_sha256(LOCKED_CSV_PATH)

    assert json_hash == EXPECTED_JSON_SHA256, (
        f"LOCKED BENCHMARK CORRUPTION: JSON hash mismatch!\n"
        f"Expected: {EXPECTED_JSON_SHA256}\n"
        f"Actual:   {json_hash}"
    )
    assert csv_hash == EXPECTED_CSV_SHA256, (
        f"LOCKED BENCHMARK CORRUPTION: CSV hash mismatch!\n"
        f"Expected: {EXPECTED_CSV_SHA256}\n"
        f"Actual:   {csv_hash}"
    )


def test_locked_benchmark_json_structure():
    """Verify that the locked JSON contains all 10 experiments (5 per tier) with required fields."""
    with open(LOCKED_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "experiments" in data
    exps = data["experiments"]
    assert len(exps) == 10, f"Expected 10 benchmark experiments, found {len(exps)}"

    # Check 5K tier
    exps_5k = [e for e in exps if e.get("dataset_id") == TIER_5K_ID]
    assert len(exps_5k) == 5, f"Expected 5 experiments for 5K tier, found {len(exps_5k)}"
    labels_5k = [e["experiment_label"] for e in exps_5k]
    for expected in EXPECTED_EXPERIMENTS:
        assert expected in labels_5k, f"Missing {expected} in 5K tier"

    # Check 50K tier
    exps_50k = [e for e in exps if e.get("dataset_id") == TIER_50K_ID]
    assert len(exps_50k) == 5, f"Expected 5 experiments for 50K tier, found {len(exps_50k)}"
    labels_50k = [e["experiment_label"] for e in exps_50k]
    for expected in EXPECTED_EXPERIMENTS:
        assert expected in labels_50k, f"Missing {expected} in 50K tier"

    # Verify metrics fields exist on all runs
    for e in exps:
        assert "pr_auc" in e
        assert "roc_auc" in e
        assert "f1_score" in e
        assert "precision" in e
        assert "recall" in e
        assert "tp" in e
        assert "fp" in e
        assert "fn" in e
        assert "test_positive" in e
        assert "test_negative" in e


def test_locked_datasets_backend_resolvability(client):
    """Verify that both locked dataset IDs resolve successfully via the backend API."""
    # 5K tier
    resp_5k = client.get(f"/api/v1/transactions/{TIER_5K_ID}/summary")
    assert resp_5k.status_code == 200, f"5K dataset failed to resolve: {resp_5k.text}"
    data_5k = resp_5k.json()
    assert data_5k["transactions"] == 31463
    assert data_5k["users"] == 5000
    assert data_5k["currency"] == "USD"

    # 50K tier
    resp_50k = client.get(f"/api/v1/transactions/{TIER_50K_ID}/summary")
    assert resp_50k.status_code == 200, f"50K dataset failed to resolve: {resp_50k.text}"
    data_50k = resp_50k.json()
    assert data_50k["transactions"] == 353850
    assert data_50k["users"] == 49992
    assert data_50k["currency"] == "USD"


def test_custom_dataset_isolation_guarantee(client):
    """Verify that user custom dataset uploads and operations leave locked benchmarks untouched."""
    json_hash_before = compute_sha256(LOCKED_JSON_PATH)
    csv_hash_before = compute_sha256(LOCKED_CSV_PATH)

    # 1. Upload a custom dataset
    csv_content = (
        "transaction_id,timestamp,sender_id,receiver_id,amount\n"
        "tx_1,2026-03-01T10:00:00Z,user_1,user_2,100.0\n"
        "tx_2,2026-03-01T10:05:00Z,user_2,user_3,150.0\n"
        "tx_3,2026-03-01T10:10:00Z,user_3,user_4,200.0\n"
        "tx_4,2026-03-01T10:15:00Z,user_4,user_5,250.0\n"
        "tx_5,2026-03-01T10:20:00Z,user_5,user_1,300.0\n"
    )
    files = {"file": ("custom_test.csv", csv_content.encode("utf-8"), "text/csv")}
    upload_resp = client.post("/api/v1/transactions/upload?strict_mode=false&currency=USD", files=files)
    assert upload_resp.status_code == 200
    custom_dataset_id = upload_resp.json()["dataset_id"]
    assert custom_dataset_id not in (TIER_5K_ID, TIER_50K_ID)

    # 2. Upload labels for the custom dataset
    label_csv = (
        "user_id,label\n"
        "user_1,1\n"
        "user_2,0\n"
        "user_3,0\n"
        "user_4,0\n"
        "user_5,0\n"
    )
    lbl_files = {"file": ("custom_labels.csv", label_csv.encode("utf-8"), "text/csv")}
    lbl_resp = client.post(f"/api/v1/datasets/{custom_dataset_id}/labels", files=lbl_files)
    assert lbl_resp.status_code == 200

    # 3. Create split
    split_resp = client.post(
        f"/api/v1/datasets/{custom_dataset_id}/splits",
        json={"split_label": "test_split", "test_size": 0.4},
    )
    assert split_resp.status_code == 200

    # 4. Train an experiment model
    train_resp = client.post(
        f"/api/v1/anomalies/{custom_dataset_id}/train",
        json={
            "experiment_label": "custom_exp_1",
            "feature_groups": ["graph"],
            "n_estimators": 50,
            "contamination": 0.2,
            "random_state": 42,
        },
    )
    assert train_resp.status_code == 200

    # 5. Generate custom evaluation report
    report_resp = client.post(
        "/api/v1/reports/generate",
        json={"source": "custom", "dataset_id": custom_dataset_id, "format": "pdf"},
    )
    assert report_resp.status_code == 200
    assert report_resp.content.startswith(b"%PDF")

    # 6. Generate official report
    official_report_resp = client.post(
        "/api/v1/reports/generate",
        json={"source": "official", "format": "pdf"},
    )
    assert official_report_resp.status_code == 200
    assert official_report_resp.content.startswith(b"%PDF")

    # 6. Cryptographic assertion: benchmark files are identical
    json_hash_after = compute_sha256(LOCKED_JSON_PATH)
    csv_hash_after = compute_sha256(LOCKED_CSV_PATH)

    assert json_hash_before == json_hash_after == EXPECTED_JSON_SHA256
    assert csv_hash_before == csv_hash_after == EXPECTED_CSV_SHA256
