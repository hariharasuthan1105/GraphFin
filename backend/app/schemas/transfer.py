"""
Pydantic schemas for Cross-Dataset Transfer & Generalization Experiments.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .evaluation import ConfusionMatrix


class BootstrapCI(BaseModel):
    """95% Bootstrap Confidence Interval bounds."""
    point_estimate: float = Field(..., description="Point estimate (e.g. PR-AUC)")
    ci_lower: float = Field(..., description="2.5th percentile lower confidence bound")
    ci_upper: float = Field(..., description="97.5th percentile upper confidence bound")


class PrecisionAtK(BaseModel):
    """Precision@K metrics evaluated on target population."""
    p_at_10: float = Field(..., description="Precision among top 10 highest ranked anomaly scores")
    p_at_25: float = Field(..., description="Precision among top 25 highest ranked anomaly scores")
    p_at_50: float = Field(..., description="Precision among top 50 highest ranked anomaly scores")
    p_at_100: float = Field(..., description="Precision among top 100 highest ranked anomaly scores")


class DegradationMetrics(BaseModel):
    """Performance degradation from source domain to target domain."""
    source_pr_auc: float = Field(..., description="Same-protocol source domain PR-AUC")
    target_pr_auc: float = Field(..., description="Target domain PR-AUC under transfer")
    absolute_degradation: float = Field(..., description="Source PR-AUC - Target PR-AUC")
    relative_degradation: Optional[float] = Field(
        None, description="(Source PR-AUC - Target PR-AUC) / Source PR-AUC (None if Source == 0)"
    )


class FeatureDistributionSummary(BaseModel):
    """Diagnostic comparison of feature distributions across source and target datasets."""
    feature_name: str = Field(..., description="Feature column name")
    source_mean: float = Field(..., description="Mean value in source dataset")
    target_mean: float = Field(..., description="Mean value in target dataset")
    source_std: float = Field(..., description="Standard deviation in source dataset")
    target_std: float = Field(..., description="Standard deviation in target dataset")
    standardized_mean_difference: float = Field(
        ..., description="Standardized mean difference = (target_mean - source_mean) / pooled_std"
    )


class ExperimentTransferResult(BaseModel):
    """Transfer metrics for one experiment configuration (E0-E5)."""
    experiment_label: str = Field(..., description="Experiment configuration (e.g. 'E0', 'E1', 'E4', 'E5')")
    status: str = Field(default="success", description="Status: 'success', 'error', or 'unsupported'")
    error: Optional[str] = Field(None, description="Detailed explanation if status is 'error' or 'unsupported'")
    method: str = Field(..., description="Model method description")
    feature_groups: List[str] = Field(..., description="Feature groups included")
    feature_count: int = Field(..., description="Total feature dimensions used")

    source_pr_auc: Optional[float] = Field(None, description="Same-protocol source PR-AUC")
    source_pr_auc_ci: Optional[BootstrapCI] = Field(None, description="Source PR-AUC 95% Bootstrap CI")

    target_pr_auc: Optional[float] = Field(None, description="Target PR-AUC under transfer")
    target_pr_auc_ci: Optional[BootstrapCI] = Field(None, description="Target PR-AUC 95% Bootstrap CI")
    target_roc_auc: Optional[float] = Field(None, description="Target ROC-AUC")
    target_precision: Optional[float] = Field(None, description="Target Precision")
    target_recall: Optional[float] = Field(None, description="Target Recall")
    target_f1: Optional[float] = Field(None, description="Target F1 Score")
    target_accuracy: Optional[float] = Field(None, description="Target Accuracy")

    confusion_matrix: Optional[ConfusionMatrix] = Field(None, description="Target confusion matrix")
    precision_at_k: Optional[PrecisionAtK] = Field(None, description="Target Precision@K metrics")
    degradation: Optional[DegradationMetrics] = Field(None, description="Transfer degradation stats")


class TransferExperimentRequest(BaseModel):
    """Request payload for running a cross-dataset transfer experiment."""
    source_dataset_id: str = Field(..., description="UUID of source dataset used for fitting models/scalers")
    target_dataset_id: str = Field(..., description="UUID of target dataset evaluated under transfer")
    experiments: List[str] = Field(
        default=["E0", "E1", "E2", "E3", "E4", "E5"],
        description="List of experiment labels to evaluate",
    )
    source_split_label: Optional[str] = Field("research-split", description="Source dataset split partition")
    target_split_label: Optional[str] = Field("research-split", description="Target dataset split partition")
    random_state: int = Field(42, description="Random seed for bootstrap resampling")
    n_bootstraps: int = Field(1000, description="Number of bootstrap iterations for confidence intervals")


class TransferExperimentResponse(BaseModel):
    """Consolidated cross-dataset transfer evaluation response."""
    source_dataset_id: str = Field(..., description="Source dataset ID")
    target_dataset_id: str = Field(..., description="Target dataset ID")
    direction: str = Field(..., description="Transfer direction label (e.g. 'IBM->PaySim')")
    is_paper_reportable: bool = Field(..., description="Flag indicating if run meets paper-reportable standards")
    run_quality_tier: str = Field(..., description="'paper_reportable' vs 'pipeline_validation'")
    betweenness_centrality_method: Dict[str, str] = Field(..., description="Centrality calculation method per dataset")
    paysim_account_label_rule: str = Field(..., description="Account label aggregation rule used for PaySim")
    timestamp: str = Field(..., description="ISO 8601 UTC execution timestamp")
    experiments: List[ExperimentTransferResult] = Field(..., description="Per-experiment transfer results")
    feature_distribution_check: List[FeatureDistributionSummary] = Field(..., description="Diagnostic feature stats")
    reproducibility_manifest: Dict[str, Any] = Field(..., description="Complete manifest of seeds and parameters")
