from typing import Optional
from fastapi import APIRouter, Query, status

from ...core.logging import get_logger
from ...schemas.evaluation import (
    EvaluationComparisonResponse,
    ExperimentEvaluationMetrics,
    ResearchExportResponse,
)
from ...services.evaluation_service import evaluation_service

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluation", tags=["Research Evaluation & Comparison"])


@router.get(
    "/{dataset_id}/compare",
    response_model=EvaluationComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare All Trained Experiments",
    description=(
        "Evaluates all trained experiments for the given dataset against stored ground-truth labels. "
        "Returns a comparison table ranked by PR-AUC (Average Precision) descending. "
        "Captures failed experiments explicitly with status='error' rather than silently omitting them. "
        "Clearly groups and distinguishes results by evaluation_mode (in-sample vs held-out). "
        "Highlights PR-AUC as the headline metric due to extreme positive-class imbalance in financial anomaly detection."
    ),
)
async def compare_dataset_experiments(
    dataset_id: str,
    include_curves: bool = Query(
        default=False,
        description="Whether to include full ROC and Precision-Recall curve point arrays for figure plotting",
    ),
    split_label: Optional[str] = Query(
        default=None,
        description="Optional dataset split label to evaluate experiments in held-out mode against test partition",
    ),
) -> EvaluationComparisonResponse:
    """Compare all trained model variants for a dataset against ground-truth labels."""
    return evaluation_service.compare_experiments(
        dataset_id=dataset_id, include_curves=include_curves, split_label=split_label
    )


@router.post(
    "/{dataset_id}/export",
    response_model=ResearchExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export Research Run Results",
    description=(
        "Exports comprehensive evaluation comparison results, experiment manifests, "
        "and metric tables into persistent JSON and CSV artifacts under data/results/."
    ),
)
async def export_research_run_results(dataset_id: str) -> ResearchExportResponse:
    """Export current multi-experiment evaluation metrics to JSON and CSV files."""
    return evaluation_service.export_research_run(dataset_id=dataset_id)


@router.get(
    "/{dataset_id}/{experiment_label}",
    response_model=ExperimentEvaluationMetrics,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Single Experiment",
    description=(
        "Computes detailed classification (confusion matrix, precision, recall, F1, accuracy) "
        "and ranking (ROC-AUC, PR-AUC) metrics for a single trained experiment against ground-truth labels. "
        "If the experiment was trained with a split or split_label is provided, evaluates against the held-out test partition."
    ),
)
async def evaluate_single_experiment(
    dataset_id: str,
    experiment_label: str,
    include_curves: bool = Query(
        default=False,
        description="Whether to include full ROC and Precision-Recall curve point arrays for figure plotting",
    ),
    split_label: Optional[str] = Query(
        default=None,
        description="Optional split label to override or specify held-out test partition evaluation",
    ),
) -> ExperimentEvaluationMetrics:
    """Evaluate one trained experiment against ground-truth labels."""
    return evaluation_service.evaluate_experiment(
        dataset_id=dataset_id,
        experiment_label=experiment_label,
        include_curves=include_curves,
        split_label=split_label,
    )
