"""
Evaluation Service for GraphFin Research Anomaly Detection.
Computes Confusion Matrix, Precision, Recall, F1, ROC-AUC, and PR-AUC
against user-level ground-truth labels across multiple experiment configurations.
Produces ranking curves (ROC / PR) and reproducible research exports.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve

from ..core.config import settings
from ..core.exceptions import ModelNotTrainedException, NotFoundException, ValidationException
from ..core.logging import get_logger
from ..schemas.evaluation import (
    ConfusionMatrix,
    EvaluationComparisonResponse,
    ExperimentEvaluationMetrics,
    PrecisionRecallCurveData,
    ResearchExportResponse,
    ROCCurveData,
    ThresholdAnalysis,
)
from .anomaly_service import anomaly_service
from .dataset_registry import dataset_registry
from .label_registry import label_registry
from .split_service import split_service

logger = get_logger(__name__)


class EvaluationService:
    """Service evaluating anomaly detection experiments against ground-truth labels."""

    def evaluate_experiment(
        self,
        dataset_id: str,
        experiment_label: str,
        include_curves: bool = False,
        split_label: Optional[str] = None,
    ) -> ExperimentEvaluationMetrics:
        """
        Compute comprehensive classification and ranking evaluation metrics for a single experiment.
        """
        clean_exp = (experiment_label or "default").strip()

        # 1. Retrieve dataset and ensure labels exist
        dataset_registry.get(dataset_id)
        labels = label_registry.get_labels(dataset_id)  # raises NotFoundException if no labels

        # 2. Retrieve model metadata and predictions (scoped to split if specified)
        effective_split = (split_label or "").strip() or None
        metadata = anomaly_service.get_model_metadata(dataset_id, clean_exp, split_label=effective_split)
        if not effective_split:
            model_split = getattr(metadata, "split_label", None)
            effective_split = (model_split or "").strip() or None

        pred_response = anomaly_service.predict_user_anomalies(
            dataset_id=dataset_id, experiment_label=clean_exp, limit=100000, split_label=effective_split
        )

        # 3. Determine evaluation mode (held_out vs in_sample)
        allowed_eval_uids = None
        if effective_split:
            split_obj = split_service.get_split(dataset_id, effective_split)
            allowed_eval_uids = set(split_obj.test_user_ids)
            eval_mode = "held_out"
            eval_note = (
                f"Entity-level held-out evaluation: evaluated on test partition entity rows "
                f"({len(split_obj.test_user_ids)} entities, split='{effective_split}'). Model fit on train partition."
            )
        else:
            eval_mode = "in_sample"
            eval_note = (
                "In-sample evaluation represents pipeline validation on the full feature population. "
                "For research reporting, use entity-level held-out evaluation on an appropriately sized dataset."
            )

        # 4. Match entities appearing in predictions AND ground-truth labels (filtered by test partition if split active)
        y_true_list: List[int] = []
        y_pred_list: List[int] = []
        scores_list: List[float] = []

        is_baseline = (metadata.model_type == "StatisticalBaseline")

        for user_result in pred_response.users:
            uid = user_result.user_id
            if allowed_eval_uids is not None and uid not in allowed_eval_uids:
                continue
            if uid in labels:
                y_true = 1 if labels[uid] else 0
                y_pred = 1 if user_result.prediction == -1 else 0

                # Continuous score for ranking / AUC curves:
                # For Isolation Forest: risk_score (0-100, higher = more anomalous)
                # For Baseline: raw_score (max z-score, higher = more anomalous)
                continuous_score = (
                    user_result.raw_score
                    if is_baseline
                    else user_result.risk_score
                )

                y_true_list.append(y_true)
                y_pred_list.append(y_pred)
                scores_list.append(continuous_score)

        usable_count = len(y_true_list)
        if usable_count == 0:
            raise ValidationException(
                f"No overlapping entities found between ground-truth labels and dataset '{dataset_id}'."
            )

        positive_count = sum(y_true_list)
        negative_count = usable_count - positive_count
        prevalence = round(positive_count / usable_count, 4) if usable_count > 0 else 0.0

        # 4. Metric warnings for tiny datasets and single-class scenarios
        metric_warnings: List[str] = []
        if usable_count < 30:
            metric_warnings.append(
                f"Small sample warning: only {usable_count} labeled entities available for evaluation. "
                "Metrics are sensitive to individual classifications and should be treated as a smoke test/pipeline validation only."
            )

        # 5. Compute Confusion Matrix
        tp = sum(1 for yt, yp in zip(y_true_list, y_pred_list) if yt == 1 and yp == 1)
        fp = sum(1 for yt, yp in zip(y_true_list, y_pred_list) if yt == 0 and yp == 1)
        tn = sum(1 for yt, yp in zip(y_true_list, y_pred_list) if yt == 0 and yp == 0)
        fn = sum(1 for yt, yp in zip(y_true_list, y_pred_list) if yt == 1 and yp == 0)

        conf_matrix = ConfusionMatrix(tp=tp, fp=fp, tn=tn, fn=fn)

        # 6. Compute Binary Classification Metrics
        accuracy = round((tp + tn) / usable_count, 4) if usable_count > 0 else 0.0
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = (
            round(2.0 * precision * recall / (precision + recall), 4)
            if (precision + recall) > 0
            else 0.0
        )

        # 7. Compute Ranking Metrics (ROC-AUC, PR-AUC) and Curves
        roc_auc: Optional[float] = None
        pr_auc: Optional[float] = None
        roc_curve_data: Optional[ROCCurveData] = None
        pr_curve_data: Optional[PrecisionRecallCurveData] = None

        unique_classes = set(y_true_list)
        if len(unique_classes) > 1:
            try:
                roc_auc = round(float(roc_auc_score(y_true_list, scores_list)), 4)
            except Exception as e:
                logger.warning(f"Could not calculate ROC-AUC for exp '{clean_exp}': {e}")
                metric_warnings.append(f"ROC-AUC calculation error: {str(e)}")

            try:
                pr_auc = round(
                    float(average_precision_score(y_true_list, scores_list)), 4
                )
            except Exception as e:
                logger.warning(f"Could not calculate PR-AUC for exp '{clean_exp}': {e}")
                metric_warnings.append(f"PR-AUC calculation error: {str(e)}")

            if include_curves:
                try:
                    fpr_arr, tpr_arr, r_thresh_arr = roc_curve(y_true_list, scores_list)
                    # Clean thresholds if inf
                    r_thresh_clean = [
                        float(round(t, 5)) if np.isfinite(t) else float(round(max(scores_list) + 1.0, 5))
                        for t in r_thresh_arr
                    ]
                    roc_curve_data = ROCCurveData(
                        fpr=[float(round(v, 5)) for v in fpr_arr],
                        tpr=[float(round(v, 5)) for v in tpr_arr],
                        thresholds=r_thresh_clean,
                    )
                except Exception as e:
                    logger.warning(f"Could not compute ROC curve data for exp '{clean_exp}': {e}")

                try:
                    p_arr, r_arr, pr_thresh_arr = precision_recall_curve(y_true_list, scores_list)
                    pr_thresh_clean = [
                        float(round(t, 5)) if np.isfinite(t) else float(round(max(scores_list) + 1.0, 5))
                        for t in pr_thresh_arr
                    ]
                    pr_curve_data = PrecisionRecallCurveData(
                        precision=[float(round(v, 5)) for v in p_arr],
                        recall=[float(round(v, 5)) for v in r_arr],
                        thresholds=pr_thresh_clean,
                    )
                except Exception as e:
                    logger.warning(f"Could not compute PR curve data for exp '{clean_exp}': {e}")
        else:
            cls_name = "positive only" if 1 in unique_classes else "negative only (normal)"
            warning_msg = (
                f"ROC-AUC and PR-AUC are undefined because the evaluation set contains only one class ({cls_name})."
            )
            metric_warnings.append(warning_msg)
            logger.info(f"Dataset '{dataset_id}' evaluation on '{clean_exp}': {warning_msg}")

        # 8. Assemble Score Direction and Threshold Analysis
        score_name = "baseline_max_z_score" if is_baseline else "risk_score"
        threshold_rule = (
            f"Population z-score >= {metadata.z_threshold or 2.0} on graph features"
            if is_baseline
            else f"Top {int((metadata.contamination or 0.1) * 100)}% percentile of training population decision score"
        )
        threshold_analysis = ThresholdAnalysis(
            binary_decision_rule=threshold_rule,
            continuous_score_name=score_name,
            score_direction="higher_is_more_anomalous",
            auc_evaluation_basis="Continuous ranking scores across all thresholds, independent of binary decision cutoff",
            risk_score_is_probability=False,
            risk_score_interpretation="Relative presentation ranking score (0-100) scaled from population percentiles. Not a fraud probability.",
        )

        method_str = getattr(
            metadata,
            "method",
            "Statistical (z-score, no ML)" if is_baseline else "Isolation Forest",
        )

        return ExperimentEvaluationMetrics(
            dataset_id=dataset_id,
            experiment_label=clean_exp,
            status="success",
            error=None,
            model_type=metadata.model_type,
            method=method_str,
            feature_groups=metadata.feature_groups,
            feature_names=metadata.feature_names,
            feature_count=metadata.feature_count,
            n_estimators=metadata.n_estimators,
            contamination=metadata.contamination,
            max_samples=metadata.max_samples,
            random_state=metadata.random_state,
            training_entity_count=metadata.entity_count,
            training_timestamp=metadata.training_timestamp,
            model_artifact_path=getattr(metadata, "model_artifact_path", f"data/models/{dataset_id}__{clean_exp}.joblib"),
            evaluation_mode=eval_mode,
            split_label=effective_split,
            evaluation_mode_note=eval_note,
            labeled_user_count=len(labels) if eval_mode == "in_sample" else (len(allowed_eval_uids) if allowed_eval_uids else 0),
            usable_labeled_user_count=usable_count,
            usable_labels_count=usable_count,
            total_dataset_users=pred_response.total_users,
            positive_count=positive_count,
            negative_count=negative_count,
            positive_prevalence=prevalence,
            score_name=score_name,
            score_direction="higher_is_more_anomalous",
            threshold_analysis=threshold_analysis,
            confusion_matrix=conf_matrix,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            roc_auc=roc_auc,
            pr_auc=pr_auc,
            headline_metric="pr_auc",
            metric_warnings=metric_warnings,
            roc_curve=roc_curve_data,
            precision_recall_curve=pr_curve_data,
            class_imbalance_note=(
                "In financial anomaly detection, the positive (anomalous) class is rare (<5%). "
                "Under severe class imbalance, accuracy can be misleadingly high (e.g. 99% accuracy by predicting all normal). "
                "PR-AUC (Average Precision) and F1 score are the primary headline metrics for evaluating detection efficacy."
            ),
        )

    def compare_experiments(
        self,
        dataset_id: str,
        include_curves: bool = False,
        split_label: Optional[str] = None,
    ) -> EvaluationComparisonResponse:
        """
        Compare all trained experiments for a dataset against ground-truth labels.
        Does NOT silently drop failed experiments; errors are captured with status='error'.
        Returns the ranked comparison table sorted by PR-AUC descending.
        """
        # Ensure labels exist and get label summary
        label_summary = label_registry.get_summary(dataset_id)

        # Retrieve all trained experiments for this dataset
        experiments = anomaly_service.list_experiments(dataset_id)
        if not experiments:
            raise ModelNotTrainedException(
                f"No trained experiments found for dataset '{dataset_id}'. "
                f"Please train at least one experiment first."
            )

        successful_evals: List[ExperimentEvaluationMetrics] = []
        failed_evals: List[ExperimentEvaluationMetrics] = []

        for exp_meta in experiments:
            exp_lbl = exp_meta.experiment_label
            try:
                if split_label is not None:
                    metrics = self.evaluate_experiment(
                        dataset_id=dataset_id,
                        experiment_label=exp_lbl,
                        include_curves=include_curves,
                        split_label=split_label,
                    )
                else:
                    metrics = self.evaluate_experiment(
                        dataset_id=dataset_id,
                        experiment_label=exp_lbl,
                        include_curves=include_curves,
                    )
                successful_evals.append(metrics)
            except Exception as e:
                logger.error(f"Evaluation failed for experiment '{exp_lbl}' on dataset '{dataset_id}': {e}")
                err_metric = ExperimentEvaluationMetrics(
                    dataset_id=dataset_id,
                    experiment_label=exp_lbl,
                    status="error",
                    error=str(e),
                    model_type=exp_meta.model_type,
                    method=getattr(exp_meta, "method", exp_meta.model_type),
                    feature_groups=exp_meta.feature_groups,
                    feature_names=exp_meta.feature_names,
                    feature_count=exp_meta.feature_count,
                    n_estimators=exp_meta.n_estimators,
                    contamination=exp_meta.contamination,
                    max_samples=exp_meta.max_samples,
                    random_state=exp_meta.random_state,
                    training_entity_count=exp_meta.entity_count,
                    training_timestamp=exp_meta.training_timestamp,
                    model_artifact_path=getattr(exp_meta, "model_artifact_path", None),
                    evaluation_mode="held_out" if (split_label or getattr(exp_meta, "split_label", None)) else "in_sample",
                    split_label=split_label or getattr(exp_meta, "split_label", None),
                    labeled_user_count=label_summary.matched_count,
                    metric_warnings=[f"Evaluation failed: {str(e)}"],
                )
                failed_evals.append(err_metric)

        # Sort successful experiments by PR-AUC descending, then F1 score descending
        successful_evals.sort(
            key=lambda m: (m.pr_auc if m.pr_auc is not None else -1.0, m.f1_score if m.f1_score is not None else -1.0),
            reverse=True,
        )

        all_evals = successful_evals + failed_evals

        # Explicitly group by evaluation mode so in-sample and held-out rows are never conflated
        by_eval_mode: Dict[str, List[ExperimentEvaluationMetrics]] = {
            "in_sample": [m for m in all_evals if m.evaluation_mode == "in_sample"],
            "held_out": [m for m in all_evals if m.evaluation_mode == "held_out"],
        }
        modes_present = {m.evaluation_mode for m in all_evals if m.evaluation_mode}
        if len(modes_present) == 1:
            comp_eval_mode = list(modes_present)[0]
        elif len(modes_present) > 1:
            comp_eval_mode = "mixed"
        else:
            comp_eval_mode = "in_sample"

        mode_note = (
            f"Held-out evaluation mode active (split='{split_label or 'custom'}'). Evaluated strictly on test partition entities."
            if comp_eval_mode == "held_out"
            else (
                "Mixed evaluation modes present (in_sample and held_out); see by_evaluation_mode for grouped rows."
                if comp_eval_mode == "mixed"
                else "In-sample evaluation represents pipeline validation. For publication, evaluations must be performed on a held-out test split or time-based partition."
            )
        )

        return EvaluationComparisonResponse(
            dataset_id=dataset_id,
            total_experiments_evaluated=len(all_evals),
            successful_experiments_count=len(successful_evals),
            failed_experiments_count=len(failed_evals),
            labels_summary=label_summary,
            evaluation_mode=comp_eval_mode,
            split_label=split_label,
            evaluation_mode_note=mode_note,
            by_evaluation_mode=by_eval_mode,
            headline_metric="pr_auc",
            class_imbalance_note=(
                "In financial anomaly detection, the positive (anomalous) class is rare (<5%). "
                "Under severe class imbalance, accuracy can be misleadingly high. "
                "PR-AUC (Average Precision) is the primary headline metric for ranking configurations."
            ),
            experiments=all_evals,
        )

    def export_research_run(
        self,
        dataset_id: str,
        results_dir: Optional[Path] = None,
    ) -> ResearchExportResponse:
        """
        Export all experiment results and metadata for a dataset into reproducible JSON and CSV artifacts.
        """
        target_dir = results_dir or (settings.DATA_DIR / "results")
        target_dir.mkdir(parents=True, exist_ok=True)

        comp = self.compare_experiments(dataset_id=dataset_id, include_curves=True)
        now_ts = datetime.now(timezone.utc).isoformat()

        json_file = target_dir / f"{dataset_id}_experiment_results.json"
        csv_file = target_dir / f"{dataset_id}_experiment_results.csv"

        # 1. Export Full JSON Manifest
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(comp.model_dump(), f, indent=2)

        # 2. Export Tabular CSV Summary
        csv_columns = [
            "experiment_label",
            "status",
            "model_type",
            "method",
            "feature_groups",
            "feature_count",
            "usable_labels_count",
            "tp",
            "fp",
            "tn",
            "fn",
            "precision",
            "recall",
            "f1_score",
            "accuracy",
            "roc_auc",
            "pr_auc",
            "evaluation_mode",
            "training_timestamp",
            "error",
        ]

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_columns)
            for exp in comp.experiments:
                cm = exp.confusion_matrix
                writer.writerow([
                    exp.experiment_label,
                    exp.status,
                    exp.model_type or "",
                    exp.method or "",
                    ";".join(exp.feature_groups),
                    exp.feature_count,
                    exp.usable_labels_count,
                    cm.tp if cm else "",
                    cm.fp if cm else "",
                    cm.tn if cm else "",
                    cm.fn if cm else "",
                    exp.precision if exp.precision is not None else "",
                    exp.recall if exp.recall is not None else "",
                    exp.f1_score if exp.f1_score is not None else "",
                    exp.accuracy if exp.accuracy is not None else "",
                    exp.roc_auc if exp.roc_auc is not None else "",
                    exp.pr_auc if exp.pr_auc is not None else "",
                    exp.evaluation_mode,
                    exp.training_timestamp or "",
                    exp.error or "",
                ])

        logger.info(
            f"Exported research run for dataset '{dataset_id}' to: "
            f"JSON={json_file.as_posix()}, CSV={csv_file.as_posix()}"
        )

        return ResearchExportResponse(
            dataset_id=dataset_id,
            export_timestamp=now_ts,
            json_path=str(json_file.as_posix()),
            csv_path=str(csv_file.as_posix()),
            total_experiments=comp.total_experiments_evaluated,
            successful_experiments=comp.successful_experiments_count,
            failed_experiments=comp.failed_experiments_count,
            evaluation_mode=comp.evaluation_mode,
        )


evaluation_service = EvaluationService()
