"""
Machine Learning Anomaly Detection Service.
Trains and evaluates Isolation Forest and Statistical Baseline models on user-level feature matrices.
Supports dynamic feature-group selection, multi-experiment persistence, deterministic
percentile-based presentation risk scoring, transparent explainability, and joblib persistence.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
import sklearn
from sklearn.ensemble import IsolationForest

from ..core.config import settings
from ..core.exceptions import (
    DataNotFoundException,
    ModelNotTrainedException,
    NotFoundException,
    ValidationException,
)
from ..core.logging import get_logger
from ..schemas.anomaly import (
    AnomalySummaryResponse,
    AnomalyTrainRequest,
    AnomalyTrainResponse,
    ModelMetadata,
    UserAnomalyListResponse,
    UserAnomalyResult,
)
from .dataset_registry import dataset_registry
from .feature_service import FEATURE_NAMES
from .split_service import split_service

logger = get_logger(__name__)

# Canonical grouping of the 19 features
FEATURE_GROUP_MAP: Dict[str, List[str]] = {
    "graph": [
        "in_degree",
        "out_degree",
        "total_degree",
        "weighted_in_degree",
        "weighted_out_degree",
        "betweenness_centrality",
    ],
    "behavioral": [
        "transaction_count",
        "total_sent",
        "total_received",
        "net_flow",
        "average_transaction_amount",
        "maximum_transaction_amount",
        "unique_receivers",
        "unique_senders",
    ],
    "temporal": [
        "transactions_per_day",
        "transactions_per_week",
        "average_time_between_transactions",
        "minimum_time_between_transactions",
        "maximum_time_between_transactions",
    ],
}


def compute_percentile_rank(score: float, population_scores: np.ndarray) -> float:
    """
    Compute empirical percentile rank of a score within a reference population.
    Formula: (count(pop < score) + 0.5 * count(pop == score)) / N
    Returns a float in [0.0, 1.0].
    """
    n = len(population_scores)
    if n <= 1:
        return 0.5
    count_less = int(np.sum(population_scores < score))
    count_equal = int(np.sum(population_scores == score))
    rank = (count_less + 0.5 * count_equal) / n
    return float(np.clip(rank, 0.0, 1.0))


def compute_risk_score(decision_score: float, train_decision_scores: np.ndarray) -> float:
    """
    Compute 0-100 presentation risk score as the inverted percentile rank of the
    Isolation Forest raw decision_function score within the training population.

    Formula:
        risk_score = 100 * (1 - percentile_rank(decision_function_score))

    Direction explanation:
        - raw decision_function score: higher values = more normal, lower/negative values = more anomalous.
        - presentation risk_score: 100 = most anomalous, 0 = most normal.
        NOTE: The 0–100 score is a relative presentation/ranking score derived from model output.
        It is NOT a calibrated probability of fraud.
        It must not be interpreted as a percentage probability that an account is fraudulent.
    """
    pct = compute_percentile_rank(decision_score, train_decision_scores)
    risk = 100.0 * (1.0 - pct)
    return round(float(np.clip(risk, 0.0, 100.0)), 2)


class AnomalyService:
    """Service managing Isolation Forest & baseline training, persistence, and inference."""

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or settings.MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        # In-memory artifact cache keyed by (dataset_id, experiment_label, split_label)
        self._cache: Dict[Tuple[str, str, Optional[str]], Dict[str, Any]] = {}

    def _get_model_path(
        self, dataset_id: str, experiment_label: str = "default", split_label: Optional[str] = None
    ) -> Path:
        clean_exp = (experiment_label or "default").strip()
        if split_label:
            clean_split = split_label.strip()
            split_path = self.models_dir / f"{dataset_id}__{clean_exp}__{clean_split}.joblib"
            if split_path.exists():
                return split_path
        path = self.models_dir / f"{dataset_id}__{clean_exp}.joblib"
        # Backward-compatibility check for legacy un-suffixed default model
        if not path.exists() and clean_exp == "default":
            legacy_path = self.models_dir / f"{dataset_id}.joblib"
            if legacy_path.exists():
                return legacy_path
        return path

    def _resolve_feature_columns(
        self, feature_groups: List[str]
    ) -> Tuple[List[str], List[int]]:
        """
        Resolve feature names and column indices corresponding to the selected feature groups,
        preserving the canonical ordering from FEATURE_NAMES.
        """
        selected_set = set()
        for group in feature_groups:
            group_key = group.strip().lower()
            if group_key in FEATURE_GROUP_MAP:
                selected_set.update(FEATURE_GROUP_MAP[group_key])
            else:
                raise ValidationException(
                    f"Unknown feature group '{group}'. Allowed values: {list(FEATURE_GROUP_MAP.keys())}."
                )

        selected_names: List[str] = []
        selected_indices: List[int] = []
        for idx, feat in enumerate(FEATURE_NAMES):
            if feat in selected_set:
                selected_names.append(feat)
                selected_indices.append(idx)

        return selected_names, selected_indices

    def train_model(
        self,
        dataset_id: str,
        request: AnomalyTrainRequest,
        experiment_label: Optional[str] = None,
    ) -> AnomalyTrainResponse:
        """
        Train an Isolation Forest model for a dataset and persist it via joblib.
        Artifacts are keyed by (dataset_id, experiment_label).
        """
        exp_label = (experiment_label or request.experiment_label or "default").strip()
        split_lbl = (request.split_label or "").strip() if request.split_label else None

        # 1. Retrieve dataset StateStore from registry
        store = dataset_registry.get(dataset_id)

        # 2. Extract the canonical 19-feature matrix (N x 19)
        user_ids, full_matrix, _ = store.get_feature_matrix()

        if len(user_ids) == 0 or full_matrix.shape[0] == 0:
            raise ValidationException(
                f"Cannot train anomaly model: dataset '{dataset_id}' contains no users or transactions."
            )

        # 3. Resolve row slice if training on a held-out split partition
        if split_lbl:
            split_assignment = split_service.get_split(dataset_id, split_lbl)
            uid_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
            train_uids = split_assignment.train_user_ids
            train_row_indices = [uid_to_idx[uid] for uid in train_uids if uid in uid_to_idx]
            if len(train_row_indices) == 0:
                raise ValidationException(
                    f"Train partition for split '{split_lbl}' has 0 matching entities in dataset '{dataset_id}'."
                )
            active_matrix = full_matrix[train_row_indices, :]
            fit_user_ids = train_uids
            eval_mode = "held_out"
        else:
            active_matrix = full_matrix
            fit_user_ids = user_ids
            eval_mode = "in_sample"

        # 4. Resolve and slice requested feature groups
        groups = request.feature_groups or ["graph", "behavioral", "temporal"]
        selected_feature_names, col_indices = self._resolve_feature_columns(groups)

        if not col_indices:
            raise ValidationException("Selected feature groups yielded 0 features.")

        X = active_matrix[:, col_indices]

        # 5. Defensive numeric validation & NaN/inf handling
        if not np.issubdtype(X.dtype, np.number):
            raise ValidationException("Feature matrix contains non-numeric data types.")

        if np.isnan(X).any() or np.isinf(X).any():
            logger.warning(
                f"Dataset '{dataset_id}' feature matrix contains NaN or Inf. "
                "Applying documented zero-imputation strategy."
            )
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # 6. Configure and fit Isolation Forest
        n_estimators = request.n_estimators or 100
        contamination = request.contamination or 0.1
        max_samples = request.max_samples or "auto"
        random_state = request.random_state if request.random_state is not None else 42

        model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1,
        )

        logger.info(
            f"Fitting IsolationForest on dataset '{dataset_id}' (exp='{exp_label}', split='{split_lbl}', mode='{eval_mode}'): shape={X.shape}, "
            f"groups={groups}, features={len(selected_feature_names)}, "
            f"n_estimators={n_estimators}, contamination={contamination}"
        )
        model.fit(X)

        # 7. Compute training population decision function scores
        train_scores = model.decision_function(X)

        # 8. Compute per-feature percentile distributions for explainability (train partition only)
        feature_stats: Dict[str, Dict[str, float]] = {}
        for col_idx, feat_name in enumerate(selected_feature_names):
            col_data = X[:, col_idx]
            feature_stats[feat_name] = {
                "p10": float(round(np.percentile(col_data, 10), 4)),
                "p50": float(round(np.percentile(col_data, 50), 4)),
                "p90": float(round(np.percentile(col_data, 90), 4)),
                "min": float(round(np.min(col_data), 4)),
                "max": float(round(np.max(col_data), 4)),
                "mean": float(round(np.mean(col_data), 4)),
            }

        model_file_path = self.models_dir / f"{dataset_id}__{exp_label}.joblib"

        # 9. Assemble ModelMetadata
        metadata = ModelMetadata(
            model_type="IsolationForest",
            method="Isolation Forest",
            sklearn_version=sklearn.__version__,
            dataset_id=dataset_id,
            experiment_label=exp_label,
            split_label=split_lbl,
            evaluation_mode=eval_mode,
            feature_groups=groups,
            feature_names=selected_feature_names,
            feature_count=len(selected_feature_names),
            n_estimators=n_estimators,
            contamination=contamination,
            max_samples=max_samples,
            random_state=random_state,
            entity_count=len(fit_user_ids),
            training_entity_count=len(fit_user_ids),
            training_timestamp=datetime.now(timezone.utc).isoformat(),
            model_artifact_path=str(model_file_path.as_posix()),
            feature_stats=feature_stats,
        )

        # 10. Persist model artifact via joblib (keyed by dataset_id and experiment_label)
        artifact = {
            "model_type": "IsolationForest",
            "model": model,
            "metadata": metadata.model_dump(),
            "train_scores": train_scores,
            "user_ids": fit_user_ids,
            "col_indices": col_indices,
            "dataset_id": dataset_id,
            "experiment_label": exp_label,
            "split_label": split_lbl,
            "evaluation_mode": eval_mode,
        }

        model_path = self.models_dir / f"{dataset_id}__{exp_label}.joblib"
        if split_lbl:
            split_model_path = self.models_dir / f"{dataset_id}__{exp_label}__{split_lbl}.joblib"
            joblib.dump(artifact, split_model_path)
            self._cache[(dataset_id, exp_label, split_lbl)] = artifact

        if not model_path.exists() or split_lbl == "research-split" or not split_lbl:
            joblib.dump(artifact, model_path)
            if exp_label == "default":
                legacy_path = self.models_dir / f"{dataset_id}.joblib"
                try:
                    joblib.dump(artifact, legacy_path)
                except Exception as e:
                    logger.warning(f"Could not write legacy model alias {legacy_path}: {e}")

            self._cache[(dataset_id, exp_label, None)] = artifact
            if split_lbl == "research-split":
                self._cache[(dataset_id, exp_label, "research-split")] = artifact

        logger.info(
            f"Model successfully trained and persisted for dataset '{dataset_id}' "
            f"(experiment='{exp_label}', split='{split_lbl}', mode='{eval_mode}') at {model_path}"
        )

        mode_msg = f"on held-out train partition ({len(fit_user_ids)} entities, split='{split_lbl}')" if split_lbl else f"on {len(fit_user_ids)} entities (in_sample)"

        return AnomalyTrainResponse(
            dataset_id=dataset_id,
            message=(
                f"Isolation Forest model trained successfully {mode_msg} "
                f"with {len(selected_feature_names)} features under experiment '{exp_label}'."
            ),
            status="success",
            model_metadata=metadata,
        )

    train = train_model

    def save_custom_artifact(
        self,
        dataset_id: str,
        experiment_label: str,
        artifact: Dict[str, Any],
        split_label: Optional[str] = None,
    ) -> None:
        """
        Store an externally generated model artifact (e.g., from BaselineService).
        """
        clean_exp = (experiment_label or "default").strip()
        effective_split = split_label or artifact.get("split_label")
        if effective_split:
            clean_split = effective_split.strip()
            split_model_path = self.models_dir / f"{dataset_id}__{clean_exp}__{clean_split}.joblib"
            joblib.dump(artifact, split_model_path)
            self._cache[(dataset_id, clean_exp, clean_split)] = artifact

        model_path = self.models_dir / f"{dataset_id}__{clean_exp}.joblib"
        if not model_path.exists() or effective_split == "research-split" or not effective_split:
            joblib.dump(artifact, model_path)
            self._cache[(dataset_id, clean_exp, None)] = artifact
            if effective_split == "research-split":
                self._cache[(dataset_id, clean_exp, "research-split")] = artifact
        logger.info(
            f"Custom artifact saved for dataset '{dataset_id}' under experiment '{clean_exp}' (split='{effective_split}') at {model_path}"
        )

    def _load_artifact(
        self, dataset_id: str, experiment_label: str = "default", split_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load model artifact for (dataset_id, experiment_label) from cache or disk.
        Supports split_label scoping to avoid cross-split model overwrites.
        Raises ModelNotTrainedException if not found.
        """
        clean_exp = (experiment_label or "default").strip()
        clean_split = split_label.strip() if split_label else None

        if clean_split:
            split_key = (dataset_id, clean_exp, clean_split)
            if split_key in self._cache:
                return self._cache[split_key]
            split_path = self.models_dir / f"{dataset_id}__{clean_exp}__{clean_split}.joblib"
            if split_path.exists():
                try:
                    artifact = joblib.load(split_path)
                    self._cache[split_key] = artifact
                    return artifact
                except Exception as e:
                    logger.warning(f"Failed to load split artifact {split_path}: {e}")

        base_key = (dataset_id, clean_exp, None)
        if base_key in self._cache:
            return self._cache[base_key]

        model_path = self._get_model_path(dataset_id, clean_exp, clean_split)
        if not model_path.exists():
            raise ModelNotTrainedException(
                f"No anomaly detection model has been trained yet for dataset '{dataset_id}' "
                f"under experiment '{clean_exp}'. "
                f"Please train a model first via POST /api/v1/anomalies/{dataset_id}/train."
            )

        try:
            artifact = joblib.load(model_path)
            if artifact.get("dataset_id") != dataset_id:
                raise ModelNotTrainedException(
                    f"Model artifact at {model_path} does not match dataset '{dataset_id}'."
                )
            self._cache[base_key] = artifact
            if clean_split:
                self._cache[(dataset_id, clean_exp, clean_split)] = artifact
            return artifact
        except Exception as e:
            if isinstance(e, ModelNotTrainedException):
                raise
            logger.error(
                f"Failed to load model artifact for dataset '{dataset_id}' ({clean_exp}): {e}"
            )
            raise ModelNotTrainedException(
                f"Could not load anomaly model for dataset '{dataset_id}' ({clean_exp}): {str(e)}"
            )

    def _generate_reasons_for_user(
        self,
        user_feat_dict: Dict[str, float],
        feature_stats: Dict[str, Dict[str, float]],
        trained_features: List[str],
        is_suspicious: bool,
    ) -> List[str]:
        """
        Generate transparent explainability reason codes based on training population percentiles.
        Only generates reasons for feature dimensions included in trained_features.
        """
        if not is_suspicious:
            return []

        reasons: List[str] = []
        trained_set = set(trained_features)

        # Behavioral Reason Heuristics
        if "transaction_count" in trained_set:
            val = user_feat_dict.get("transaction_count", 0.0)
            p90 = feature_stats.get("transaction_count", {}).get("p90", 0.0)
            if val > p90 and val > 1:
                reasons.append("unusually high transaction count")

        if "total_sent" in trained_set:
            val = user_feat_dict.get("total_sent", 0.0)
            p90 = feature_stats.get("total_sent", {}).get("p90", 0.0)
            if val > p90 and val > 0:
                reasons.append("unusually high outgoing volume")

        if "total_received" in trained_set:
            val = user_feat_dict.get("total_received", 0.0)
            p90 = feature_stats.get("total_received", {}).get("p90", 0.0)
            if val > p90 and val > 0:
                reasons.append("unusually high incoming volume")

        if "maximum_transaction_amount" in trained_set:
            val = user_feat_dict.get("maximum_transaction_amount", 0.0)
            p90 = feature_stats.get("maximum_transaction_amount", {}).get("p90", 0.0)
            if val > p90 and val > 0:
                reasons.append("unusually high transaction amount")

        if "unique_receivers" in trained_set:
            val = user_feat_dict.get("unique_receivers", 0.0)
            p90 = feature_stats.get("unique_receivers", {}).get("p90", 0.0)
            if val > p90 and val > 1:
                reasons.append("unusually high receiver diversity")

        if "unique_senders" in trained_set:
            val = user_feat_dict.get("unique_senders", 0.0)
            p90 = feature_stats.get("unique_senders", {}).get("p90", 0.0)
            if val > p90 and val > 1:
                reasons.append("unusually high sender diversity")

        # Temporal Reason Heuristics
        if "minimum_time_between_transactions" in trained_set:
            val = user_feat_dict.get("minimum_time_between_transactions", 0.0)
            p10 = feature_stats.get("minimum_time_between_transactions", {}).get("p10", 0.0)
            if val <= p10 and val >= 0.0:
                reasons.append("unusually short transaction intervals")

        # Graph Structural Reason Heuristics
        if "betweenness_centrality" in trained_set:
            val = user_feat_dict.get("betweenness_centrality", 0.0)
            p90 = feature_stats.get("betweenness_centrality", {}).get("p90", 0.0)
            if val > p90 and val > 0.0:
                reasons.append("unusually high network centrality")

        if "total_degree" in trained_set:
            val = user_feat_dict.get("total_degree", 0.0)
            p90 = feature_stats.get("total_degree", {}).get("p90", 0.0)
            if val > p90 and val > 1:
                reasons.append("unusually high counterparty connections")

        if "weighted_out_degree" in trained_set:
            val = user_feat_dict.get("weighted_out_degree", 0.0)
            p90 = feature_stats.get("weighted_out_degree", {}).get("p90", 0.0)
            if val > p90 and val > 0.0:
                reasons.append("unusually high graph outgoing weight")

        if "weighted_in_degree" in trained_set:
            val = user_feat_dict.get("weighted_in_degree", 0.0)
            p90 = feature_stats.get("weighted_in_degree", {}).get("p90", 0.0)
            if val > p90 and val > 0.0:
                reasons.append("unusually high graph incoming weight")

        return reasons

    def predict_user_anomalies(
        self,
        dataset_id: str,
        experiment_label: str = "default",
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        suspicious_only: bool = False,
        split_label: Optional[str] = None,
        partition: Optional[str] = None,
    ) -> UserAnomalyListResponse:
        """
        Evaluate anomaly status and compute risk scores for users in the specified dataset
        under a given experiment configuration.
        """
        clean_exp = (experiment_label or "default").strip()
        store = dataset_registry.get(dataset_id)
        artifact = self._load_artifact(dataset_id, clean_exp, split_label)

        model_type = artifact.get("model_type", "IsolationForest")
        curr_user_ids, full_matrix, _ = store.get_feature_matrix()

        if len(curr_user_ids) == 0:
            return UserAnomalyListResponse(
                dataset_id=dataset_id,
                experiment_label=clean_exp,
                total_users=0,
                suspicious_count=0,
                normal_count=0,
                limit=limit,
                offset=offset,
                users=[],
            )

        results: List[UserAnomalyResult] = []
        suspicious_count = 0
        normal_count = 0

        # Branch 1: Statistical Baseline Model
        if model_type == "StatisticalBaseline":
            raw_scores = artifact.get("raw_scores", {})
            predictions = artifact.get("predictions", {})
            risk_scores = artifact.get("risk_scores", {})
            reasons_dict = artifact.get("reasons", {})

            for uid in curr_user_ids:
                score = float(raw_scores.get(uid, 0.0))
                pred = int(predictions.get(uid, 1))
                is_suspicious = (pred == -1)
                if is_suspicious:
                    suspicious_count += 1
                    status = "suspicious"
                else:
                    normal_count += 1
                    status = "normal"

                risk = float(risk_scores.get(uid, 0.0))
                reasons = reasons_dict.get(uid, [])

                res = UserAnomalyResult(
                    user_id=uid,
                    raw_score=score,
                    prediction=pred,
                    status=status,
                    risk_score=risk,
                    reasons=reasons,
                )
                results.append(res)

        # Branch 2: Isolation Forest Model
        else:
            model: IsolationForest = artifact["model"]
            meta_dict: Dict[str, Any] = artifact["metadata"]
            train_scores: np.ndarray = artifact["train_scores"]
            col_indices: List[int] = artifact["col_indices"]
            trained_features: List[str] = meta_dict["feature_names"]
            feature_stats: Dict[str, Dict[str, float]] = meta_dict["feature_stats"]

            X_sliced = full_matrix[:, col_indices]
            if np.isnan(X_sliced).any() or np.isinf(X_sliced).any():
                X_sliced = np.nan_to_num(X_sliced, nan=0.0, posinf=0.0, neginf=0.0)

            raw_scores = model.decision_function(X_sliced)
            predictions = model.predict(X_sliced)

            for i, uid in enumerate(curr_user_ids):
                score = float(round(raw_scores[i], 6))
                pred = int(predictions[i])
                is_suspicious = (pred == -1)

                if is_suspicious:
                    suspicious_count += 1
                    status = "suspicious"
                else:
                    normal_count += 1
                    status = "normal"

                risk = compute_risk_score(score, train_scores)

                user_features_obj = store.feature_service.user_features.get(uid)
                user_feat_map = {}
                if user_features_obj:
                    user_feat_map = {
                        feat: getattr(user_features_obj, feat, 0.0)
                        for feat in trained_features
                    }

                reasons = self._generate_reasons_for_user(
                    user_feat_map, feature_stats, trained_features, is_suspicious
                )

                res = UserAnomalyResult(
                    user_id=uid,
                    raw_score=score,
                    prediction=pred,
                    status=status,
                    risk_score=risk,
                    reasons=reasons,
                )
                results.append(res)

        # Filter by split partition if split_label is provided
        if split_label:
            split_obj = split_service.get_split(dataset_id, split_label)
            allowed_uids = (
                set(split_obj.train_user_ids)
                if partition == "train"
                else set(split_obj.test_user_ids)
            )
            results = [r for r in results if r.user_id in allowed_uids]
            suspicious_count = sum(1 for r in results if r.prediction == -1)
            normal_count = len(results) - suspicious_count

        # Filter by single user if requested
        if user_id:
            user_matches = [r for r in results if r.user_id == user_id]
            if not user_matches:
                raise NotFoundException(f"User '{user_id}' not found in dataset '{dataset_id}'.")
            return UserAnomalyListResponse(
                dataset_id=dataset_id,
                experiment_label=clean_exp,
                total_users=1,
                suspicious_count=1 if user_matches[0].prediction == -1 else 0,
                normal_count=0 if user_matches[0].prediction == -1 else 1,
                limit=limit,
                offset=0,
                users=user_matches,
            )

        if suspicious_only:
            results = [r for r in results if r.prediction == -1]

        total_count = len(results)
        paginated_results = results[offset : offset + limit]

        return UserAnomalyListResponse(
            dataset_id=dataset_id,
            experiment_label=clean_exp,
            total_users=total_count,
            suspicious_count=suspicious_count,
            normal_count=normal_count,
            limit=limit,
            offset=offset,
            users=paginated_results,
        )

    def get_anomaly_summary(
        self,
        dataset_id: str,
        experiment_label: str = "default",
        split_label: Optional[str] = None,
    ) -> AnomalySummaryResponse:
        """
        Return aggregate summary of model predictions and metadata for a dataset under an experiment.
        """
        clean_exp = (experiment_label or "default").strip()
        dataset_registry.get(dataset_id)
        artifact = self._load_artifact(dataset_id, clean_exp, split_label)

        meta_dict = artifact["metadata"]
        metadata = ModelMetadata(**meta_dict)

        user_list = self.predict_user_anomalies(
            dataset_id=dataset_id,
            experiment_label=clean_exp,
            limit=100000,
            split_label=split_label,
        )
        total = user_list.total_users
        suspicious = user_list.suspicious_count
        normal = user_list.normal_count
        rate = float(round(suspicious / total, 4)) if total > 0 else 0.0

        return AnomalySummaryResponse(
            dataset_id=dataset_id,
            experiment_label=clean_exp,
            total_entities=total,
            suspicious_count=suspicious,
            normal_count=normal,
            contamination_rate=rate,
            feature_groups=metadata.feature_groups,
            feature_count=metadata.feature_count,
            model_metadata=metadata,
        )

    def get_model_metadata(
        self, dataset_id: str, experiment_label: str = "default", split_label: Optional[str] = None
    ) -> ModelMetadata:
        """
        Retrieve stored model metadata for a given experiment without user prediction records.
        """
        clean_exp = (experiment_label or "default").strip()
        dataset_registry.get(dataset_id)
        artifact = self._load_artifact(dataset_id, clean_exp, split_label)
        return ModelMetadata(**artifact["metadata"])

    def list_experiments(self, dataset_id: str) -> List[ModelMetadata]:
        """
        List all trained experiments for a dataset by inspecting cache and disk artifacts.
        """
        dataset_registry.get(dataset_id)
        experiments: Dict[str, ModelMetadata] = {}

        # 1. From cache
        for cache_key, art in self._cache.items():
            if len(cache_key) == 3:
                ds_id, exp_lbl, sp_lbl = cache_key
            else:
                ds_id, exp_lbl = cache_key
                sp_lbl = None
            if ds_id == dataset_id and "metadata" in art:
                if exp_lbl not in experiments or sp_lbl in (None, "research-split"):
                    experiments[exp_lbl] = ModelMetadata(**art["metadata"])

        # 2. From disk files matching dataset_id__*.joblib
        prefix = f"{dataset_id}__"
        for p in self.models_dir.glob(f"{prefix}*.joblib"):
            stem = p.stem[len(prefix) :]
            if "__" in stem:
                exp_name = stem.split("__")[0]
            else:
                exp_name = stem
            if exp_name not in experiments:
                try:
                    art = joblib.load(p)
                    if "metadata" in art:
                        experiments[exp_name] = ModelMetadata(**art["metadata"])
                except Exception as e:
                    logger.warning(f"Could not load experiment artifact {p}: {e}")

        # 3. Check legacy {dataset_id}.joblib
        legacy = self.models_dir / f"{dataset_id}.joblib"
        if legacy.exists() and "default" not in experiments:
            try:
                art = joblib.load(legacy)
                if "metadata" in art:
                    experiments["default"] = ModelMetadata(**art["metadata"])
            except Exception as e:
                logger.warning(f"Could not load legacy artifact {legacy}: {e}")

        # Return sorted by experiment label (excluding simulation runs)
        return sorted(
            [m for m in experiments.values() if not m.experiment_label.startswith("sim_")],
            key=lambda m: m.experiment_label,
        )

    def clear(self) -> None:
        """Reset cache and delete test model artifacts from disk (used by tests)."""
        self._cache.clear()
        for joblib_file in self.models_dir.glob("*.joblib"):
            try:
                joblib_file.unlink()
            except Exception as e:
                logger.warning(f"Could not remove model artifact {joblib_file}: {e}")
        try:
            split_service.clear()
        except Exception as e:
            logger.warning(f"Could not clear split service: {e}")


anomaly_service = AnomalyService()
