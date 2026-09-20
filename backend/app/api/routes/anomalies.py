"""
Anomaly Detection REST API Endpoints.
Provides endpoints for training Isolation Forest models and statistical baselines,
retrieving per-user anomaly scores, inspecting model metadata, and listing trained experiments.
"""
from typing import Optional
from fastapi import APIRouter, Body, Query, status

from ...core.logging import get_logger
from ...schemas.anomaly import (
    AnomalySummaryResponse,
    AnomalyTrainRequest,
    AnomalyTrainResponse,
    BaselineTrainRequest,
    ExperimentListResponse,
    ModelMetadata,
    UserAnomalyListResponse,
)
from ...services.anomaly_service import anomaly_service
from ...services.baseline_service import baseline_service

logger = get_logger(__name__)

router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection (Machine Learning)"])


@router.post(
    "/{dataset_id}/train",
    response_model=AnomalyTrainResponse,
    status_code=status.HTTP_200_OK,
    summary="Train Isolation Forest Model",
    description=(
        "Trains an unsupervised Isolation Forest model on the user-level feature matrix "
        "associated with the given dataset_id. Supports specifying an experiment_label, "
        "hyperparameter overrides (n_estimators, contamination, max_samples, random_state), "
        "and feature groups ('graph', 'behavioral', 'temporal')."
    ),
)
async def train_anomaly_model(
    dataset_id: str,
    payload: Optional[AnomalyTrainRequest] = Body(
        default_factory=AnomalyTrainRequest,
        description="Optional hyperparameter, feature group, and experiment label overrides.",
    ),
    experiment_label: Optional[str] = Query(
        None, description="Optional experiment label (defaults to payload.experiment_label or 'default')"
    ),
    split_label: Optional[str] = Query(
        None, description="Optional split label for held-out training partition (overrides payload.split_label)"
    ),
) -> AnomalyTrainResponse:
    """Train or retrain an anomaly model for the specified dataset under an experiment label."""
    request_data = payload or AnomalyTrainRequest()
    exp_label = (experiment_label or request_data.experiment_label or "default").strip()
    if split_label:
        request_data.split_label = split_label.strip()

    logger.info(
        f"Training anomaly model request received for dataset '{dataset_id}' (exp='{exp_label}', split='{request_data.split_label}')."
    )

    if exp_label == "baseline_statistical":
        return baseline_service.train_baseline(
            dataset_id=dataset_id,
            request=BaselineTrainRequest(experiment_label=exp_label, split_label=request_data.split_label),
        )

    return anomaly_service.train_model(
        dataset_id=dataset_id,
        request=request_data,
        experiment_label=exp_label,
    )


@router.post(
    "/{dataset_id}/baseline",
    response_model=AnomalyTrainResponse,
    status_code=status.HTTP_200_OK,
    summary="Train Statistical Baseline (Non-ML)",
    description=(
        "Fits a non-ML rule-based z-score threshold statistical baseline. Flags users exceeding "
        "mean + z_threshold * std_dev across structural and behavioral features. "
        "Saved under experiment_label (default 'baseline_statistical') for uniform evaluation."
    ),
)
async def train_statistical_baseline(
    dataset_id: str,
    payload: Optional[BaselineTrainRequest] = Body(
        default_factory=BaselineTrainRequest,
        description="Configuration for z-score threshold rule.",
    ),
) -> AnomalyTrainResponse:
    """Compute and persist rule-based statistical baseline."""
    request_data = payload or BaselineTrainRequest()
    return baseline_service.train_baseline(dataset_id=dataset_id, request=request_data)


@router.get(
    "/{dataset_id}/experiments",
    response_model=ExperimentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List All Trained Experiments for Dataset",
    description="Lists all experiment_labels currently trained for a dataset, along with feature groups and hyperparameters.",
)
async def list_dataset_experiments(dataset_id: str) -> ExperimentListResponse:
    """List all trained model variants and baselines for the dataset."""
    exps = anomaly_service.list_experiments(dataset_id)
    return ExperimentListResponse(
        dataset_id=dataset_id,
        total_experiments=len(exps),
        experiments=exps,
    )


@router.get(
    "/{dataset_id}/users",
    response_model=UserAnomalyListResponse,
    summary="Get User Anomaly Scores and Classifications",
    description=(
        "Returns per-user anomaly detection results for a given experiment_label including raw continuous scores, "
        "relative 0-100 presentation risk scores (inverted percentile rank), suspicious/normal status, "
        "and explainability reason codes based on training population deviations."
    ),
)
async def get_user_anomalies(
    dataset_id: str,
    experiment_label: str = Query(
        "default", description="Experiment identifier (e.g. 'default', 'e1', 'baseline_statistical')"
    ),
    user_id: Optional[str] = Query(
        None, description="Optional user ID filter for single entity inspection"
    ),
    limit: int = Query(50, ge=1, le=500, description="Page size limit"),
    offset: int = Query(0, ge=0, description="Page offset index"),
    suspicious_only: bool = Query(
        False, description="If true, returns only entities flagged as suspicious"
    ),
    split_label: Optional[str] = Query(
        None, description="Optional split label to evaluate held-out test partition users"
    ),
) -> UserAnomalyListResponse:
    """Retrieve anomaly predictions for entities in the specified dataset under an experiment."""
    return anomaly_service.predict_user_anomalies(
        dataset_id=dataset_id,
        experiment_label=experiment_label,
        user_id=user_id,
        limit=limit,
        offset=offset,
        suspicious_only=suspicious_only,
        split_label=split_label,
    )


@router.get(
    "/{dataset_id}/summary",
    response_model=AnomalySummaryResponse,
    summary="Get Dataset Anomaly Summary",
    description=(
        "Returns aggregate anomaly statistics (total entities, suspicious count, normal count, "
        "contamination rate, feature groups) along with the active model's metadata for the specified experiment."
    ),
)
async def get_anomaly_summary(
    dataset_id: str,
    experiment_label: str = Query(
        "default", description="Experiment identifier (e.g. 'default', 'e1', 'baseline_statistical')"
    ),
    split_label: Optional[str] = Query(
        None, description="Optional split label to compute summary over test partition"
    ),
) -> AnomalySummaryResponse:
    """Retrieve aggregate anomaly detection statistics for the specified dataset and experiment."""
    return anomaly_service.get_anomaly_summary(
        dataset_id=dataset_id, experiment_label=experiment_label, split_label=split_label
    )


@router.get(
    "/{dataset_id}/model",
    response_model=ModelMetadata,
    summary="Get Trained Model Metadata",
    description=(
        "Returns the full stored model metadata (algorithm, sklearn version, hyperparameters, "
        "exact feature names and groups used, entity count, training timestamp) for the specified experiment."
    ),
)
async def get_model_metadata(
    dataset_id: str,
    experiment_label: str = Query(
        "default", description="Experiment identifier (e.g. 'default', 'e1', 'baseline_statistical')"
    ),
    split_label: Optional[str] = Query(
        None, description="Optional split label to retrieve split-scoped model metadata"
    ),
) -> ModelMetadata:
    """Retrieve stored model metadata for experiment confirmation and auditability."""
    return anomaly_service.get_model_metadata(
        dataset_id=dataset_id, experiment_label=experiment_label, split_label=split_label
    )
