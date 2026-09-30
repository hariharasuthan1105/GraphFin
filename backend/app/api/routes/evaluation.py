from typing import Optional
from fastapi import APIRouter, Query, status

from ...core.logging import get_logger
from ...schemas.evaluation import (
    EvaluationComparisonResponse,
    ExperimentEvaluationMetrics,
    ResearchExportResponse,
)
from ...schemas.transfer import (
    TransferExperimentRequest,
    TransferExperimentResponse,
)
from ...services.evaluation_service import evaluation_service
from ...services.transfer_service import transfer_service

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluation", tags=["Research Evaluation & Comparison"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Evaluation Service Info",
    description="Returns research evaluation service status and primary metrics.",
)
@router.get(
    "/",
    include_in_schema=False,
)
async def get_evaluation_info():
    """Return evaluation service info."""
    return {
        "status": "active",
        "service": "evaluation",
        "primary_metric": "PR-AUC",
        "evaluation_modes": ["in_sample", "held_out"],
    }


@router.post(
    "/transfer",
    response_model=TransferExperimentResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Cross-Dataset Transfer Experiment",
    description=(
        "Executes source-only model fitting and transfers models/scalers to a target dataset. "
        "Strictly verifies feature schema equality before fitting. "
        "Computes PR-AUC with 95% Bootstrap Confidence Intervals (N=1000), Precision@K (P@10, P@25, P@50, P@100), "
        "transfer degradation metrics, and feature distribution shift diagnostics."
    ),
)
async def evaluate_cross_dataset_transfer(
    payload: TransferExperimentRequest,
) -> TransferExperimentResponse:
    """Evaluate cross-dataset generalization transfer between source and target datasets."""
    return transfer_service.evaluate_transfer(payload)


@router.get(
    "/transfer/artifacts",
    status_code=status.HTTP_200_OK,
    summary="Get Stored Cross-Dataset Transfer Evaluation Artifacts",
    description="Returns pre-computed transfer evaluation JSON artifacts for IBM -> PaySim and PaySim -> IBM.",
)
async def get_transfer_artifacts():
    """Retrieve pre-computed cross-dataset transfer result artifacts."""
    import json
    from ...core.config import settings

    out_dir = settings.DATA_DIR / "results" / "cross_dataset"
    a_path = out_dir / "ibm_to_paysim_transfer.json"
    b_path = out_dir / "paysim_to_ibm_transfer.json"

    res_a = json.loads(a_path.read_text()) if a_path.exists() else None
    res_b = json.loads(b_path.read_text()) if b_path.exists() else None

    return {
        "status": "success",
        "ibm_to_paysim": res_a,
        "paysim_to_ibm": res_b,
    }


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
