"""
GraphFin Research Experiment Runner.
Executes the canonical five-experiment benchmark pipeline on a dataset:
  1. baseline_statistical (Graph, z-score threshold)
  2. E1 (Graph, Isolation Forest)
  3. E2 (Graph + Behavioral, Isolation Forest)
  4. E3 (Graph + Temporal, Isolation Forest)
  5. E4 (Graph + Behavioral + Temporal, Isolation Forest)

Produces reproducible JSON manifest and canonical CSV summary under data/results/.
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import fastapi
import networkx as nx
import numpy as np
import pandas as pd
import sklearn

from ..core.config import settings
from ..core.exceptions import NotFoundException, ValidationException
from ..core.logging import get_logger
from ..schemas.anomaly import AnomalyTrainRequest, BaselineTrainRequest
from ..schemas.evaluation import ExperimentEvaluationMetrics
from .anomaly_service import anomaly_service
from .baseline_service import DEFAULT_BASELINE_FEATURES, baseline_service
from .dataset_registry import dataset_registry
from .evaluation_service import evaluation_service
from .feature_service import FEATURE_NAMES
from .label_registry import label_registry
from .preprocessing import PreprocessingService
from .split_service import split_service

logger = get_logger(__name__)

CANONICAL_EXPERIMENT_LABELS: List[str] = [
    "baseline_statistical",
    "E1",
    "E2",
    "E3",
    "E4",
]

CANONICAL_EXPERIMENT_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "baseline_statistical": {
        "method": "Statistical (z-score, no ML)",
        "feature_groups": ["graph"],
        "feature_count": 3,
        "features": DEFAULT_BASELINE_FEATURES,
        "description": "Non-ML rule-based statistical baseline: population z-score threshold (z >= 2.0) across graph topology metrics.",
    },
    "E1": {
        "method": "Isolation Forest",
        "feature_groups": ["graph"],
        "feature_count": 6,
        "description": "Unsupervised Isolation Forest trained purely on graph topological metrics.",
    },
    "E2": {
        "method": "Isolation Forest",
        "feature_groups": ["graph", "behavioral"],
        "feature_count": 14,
        "description": "Unsupervised Isolation Forest combining graph topology with entity transaction statistics.",
    },
    "E3": {
        "method": "Isolation Forest",
        "feature_groups": ["graph", "temporal"],
        "feature_count": 11,
        "description": "Unsupervised Isolation Forest combining graph topology with burst and inter-transaction intervals.",
    },
    "E4": {
        "method": "Isolation Forest",
        "feature_groups": ["graph", "behavioral", "temporal"],
        "feature_count": 19,
        "description": "Comprehensive feature fusion combining all three groups (19 features, full model).",
    },
}


class ResearchRunner:
    """Orchestrates end-to-end multi-experiment research benchmarks."""

    def run_experiments(
        self,
        dataset_id: str,
        is_demo: bool = False,
        random_state: int = 42,
        output_path: Optional[str] = None,
        split_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the complete 5-experiment benchmark for a dataset.

        :param dataset_id: UUID of the uploaded dataset
        :param is_demo: If True, allows synthetic demo labels; marks run as demo validation
        :param random_state: Random seed for deterministic reproducibility
        :param output_path: Custom target path for the JSON research run artifact
        :param split_label: Optional split label for entity-level held-out evaluation
        """
        results_dir = settings.DATA_DIR / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        clean_split: Optional[str] = (
            split_label.strip() if split_label and split_label.strip() else None
        )
        split_obj = None

        logger.info(
            f"Initiating research experiment run for dataset '{dataset_id}' "
            f"(is_demo={is_demo}, split_label={clean_split})."
        )

        # 1. Verify dataset exists
        try:
            store = dataset_registry.get(dataset_id)
        except NotFoundException:
            raise NotFoundException(f"Dataset '{dataset_id}' not found in registry or processed data directory.")

        user_ids, full_matrix, feat_names = store.get_feature_matrix()
        if len(user_ids) == 0:
            raise ValidationException(f"Dataset '{dataset_id}' contains 0 entities in feature matrix.")

        # 1b. If split_label provided, verify split exists (raises NotFoundException if not found, does NOT auto-create)
        if clean_split is not None:
            split_obj = split_service.get_split(dataset_id, clean_split)
            logger.info(
                f"Verified entity split '{clean_split}' for dataset '{dataset_id}': "
                f"train={len(split_obj.train_user_ids)}, test={len(split_obj.test_user_ids)}"
            )

        # 2. Strict Label Leakage Check
        if feat_names != FEATURE_NAMES or len(feat_names) != 19:
            raise ValidationException(
                f"Feature matrix columns corrupted or misaligned. Expected {FEATURE_NAMES}, got {feat_names}."
            )
        for col in feat_names:
            col_l = col.lower()
            if "label" in col_l or "fraud" in col_l or "target" in col_l:
                raise ValidationException(f"Label leakage detected in feature matrix: column '{col}' is present.")

        # 3. Check and Validate Labels
        demo_disclaimer: Optional[str] = None
        has_lbls = label_registry.has_labels(dataset_id)

        if not has_lbls:
            if is_demo:
                # In demo mode, synthesize transparent demo labels for pipeline validation
                logger.warning(
                    f"No labels found for dataset '{dataset_id}'. Generating synthetic/demo labels for pipeline validation."
                )
                demo_disclaimer = "SYNTHETIC/DEMO LABELS FOR PIPELINE VALIDATION ONLY. NOT REAL GROUND TRUTH."
                # Synthesize labels: top 18% entities = 1, remainder = 0
                n_pos = max(1, int(len(user_ids) * 0.18))
                demo_lines = ["user_id,label"]
                for i, uid in enumerate(user_ids):
                    lbl = "1" if i < n_pos else "0"
                    demo_lines.append(f"{uid},{lbl}")
                demo_csv = "\n".join(demo_lines).encode("utf-8")
                label_registry.store_labels_from_csv(dataset_id, demo_csv)
            else:
                raise ValidationException(
                    f"Dataset '{dataset_id}' has no ground-truth labels attached. "
                    "Research mode requires authentic stored labels. "
                    "Use --demo flag to run pipeline validation with synthetic demo labels."
                )
        else:
            if is_demo:
                demo_disclaimer = "DEMO RUN: Evaluated using existing dataset labels under demo execution flag."

        labels = label_registry.get_labels(dataset_id)
        label_summary = label_registry.get_summary(dataset_id)

        # 4. Label Coverage & Protocol Validation
        matched_uids = set(labels.keys()).intersection(set(user_ids))
        if len(matched_uids) == 0:
            raise ValidationException(
                f"Zero overlapping user IDs between labels and feature matrix for dataset '{dataset_id}'."
            )

        run_warnings: List[str] = []
        if label_summary.matched_count < 30:
            run_warnings.append(
                f"Small sample warning ($N = {label_summary.matched_count} < 30$): "
                "Metrics are highly sensitive to individual classifications. Treat as smoke test/pipeline validation."
            )

        if label_summary.positive_count == 0 or label_summary.negative_count == 0:
            run_warnings.append(
                f"Single-class label warning: dataset contains only "
                f"{'positive' if label_summary.positive_count > 0 else 'negative'} labels. "
                "ROC-AUC and PR-AUC will be undefined."
            )

        # 5. Train Canonical 5 Configurations (passing split_label if active)
        logger.info(f"Training Baseline statistical experiment on dataset '{dataset_id}' (split={clean_split})...")
        baseline_service.train_baseline(
            dataset_id=dataset_id,
            request=BaselineTrainRequest(
                experiment_label="baseline_statistical",
                z_threshold=2.0,
                features=DEFAULT_BASELINE_FEATURES,
                split_label=clean_split,
            ),
        )

        configs = [
            ("E1", ["graph"]),
            ("E2", ["graph", "behavioral"]),
            ("E3", ["graph", "temporal"]),
            ("E4", ["graph", "behavioral", "temporal"]),
        ]

        for exp_label, grps in configs:
            logger.info(f"Training {exp_label} ({grps}) on dataset '{dataset_id}' (split={clean_split})...")
            anomaly_service.train_model(
                dataset_id=dataset_id,
                request=AnomalyTrainRequest(
                    experiment_label=exp_label,
                    feature_groups=grps,
                    random_state=random_state,
                    split_label=clean_split,
                ),
                experiment_label=exp_label,
            )

        # 6. Evaluate Each Experiment in Exact Canonical Order
        evaluated_experiments: List[ExperimentEvaluationMetrics] = []
        for exp_label in CANONICAL_EXPERIMENT_LABELS:
            metrics = evaluation_service.evaluate_experiment(
                dataset_id=dataset_id,
                experiment_label=exp_label,
                split_label=clean_split,
                include_curves=True,
            )
            evaluated_experiments.append(metrics)

        # 7. Assemble Complete Research Run Manifest
        now_ts = datetime.now(timezone.utc).isoformat()

        if clean_split is not None and split_obj is not None:
            eval_mode = "held_out"
            eval_note = (
                f"Entity-level held-out evaluation: evaluated on test partition entity rows "
                f"({len(split_obj.test_user_ids)} entities, split='{clean_split}'). "
                f"Model fit on train partition ({len(split_obj.train_user_ids)} entities)."
            )
            training_entity_count = len(split_obj.train_user_ids)
            usable_labeled_user_count = len(split_obj.test_user_ids)
            pos_count = split_obj.test_positive_count
            neg_count = split_obj.test_negative_count
            pos_prev = split_obj.test_prevalence
        else:
            eval_mode = "in_sample"
            eval_note = (
                "In-sample evaluation represents pipeline validation on the full feature population. "
                "For research reporting, use entity-level held-out evaluation on an appropriately sized dataset."
            )
            training_entity_count = len(user_ids)
            usable_labeled_user_count = label_summary.matched_count
            pos_count = label_summary.positive_count
            neg_count = label_summary.negative_count
            pos_prev = label_summary.prevalence_rate

        run_manifest: Dict[str, Any] = {
            "dataset_id": dataset_id,
            "transaction_count": len(store.transactions_df),
            "unique_user_count": len(user_ids),
            "labeled_user_count": label_summary.total_labels_uploaded,
            "usable_labeled_user_count": usable_labeled_user_count,
            "training_entity_count": training_entity_count,
            "positive_count": pos_count,
            "negative_count": neg_count,
            "positive_prevalence": pos_prev,
            "evaluation_mode": eval_mode,
            "evaluation_mode_note": eval_note,
            "split_label": clean_split,
            "is_demo": is_demo,
            "demo_disclaimer": demo_disclaimer,
            "experiment_order": CANONICAL_EXPERIMENT_LABELS,
            "experiment_definitions": CANONICAL_EXPERIMENT_DEFINITIONS,
            "experiments": [m.model_dump() for m in evaluated_experiments],
            "metric_warnings": run_warnings,
            "score_direction": "higher_is_more_anomalous",
            "random_state": random_state,
            "timestamp": now_ts,
            "software_metadata": {
                "graphfin_version": "1.0.0",
                "python_version": sys.version.split()[0],
                "sklearn_version": sklearn.__version__,
                "networkx_version": nx.__version__,
                "fastapi_version": fastapi.__version__,
            },
        }

        if split_obj is not None:
            run_manifest["train_entity_count"] = len(split_obj.train_user_ids)
            run_manifest["test_entity_count"] = len(split_obj.test_user_ids)
            run_manifest["train_positive_count"] = split_obj.train_positive_count
            run_manifest["test_positive_count"] = split_obj.test_positive_count
            run_manifest["train_prevalence"] = split_obj.train_prevalence
            run_manifest["test_prevalence"] = split_obj.test_prevalence
            run_manifest["stratified"] = split_obj.stratified
            run_manifest["stratification_warning"] = split_obj.warning

        # 8. Save Output JSON
        target_json = Path(output_path) if output_path else (results_dir / f"{dataset_id}_research_run.json")
        target_json.parent.mkdir(parents=True, exist_ok=True)
        with open(target_json, "w", encoding="utf-8") as f:
            json.dump(run_manifest, f, indent=2)

        # 9. Save Output CSV in Exact Canonical Order (NOT alphabetically sorted)
        target_csv = target_json.with_suffix(".csv")
        csv_headers = [
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

        with open(target_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
            for m in evaluated_experiments:
                writer.writerow([
                    m.experiment_label,
                    m.method or "",
                    ";".join(m.feature_groups),
                    m.feature_count,
                    m.usable_labeled_user_count,
                    m.positive_count,
                    m.negative_count,
                    f"{m.precision:.4f}" if m.precision is not None else "",
                    f"{m.recall:.4f}" if m.recall is not None else "",
                    f"{m.f1_score:.4f}" if m.f1_score is not None else "",
                    f"{m.accuracy:.4f}" if m.accuracy is not None else "",
                    f"{m.roc_auc:.4f}" if m.roc_auc is not None else "",
                    f"{m.pr_auc:.4f}" if m.pr_auc is not None else "",
                    m.evaluation_mode,
                ])

        run_manifest["json_path"] = str(target_json.as_posix())
        run_manifest["csv_path"] = str(target_csv.as_posix())

        logger.info(
            f"Research run complete for dataset '{dataset_id}'. "
            f"Artifacts saved to:\n  JSON: {target_json.as_posix()}\n  CSV:  {target_csv.as_posix()}"
        )

        return run_manifest


research_runner = ResearchRunner()


def main():
    """CLI entrypoint for executing research experiment runs."""
    parser = argparse.ArgumentParser(
        description="GraphFin Research Experiment Runner — executes canonical 5-experiment benchmark for one dataset."
    )
    parser.add_argument(
        "--dataset-id",
        type=str,
        required=True,
        help="UUID or identifier of the dataset to evaluate.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path for output JSON artifact (defaults to data/results/<dataset_id>_research_run.json).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode: allows synthetic/demo labels and explicitly marks results as pipeline validation.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for deterministic tree fitting (default: 42).",
    )
    parser.add_argument(
        "--transactions-file",
        type=str,
        default=None,
        help="Optional path to a transaction CSV to load if dataset_id is not already loaded.",
    )
    parser.add_argument(
        "--labels-file",
        type=str,
        default=None,
        help="Optional path to a ground-truth labels CSV to ingest before running.",
    )
    parser.add_argument(
        "--split-label",
        type=str,
        default=None,
        help="Optional split label to run all 5 experiments in entity-level held-out evaluation mode.",
    )

    args = parser.parse_args()

    # If transaction file provided, preprocess and register dataset
    dataset_id = args.dataset_id
    if args.transactions_file:
        tx_path = Path(args.transactions_file)
        if not tx_path.exists():
            print(f"Error: Transactions file '{tx_path}' does not exist.", file=sys.stderr)
            sys.exit(1)
        preprocessor = PreprocessingService(strict_mode=False)
        clean_df, _, _ = preprocessor.process_csv(tx_path.read_bytes())
        dataset_id = dataset_registry.create_dataset(clean_df)
        print(f"Loaded transactions from '{tx_path}' into dataset '{dataset_id}'.")

    # If labels file provided, store labels
    if args.labels_file:
        lbl_path = Path(args.labels_file)
        if not lbl_path.exists():
            print(f"Error: Labels file '{lbl_path}' does not exist.", file=sys.stderr)
            sys.exit(1)
        label_registry.store_labels_from_csv(dataset_id, lbl_path.read_bytes())
        print(f"Loaded ground-truth labels from '{lbl_path}' into dataset '{dataset_id}'.")

    try:
        manifest = research_runner.run_experiments(
            dataset_id=dataset_id,
            is_demo=args.demo,
            random_state=args.random_state,
            output_path=args.output,
            split_label=args.split_label,
        )
    except Exception as e:
        print(f"Research Run Failed: {str(e)}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("GRAPHFIN RESEARCH EXPERIMENT RUN COMPLETE")
    print("=" * 80)
    print(f"Dataset ID:        {manifest['dataset_id']}")
    print(f"Unique Entities:   {manifest['unique_user_count']}")
    print(f"Transactions:      {manifest['transaction_count']}")
    print(f"Evaluation Mode:   {manifest['evaluation_mode']}")
    if manifest.get('split_label'):
        print(f"Split Label:       {manifest['split_label']}")
        print(f"Train Entities:    {manifest.get('train_entity_count')}")
        print(f"Test Entities:     {manifest.get('test_entity_count')}")
    if manifest['is_demo']:
        print(f"DEMO DISCLAIMER:   {manifest['demo_disclaimer']}")
    print("-" * 80)
    print(f"{'Experiment':<22} | {'Method':<25} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'F1':<6}")
    print("-" * 80)
    for exp in manifest["experiments"]:
        el = exp["experiment_label"]
        mt = exp["method"] or exp["model_type"]
        pr = f"{exp['pr_auc']:.4f}" if exp["pr_auc"] is not None else "N/A"
        roc = f"{exp['roc_auc']:.4f}" if exp["roc_auc"] is not None else "N/A"
        f1 = f"{exp['f1_score']:.4f}" if exp["f1_score"] is not None else "N/A"
        print(f"{el:<22} | {mt:<25} | {pr:<8} | {roc:<8} | {f1:<6}")
    print("=" * 80)
    print(f"Artifacts saved:")
    print(f"  JSON: {manifest['json_path']}")
    print(f"  CSV:  {manifest['csv_path']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
