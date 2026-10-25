"""
Pytest configuration and fixtures.
"""
import pytest
from pathlib import Path


def pytest_sessionstart(session):
    root = Path(__file__).resolve().parents[2]
    marker = root / ".graphfin-test-sandbox"
    if not marker.exists() or marker.read_text().strip() != str(root.resolve()):
        raise pytest.UsageError("Tests delete model/split state. Run backend/scripts/verify_phase2.py with a scratch directory outside this repository.")

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.anomaly_service import anomaly_service
from backend.app.services.label_registry import label_registry
from backend.app.services.split_service import split_service
from backend.app.core.config import settings


from backend.app.services.stream_simulator import stream_simulator


@pytest.fixture(autouse=True)
def reset_state(tmp_path, monkeypatch):
    """Reset the in-memory dataset registry, anomaly models, labels, and stream simulator before each test."""
    # Disk-restored labels/splits must not leak from one test into another.
    # Keep persistence functional within each test, in its own disposable directory.
    processed = tmp_path / "processed"
    processed.mkdir()
    monkeypatch.setattr(settings, "DATA_PROCESSED_DIR", processed)
    monkeypatch.setattr(split_service, "storage_dir", processed)
    split_service._splits.clear()
    dataset_registry.clear()
    anomaly_service.clear()
    label_registry.clear()
    split_service._splits.clear()
    stream_simulator.clear()
    yield
    stream_simulator.clear()
    dataset_registry.clear()
    anomaly_service.clear()
    label_registry.clear()



@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def valid_csv_bytes() -> bytes:
    content = (
        "transaction_id,sender_id,receiver_id,amount,timestamp\n"
        "TX_1,USER_A,USER_B,100.50,2026-03-01 10:00:00\n"
        "TX_2,USER_B,USER_C,50.25,2026-03-01 11:30:00\n"
        "TX_3,USER_A,USER_C,75.00,2026-03-02 09:15:00\n"
        "TX_4,USER_C,USER_A,25.00,2026-03-02 14:00:00\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def second_valid_csv_bytes() -> bytes:
    content = (
        "transaction_id,sender_id,receiver_id,amount,timestamp\n"
        "TX_100,USER_X,USER_Y,999.00,2026-03-05 12:00:00\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def soft_duplicate_csv_bytes() -> bytes:
    content = (
        "transaction_id,sender_id,receiver_id,amount,timestamp\n"
        "TX_1,USER_A,USER_B,100.00,2026-03-01 10:00:00\n"
        "TX_2,USER_A,USER_B,100.00,2026-03-01 10:00:00\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def invalid_amount_csv_bytes() -> bytes:
    content = (
        "transaction_id,sender_id,receiver_id,amount,timestamp\n"
        "TX_1,USER_A,USER_B,-150.00,2026-03-01 10:00:00\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def duplicate_id_csv_bytes() -> bytes:
    content = (
        "transaction_id,sender_id,receiver_id,amount,timestamp\n"
        "TX_1,USER_A,USER_B,100.00,2026-03-01 10:00:00\n"
        "TX_1,USER_C,USER_D,200.00,2026-03-01 11:00:00\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def missing_columns_csv_bytes() -> bytes:
    content = (
        "transaction_id,sender_id,amount\n"
        "TX_1,USER_A,100.00\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def self_transfer_csv_bytes() -> bytes:
    content = (
        "transaction_id,sender_id,receiver_id,amount,timestamp\n"
        "TX_1,USER_A,USER_A,100.00,2026-03-01 10:00:00\n"
    )
    return content.encode("utf-8")


@pytest.fixture
def empty_csv_bytes() -> bytes:
    return b""


@pytest.fixture
def sample_csv_bytes() -> bytes:
    from backend.app.core.config import settings
    if settings.DEFAULT_SAMPLE_CSV.exists():
        return settings.DEFAULT_SAMPLE_CSV.read_bytes()
    return b""
