"""
Tests for PaySim Cross-Dataset Evaluation Report Download Feature.
Validates:
1. Report endpoint returns 200 when artifacts exist.
2. Content-Type is PDF (application/pdf).
3. Content-Disposition contains the expected filename (graphfin_paysim_cross_dataset_evaluation.pdf).
4. Report generation does not rerun evaluation.
5. Existing cross-dataset artifact remains unchanged (hash verification).
6. Missing artifact returns appropriate error (404).
7. Report contains both transfer directions.
8. Report contains E0–E5.
9. Report contains the existing PR-AUC values.
10. Report contains 95% CI values.
11. Report contains Precision@K values.
"""
import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import pypdf
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.report_service import report_service
from backend.app.services.transfer_service import transfer_service

CROSS_DATASET_DIR = settings.DATA_DIR / "results" / "cross_dataset"
IBM_TO_PAYSIM_PATH = CROSS_DATASET_DIR / "ibm_to_paysim_transfer.json"
PAYSIM_TO_IBM_PATH = CROSS_DATASET_DIR / "paysim_to_ibm_transfer.json"


def get_file_hash(p: Path) -> str:
    """Compute sha256 checksum of a file."""
    if not p.exists():
        return ""
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture
def client():
    return TestClient(app)


def test_paysim_report_endpoint_success_and_headers(client):
    """
    Requirements 1, 2, 3:
    1. Report endpoint returns 200 when artifacts exist.
    2. Content-Type is PDF.
    3. Content-Disposition contains the expected filename.
    """
    assert IBM_TO_PAYSIM_PATH.exists(), "IBM->PaySim artifact missing"
    assert PAYSIM_TO_IBM_PATH.exists(), "PaySim->IBM artifact missing"

    resp = client.get("/api/v1/evaluation/paysim/report")
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers.get("content-type", "")
    content_disp = resp.headers.get("content-disposition", "")
    assert "attachment" in content_disp
    assert "graphfin_paysim_cross_dataset_evaluation.pdf" in content_disp
    assert len(resp.content) > 1000


def test_paysim_report_does_not_rerun_evaluation(client):
    """
    Requirement 4: Report generation does not rerun evaluation.
    """
    with patch.object(transfer_service, "evaluate_transfer") as mock_eval:
        resp = client.get("/api/v1/evaluation/paysim/report")
        assert resp.status_code == 200
        mock_eval.assert_not_called()


def test_cross_dataset_artifacts_remain_unchanged(client):
    """
    Requirement 5: Existing cross-dataset artifact remains unchanged.
    """
    hash_a_before = get_file_hash(IBM_TO_PAYSIM_PATH)
    hash_b_before = get_file_hash(PAYSIM_TO_IBM_PATH)

    resp = client.get("/api/v1/evaluation/paysim/report")
    assert resp.status_code == 200

    hash_a_after = get_file_hash(IBM_TO_PAYSIM_PATH)
    hash_b_after = get_file_hash(PAYSIM_TO_IBM_PATH)

    assert hash_a_before == hash_a_after, "ibm_to_paysim_transfer.json was mutated!"
    assert hash_b_before == hash_b_after, "paysim_to_ibm_transfer.json was mutated!"


def test_missing_artifact_returns_404(client, monkeypatch):
    """
    Requirement 6: Missing artifact returns appropriate error (404).
    """
    with patch("backend.app.services.report_service.settings.DATA_DIR", settings.DATA_DIR / "results" / "does_not_exist"):
        resp = client.get("/api/v1/evaluation/paysim/report")
        assert resp.status_code == 404
        assert "not found" in resp.text.lower()


def test_report_pdf_content_validation(client):
    """
    Requirements 7, 8, 9, 10, 11:
    7. Report contains both transfer directions.
    8. Report contains E0–E5.
    9. Report contains the existing PR-AUC values.
    10. Report contains 95% CI values.
    11. Report contains Precision@K values.
    """
    with open(IBM_TO_PAYSIM_PATH, "r", encoding="utf-8") as f:
        da = json.load(f)
    with open(PAYSIM_TO_IBM_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    resp = client.get("/api/v1/evaluation/paysim/report")
    assert resp.status_code == 200

    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    assert len(reader.pages) >= 2

    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    # 7. Both transfer directions present
    assert "Direction A" in full_text
    assert "IBM AML 50K -> PaySim" in full_text or "IBM AML 50K" in full_text
    assert "Direction B" in full_text
    assert "PaySim -> IBM AML 50K" in full_text or "PaySim" in full_text

    # 8. All E0-E5 experiments present
    for exp_id in ["E0", "E1", "E2", "E3", "E4", "E5"]:
        assert exp_id in full_text, f"Experiment {exp_id} missing from PDF text"

    # 9. Existing PR-AUC values present
    # Direction A E0 src PR-AUC = 0.0116, tgt PR-AUC = 0.0018
    # Direction B E0 src PR-AUC = 0.0065, tgt PR-AUC = 0.0128
    assert "0.0116" in full_text, "Dir A E0 source PR-AUC missing"
    assert "0.0018" in full_text, "Dir A E0 target PR-AUC missing"
    assert "0.0065" in full_text, "Dir B E0 source PR-AUC missing"
    assert "0.0128" in full_text, "Dir B E0 target PR-AUC missing"

    # Direction A E1 src = 0.0222, tgt = 0.0081
    assert "0.0222" in full_text, "Dir A E1 source PR-AUC missing"
    assert "0.0081" in full_text, "Dir A E1 target PR-AUC missing"

    # Direction B E3 src = 0.0054, tgt = 0.0155
    assert "0.0054" in full_text, "Dir B E3 source PR-AUC missing"
    assert "0.0155" in full_text, "Dir B E3 target PR-AUC missing"

    # 10. 95% CI values present
    # Dir A E0: [0.0081, 0.0214] and [0.0017, 0.0027]
    assert "0.0081" in full_text and "0.0214" in full_text, "Dir A E0 source 95% CI missing"
    assert "0.0017" in full_text and "0.0027" in full_text, "Dir A E0 target 95% CI missing"

    # 11. Precision@K values present
    assert "P@10" in full_text
    assert "P@25" in full_text
    assert "P@50" in full_text
    assert "P@100" in full_text

    # Direction A E3/E4 P@10 = 0.10, Direction B E1 P@25 = 0.08
    assert "0.10" in full_text
    assert "0.08" in full_text

    # Research dataset scale mention (not 10K)
    assert "300K" in full_text or "299,999" in full_text
    assert "547K" in full_text or "547,686" in full_text
    assert "353K" in full_text or "353,150" in full_text
    assert "50K" in full_text or "50,000" in full_text
    assert "1000 bootstrap resamples" in full_text


def test_reports_generate_paysim_source(client):
    """
    Verify POST /api/v1/reports/generate with source='paysim_transfer' also works.
    """
    resp = client.post(
        "/api/v1/reports/generate",
        json={"source": "paysim_transfer", "format": "pdf"},
    )
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers.get("content-type", "")
    assert "graphfin_paysim_cross_dataset_evaluation.pdf" in resp.headers.get("content-disposition", "")
