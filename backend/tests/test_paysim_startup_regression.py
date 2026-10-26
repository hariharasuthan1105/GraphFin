"""
Focused regression tests for PaySim dataset loading, alias resolution,
re-entrancy prevention, idempotency, failure recovery, and FastAPI startup.
"""
from contextlib import asynccontextmanager
import threading
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app, lifespan
from backend.app.services.dataset_registry import (
    dataset_registry,
    PAYSIM_DATASET_ID,
    PAYSIM_UUID_ALIAS,
)
from backend.app.services.label_registry import label_registry


@pytest.fixture(autouse=True)
def clean_registries():
    """Ensure clean registry state before and after each regression test."""
    dataset_registry.clear()
    label_registry.clear()
    yield
    dataset_registry.clear()
    label_registry.clear()


def test_paysim_first_load_and_idempotency():
    """Verify first load succeeds and subsequent load is strictly idempotent."""
    store1 = dataset_registry.load_paysim()
    assert store1 is not None
    assert len(store1.transactions_df) == 10000
    assert len(store1.feature_service.user_features) == 18711

    # Second load must return exact same instance instantly
    store2 = dataset_registry.load_paysim()
    assert store2 is store1
    assert dataset_registry.is_loaded(PAYSIM_DATASET_ID)
    assert dataset_registry.is_loaded(PAYSIM_UUID_ALIAS)


def test_paysim_alias_lookup():
    """Verify alias lookup retrieves identical StateStore and labels."""
    store_main = dataset_registry.get(PAYSIM_DATASET_ID)
    store_alias = dataset_registry.get(PAYSIM_UUID_ALIAS)
    assert store_main is store_alias

    lbls_main = label_registry.get_labels(PAYSIM_DATASET_ID)
    lbls_alias = label_registry.get_labels(PAYSIM_UUID_ALIAS)
    assert lbls_main == lbls_alias
    assert len(lbls_main) == 18711
    assert sum(lbls_main.values()) == 129


def test_no_recursive_loading_during_initialization():
    """Verify dataset_registry.get() during loading returns without re-entry."""
    call_depths = []
    current_depth = [0]
    orig_load = dataset_registry.load_paysim

    def instrumented_load():
        current_depth[0] += 1
        call_depths.append(current_depth[0])
        try:
            return orig_load()
        finally:
            current_depth[0] -= 1

    with patch.object(dataset_registry, "load_paysim", side_effect=instrumented_load):
        store = dataset_registry.load_paysim()

    assert store is not None
    # Maximum call depth must be strictly 1 (no recursive re-entry)
    assert max(call_depths) == 1
    assert len(call_depths) == 1


def test_lookup_during_in_progress_loading():
    """Verify concurrent / re-entrant get() during loading does not spawn duplicate load."""
    load_started = threading.Event()
    load_release = threading.Event()
    orig_load = dataset_registry.load_paysim

    def slow_load():
        load_started.set()
        load_release.wait(timeout=2.0)
        return orig_load()

    thread_results = []

    def background_get():
        load_started.wait(timeout=2.0)
        # Attempt get() while loading is in progress
        store = dataset_registry.get(PAYSIM_DATASET_ID)
        thread_results.append(store)

    t = threading.Thread(target=background_get)
    t.start()

    with patch.object(dataset_registry, "load_paysim", side_effect=slow_load):
        main_store = dataset_registry.load_paysim()
        load_release.set()

    t.join(timeout=3.0)
    assert len(thread_results) == 1
    assert thread_results[0] is main_store


def test_failed_initialization_leaves_no_corrupted_state():
    """Verify failed initialization cleans up partial registry entries and allows retry."""
    with patch("pandas.read_csv", side_effect=IOError("Simulated disk read failure")):
        with pytest.raises(IOError, match="Simulated disk read failure"):
            dataset_registry.load_paysim()

    # Registry must be completely clean; no partial store registered
    assert PAYSIM_DATASET_ID not in dataset_registry._datasets
    assert PAYSIM_UUID_ALIAS not in dataset_registry._datasets
    assert not dataset_registry.is_loaded(PAYSIM_DATASET_ID)

    # Subsequent retry with real data must succeed cleanly
    recovered_store = dataset_registry.load_paysim()
    assert recovered_store is not None
    assert dataset_registry.is_loaded(PAYSIM_DATASET_ID)


def test_label_value_preservation():
    """Verify exact count and positive prevalence alignment for PaySim labels."""
    dataset_registry.load_paysim()
    summary_main = label_registry.get_summary(PAYSIM_DATASET_ID)
    summary_alias = label_registry.get_summary(PAYSIM_UUID_ALIAS)

    assert summary_main.matched_count == 18711
    assert summary_main.positive_count == 129
    assert summary_main.negative_count == 18582
    assert summary_alias.matched_count == summary_main.matched_count
    assert summary_alias.positive_count == summary_main.positive_count


def test_fastapi_lifespan_startup_and_shutdown():
    """Verify full FastAPI lifespan starts and shuts down cleanly without hang."""
    with TestClient(app) as client:
        assert dataset_registry.is_loaded(PAYSIM_DATASET_ID)
        assert label_registry.has_labels(PAYSIM_DATASET_ID)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "financial-anomaly-detection-api"}

