"""
Pydantic schemas for model research evaluation, experiment comparison metrics,
ranking curves, and publication research exports.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .labels import DatasetLabelsSummaryResponse


class ConfusionMatrix(BaseModel):
    """Confusion matrix counts for binary classification."""

    tp: int = Field(..., description="True Positives (actual positive flagged as suspicious)")
    fp: int = Field(..., description="False Positives (actual normal flagged as suspicious)")
    tn: int = Field(..., description="True Negatives (actual normal correctly classified normal)")
    fn: int = Field(..., description="False Negatives (actual positive missed by model)")


class ROCCurveData(BaseModel):
    """Coordinates for Receiver Operating Characteristic (ROC) curve plotting."""

    fpr: List[float] = Field(..., description="False Positive Rates at decision thresholds")
    tpr: List[float] = Field(..., description="True Positive Rates at decision thresholds")
    thresholds: List[float] = Field(..., description="Score decision thresholds (continuous)")


class PrecisionRecallCurveData(BaseModel):
    """Coordinates for Precision-Recall (PR) curve plotting."""

    precision: List[float] = Field(..., description="Precision values across operating points")
    recall: List[float] = Field(..., description="Recall values across operating points")
    thresholds: List[float] = Field(..., description="Decision thresholds corresponding to precision/recall")


class ThresholdAnalysis(BaseModel):
    """Analysis of model binary decision boundary vs continuous ranking scores."""

    binary_decision_rule: str = Field(..., description="Description of binary cutoff (contamination or z-score)")
    continuous_score_name: str = Field(..., description="Name of continuous score evaluated ('risk_score' or 'baseline_score')")
    score_direction: str = Field(default="higher_is_more_anomalous", description="Continuous score ranking direction")
    auc_evaluation_basis: str = Field(
        default="Continuous ranking scores across all thresholds, independent of binary decision cutoff",
        description="Explanation of AUC metric independence from binary cutoff",
    )
    risk_score_is_probability: bool = Field(
        default=False,
        description="Explicit flag confirming risk score is NOT a calibrated probability",
    )
    risk_score_interpretation: str = Field(
        default="Relative presentation ranking score (0-100) scaled from population percentiles. Not a fraud probability.",
        description="Guidance on score interpretation",
    )


class ExperimentEvaluationMetrics(BaseModel):
    """Full quantitative performance evaluation metrics and manifest for one trained experiment."""

    dataset_id: str = Field(..., description="UUID of the evaluated dataset")
    experiment_label: str = Field(..., description="Experiment identifier (e.g. 'baseline', 'e1', 'e2')")
    status: str = Field(default="success", description="Evaluation status: 'success' or 'error'")
    error: Optional[str] = Field(None, description="Detailed explanation if evaluation status is 'error'")

    # Reproducibility & Model Manifest
    model_type: Optional[str] = Field(None, description="Model architecture ('IsolationForest' or 'StatisticalBaseline')")
    method: Optional[str] = Field(None, description="Human-readable method title (e.g. 'Isolation Forest' or 'Statistical (z-score, no ML)')")
    feature_groups: List[str] = Field(default_factory=list, description="Feature groups used in this experiment")
    feature_names: List[str] = Field(default_factory=list, description="Ordered list of feature column names")
    feature_count: int = Field(default=0, description="Total feature dimensions used")
    n_estimators: Optional[int] = Field(None, description="Number of isolation trees (if ML)")
    contamination: Optional[float] = Field(None, description="Configured outlier contamination rate")
    max_samples: Optional[Any] = Field(None, description="Subsample ratio or count per tree")
    random_state: Optional[int] = Field(None, description="Random seed used for deterministic fitting")
    training_entity_count: Optional[int] = Field(None, description="Number of unique entities used in training")
    training_timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp of model training completion")
    model_artifact_path: Optional[str] = Field(None, description="Relative file path where model artifact is stored")

    # Evaluation Protocol Metadata
    evaluation_mode: str = Field(
        default="in_sample",
        description="Protocol mode: 'in_sample' (pipeline validation) or 'held_out' (split test set)",
    )
    split_label: Optional[str] = Field(
        default=None,
        description="Dataset split label if evaluated in held-out mode (e.g. 'default', 'test_split')",
    )
    evaluation_mode_note: str = Field(
        default="In-sample evaluation represents pipeline validation. For publication, evaluations must be performed on a held-out test split or time-based partition.",
        description="Notice on in-sample vs held-out evaluation validity",
    )
    labeled_user_count: int = Field(default=0, description="Total ground-truth labeled entities stored for this dataset")
    usable_labeled_user_count: int = Field(default=0, description="Count of labeled entities overlapping with dataset feature matrix")
    usable_labels_count: int = Field(default=0, description="Backward-compatible alias for usable_labeled_user_count")
    total_dataset_users: int = Field(default=0, description="Total unique entities present in the dataset")
    positive_count: int = Field(default=0, description="Number of positive (anomalous) entities among usable labels")
    negative_count: int = Field(default=0, description="Number of negative (normal) entities among usable labels")
    positive_prevalence: float = Field(default=0.0, description="Proportion of positive entities (positives / usable labels)")

    # Score Direction & Threshold Analysis
    score_name: str = Field(default="risk_score", description="Name of continuous score evaluated")
    score_direction: str = Field(default="higher_is_more_anomalous", description="Continuous score direction: higher = more anomalous")
    threshold_analysis: Optional[ThresholdAnalysis] = Field(None, description="Threshold and continuous ranking analysis")

    # Classification & Ranking Metrics (Optional in case of error)
    confusion_matrix: Optional[ConfusionMatrix] = Field(None, description="Binary confusion matrix (TP, FP, TN, FN)")
    precision: Optional[float] = Field(None, description="Precision = TP / (TP + FP)")
    recall: Optional[float] = Field(None, description="Recall = TP / (TP + FN)")
    f1_score: Optional[float] = Field(None, description="Harmonic mean of precision and recall")
    accuracy: Optional[float] = Field(None, description="Overall accuracy = (TP + TN) / Total")
    roc_auc: Optional[float] = Field(
        None,
        description="Receiver Operating Characteristic Area Under Curve (computed using continuous scores)",
    )
    pr_auc: Optional[float] = Field(
        None,
        description="Precision-Recall Area Under Curve / Average Precision score (headline metric for class imbalance)",
    )
    headline_metric: str = Field(
        default="pr_auc",
        description="Designated primary comparison metric for financial anomaly detection under class imbalance",
    )

    # Edge Cases & Curves
    metric_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings regarding single-class labels, small sample sizes, or undefined metrics",
    )
    roc_curve: Optional[ROCCurveData] = Field(None, description="ROC curve points (FPR, TPR, thresholds) for figure plotting")
    precision_recall_curve: Optional[PrecisionRecallCurveData] = Field(None, description="PR curve points (Precision, Recall, thresholds) for figure plotting")
    class_imbalance_note: str = Field(
        default=(
            "In financial anomaly detection, the positive (anomalous) class is rare (<5%). "
            "Under severe class imbalance, accuracy can be misleadingly high (e.g. 99% accuracy by predicting all normal). "
            "PR-AUC (Average Precision) and F1 score are the primary headline metrics for evaluating detection efficacy."
        ),
        description="Methodological note regarding class imbalance and metric selection",
    )


class EvaluationComparisonResponse(BaseModel):
    """Multi-experiment performance comparison table sorted by PR-AUC descending."""

    dataset_id: str = Field(..., description="UUID of the evaluated dataset")
    total_experiments_evaluated: int = Field(..., description="Total count of experiments attempted in this run")
    successful_experiments_count: int = Field(default=0, description="Count of successfully evaluated experiments")
    failed_experiments_count: int = Field(default=0, description="Count of experiments that encountered an evaluation error")
    labels_summary: DatasetLabelsSummaryResponse = Field(..., description="Summary of ground-truth labels used")
    evaluation_mode: str = Field(
        default="in_sample",
        description="Protocol mode: 'in_sample' (pipeline validation), 'held_out' (split test set), or 'mixed'",
    )
    split_label: Optional[str] = Field(
        default=None,
        description="Optional split label if evaluation was restricted to a specific split",
    )
    evaluation_mode_note: str = Field(
        default="In-sample evaluation represents pipeline validation. For publication, evaluations must be performed on a held-out test split or time-based partition.",
        description="Notice on in-sample vs held-out evaluation validity",
    )
    by_evaluation_mode: Optional[Dict[str, List[ExperimentEvaluationMetrics]]] = Field(
        default=None,
        description="Experiments explicitly partitioned by evaluation_mode ('in_sample' vs 'held_out') to prevent conflation",
    )
    headline_metric: str = Field(default="pr_auc", description="Primary ranking metric")
    class_imbalance_note: str = Field(
        default=(
            "In financial anomaly detection, the positive (anomalous) class is rare (<5%). "
            "Under severe class imbalance, accuracy can be misleadingly high. "
            "PR-AUC (Average Precision) is the primary headline metric for ranking configurations."
        )
    )
    experiments: List[ExperimentEvaluationMetrics] = Field(
        ...,
        description="List of experiment evaluation metrics sorted by PR-AUC descending (successful first, followed by errors)",
    )


class ResearchExportResponse(BaseModel):
    """Response confirming research run export to JSON and CSV artifacts."""

    dataset_id: str = Field(..., description="UUID of the exported dataset")
    export_timestamp: str = Field(..., description="UTC timestamp of the export")
    json_path: str = Field(..., description="File path of exported JSON results")
    csv_path: str = Field(..., description="File path of exported CSV results table")
    total_experiments: int = Field(..., description="Count of experiments included in the export")
    successful_experiments: int = Field(..., description="Count of successfully evaluated experiments")
    failed_experiments: int = Field(..., description="Count of failed experiments")
    evaluation_mode: str = Field(..., description="Evaluation mode (e.g. 'in_sample')")
