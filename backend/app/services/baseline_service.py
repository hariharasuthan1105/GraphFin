"""
Rule-Based Statistical Baseline Anomaly Detection Service.
Computes population z-scores across structural and behavioral features.
Flags users as anomalous if any feature exceeds mean + z_threshold * std_dev.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np

from ..core.exceptions import ValidationException
from ..core.logging import get_logger
from ..schemas.anomaly import (
    AnomalyTrainResponse,
    BaselineTrainRequest,
    ModelMetadata,
)
from .dataset_registry import dataset_registry
from .feature_service import FEATURE_NAMES

logger = get_logger(__name__)

DEFAULT_BASELINE_FEATURES = [
    "weighted_out_degree",
    "betweenness_centrality",
    "total_degree",
]


class BaselineService:
    """Non-ML rule-based statistical baseline detector using population z-scores."""

    def train_baseline(
        self,
        dataset_id: str,
        request: Optional[BaselineTrainRequest] = None,
    ) -> AnomalyTrainResponse:
        """
        Evaluate statistical baseline on the dataset's features and persist as a unified experiment.
        """
        from .anomaly_service import anomaly_service, compute_percentile_rank

        req = request or BaselineTrainRequest()
        exp_label = (req.experiment_label or "baseline_statistical").strip()
        z_thresh = req.z_threshold if req.z_threshold is not None else 2.0

        if req.feature_groups:
            selected_features, col_indices = anomaly_service._resolve_feature_columns(req.feature_groups)
        else:
            selected_features = req.features or DEFAULT_BASELINE_FEATURES

            # 2. Validate requested features
            col_indices = []
            for feat in selected_features:
                if feat not in FEATURE_NAMES:
                    raise ValidationException(
                        f"Unknown feature '{feat}' requested for baseline. Available: {FEATURE_NAMES}"
                    )
                col_indices.append(FEATURE_NAMES.index(feat))

        # 1. Retrieve dataset
        store = dataset_registry.get(dataset_id)
        user_ids, full_matrix, _ = store.get_feature_matrix()

        if len(user_ids) == 0 or full_matrix.shape[0] == 0:
            raise ValidationException(
                f"Cannot compute baseline on empty dataset '{dataset_id}'."
            )

        # 3. Resolve row slice if training on a held-out split partition
        split_lbl = (req.split_label or "").strip() if req.split_label else None
        if split_lbl:
            from .split_service import split_service
            split_obj = split_service.get_split(dataset_id, split_lbl)
            uid_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
            train_uids = split_obj.train_user_ids
            train_indices = [uid_to_idx[uid] for uid in train_uids if uid in uid_to_idx]
            if len(train_indices) == 0:
                raise ValidationException(
                    f"Train partition for split '{split_lbl}' has 0 matching entities in dataset '{dataset_id}'."
                )
            X_train = full_matrix[train_indices, :][:, col_indices]
            fit_user_ids = train_uids
            eval_mode = "held_out"
        else:
            X_train = full_matrix[:, col_indices]
            fit_user_ids = user_ids
            eval_mode = "in_sample"

        if np.isnan(X_train).any() or np.isinf(X_train).any():
            X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)

        # 4. Compute mean and standard deviation per feature strictly from train partition
        n_entities = len(fit_user_ids)
        means = np.mean(X_train, axis=0)
        stds = np.std(X_train, axis=0)

        # 5. Compute z-scores for all users in the dataset relative to train distribution
        X_all = full_matrix[:, col_indices]
        if np.isnan(X_all).any() or np.isinf(X_all).any():
            X_all = np.nan_to_num(X_all, nan=0.0, posinf=0.0, neginf=0.0)

        z_matrix = np.zeros_like(X_all)
        feature_stats: Dict[str, Dict[str, float]] = {}

        for j, feat_name in enumerate(selected_features):
            m = float(means[j])
            s = float(stds[j])
            if s > 1e-9:
                z_matrix[:, j] = (X_all[:, j] - m) / s
            else:
                z_matrix[:, j] = 0.0

            col_data = X_train[:, j]
            feature_stats[feat_name] = {
                "mean": float(round(m, 4)),
                "std": float(round(s, 4)),
                "p10": float(round(np.percentile(col_data, 10), 4)),
                "p50": float(round(np.percentile(col_data, 50), 4)),
                "p90": float(round(np.percentile(col_data, 90), 4)),
                "min": float(round(np.min(col_data), 4)),
                "max": float(round(np.max(col_data), 4)),
            }

        # 6. For each user, compute max z-score, prediction, risk score, and reasons
        max_z_scores = np.max(z_matrix, axis=1)

        raw_scores_dict: Dict[str, float] = {}
        predictions_dict: Dict[str, int] = {}
        risk_scores_dict: Dict[str, float] = {}
        reasons_dict: Dict[str, List[str]] = {}

        # Reason mapping dictionary
        reason_map = {
            "transaction_count": "unusually high transaction count",
            "total_sent": "unusually high outgoing volume",
            "total_received": "unusually high incoming volume",
            "maximum_transaction_amount": "unusually high transaction amount",
            "unique_receivers": "unusually high receiver diversity",
            "unique_senders": "unusually high sender diversity",
            "betweenness_centrality": "unusually high network centrality",
            "weighted_out_degree": "unusually high graph outgoing weight",
            "weighted_in_degree": "unusually high graph incoming weight",
            "total_degree": "unusually high counterparty connections",
            "in_degree": "unusually high incoming connection count",
            "out_degree": "unusually high outgoing connection count",
        }

        for i, uid in enumerate(user_ids):
            max_z = float(round(max_z_scores[i], 4))
            raw_scores_dict[uid] = max_z

            is_suspicious = bool(max_z >= z_thresh)
            predictions_dict[uid] = -1 if is_suspicious else 1

            # Risk score: percentile rank of max_z in the population (higher z = higher risk)
            pct = compute_percentile_rank(max_z, max_z_scores)
            risk_score = round(float(np.clip(100.0 * pct, 0.0, 100.0)), 2)
            risk_scores_dict[uid] = risk_score

            user_reasons: List[str] = []
            if is_suspicious:
                for j, feat_name in enumerate(selected_features):
                    if z_matrix[i, j] >= z_thresh:
                        reason_text = reason_map.get(
                            feat_name, f"unusually high {feat_name}"
                        )
                        user_reasons.append(reason_text)
            reasons_dict[uid] = user_reasons

        # Feature groups (explicit or inferred)
        if req.feature_groups:
            groups = list(req.feature_groups)
        else:
            groups = []
            if any(f in ["in_degree", "out_degree", "total_degree", "weighted_in_degree", "weighted_out_degree", "betweenness_centrality"] for f in selected_features):
                groups.append("graph")
            if any(f in ["transaction_count", "total_sent", "total_received", "net_flow", "average_transaction_amount", "maximum_transaction_amount", "unique_receivers", "unique_senders"] for f in selected_features):
                groups.append("behavioral")
            if any(f in ["transactions_per_day", "transactions_per_week", "average_time_between_transactions", "minimum_time_between_transactions", "maximum_time_between_transactions"] for f in selected_features):
                groups.append("temporal")

        # 7. Assemble metadata
        metadata = ModelMetadata(
            model_type="StatisticalBaseline",
            method="Statistical (z-score, no ML)",
            sklearn_version="N/A",
            dataset_id=dataset_id,
            experiment_label=exp_label,
            split_label=split_lbl,
            evaluation_mode=eval_mode,
            feature_groups=groups,
            feature_names=selected_features,
            feature_count=len(selected_features),
            z_threshold=z_thresh,
            z_score_threshold=z_thresh,
            baseline_feature_names=selected_features,
            entity_count=n_entities,
            training_entity_count=n_entities,
            training_timestamp=datetime.now(timezone.utc).isoformat(),
            model_artifact_path=f"data/models/{dataset_id}__{exp_label}.joblib",
            feature_stats=feature_stats,
        )

        artifact = {
            "model_type": "StatisticalBaseline",
            "metadata": metadata.model_dump(),
            "dataset_id": dataset_id,
            "experiment_label": exp_label,
            "split_label": split_lbl,
            "evaluation_mode": eval_mode,
            "raw_scores": raw_scores_dict,
            "predictions": predictions_dict,
            "risk_scores": risk_scores_dict,
            "reasons": reasons_dict,
            "user_ids": fit_user_ids,
            "z_threshold": z_thresh,
            "features": selected_features,
        }

        # Save into unified anomaly service repository
        anomaly_service.save_custom_artifact(dataset_id, exp_label, artifact, split_label=split_lbl)

        logger.info(
            f"Trained statistical baseline on dataset '{dataset_id}' as experiment '{exp_label}' "
            f"with {len(selected_features)} features and z_threshold={z_thresh}."
        )

        return AnomalyTrainResponse(
            dataset_id=dataset_id,
            message=(
                f"Statistical baseline evaluated successfully on {n_entities} entities using "
                f"{len(selected_features)} features with z_threshold={z_thresh}."
            ),
            status="success",
            model_metadata=metadata,
        )


baseline_service = BaselineService()
