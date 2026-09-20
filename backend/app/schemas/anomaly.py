"""
Anomaly detection schemas for Isolation Forest modeling, statistical baseline, predictions, and metadata.
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator

VALID_FEATURE_GROUPS = {"graph", "behavioral", "temporal"}


class AnomalyTrainRequest(BaseModel):
    """Configuration payload for training an Isolation Forest model on a dataset."""

    experiment_label: Optional[str] = Field(
        default="default",
        description="Experiment identifier (e.g. 'default', 'e1', 'e2', 'baseline_statistical').",
    )
    feature_groups: Optional[List[str]] = Field(
        default=["graph", "behavioral", "temporal"],
        description="Feature group subsets to include in training ('graph', 'behavioral', 'temporal').",
    )
    n_estimators: Optional[int] = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of base isolation trees in the ensemble.",
    )
    contamination: Optional[float] = Field(
        default=0.1,
        gt=0.0,
        le=0.5,
        description="Expected proportion of outliers in the data set.",
    )
    max_samples: Optional[Union[int, float, str]] = Field(
        default="auto",
        description="Number of samples to draw from features to train each tree ('auto', int, or float (0, 1]).",
    )
    random_state: Optional[int] = Field(
        default=42,
        description="Deterministic random seed for reproducible tree splits.",
    )
    split_label: Optional[str] = Field(
        default=None,
        description="Optional dataset split label for held-out training partition. If omitted, trains on full population (in_sample).",
    )

    @field_validator("experiment_label")
    @classmethod
    def validate_experiment_label(cls, v: Optional[str]) -> str:
        if not v or str(v).strip() == "":
            return "default"
        return str(v).strip()

    @field_validator("split_label")
    @classmethod
    def validate_split_label(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = str(v).strip()
        return clean if clean else None

    @field_validator("feature_groups")
    @classmethod
    def validate_feature_groups(cls, v: Optional[List[str]]) -> List[str]:
        if not v:
            raise ValueError("feature_groups cannot be empty. Allowed values: 'graph', 'behavioral', 'temporal'.")
        seen = set()
        normalized = []
        for g in v:
            g_clean = g.strip().lower()
            if g_clean not in VALID_FEATURE_GROUPS:
                raise ValueError(
                    f"Invalid feature group '{g}'. Allowed groups are: {sorted(list(VALID_FEATURE_GROUPS))}."
                )
            if g_clean not in seen:
                seen.add(g_clean)
                normalized.append(g_clean)
        return normalized

    @field_validator("max_samples")
    @classmethod
    def validate_max_samples(cls, v: Union[int, float, str]) -> Union[int, float, str]:
        if isinstance(v, str):
            if v.strip().lower() != "auto":
                raise ValueError("String value for max_samples must be 'auto'.")
            return "auto"
        elif isinstance(v, int):
            if v <= 0:
                raise ValueError("Integer max_samples must be greater than 0.")
            return v
        elif isinstance(v, float):
            if v <= 0.0 or v > 1.0:
                raise ValueError("Float max_samples must be in (0.0, 1.0].")
            return v
        raise ValueError("max_samples must be 'auto', an integer > 0, or a float in (0.0, 1.0].")


class BaselineTrainRequest(BaseModel):
    """Configuration payload for training a non-ML rule-based statistical baseline."""

    experiment_label: Optional[str] = Field(
        default="baseline_statistical",
        description="Experiment identifier for statistical baseline.",
    )
    z_threshold: Optional[float] = Field(
        default=2.0,
        gt=0.0,
        description="Z-score threshold for classifying an entity as anomalous (default: 2.0, representing ~2.28% upper tail).",
    )
    features: Optional[List[str]] = Field(
        default=["weighted_out_degree", "betweenness_centrality", "total_degree"],
        description="List of graph feature names to evaluate using population z-scores (default: weighted_out_degree, betweenness_centrality, total_degree).",
    )
    feature_groups: Optional[List[str]] = Field(
        default=None,
        description="Optional list of feature groups ('graph', 'behavioral', 'temporal'). If provided, resolves and overrides features with group features.",
    )
    split_label: Optional[str] = Field(
        default=None,
        description="Optional dataset split label for held-out baseline fitting.",
    )


class ModelMetadata(BaseModel):
    """Complete metadata and hyperparameter specification for a trained model/experiment."""

    model_type: str = Field(default="IsolationForest", description="Model algorithm ('IsolationForest' or 'StatisticalBaseline')")
    method: str = Field(default="Isolation Forest", description="Human-readable method title (e.g. 'Isolation Forest' or 'Statistical (z-score, no ML)')")
    sklearn_version: str = Field(..., description="scikit-learn runtime library version (or 'N/A' for baseline)")
    dataset_id: str = Field(..., description="UUID of the training dataset")
    experiment_label: str = Field(default="default", description="Experiment identifier")
    split_label: Optional[str] = Field(None, description="Optional split label if trained on a held-out partition")
    evaluation_mode: str = Field(default="in_sample", description="Evaluation mode ('in_sample' or 'held_out')")
    feature_groups: List[str] = Field(..., description="Feature groups selected for this model")
    feature_names: List[str] = Field(..., description="Ordered list of feature column names")
    feature_count: int = Field(..., description="Number of feature dimensions")
    n_estimators: Optional[int] = Field(None, description="Number of isolation trees (if ML)")
    contamination: Optional[float] = Field(None, description="Configured outlier contamination rate")
    max_samples: Optional[Union[int, float, str]] = Field(None, description="Subsample ratio or count per tree")
    random_state: Optional[int] = Field(None, description="Random seed used for deterministic fitting")
    z_threshold: Optional[float] = Field(None, description="Z-score threshold (if statistical baseline)")
    z_score_threshold: Optional[float] = Field(None, description="Z-score threshold alias")
    baseline_feature_names: Optional[List[str]] = Field(None, description="Features used by statistical baseline")
    entity_count: int = Field(..., description="Number of unique user entities used in training")
    training_entity_count: Optional[int] = Field(None, description="Count of training entities")
    training_timestamp: str = Field(..., description="ISO 8601 timestamp of model training completion")
    model_artifact_path: Optional[str] = Field(None, description="Relative file path where model artifact is stored")
    feature_stats: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Per-feature distributions (p10, p50, p90, min, max, mean, std) for explanations and baseline scoring",
    )


class AnomalyTrainResponse(BaseModel):
    """Response returned upon successful model training."""

    dataset_id: str
    message: str
    status: str = "success"
    model_metadata: ModelMetadata


class UserAnomalyResult(BaseModel):
    """Per-user anomaly detection scoring, classification, and explanation."""

    user_id: str = Field(..., description="Unique entity/user identifier")
    raw_score: float = Field(
        ...,
        description="Raw continuous model score (decision_function score for Isolation Forest, or max z-score for baseline).",
    )
    prediction: int = Field(
        ...,
        description="Classification decision (-1 for anomaly/outlier, 1 for normal/inlier).",
    )
    status: str = Field(
        ...,
        description="Categorical entity classification: 'suspicious' or 'normal'.",
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Relative presentation risk score (0-100) derived from model output. "
            "NOTE: The 0–100 score is a relative presentation/ranking score derived from model output. "
            "It is NOT a calibrated probability of fraud. It must not be interpreted as a percentage "
            "probability that an account is fraudulent. 100 = most anomalous, 0 = most normal."
        ),
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Supporting explainability reason codes derived from training population percentiles.",
    )


class UserAnomalyListResponse(BaseModel):
    """Paginated collection of per-user anomaly detection results."""

    dataset_id: str = Field(..., description="Dataset identifier")
    experiment_label: str = Field(default="default", description="Experiment identifier")
    total_users: int = Field(..., description="Total users evaluated")
    suspicious_count: int = Field(..., description="Total users flagged as suspicious (prediction == -1)")
    normal_count: int = Field(..., description="Total users classified as normal (prediction == 1)")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Page offset")
    users: List[UserAnomalyResult] = Field(..., description="List of user anomaly scores and classifications")


class AnomalySummaryResponse(BaseModel):
    """High-level summary of anomaly distribution and model configuration."""

    dataset_id: str = Field(..., description="Dataset identifier")
    experiment_label: str = Field(default="default", description="Experiment identifier")
    total_entities: int = Field(..., description="Total number of evaluated entities")
    suspicious_count: int = Field(..., description="Count of entities flagged as suspicious")
    normal_count: int = Field(..., description="Count of entities classified as normal")
    contamination_rate: float = Field(..., description="Proportion of entities classified as suspicious")
    feature_groups: List[str] = Field(..., description="Feature groups used during training")
    feature_count: int = Field(..., description="Number of features used during training")
    model_metadata: ModelMetadata = Field(..., description="Complete stored model metadata")


class ExperimentListResponse(BaseModel):
    """List of all trained experiments currently stored for a dataset."""

    dataset_id: str = Field(..., description="Dataset identifier")
    total_experiments: int = Field(..., description="Total count of trained experiments stored for this dataset")
    experiments: List[ModelMetadata] = Field(..., description="List of stored model metadata objects")
