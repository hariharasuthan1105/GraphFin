"""
Tests for Report Generation Endpoint (POST /api/v1/reports/generate).
Validates PDF, Word (DOCX), and CSV report exports for both official locked research results
and live custom user-uploaded datasets.
Ensures zero alteration of locked research artifacts.
"""
import hashlib
import io
from pathlib import Path
import zipfile
import matplotlib.pyplot as plt
from docx import Document
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings

LOCKED_JSON = settings.DATA_DIR / "results" / "final_e0_e4_comparison.json"
LOCKED_CSV = settings.DATA_DIR / "results" / "final_e0_e4_comparison.csv"


def get_file_hash(p: Path) -> str:
    if not p.exists():
        return ""
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture
def client():
    return TestClient(app)


def test_official_reports_csv(client):
    """Test official research results export in CSV format."""
    initial_json_hash = get_file_hash(LOCKED_JSON)
    initial_csv_hash = get_file_hash(LOCKED_CSV)

    resp = client.post(
        "/api/v1/reports/generate",
        json={"source": "official", "format": "csv"},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "graphfin_official_research_results.csv" in resp.headers.get("content-disposition", "")
    assert len(resp.content) > 100
    assert "experiment_label" in resp.text
    assert "pr_auc" in resp.text

    # Verify locked files are untouched
    assert get_file_hash(LOCKED_JSON) == initial_json_hash
    assert get_file_hash(LOCKED_CSV) == initial_csv_hash


def test_official_reports_pdf(client):
    """Test official research results export in PDF format."""
    resp = client.post(
        "/api/v1/reports/generate",
        json={"source": "official", "format": "pdf"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "graphfin_official_research_results.pdf" in resp.headers.get("content-disposition", "")
    # Check PDF magic bytes
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 1000


def test_official_reports_docx(client):
    """Test official research results export in DOCX format."""
    resp = client.post(
        "/api/v1/reports/generate",
        json={"source": "official", "format": "docx"},
    )
    assert resp.status_code == 200
    assert "wordprocessingml.document" in resp.headers["content-type"]
    assert "graphfin_official_research_results.docx" in resp.headers.get("content-disposition", "")
    # DOCX is a zip archive starting with PK\x03\x04
    assert resp.content.startswith(b"PK\x03\x04")
    assert len(resp.content) > 1000


def test_custom_report_lifecycle(client):
    """
    Test custom evaluation report lifecycle:
    1. Upload dataset
    2. Upload labels
    3. Create split
    4. Train anomaly model
    5. Generate PDF, DOCX, and CSV reports
    6. Verify locked benchmarks are untouched
    """
    initial_json_hash = get_file_hash(LOCKED_JSON)
    initial_csv_hash = get_file_hash(LOCKED_CSV)

    # 1. Upload transactions
    tx_csv = (
        "transaction_id,timestamp,sender_id,receiver_id,amount,currency\n"
        "tx_1,2023-01-01T00:00:00Z,user_1,user_2,100.0,USD\n"
        "tx_2,2023-01-01T01:00:00Z,user_2,user_3,150.0,USD\n"
        "tx_3,2023-01-01T02:00:00Z,user_3,user_1,200.0,USD\n"
        "tx_4,2023-01-01T03:00:00Z,user_4,user_1,50.0,USD\n"
        "tx_5,2023-01-01T04:00:00Z,user_1,user_5,500.0,USD\n"
    )
    upload_res = client.post(
        "/api/v1/transactions/upload",
        files={"file": ("custom_tx.csv", tx_csv, "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    # 2. Upload labels
    labels_csv = (
        "user_id,label\n"
        "user_1,1\n"
        "user_2,0\n"
        "user_3,0\n"
        "user_4,0\n"
        "user_5,0\n"
    )
    labels_res = client.post(
        f"/api/v1/datasets/{dataset_id}/labels",
        files={"file": ("custom_labels.csv", labels_csv, "text/csv")},
    )
    assert labels_res.status_code == 200

    # 3. Train model
    train_res = client.post(
        f"/api/v1/anomalies/{dataset_id}/train",
        json={
            "experiment_label": "custom_exp_1",
            "feature_groups": ["graph"],
            "n_estimators": 50,
            "contamination": 0.2,
            "random_state": 42,
        },
    )
    assert train_res.status_code == 200

    # 4. Generate custom CSV report
    csv_rep = client.post(
        "/api/v1/reports/generate",
        json={"source": "custom", "format": "csv", "dataset_id": dataset_id},
    )
    assert csv_rep.status_code == 200
    assert "text/csv" in csv_rep.headers["content-type"]
    assert f"graphfin_custom_eval_{dataset_id[:8]}.csv" in csv_rep.headers.get("content-disposition", "")
    assert "custom_exp_1" in csv_rep.text

    # 5. Generate custom PDF report
    pdf_rep = client.post(
        "/api/v1/reports/generate",
        json={"source": "custom", "format": "pdf", "dataset_id": dataset_id},
    )
    assert pdf_rep.status_code == 200
    assert pdf_rep.headers["content-type"] == "application/pdf"
    assert pdf_rep.content.startswith(b"%PDF")

    # 6. Generate custom DOCX report
    docx_rep = client.post(
        "/api/v1/reports/generate",
        json={"source": "custom", "format": "docx", "dataset_id": dataset_id},
    )
    assert docx_rep.status_code == 200
    assert "wordprocessingml.document" in docx_rep.headers["content-type"]
    assert docx_rep.content.startswith(b"PK\x03\x04")

    # 7. Strictly verify locked benchmark files remain identical
    assert get_file_hash(LOCKED_JSON) == initial_json_hash
    assert get_file_hash(LOCKED_CSV) == initial_csv_hash


def test_reports_validation_errors(client):
    """Test validation errors for invalid arguments."""
    # Invalid source
    res1 = client.post(
        "/api/v1/reports/generate",
        json={"source": "unknown", "format": "pdf"},
    )
    assert res1.status_code in (400, 422)

    # Invalid format
    res2 = client.post(
        "/api/v1/reports/generate",
        json={"source": "official", "format": "xlsx"},
    )
    assert res2.status_code in (400, 422)

    # Missing dataset_id for custom
    res3 = client.post(
        "/api/v1/reports/generate",
        json={"source": "custom", "format": "pdf"},
    )
    assert res3.status_code in (400, 422)


def test_report_charts_embedded_and_file_size_increase(client):
    """
    Test 1: Verify PDF and DOCX reports contain embedded chart images.
    - PDF size is meaningfully increased (> 300 KB vs ~15 KB table-only).
    - PDF contains embedded Image objects.
    - DOCX zip archive contains 12 embedded images (2 grouped bar charts + 10 confusion matrices).
    """
    pdf_resp = client.post("/api/v1/reports/generate", json={"source": "official", "format": "pdf"})
    assert pdf_resp.status_code == 200
    assert len(pdf_resp.content) > 300_000
    assert b"/Subtype /Image" in pdf_resp.content

    docx_resp = client.post("/api/v1/reports/generate", json={"source": "official", "format": "docx"})
    assert docx_resp.status_code == 200
    assert len(docx_resp.content) > 300_000
    with zipfile.ZipFile(io.BytesIO(docx_resp.content)) as zf:
        embedded_imgs = [n for n in zf.namelist() if n.startswith("word/media/")]
        assert len(embedded_imgs) == 12


def test_report_unavailable_curve_fallback_note():
    """
    Test 2: Generating a report for an experiment where curve metrics are unavailable
    (e.g., insufficient class diversity) does not crash and includes the fallback note.
    """
    from backend.app.services.report_service import report_service

    mock_exp = [{
        "experiment_label": "Single_Class_Partition",
        "scale": "Custom Dataset",
        "method": "Isolation Forest",
        "feature_groups": ["graph"],
        "feature_count": 6,
        "contamination": 0.1,
        "evaluation_mode": "held_out",
        "precision": 0.0,
        "recall": 0.0,
        "f1_score": 0.0,
        "accuracy": 1.0,
        "roc_auc": None,
        "pr_auc": None,
        "tp": 0,
        "fp": 0,
        "tn": 50,
        "fn": 0,
        "roc_curve": None,
        "precision_recall_curve": None,
    }]

    pdf_bytes = report_service._build_pdf(
        title="Custom Evaluation Report",
        banner_text="Custom Evaluation",
        is_official=False,
        meta_pairs=[("Dataset", "single_class_ds")],
        experiments=mock_exp,
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

    docx_bytes = report_service._build_docx(
        title="Custom Evaluation Report",
        banner_text="Custom Evaluation",
        is_official=False,
        meta_pairs=[("Dataset", "single_class_ds")],
        experiments=mock_exp,
    )
    doc = Document(io.BytesIO(docx_bytes))
    full_text = " ".join([p.text for p in doc.paragraphs])
    assert "ROC curve unavailable: insufficient class diversity in test partition" in full_text
    assert "Precision-Recall curve unavailable: insufficient class diversity in test partition" in full_text


def test_matplotlib_figures_closed_properly():
    """
    Test 4: Matplotlib figures are properly closed (no unbounded memory growth)
    across repeated report generations.
    """
    from backend.app.services.report_service import report_service

    for _ in range(3):
        report_service.generate_report(source="official", format_type="pdf")
        report_service.generate_report(source="official", format_type="docx")
        assert len(plt.get_fignums()) == 0


def test_locked_research_artifacts_remain_untouched_after_chart_rendering():
    """
    Test 3: Confirm no locked research artifacts were modified by chart generation.
    """
    assert get_file_hash(LOCKED_JSON).lower() == "e16e2d5948b66f0cde493fadf43e1491fee219b582faa6a38eabfe53be786ad2"
    assert get_file_hash(LOCKED_CSV).lower() == "ba89012faf612cfe96d9e5049a869c40596894d167d37bb26a1581d976efa40a"

