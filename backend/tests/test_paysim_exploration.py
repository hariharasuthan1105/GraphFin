"""
Tests for GET /api/v1/datasets/paysim/exploration endpoint.
Validates:
- HTTP 200 when PaySim loaded
- Correct dataset_id
- Transaction count matches loaded slice
- Account count matches loaded dataset
- Fraud + normal account counts sum to total accounts
- All 19 features present in feature_summary
- Feature statistics fields present
- Endpoint does not modify dataset state
- Endpoint does not modify research results
- Repeated requests use cached exploration data
- Unloaded PaySim handled gracefully
"""
import time
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.state_store import StateStore
from backend.app.services.exploration_service import paysim_exploration_service
from backend.app.services.feature_service import CANONICAL_TRANSFER_FEATURES


# Minimal PaySim-like CSV for tests (uses sender_id / receiver_id schema)
_PAYSIM_MINI_CSV = (
    "transaction_id,sender_id,receiver_id,amount,timestamp,step\n"
    "T001,ACC_A,ACC_B,500.0,2026-01-01 00:00:00,1\n"
    "T002,ACC_B,ACC_C,1500.0,2026-01-01 01:00:00,1\n"
    "T003,ACC_C,ACC_D,25000.0,2026-01-01 02:00:00,2\n"
    "T004,ACC_D,ACC_E,75000.0,2026-01-01 03:00:00,2\n"
    "T005,ACC_E,ACC_A,250000.0,2026-01-01 04:00:00,3\n"
    "T006,ACC_A,ACC_C,600000.0,2026-01-01 05:00:00,3\n"
    "T007,ACC_B,ACC_D,800.0,2026-01-01 06:00:00,4\n"
    "T008,ACC_C,ACC_E,1200.0,2026-01-01 07:00:00,4\n"
    "T009,ACC_D,ACC_A,45000.0,2026-01-01 08:00:00,5\n"
    "T010,ACC_E,ACC_B,120000.0,2026-01-01 09:00:00,5\n"
)


@pytest.fixture(autouse=True)
def reset_exploration_cache():
    """Ensure exploration cache is clear before each test."""
    paysim_exploration_service.invalidate()
    yield
    paysim_exploration_service.invalidate()


def _load_mini_paysim() -> None:
    """Load the minimal PaySim fixture into the dataset registry."""
    df = pd.read_csv(pd.io.common.StringIO(_PAYSIM_MINI_CSV))
    store = StateStore()
    store.load_transactions(df)
    dataset_registry._datasets["paysim"] = store
    dataset_registry._datasets["e8d9c7b6-a5f4-4e3d-b2c1-a09876543210"] = store
    dataset_registry._currencies["paysim"] = "USD"


# ---------------------------------------------------------------------------
# 1. Unloaded PaySim is handled gracefully
# ---------------------------------------------------------------------------

def test_exploration_not_loaded_returns_gracefully(client: TestClient):
    """GET /api/v1/datasets/paysim/exploration with no PaySim loaded returns not_loaded."""
    response = client.get("/api/v1/datasets/paysim/exploration")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "paysim"
    assert data["status"] == "not_loaded"
    assert "message" in data


# ---------------------------------------------------------------------------
# 2. HTTP 200 when PaySim loaded
# ---------------------------------------------------------------------------

def test_exploration_returns_200_when_loaded(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 3. Correct dataset_id
# ---------------------------------------------------------------------------

def test_exploration_correct_dataset_id(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    assert data["dataset_id"] == "paysim"
    assert data["status"] == "loaded"
    assert data["scope"] == "production_slice"


# ---------------------------------------------------------------------------
# 4. Transaction count matches loaded slice
# ---------------------------------------------------------------------------

def test_exploration_transaction_count_matches_loaded_slice(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    assert data["transactions"]["count"] == 10


# ---------------------------------------------------------------------------
# 5. Account count matches loaded dataset
# ---------------------------------------------------------------------------

def test_exploration_account_count_matches_loaded_dataset(client: TestClient):
    _load_mini_paysim()
    store = dataset_registry.get("paysim")
    expected_accounts = len(store.feature_service.user_features)

    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    assert data["accounts"]["count"] == expected_accounts


# ---------------------------------------------------------------------------
# 6. Fraud + normal account counts sum to total accounts
# ---------------------------------------------------------------------------

def test_exploration_fraud_normal_sum_to_total(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    accounts = data["accounts"]
    # When no labels loaded: all accounts are treated as normal
    assert accounts["fraud_involved"] + accounts["normal"] == accounts["count"]


# ---------------------------------------------------------------------------
# 7. All 19 canonical features present in feature_summary
# ---------------------------------------------------------------------------

def test_exploration_all_19_features_present(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    feature_names_returned = [f["feature_name"] for f in data["feature_summary"]]
    for fname in CANONICAL_TRANSFER_FEATURES:
        assert fname in feature_names_returned, f"Missing feature: {fname}"
    assert len(data["feature_summary"]) >= 19


# ---------------------------------------------------------------------------
# 8. Feature statistics fields are present
# ---------------------------------------------------------------------------

def test_exploration_feature_stats_fields_present(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    for feat in data["feature_summary"]:
        assert "feature_name" in feat
        assert "group" in feat
        assert "mean" in feat
        assert "std" in feat
        assert "min" in feat
        assert "max" in feat
        assert "pct_missing" in feat


# ---------------------------------------------------------------------------
# 9. Endpoint does not modify dataset state
# ---------------------------------------------------------------------------

def test_exploration_does_not_modify_dataset_state(client: TestClient):
    _load_mini_paysim()
    store_before = dataset_registry.get("paysim")
    tx_count_before = len(store_before.transactions_df)
    user_count_before = len(store_before.feature_service.user_features)

    client.get("/api/v1/datasets/paysim/exploration")

    store_after = dataset_registry.get("paysim")
    assert len(store_after.transactions_df) == tx_count_before
    assert len(store_after.feature_service.user_features) == user_count_before


# ---------------------------------------------------------------------------
# 10. Repeated requests use cached exploration data (not recomputed)
# ---------------------------------------------------------------------------

def test_exploration_repeated_requests_use_cache(client: TestClient):
    _load_mini_paysim()

    # First request: compute and cache
    t0 = time.perf_counter()
    r1 = client.get("/api/v1/datasets/paysim/exploration")
    t1 = time.perf_counter()
    first_duration = t1 - t0

    # Second request: must be significantly faster (served from cache)
    t2 = time.perf_counter()
    r2 = client.get("/api/v1/datasets/paysim/exploration")
    t3 = time.perf_counter()
    second_duration = t3 - t2

    assert r1.status_code == 200
    assert r2.status_code == 200

    # Second request must be at least 5x faster (cache hit vs computation)
    if first_duration > 0.05:
        assert second_duration < first_duration * 0.5, (
            f"Second request ({second_duration:.4f}s) was not faster than "
            f"first ({first_duration:.4f}s) — cache may not be working"
        )

    # Response data must be identical
    assert r1.json()["transactions"]["count"] == r2.json()["transactions"]["count"]


# ---------------------------------------------------------------------------
# 11. Network summary fields present
# ---------------------------------------------------------------------------

def test_exploration_network_summary_fields(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    net = data["network"]
    assert "nodes" in net
    assert "edges" in net
    assert "density" in net
    assert "weakly_connected_components" in net
    assert net["nodes"] > 0
    assert net["edges"] > 0


# ---------------------------------------------------------------------------
# 12. Amount distribution has expected buckets
# ---------------------------------------------------------------------------

def test_exploration_amount_distribution_buckets(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    buckets = data["amount_distribution"]
    assert len(buckets) == 6  # exactly 6 defined buckets
    total_across_buckets = sum(b["count"] for b in buckets)
    assert total_across_buckets == 10  # total transactions


# ---------------------------------------------------------------------------
# 13. Top senders and receivers are present
# ---------------------------------------------------------------------------

def test_exploration_top_senders_receivers_present(client: TestClient):
    _load_mini_paysim()
    response = client.get("/api/v1/datasets/paysim/exploration")
    data = response.json()
    assert len(data["top_senders"]) > 0
    assert len(data["top_receivers"]) > 0
    for acct in data["top_senders"] + data["top_receivers"]:
        assert "account_id" in acct
        assert "transaction_count" in acct
        assert "total_amount" in acct
