"""
Cross-Dataset Transfer Evaluation Service for GraphFin.
Executes source-only trained anomaly models on target datasets, computing transfer metrics,
95% Bootstrap Confidence Intervals, Precision@K, transfer degradation, and feature distribution shift checks.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score

from ..core.config import settings
from ..core.exceptions import NotFoundException, ValidationException
from ..core.logging import get_logger
from ..schemas.evaluation import ConfusionMatrix
from ..schemas.transfer import (
    BootstrapCI,
    DegradationMetrics,
    ExperimentTransferResult,
    FeatureDistributionSummary,
    PrecisionAtK,
    TransferExperimentRequest,
    TransferExperimentResponse,
)
from .anomaly_service import FEATURE_GROUP_MAP, anomaly_service, compute_percentile_rank
from .dataset_registry import dataset_registry
from .feature_service import FEATURE_NAMES
from .label_registry import label_registry
from .split_service import split_service

logger = get_logger(__name__)


def compute_bootstrap_pr_auc_ci(
    y_true: List[int],
    scores: List[float],
    n_bootstraps: int = 1000,
    random_state: int = 42,
) -> Tuple[float, BootstrapCI]:
    """
    Compute 95% Bootstrap Confidence Interval for PR-AUC / Average Precision.
    Resamples evaluation set with replacement N times using a fixed random_state.
    """
    yt = np.asarray(y_true)
    sc = np.asarray(scores)
    point_estimate = round(float(average_precision_score(yt, sc)), 4) if len(np.unique(yt)) > 1 else 0.0

    if len(yt) == 0 or len(np.unique(yt)) <= 1:
        ci = BootstrapCI(
            point_estimate=point_estimate,
            ci_lower=point_estimate,
            ci_upper=point_estimate,
        )
        return point_estimate, ci

    rng = np.random.RandomState(random_state)
    n = len(yt)
    boot_scores = []

    # Stratified subsample for bootstrap speed if evaluation set > 20,000
    if n > 20000:
        pos_idxs = np.where(yt == 1)[0]
        neg_idxs = np.where(yt == 0)[0]
        max_neg = min(len(neg_idxs), 20000 - len(pos_idxs))
        sub_idxs = np.concatenate([pos_idxs, rng.choice(neg_idxs, size=max_neg, replace=False)])
        yt = yt[sub_idxs]
        sc = sc[sub_idxs]
        n = len(yt)

    for _ in range(n_bootstraps):
        idxs = rng.randint(0, n, size=n)
        yt_b = yt[idxs]
        sc_b = sc[idxs]
        if len(np.unique(yt_b)) > 1:
            boot_scores.append(float(average_precision_score(yt_b, sc_b)))
        else:
            boot_scores.append(point_estimate)

    ci_lower = round(float(np.percentile(boot_scores, 2.5)), 4)
    ci_upper = round(float(np.percentile(boot_scores, 97.5)), 4)

    ci = BootstrapCI(
        point_estimate=point_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
    )
    return point_estimate, ci


def compute_precision_at_k(
    y_true: List[int],
    scores: List[float],
    k_values: List[int] = [10, 25, 50, 100],
) -> PrecisionAtK:
    """
    Compute Precision@K = (true positives in top K highest score accounts) / K.
    Uses K = min(K, len(target_entities)).
    """
    n = len(y_true)
    if n == 0:
        return PrecisionAtK(p_at_10=0.0, p_at_25=0.0, p_at_50=0.0, p_at_100=0.0)

    # Sort descending by continuous score
    order = np.argsort(scores)[::-1]
    y_sorted = np.asarray(y_true)[order]

    res = {}
    for k in k_values:
        eff_k = min(k, n)
        if eff_k > 0:
            tp_k = int(np.sum(y_sorted[:eff_k]))
            p_k = round(float(tp_k / eff_k), 4)
        else:
            p_k = 0.0
        res[f"p_at_{k}"] = p_k

    return PrecisionAtK(**res)


def compute_degradation(source_pr_auc: float, target_pr_auc: float) -> DegradationMetrics:
    """
    Compute absolute and relative transfer degradation.
    relative_degradation = (source_pr_auc - target_pr_auc) / source_pr_auc (None if source == 0).
    """
    abs_deg = round(float(source_pr_auc - target_pr_auc), 4)
    rel_deg = round(float(abs_deg / source_pr_auc), 4) if source_pr_auc > 0 else None
    return DegradationMetrics(
        source_pr_auc=round(float(source_pr_auc), 4),
        target_pr_auc=round(float(target_pr_auc), 4),
        absolute_degradation=abs_deg,
        relative_degradation=rel_deg,
    )



class TransferService:
    """Service evaluating cross-dataset transfer generalization performance."""

    def evaluate_transfer(
        self,
        request: TransferExperimentRequest,
    ) -> TransferExperimentResponse:
        """
        Execute cross-dataset transfer experiment between source and target datasets.
        """
        src_id = request.source_dataset_id
        tgt_id = request.target_dataset_id
        seed = request.random_state if request.random_state is not None else 42
        n_boot = request.n_bootstraps if request.n_bootstraps is not None else 1000

        # 1. Retrieve datasets and ground-truth labels
        src_store = dataset_registry.get(src_id)
        tgt_store = dataset_registry.get(tgt_id)

        src_labels = label_registry.get_labels(src_id)
        tgt_labels = label_registry.get_labels(tgt_id)

        # 2. Extract feature matrices
        src_uids, src_full_matrix, src_feat_names = src_store.get_feature_matrix()
        tgt_uids, tgt_full_matrix, tgt_feat_names = tgt_store.get_feature_matrix()

        # Phase 2: Feature Space Validation — FAIL LOUDLY if schemas mismatch
        if src_feat_names != tgt_feat_names:
            raise ValidationException(
                f"Feature schema mismatch between source '{src_id}' ({src_feat_names}) "
                f"and target '{tgt_id}' ({tgt_feat_names}). Cannot proceed with cross-dataset transfer."
            )

        # 3. Resolve Train/Test Splits for Source and Target
        src_split_lbl = (request.source_split_label or "research-split").strip()
        tgt_split_lbl = (request.target_split_label or "research-split").strip()

        try:
            src_split_obj = split_service.get_split(src_id, src_split_lbl)
        except NotFoundException:
            src_split_obj = split_service.create_split(
                src_id, test_size=0.30, random_state=seed, split_label=src_split_lbl
            )

        try:
            tgt_split_obj = split_service.get_split(tgt_id, tgt_split_lbl)
        except NotFoundException:
            tgt_split_obj = split_service.create_split(
                tgt_id, test_size=0.30, random_state=seed, split_label=tgt_split_lbl
            )

        src_uid_to_idx = {u: i for i, u in enumerate(src_uids)}
        tgt_uid_to_idx = {u: i for i, u in enumerate(tgt_uids)}

        src_train_indices = [src_uid_to_idx[u] for u in src_split_obj.train_user_ids if u in src_uid_to_idx]
        src_test_indices = [src_uid_to_idx[u] for u in src_split_obj.test_user_ids if u in src_uid_to_idx]
        tgt_test_indices = [tgt_uid_to_idx[u] for u in tgt_split_obj.test_user_ids if u in tgt_uid_to_idx]

        # 4. Feature Distribution Check (Source vs Target across all 19+ features)
        distribution_checks: List[FeatureDistributionSummary] = []
        for j, fname in enumerate(src_feat_names):
            s_col = src_full_matrix[:, j]
            t_col = tgt_full_matrix[:, j]

            s_mean = float(np.mean(s_col))
            s_std = float(np.std(s_col))
            t_mean = float(np.mean(t_col))
            t_std = float(np.std(t_col))

            pooled_std = np.sqrt((s_std**2 + t_std**2) / 2.0)
            smd = (t_mean - s_mean) / pooled_std if pooled_std > 1e-9 else 0.0

            distribution_checks.append(
                FeatureDistributionSummary(
                    feature_name=fname,
                    source_mean=round(s_mean, 4),
                    target_mean=round(t_mean, 4),
                    source_std=round(s_std, 4),
                    target_std=round(t_std, 4),
                    standardized_mean_difference=round(float(smd), 4),
                )
            )

        # 5. Experiment Execution (E0 through E5)
        requested_exps = request.experiments or ["E0", "E1", "E2", "E3", "E4", "E5"]
        results: List[ExperimentTransferResult] = []

        exp_configs = {
            "E0": {
                "label": "E0_graph_baseline",
                "method": "Statistical z-score (source fitted)",
                "groups": ["graph"],
            },
            "E1": {
                "label": "E1_graph_ml",
                "method": "Isolation Forest (Graph only)",
                "groups": ["graph"],
            },
            "E2": {
                "label": "E2_graph_behavioral_ml",
                "method": "Isolation Forest (Graph + Behavioral)",
                "groups": ["graph", "behavioral"],
            },
            "E3": {
                "label": "E3_graph_temporal_ml",
                "method": "Isolation Forest (Graph + Temporal)",
                "groups": ["graph", "temporal"],
            },
            "E4": {
                "label": "E4_full_graphfin",
                "method": "Isolation Forest (Full GraphFin)",
                "groups": ["graph", "behavioral", "temporal"],
            },
            "E5": {
                "label": "E5_egonet_baseline",
                "method": "Isolation Forest (Egonet + Circular Flow)",
                "groups": ["egonet"],
            },
        }

        for exp_key in ["E0", "E1", "E2", "E3", "E4", "E5"]:
            if exp_key not in requested_exps and f"{exp_key}_" not in str(requested_exps):
                continue

            cfg = exp_configs[exp_key]
            exp_label = cfg["label"]
            groups = cfg["groups"]

            # Resolve feature indices for this experiment's feature groups
            col_indices = []
            for g in groups:
                if g in FEATURE_GROUP_MAP:
                    for f in FEATURE_GROUP_MAP[g]:
                        if f in src_feat_names:
                            col_indices.append(src_feat_names.index(f))

            if not col_indices:
                results.append(
                    ExperimentTransferResult(
                        experiment_label=exp_key,
                        status="error",
                        error="Selected feature groups produced 0 features.",
                        method=cfg["method"],
                        feature_groups=groups,
                        feature_count=0,
                    )
                )
                continue

            # Feature matrices for source train, source test, and target test
            X_src_train = src_full_matrix[src_train_indices, :][:, col_indices]
            X_src_test = src_full_matrix[src_test_indices, :][:, col_indices]
            X_tgt_test = tgt_full_matrix[tgt_test_indices, :][:, col_indices]

            # Ground truth labels for source test and target test
            src_test_uids = [src_uids[i] for i in src_test_indices]
            tgt_test_uids = [tgt_uids[i] for i in tgt_test_indices]

            y_src_test = [1 if src_labels.get(u, False) else 0 for u in src_test_uids]
            y_tgt_test = [1 if tgt_labels.get(u, False) else 0 for u in tgt_test_uids]

            # Fit source scaler (mean and std) strictly on X_src_train
            src_means = np.mean(X_src_train, axis=0)
            src_stds = np.std(X_src_train, axis=0)
            src_stds[src_stds < 1e-9] = 1.0

            # Scale source train, source test, and target test using source parameters ONLY
            X_src_train_scaled = (X_src_train - src_means) / src_stds
            X_src_test_scaled = (X_src_test - src_means) / src_stds
            X_tgt_test_scaled = (X_tgt_test - src_means) / src_stds

            # -------------------------------------------------------------
            # Branch A: E0 Statistical Baseline (z-score thresholding)
            # -------------------------------------------------------------
            if exp_key == "E0":
                # Compute max z-scores relative to source distribution
                src_test_z = np.max((X_src_test - src_means) / src_stds, axis=1)
                tgt_test_z = np.max((X_tgt_test - src_means) / src_stds, axis=1)

                # Source-domain evaluation
                src_pr, src_pr_ci = compute_bootstrap_pr_auc_ci(y_src_test, src_test_z.tolist(), n_bootstraps=n_boot, random_state=seed)

                # Target-domain evaluation
                tgt_pr, tgt_pr_ci = compute_bootstrap_pr_auc_ci(y_tgt_test, tgt_test_z.tolist(), n_bootstraps=n_boot, random_state=seed)
                tgt_roc = round(float(roc_auc_score(y_tgt_test, tgt_test_z)), 4) if len(np.unique(y_tgt_test)) > 1 else 0.0

                # Binary decision rule: z >= 2.0
                y_pred_tgt = [1 if z >= 2.0 else 0 for z in tgt_test_z]
                tp = sum(1 for yt, yp in zip(y_tgt_test, y_pred_tgt) if yt == 1 and yp == 1)
                fp = sum(1 for yt, yp in zip(y_tgt_test, y_pred_tgt) if yt == 0 and yp == 1)
                tn = sum(1 for yt, yp in zip(y_tgt_test, y_pred_tgt) if yt == 0 and yp == 0)
                fn = sum(1 for yt, yp in zip(y_tgt_test, y_pred_tgt) if yt == 1 and yp == 0)

                prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
                rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
                f1 = round(2.0 * prec * rec / (prec + rec), 4) if (prec + rec) > 0 else 0.0
                acc = round((tp + tn) / len(y_tgt_test), 4) if len(y_tgt_test) > 0 else 0.0

                p_at_k = compute_precision_at_k(y_tgt_test, tgt_test_z.tolist())

                abs_deg = round(src_pr - tgt_pr, 4)
                rel_deg = round(abs_deg / src_pr, 4) if src_pr > 0 else None

                results.append(
                    ExperimentTransferResult(
                        experiment_label=exp_key,
                        status="success",
                        method=cfg["method"],
                        feature_groups=groups,
                        feature_count=len(col_indices),
                        source_pr_auc=src_pr,
                        source_pr_auc_ci=src_pr_ci,
                        target_pr_auc=tgt_pr,
                        target_pr_auc_ci=tgt_pr_ci,
                        target_roc_auc=tgt_roc,
                        target_precision=prec,
                        target_recall=rec,
                        target_f1=f1,
                        target_accuracy=acc,
                        confusion_matrix=ConfusionMatrix(tp=tp, fp=fp, tn=tn, fn=fn),
                        precision_at_k=p_at_k,
                        degradation=DegradationMetrics(
                            source_pr_auc=src_pr,
                            target_pr_auc=tgt_pr,
                            absolute_degradation=abs_deg,
                            relative_degradation=rel_deg,
                        ),
                    )
                )

            # -------------------------------------------------------------
            # Branch B: E1-E5 Isolation Forest Models
            # -------------------------------------------------------------
            else:
                # Fit Isolation Forest strictly on source train partition
                model = IsolationForest(
                    n_estimators=100,
                    contamination=0.005,
                    max_samples="auto",
                    random_state=seed,
                    n_jobs=-1,
                )
                model.fit(X_src_train_scaled)

                # Source test scores & target test scores (decision_function: lower/more negative = more anomalous -> invert to risk scores)
                src_train_dec = model.decision_function(X_src_train_scaled)
                src_test_dec = model.decision_function(X_src_test_scaled)
                tgt_test_dec = model.decision_function(X_tgt_test_scaled)

                # Convert decision scores to presentation risk scores (0-100) using source train percentiles
                src_test_scores = [100.0 * (1.0 - compute_percentile_rank(s, src_train_dec)) for s in src_test_dec]
                tgt_test_scores = [100.0 * (1.0 - compute_percentile_rank(s, src_train_dec)) for s in tgt_test_dec]

                # Source-domain evaluation
                src_pr, src_pr_ci = compute_bootstrap_pr_auc_ci(y_src_test, src_test_scores, n_bootstraps=n_boot, random_state=seed)

                # Target-domain evaluation
                tgt_pr, tgt_pr_ci = compute_bootstrap_pr_auc_ci(y_tgt_test, tgt_test_scores, n_bootstraps=n_boot, random_state=seed)
                tgt_roc = round(float(roc_auc_score(y_tgt_test, tgt_test_scores)), 4) if len(np.unique(y_tgt_test)) > 1 else 0.0

                # Target prediction cutoffs using source-fitted model.predict()
                tgt_preds = model.predict(X_tgt_test_scaled)
                y_pred_tgt = [1 if p == -1 else 0 for p in tgt_preds]

                tp = sum(1 for yt, yp in zip(y_tgt_test, y_pred_tgt) if yt == 1 and yp == 1)
                fp = sum(1 for yt, yp in zip(y_tgt_test, y_pred_tgt) if yt == 0 and yp == 1)
                tn = sum(1 for yt, yp in zip(y_tgt_test, y_pred_tgt) if yt == 0 and yp == 0)
                fn = sum(1 for yt, yp in zip(y_tgt_test, y_pred_tgt) if yt == 1 and yp == 0)

                prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
                rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
                f1 = round(2.0 * prec * rec / (prec + rec), 4) if (prec + rec) > 0 else 0.0
                acc = round((tp + tn) / len(y_tgt_test), 4) if len(y_tgt_test) > 0 else 0.0

                p_at_k = compute_precision_at_k(y_tgt_test, tgt_test_scores)

                abs_deg = round(src_pr - tgt_pr, 4)
                rel_deg = round(abs_deg / src_pr, 4) if src_pr > 0 else None

                results.append(
                    ExperimentTransferResult(
                        experiment_label=exp_key,
                        status="success",
                        method=cfg["method"],
                        feature_groups=groups,
                        feature_count=len(col_indices),
                        source_pr_auc=src_pr,
                        source_pr_auc_ci=src_pr_ci,
                        target_pr_auc=tgt_pr,
                        target_pr_auc_ci=tgt_pr_ci,
                        target_roc_auc=tgt_roc,
                        target_precision=prec,
                        target_recall=rec,
                        target_f1=f1,
                        target_accuracy=acc,
                        confusion_matrix=ConfusionMatrix(tp=tp, fp=fp, tn=tn, fn=fn),
                        precision_at_k=p_at_k,
                        degradation=DegradationMetrics(
                            source_pr_auc=src_pr,
                            target_pr_auc=tgt_pr,
                            absolute_degradation=abs_deg,
                            relative_degradation=rel_deg,
                        ),
                    )
                )

        # Direction label
        src_label = "IBM AML" if "ibm" in src_id.lower() or "ddb" in src_id or "03f" in src_id else "PaySim"
        tgt_label = "PaySim" if "paysim" in tgt_id.lower() or "e8d" in tgt_id else "IBM AML"
        direction = f"{src_label}->{tgt_label}"

        # Paper-reportable status validation
        is_paper_reportable = bool(
            len(results) > 0
            and all(r.status == "success" for r in results)
            and len(tgt_test_indices) >= 500
        )
        run_tier = "paper_reportable" if is_paper_reportable else "pipeline_validation"

        betweenness_methods = {
            src_id: "Sampled betweenness centrality (Brandes with k=500, random_state=42)",
            tgt_id: "Sampled betweenness centrality (Brandes with k=500, random_state=42)",
        }

        paysim_label_rule = (
            "Account-involvement rule: An account is labeled positive (1) if it appears as sender or receiver "
            "in at least one transaction where isFraud == 1; negative (0) otherwise."
        )

        now_str = datetime.now(timezone.utc).isoformat()

        response = TransferExperimentResponse(
            source_dataset_id=src_id,
            target_dataset_id=tgt_id,
            direction=direction,
            is_paper_reportable=is_paper_reportable,
            run_quality_tier=run_tier,
            betweenness_centrality_method=betweenness_methods,
            paysim_account_label_rule=paysim_label_rule,
            timestamp=now_str,
            experiments=results,
            feature_distribution_check=distribution_checks,
            reproducibility_manifest={
                "source_dataset_id": src_id,
                "target_dataset_id": tgt_id,
                "source_entities": len(src_uids),
                "target_entities": len(tgt_uids),
                "source_split_label": src_split_lbl,
                "target_split_label": tgt_split_lbl,
                "random_state": seed,
                "n_bootstraps": n_boot,
                "feature_count": len(src_feat_names),
                "feature_names": src_feat_names,
            },
        )

        # Export result to data/results/cross_dataset/
        try:
            out_dir = settings.DATA_DIR / "results" / "cross_dataset"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"transfer_{src_label}_to_{tgt_label}.json".lower().replace(" ", "_")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(response.model_dump(), f, indent=2)
            logger.info(f"Exported cross-dataset transfer result to {out_file}")
        except Exception as e:
            logger.warning(f"Could not export transfer result to disk: {e}")

        return response


transfer_service = TransferService()
