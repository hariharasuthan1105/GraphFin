from typing import List, Optional
from fastapi import APIRouter, Body, File, Query, UploadFile, status

from ...core.logging import get_logger
from ...schemas.labels import DatasetLabelsSummaryResponse
from ...schemas.split import SplitCreateRequest, SplitSummaryResponse
from ...services.label_registry import label_registry
from ...services.split_service import split_service

logger = get_logger(__name__)

router = APIRouter(prefix="/datasets", tags=["Datasets, Splits & Ground-Truth Labels"])


@router.post(
    "/{dataset_id}/labels",
    response_model=DatasetLabelsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload Ground-Truth Labels CSV",
    description=(
        "Uploads a CSV file containing user/account-level ground-truth labels. "
        "Normalizes labels to boolean (accepts 1/0, true/false, fraud/normal, suspicious/normal). "
        "Validates that labeled user IDs exist in the dataset's feature matrix without corrupting or leaking "
        "into the feature engineering pipeline. Returns summary counts and prevalence rate."
    ),
)
async def upload_dataset_labels(
    dataset_id: str,
    file: UploadFile = File(..., description="CSV file containing user IDs and ground-truth labels"),
    user_id_col: str = Query(
        "user_id",
        description="Name of the CSV column containing user/account identifiers",
    ),
    label_col: str = Query(
        "label",
        description="Name of the CSV column containing ground-truth anomaly labels",
    ),
    strict: bool = Query(
        False,
        description="If true, aborts upload if any user_id does not exist in dataset",
    ),
) -> DatasetLabelsSummaryResponse:
    """Ingest ground-truth labels for offline research evaluation."""
    logger.info(
        f"Uploading ground-truth labels for dataset '{dataset_id}' "
        f"(user_id_col='{user_id_col}', label_col='{label_col}', strict={strict})"
    )
    content = await file.read()
    return label_registry.store_labels_from_csv(
        dataset_id=dataset_id,
        csv_content=content,
        user_id_col=user_id_col,
        label_col=label_col,
        strict=strict,
    )


@router.get(
    "/{dataset_id}/labels/summary",
    response_model=DatasetLabelsSummaryResponse,
    summary="Get Stored Label Summary",
    description="Returns aggregate counts and prevalence rate of ground-truth labels stored for this dataset.",
)
async def get_dataset_labels_summary(dataset_id: str) -> DatasetLabelsSummaryResponse:
    """Retrieve stored ground-truth label summary without re-uploading."""
    return label_registry.get_summary(dataset_id)


@router.post(
    "/{dataset_id}/splits",
    response_model=SplitSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Entity-Level Train/Test Split",
    description=(
        "Creates and stores a deterministic entity-level train/test partition for a dataset. "
        "Requires ground-truth labels to be uploaded first. Stratifies by label if possible, "
        "Restricts model fitting and percentile explainability strictly to training entity rows."
    ),
)
async def create_dataset_split(
    dataset_id: str,
    payload: Optional[SplitCreateRequest] = Body(
        default_factory=SplitCreateRequest,
        description="Split configuration parameters (split_label, test_size, random_state, stratify_by_label)",
    ),
) -> SplitSummaryResponse:
    """Create and persist an entity-level train/test split."""
    req = payload or SplitCreateRequest()
    assignment = split_service.create_split(
        dataset_id=dataset_id,
        test_size=req.test_size or 0.3,
        random_state=req.random_state if req.random_state is not None else 42,
        stratify_by_label=req.stratify_by_label if req.stratify_by_label is not None else True,
        split_label=req.split_label or "default",
    )
    return SplitSummaryResponse(**assignment.model_dump(exclude={"train_user_ids", "test_user_ids"}))


@router.get(
    "/{dataset_id}/splits/{split_label}",
    response_model=SplitSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Split Assignment Summary",
    description="Returns stored split configuration, counts, and prevalence rates without raw user ID lists.",
)
async def get_dataset_split(
    dataset_id: str,
    split_label: str,
) -> SplitSummaryResponse:
    """Retrieve stored split summary by label."""
    return split_service.get_split_summary(dataset_id=dataset_id, split_label=split_label)


@router.get(
    "/{dataset_id}/splits",
    response_model=List[SplitSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List All Dataset Splits",
    description="Lists all train/test split partitions configured for this dataset.",
)
async def list_dataset_splits(
    dataset_id: str,
) -> List[SplitSummaryResponse]:
    """List all entity splits stored for a dataset."""
    return split_service.list_splits(dataset_id=dataset_id)
