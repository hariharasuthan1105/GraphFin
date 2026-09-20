"""
Tests for Real-Time Streaming Simulation Service and API Endpoints.
Validates:
1. Progression through ticks until 'complete'.
2. Rescoring at configured tick intervals, not every tick.
3. Read-only model inference without calling fit() or rewriting model artifacts.
4. Experiment label segregation (sim_ namespace) preventing artifact collisions.
5. Error when starting concurrent simulation on the same dataset.
6. Clean halt when stopping simulation.
7. Strict artifact isolation: final_e0_e4_comparison.json / .csv remain bit-for-bit identical
   and no new files appear under settings.MODELS_DIR.
"""
import hashlib
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.services.stream_simulator import stream_simulator


def hash_file(path: Path) -> str:
    """Compute SHA-256 hash of a file if it exists, else empty string."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def trained_dataset_id(client: TestClient, sample_csv_bytes: bytes) -> str:
    """Helper to upload sample transactions and train a default anomaly model."""
    upload_resp = client.post(
        "/api/v1/transactions/upload",
        files={"file": ("sample.csv", sample_csv_bytes, "text/csv")},
        data={"strict": "false"},
    )
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]

    # Train model under "E4_full_graphfin"
    train_resp = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={
            "experiment_label": "E4_full_graphfin",
            "feature_groups": ["graph", "behavioral", "temporal"],
            "n_estimators": 20,
            "random_state": 42,
        },
    )
    assert train_resp.status_code == 200
    return dataset_id


def test_simulation_progresses_to_complete(client: TestClient, trained_dataset_id: str):
    """Test 1: Starting a simulation advances ticks and reaches complete."""
    start_resp = client.post(
        f"/api/v1/stream/{trained_dataset_id}/start",
        json={
            "experiment_label": "E4_full_graphfin",
            "transactions_per_tick": 10,
            "tick_interval_seconds": 0.05,
            "rescoring_interval_ticks": 2,
        },
    )
    assert start_resp.status_code == 200
    data = start_resp.json()
    assert data["dataset_id"] == trained_dataset_id
    assert data["status"] == "running"
    assert data["total_transactions"] > 0

    # Poll until complete or timeout
    max_wait = 5.0
    start_time = time.time()
    final_state = None

    while time.time() - start_time < max_wait:
        time.sleep(0.1)
        state_resp = client.get(f"/api/v1/stream/{trained_dataset_id}/state")
        assert state_resp.status_code == 200
        state = state_resp.json()
        if state["status"] == "complete":
            final_state = state
            break

    assert final_state is not None, "Simulation did not reach 'complete' within timeout."
    assert final_state["transactions_revealed"] == final_state["total_transactions"]
    assert final_state["current_tick"] >= 2
    assert final_state["last_rescoring_tick"] is not None
    assert final_state["scoring_results"] is not None
    assert final_state["scoring_results"]["total_users"] > 0


def test_rescoring_occurs_at_configured_interval_only(client: TestClient, trained_dataset_id: str):
    """Test 2: Rescoring occurs only at rescoring_interval_ticks, not every tick."""
    # Set rescoring_interval_ticks to 10 with transactions_per_tick = 2
    start_resp = client.post(
        f"/api/v1/stream/{trained_dataset_id}/start",
        json={
            "experiment_label": "E4_full_graphfin",
            "transactions_per_tick": 2,
            "tick_interval_seconds": 0.1,
            "rescoring_interval_ticks": 10,
        },
    )
    assert start_resp.status_code == 200

    # After 1-2 ticks, rescoring should not have fired yet
    time.sleep(0.25)
    state = client.get(f"/api/v1/stream/{trained_dataset_id}/state").json()
    if state["current_tick"] < 10 and state["status"] == "running":
        assert state["last_rescoring_tick"] is None
        assert state["scoring_results"] is None

    # Stop simulation
    client.post(f"/api/v1/stream/{trained_dataset_id}/stop")


def test_read_only_model_integrity(client: TestClient, trained_dataset_id: str):
    """Test 3: Existing model artifact is NOT modified or rewritten during simulation."""
    model_path = settings.MODELS_DIR / f"{trained_dataset_id}__E4_full_graphfin.joblib"
    assert model_path.exists(), "Model file must exist prior to simulation."
    initial_mtime = model_path.stat().st_mtime_ns
    initial_hash = hash_file(model_path)

    # Run simulation
    client.post(
        f"/api/v1/stream/{trained_dataset_id}/start",
        json={
            "experiment_label": "E4_full_graphfin",
            "transactions_per_tick": 15,
            "tick_interval_seconds": 0.05,
            "rescoring_interval_ticks": 1,
        },
    )

    # Wait for at least one rescore
    time.sleep(0.3)
    client.post(f"/api/v1/stream/{trained_dataset_id}/stop")

    # Assert model file was untouched
    post_mtime = model_path.stat().st_mtime_ns
    post_hash = hash_file(model_path)

    assert post_mtime == initial_mtime, "Model file mtime was altered during simulation!"
    assert post_hash == initial_hash, "Model file SHA-256 changed during simulation!"


def test_conflict_on_concurrent_simulation(client: TestClient, trained_dataset_id: str):
    """Test 5: Starting a second simulation on the same dataset returns an error."""
    start_resp = client.post(
        f"/api/v1/stream/{trained_dataset_id}/start",
        json={
            "experiment_label": "E4_full_graphfin",
            "transactions_per_tick": 1,
            "tick_interval_seconds": 1.0,
            "rescoring_interval_ticks": 5,
        },
    )
    assert start_resp.status_code == 200

    # Attempt to start another simulation on same dataset
    conflict_resp = client.post(
        f"/api/v1/stream/{trained_dataset_id}/start",
        json={
            "experiment_label": "E4_full_graphfin",
            "transactions_per_tick": 1,
            "tick_interval_seconds": 1.0,
        },
    )
    assert conflict_resp.status_code in (400, 409, 422)
    resp_text = str(conflict_resp.json())
    assert "already actively running" in resp_text

    # Clean up
    client.post(f"/api/v1/stream/{trained_dataset_id}/stop")


def test_stopping_simulation_halts_task(client: TestClient, trained_dataset_id: str):
    """Test 6: Stopping a simulation halts background task execution."""
    client.post(
        f"/api/v1/stream/{trained_dataset_id}/start",
        json={
            "experiment_label": "E4_full_graphfin",
            "transactions_per_tick": 1,
            "tick_interval_seconds": 0.5,
            "rescoring_interval_ticks": 5,
        },
    )
    time.sleep(0.2)

    stop_resp = client.post(f"/api/v1/stream/{trained_dataset_id}/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] == "stopped"

    tick_after_stop = stop_resp.json()["current_tick"]
    time.sleep(0.8)

    state = client.get(f"/api/v1/stream/{trained_dataset_id}/state").json()
    assert state["status"] == "stopped"
    assert state["current_tick"] == tick_after_stop, "Simulation continued advancing after stop!"


def test_strict_artifact_isolation(client: TestClient, trained_dataset_id: str):
    """
    Test 7: Strict artifact isolation.
    Asserts that running a simulation session does NOT alter:
      - data/results/final_e0_e4_comparison.json
      - data/results/final_e0_e4_comparison.csv
    and creates NO new files in settings.MODELS_DIR.
    """
    json_path = settings.DATA_DIR / "results" / "final_e0_e4_comparison.json"
    csv_path = settings.DATA_DIR / "results" / "final_e0_e4_comparison.csv"

    initial_json_hash = hash_file(json_path)
    initial_csv_hash = hash_file(csv_path)
    initial_model_files = set(settings.MODELS_DIR.glob("*"))

    # Run complete simulation
    client.post(
        f"/api/v1/stream/{trained_dataset_id}/start",
        json={
            "experiment_label": "E4_full_graphfin",
            "transactions_per_tick": 20,
            "tick_interval_seconds": 0.02,
            "rescoring_interval_ticks": 1,
        },
    )

    # Wait for completion
    for _ in range(30):
        time.sleep(0.1)
        st = client.get(f"/api/v1/stream/{trained_dataset_id}/state").json()
        if st["status"] == "complete":
            break

    # 1. Assert locked comparison files are byte-for-byte unchanged
    assert hash_file(json_path) == initial_json_hash, "final_e0_e4_comparison.json was altered!"
    assert hash_file(csv_path) == initial_csv_hash, "final_e0_e4_comparison.csv was altered!"

    # 2. Assert no new files appeared in MODELS_DIR
    post_model_files = set(settings.MODELS_DIR.glob("*"))
    assert post_model_files == initial_model_files, (
        f"New files created in MODELS_DIR: {post_model_files - initial_model_files}"
    )

    # 3. Assert simulation runs do not leak into list_experiments
    exp_list_resp = client.get(f"/api/v1/anomalies/{trained_dataset_id}/experiments")
    assert exp_list_resp.status_code == 200
    listed_labels = [e["experiment_label"] for e in exp_list_resp.json()["experiments"]]
    for label in listed_labels:
        assert not label.startswith("sim_"), f"Simulation run leaked into experiments list: {label}"
