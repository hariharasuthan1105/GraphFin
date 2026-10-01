from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Body, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ...core.logging import get_logger
from ...schemas.labels import DatasetLabelsSummaryResponse
from ...schemas.split import SplitCreateRequest, SplitSummaryResponse
from ...services.label_registry import label_registry
from ...services.split_service import split_service
from ...services.dataset_registry import dataset_registry

logger = get_logger(__name__)

router = APIRouter(prefix="/datasets", tags=["Datasets, Splits & Ground-Truth Labels"])

# PaySim background loading state
_paysim_status: dict = {"state": "idle", "error": None}  # idle | loading | loaded | error


# ---------------------------------------------------------------------------
# Locked research dataset discovery
# ---------------------------------------------------------------------------

# These UUIDs were assigned when the IBM AML research benchmark datasets were
# first registered. They are frozen and hardcoded here as the single source of
# truth so the frontend can query which locked datasets are actually available
# in the current backend instance, rather than assuming they are always present.
_LOCKED_DATASET_IDS = {
    "ddbaab44-78b6-41be-a8fb-e83dfec66358": {
        "label": "Research — 5,000 accounts (IBM AML HI-Small subsample)",
        "tier": "medium_real",
        "transactions": 31463,
        "users": 5000,
        "currency": "USD",
        "is_paper_reportable": False,
        "run_quality_tier": "pipeline_validation",
    },
    "03fb9ab0-4f42-4404-9d76-723fd4d8753e": {
        "label": "Research — 49,992 accounts (IBM AML HI-Small subsample)",
        "tier": "large_real",
        "transactions": 353850,
        "users": 49992,
        "currency": "USD",
        "is_paper_reportable": True,
        "run_quality_tier": "paper_reportable",
    },
}


class LockedDatasetInfo(BaseModel):
    dataset_id: str
    tier: str
    label: str
    transactions: int
    users: int
    currency: str
    is_paper_reportable: bool = False
    run_quality_tier: str = "pipeline_validation"


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List Registered, Locked, and Secondary Research Datasets",
    description="Returns metadata for all registered datasets in the active registry.",
)
@router.get(
    "/",
    include_in_schema=False,
)
async def list_all_datasets():
    """List registered datasets, locked benchmark datasets, and secondary research datasets."""
    registered = [
        {
            "dataset_id": ds_id,
            "transaction_count": len(store.transactions_df),
            "currency": dataset_registry.get_currency(ds_id),
        }
        for ds_id, store in dataset_registry._datasets.items()
    ]

    is_paysim_loaded = dataset_registry.is_loaded("paysim")
    paysim_tx = 0
    paysim_users = 0
    if is_paysim_loaded:
        try:
            store = dataset_registry.get("paysim")
            paysim_tx = len(store.transactions_df)
            paysim_users = len(store.feature_service.user_features)
        except Exception:
            pass

    secondary_datasets = [
        {
            "id": "paysim",
            "name": "PaySim",
            "display_name": "Research — PaySim",
            "source_type": "raw_transaction",
            "entity_level": "account",
            "paper_reportable": False,
            "is_locked": False,
            "is_loaded": is_paysim_loaded,
            "transactions": paysim_tx,
            "users": paysim_users,
            "currency": "USD",
            "status": "loaded" if is_paysim_loaded else "not_processed",
        }
    ]

    return {
        "status": "success",
        "datasets": registered,
        "secondary_datasets": secondary_datasets,
    }


@router.post(
    "/paysim/load",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Load PaySim Research Dataset (async)",
    description=(
        "Triggers background loading of the PaySim dataset. Returns 202 immediately. "
        "Poll GET /datasets/paysim/status to check progress. "
        "Returns 200 with full metadata if already loaded."
    ),
)
async def load_paysim_dataset(background_tasks: BackgroundTasks):
    """Trigger PaySim loading asynchronously to avoid Render gateway timeout."""
    global _paysim_status

    # If already loaded, return synchronously with 200
    if dataset_registry.is_loaded("paysim"):
        store = dataset_registry.get("paysim")
        return JSONResponse(status_code=200, content={
            "status": "success",
            "dataset_id": "paysim",
            "name": "PaySim",
            "display_name": "Research \u2014 PaySim",
            "transactions": len(store.transactions_df),
            "users": len(store.feature_service.user_features),
            "currency": "USD",
        })

    # If already loading, don't double-trigger
    if _paysim_status["state"] == "loading":
        return JSONResponse(status_code=202, content={
            "status": "loading",
            "message": "PaySim dataset is currently being processed. Poll /datasets/paysim/status.",
        })

    def _do_load():
        global _paysim_status
        _paysim_status = {"state": "loading", "error": None}
        try:
            logger.info("Background: starting PaySim dataset load...")
            dataset_registry.load_paysim()
            _paysim_status = {"state": "loaded", "error": None}
            logger.info("Background: PaySim dataset loaded successfully.")
        except Exception as e:
            _paysim_status = {"state": "error", "error": str(e)}
            logger.error(f"Background: PaySim load failed: {e}")

    _paysim_status = {"state": "loading", "error": None}
    background_tasks.add_task(_do_load)
    logger.info("PaySim load triggered as background task.")
    return JSONResponse(status_code=202, content={
        "status": "loading",
        "dataset_id": "paysim",
        "message": "PaySim dataset loading started in background. Poll /datasets/paysim/status for progress.",
    })


@router.get(
    "/paysim/status",
    status_code=status.HTTP_200_OK,
    summary="PaySim Loading Status",
    description="Returns the current loading state of the PaySim dataset.",
)
async def paysim_load_status():
    """Return current PaySim loading state."""
    is_loaded = dataset_registry.is_loaded("paysim")
    if is_loaded:
        store = dataset_registry.get("paysim")
        return {
            "state": "loaded",
            "is_loaded": True,
            "transactions": len(store.transactions_df),
            "users": len(store.feature_service.user_features),
        }
    return {
        "state": _paysim_status["state"],
        "is_loaded": False,
        "error": _paysim_status.get("error"),
    }


@router.get(
    "/locked",
    response_model=List[LockedDatasetInfo],
    status_code=status.HTTP_200_OK,
    summary="List Available Locked Research Datasets",
    description=(
        "Returns the subset of locked IBM AML research benchmark datasets that are "
        "currently registered in the backend's dataset registry. "
        "Returns an empty list on fresh checkouts where the fixture CSVs have not been "
        "loaded — the frontend should display an honest empty state in this case. "
        "Locked datasets are pre-registered when the research evaluation script "
        "(backend/scripts/run_final_research_evaluation.py) has been run."
    ),
)
async def list_locked_datasets() -> List[LockedDatasetInfo]:
    """Return locked benchmark datasets that are currently available in the registry."""
    available = []
    for ds_id, meta in _LOCKED_DATASET_IDS.items():
        try:
            dataset_registry.get(ds_id)  # raises NotFoundException if not registered
            available.append(LockedDatasetInfo(dataset_id=ds_id, **meta))
        except Exception:
            pass
    return available




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
