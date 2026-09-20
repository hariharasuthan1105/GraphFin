"""
Unit and integration tests for GraphFin Research Experiment Runner service and CLI.
Validates the canonical 5-experiment pipeline, manifest creation, CSV schemas,
ordering, leakage protection, deterministic reproducibility, and demo safety.
"""
import csv
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.exceptions import NotFoundException, ValidationException
from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.label_registry import label_registry
from backend.app.services.preprocessing import PreprocessingService
from backend.app.services.research_runner import (
    CANONICAL_EXPERIMENT_LABELS,
    research_runner,
)
from backend.app.services.split_service import split_service


@pytest.fixture
def test_dataset(client: TestClient, sample_csv_bytes: bytes) -> str:
    """Helper fixture to upload and register a clean test dataset."""
    preprocessor = PreprocessingService(strict_mode=False)
    clean_df, _, _ = preprocessor.process_csv(sample_csv_bytes)
    return dataset_registry.create_dataset(clean_df)


@pytest.fixture
def test_dataset_with_labels(test_dataset: str) -> str:
    """Helper fixture with genuine/research test labels attached."""
    dataset_id = test_dataset
    label_csv = (
        "user_id,label\n"
        "USR_ALICE,0\n"
        "USR_BOB,0\n"
        "USR_CHARLIE,0\n"
        "USR_DAVID,0\n"
        "USR_EMILY,0\n"
        "USR_FRANK,0\n"
        "USR_GRACE,0\n"
        "USR_HENRY,0\n"
        "USR_MERCHANT_99,0\n"
        "USR_BURST_01,1\n"
        "USR_WHALE_01,1\n"
    ).encode("utf-8")
    label_registry.store_labels_from_csv(dataset_id, label_csv)
    return dataset_id


# 1. Successful full five-experiment run
def test_research_runner_full_five_experiment_run(test_dataset_with_labels: str, tmp_path: Path):
    dataset_id = test_dataset_with_labels
    out_json = tmp_path / "custom_run.json"

    manifest = research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        random_state=42,
        output_path=str(out_json),
    )

    assert manifest["dataset_id"] == dataset_id
    assert len(manifest["experiments"]) == 5
    for exp in manifest["experiments"]:
        assert exp["status"] == "success"
        assert exp["error"] is None
        assert exp["confusion_matrix"] is not None
        assert exp["accuracy"] is not None
        assert exp["f1_score"] is not None


# 2. Missing labels raises ValidationException in research mode
def test_research_runner_missing_labels(test_dataset: str):
    dataset_id = test_dataset
    # Do not attach labels
    with pytest.raises(ValidationException) as exc_info:
        research_runner.run_experiments(dataset_id=dataset_id, is_demo=False)
    assert "has no ground-truth labels" in str(exc_info.value)


# 3. Unknown dataset raises NotFoundException
def test_research_runner_unknown_dataset():
    with pytest.raises(NotFoundException) as exc_info:
        research_runner.run_experiments(dataset_id="non-existent-dataset-id", is_demo=False)
    assert "not found" in str(exc_info.value)


# 4. Single-class label set handled gracefully with warnings
def test_research_runner_single_class_label_set(test_dataset: str, tmp_path: Path):
    dataset_id = test_dataset
    # All normal (0) labels
    label_csv = "user_id,label\nUSR_ALICE,0\nUSR_BOB,0\nUSR_CHARLIE,0\n".encode("utf-8")
    label_registry.store_labels_from_csv(dataset_id, label_csv)

    manifest = research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        output_path=str(tmp_path / "single_class.json"),
    )

    assert any("Single-class label warning" in w for w in manifest["metric_warnings"])
    for exp in manifest["experiments"]:
        assert exp["roc_auc"] is None
        assert exp["pr_auc"] is None


# 5. Label leakage protection
def test_research_runner_label_leakage_protection(test_dataset_with_labels: str, tmp_path: Path):
    dataset_id = test_dataset_with_labels
    manifest = research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        output_path=str(tmp_path / "leakage_test.json"),
    )

    for exp in manifest["experiments"]:
        for feat in exp["feature_names"]:
            assert "label" not in feat.lower()
            assert "fraud" not in feat.lower()
            assert "target" not in feat.lower()


# 6. Output JSON schema completeness
def test_research_runner_output_json_schema(test_dataset_with_labels: str, tmp_path: Path):
    dataset_id = test_dataset_with_labels
    out_json = tmp_path / "schema_test.json"

    research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        output_path=str(out_json),
    )

    assert out_json.exists()
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_keys = [
        "dataset_id",
        "transaction_count",
        "unique_user_count",
        "labeled_user_count",
        "usable_labeled_user_count",
        "positive_count",
        "negative_count",
        "positive_prevalence",
        "evaluation_mode",
        "is_demo",
        "demo_disclaimer",
        "experiment_order",
        "experiment_definitions",
        "experiments",
        "metric_warnings",
        "score_direction",
        "random_state",
        "timestamp",
        "software_metadata",
    ]
    for key in required_keys:
        assert key in data, f"Missing required manifest key: '{key}'"


# 7. Output CSV schema correctness
def test_research_runner_output_csv_schema(test_dataset_with_labels: str, tmp_path: Path):
    dataset_id = test_dataset_with_labels
    out_json = tmp_path / "csv_schema_test.json"
    out_csv = tmp_path / "csv_schema_test.csv"

    research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        output_path=str(out_json),
    )

    assert out_csv.exists()
    with open(out_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    expected_headers = [
        "experiment_label",
        "method",
        "feature_groups",
        "feature_count",
        "labeled_users",
        "positive_count",
        "negative_count",
        "precision",
        "recall",
        "f1",
        "accuracy",
        "roc_auc",
        "pr_auc",
        "evaluation_mode",
    ]
    assert rows[0] == expected_headers
    assert len(rows) == 6  # 1 header + 5 experiments


# 8. Correct experiment ordering (canonical research order, NOT alphabetical)
def test_research_runner_experiment_ordering(test_dataset_with_labels: str, tmp_path: Path):
    dataset_id = test_dataset_with_labels
    out_json = tmp_path / "ordering_test.json"
    out_csv = tmp_path / "ordering_test.csv"

    manifest = research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        output_path=str(out_json),
    )

    # Check JSON ordering
    json_exp_labels = [exp["experiment_label"] for exp in manifest["experiments"]]
    assert json_exp_labels == CANONICAL_EXPERIMENT_LABELS
    assert json_exp_labels == ["baseline_statistical", "E1", "E2", "E3", "E4"]
    assert json_exp_labels != sorted(CANONICAL_EXPERIMENT_LABELS)  # Must NOT be alphabetical

    # Check CSV ordering
    with open(out_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        csv_labels = [row[0] for row in list(reader)[1:]]
    assert csv_labels == CANONICAL_EXPERIMENT_LABELS


# 9. Deterministic repeat run
def test_research_runner_deterministic_repeat_run(test_dataset_with_labels: str, tmp_path: Path):
    dataset_id = test_dataset_with_labels

    m1 = research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        random_state=42,
        output_path=str(tmp_path / "run1.json"),
    )
    m2 = research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        random_state=42,
        output_path=str(tmp_path / "run2.json"),
    )

    for e1, e2 in zip(m1["experiments"], m2["experiments"]):
        assert e1["experiment_label"] == e2["experiment_label"]
        assert e1["precision"] == e2["precision"]
        assert e1["recall"] == e2["recall"]
        assert e1["f1_score"] == e2["f1_score"]
        assert e1["accuracy"] == e2["accuracy"]
        assert e1["roc_auc"] == e2["roc_auc"]
        assert e1["pr_auc"] == e2["pr_auc"]


# 10. Demo mode clearly marks synthetic labels
def test_research_runner_demo_mode_clearly_marks_synthetic_labels(test_dataset: str, tmp_path: Path):
    dataset_id = test_dataset
    # Dataset has no labels, run in demo mode
    out_json = tmp_path / "demo_run.json"
    manifest = research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=True,
        output_path=str(out_json),
    )

    assert manifest["is_demo"] is True
    assert manifest["demo_disclaimer"] is not None
    assert "SYNTHETIC/DEMO LABELS FOR PIPELINE VALIDATION ONLY" in manifest["demo_disclaimer"]
    assert "NOT REAL GROUND TRUTH" in manifest["demo_disclaimer"]


# 11. Held-out evaluation with split_label
def test_research_runner_held_out_split_all_requirements(test_dataset_with_labels: str, tmp_path: Path):
    dataset_id = test_dataset_with_labels
    split_label = "paper_holdout"

    # User explicitly creates split first
    split_obj = split_service.create_split(
        dataset_id=dataset_id,
        split_label=split_label,
        test_size=0.3,
        random_state=42,
        stratify_by_label=True,
    )
    train_size = len(split_obj.train_user_ids)
    test_size = len(split_obj.test_user_ids)

    out_json = tmp_path / "heldout_run.json"
    manifest = research_runner.run_experiments(
        dataset_id=dataset_id,
        is_demo=False,
        split_label=split_label,
        output_path=str(out_json),
    )

    # 1. Manifest evaluation_mode and split_label
    assert manifest["evaluation_mode"] == "held_out"
    assert manifest["split_label"] == split_label
    assert manifest["training_entity_count"] == train_size
    assert manifest["usable_labeled_user_count"] == test_size
    assert manifest["train_entity_count"] == train_size
    assert manifest["test_entity_count"] == test_size

    # 2. All five experiments use the same split and held_out mode
    assert len(manifest["experiments"]) == 5
    for exp in manifest["experiments"]:
        assert exp["split_label"] == split_label
        assert exp["evaluation_mode"] == "held_out"
        assert exp["usable_labeled_user_count"] == test_size
        assert exp["training_entity_count"] == train_size

        # 3. No label leakage into features
        for feat in exp["feature_names"]:
            assert "label" not in feat.lower()
            assert "fraud" not in feat.lower()
            assert "target" not in feat.lower()

    # 4. Check generated CSV
    csv_file = out_json.with_suffix(".csv")
    assert csv_file.exists()
    with open(csv_file, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        assert row[-1] == "held_out"  # evaluation_mode
        assert int(row[4]) == test_size  # labeled_users


# 12. Held-out deterministic repeat run
def test_research_runner_held_out_deterministic_repeat_run(test_dataset_with_labels: str, tmp_path: Path):
    dataset_id = test_dataset_with_labels
    split_label = "deterministic_split"

    split_service.create_split(
        dataset_id=dataset_id,
        split_label=split_label,
        test_size=0.3,
        random_state=42,
        stratify_by_label=True,
    )

    m1 = research_runner.run_experiments(
        dataset_id=dataset_id,
        split_label=split_label,
        random_state=42,
        output_path=str(tmp_path / "h_run1.json"),
    )
    m2 = research_runner.run_experiments(
        dataset_id=dataset_id,
        split_label=split_label,
        random_state=42,
        output_path=str(tmp_path / "h_run2.json"),
    )

    assert m1["evaluation_mode"] == "held_out"
    assert m2["evaluation_mode"] == "held_out"
    for e1, e2 in zip(m1["experiments"], m2["experiments"]):
        assert e1["experiment_label"] == e2["experiment_label"]
        assert e1["precision"] == e2["precision"]
        assert e1["recall"] == e2["recall"]
        assert e1["f1_score"] == e2["f1_score"]
        assert e1["accuracy"] == e2["accuracy"]
        assert e1["roc_auc"] == e2["roc_auc"]
        assert e1["pr_auc"] == e2["pr_auc"]


# 13. Runner does not auto-create split: missing split raises NotFoundException
def test_research_runner_missing_split_raises_not_found(test_dataset_with_labels: str):
    dataset_id = test_dataset_with_labels
    with pytest.raises(NotFoundException) as exc_info:
        research_runner.run_experiments(
            dataset_id=dataset_id,
            split_label="non_existent_split",
        )
    assert "not found" in str(exc_info.value).lower()


# 14. CLI invocation with --split-label
def test_research_runner_cli_with_split_label(
    test_dataset_with_labels: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    dataset_id = test_dataset_with_labels
    split_label = "cli_split"
    split_service.create_split(
        dataset_id=dataset_id,
        split_label=split_label,
        test_size=0.3,
        random_state=42,
        stratify_by_label=True,
    )
    out_json = str(tmp_path / "cli_run.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "research_runner",
            "--dataset-id",
            dataset_id,
            "--split-label",
            split_label,
            "--output",
            out_json,
        ],
    )
    from backend.app.services.research_runner import main
    main()
    captured = capsys.readouterr()
    assert "GRAPHFIN RESEARCH EXPERIMENT RUN COMPLETE" in captured.out
    assert "Evaluation Mode:   held_out" in captured.out
    assert f"Split Label:       {split_label}" in captured.out
    assert Path(out_json).exists()
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["evaluation_mode"] == "held_out"
    assert data["split_label"] == split_label
    assert len(data["experiments"]) == 5

