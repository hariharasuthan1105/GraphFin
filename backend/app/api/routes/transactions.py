"""
Transaction ingestion, status, and summary endpoints.
"""
from fastapi import APIRouter, File, Query, UploadFile, status
from ...core.config import settings
from ...core.exceptions import ValidationException
from ...core.logging import get_logger
from ...schemas.transaction import (
    DatasetStatusResponse,
    TransactionSummaryResponse,
    TransactionUploadResponse,
)
from ...services.preprocessing import PreprocessingService
from ...services.dataset_registry import dataset_registry, SUPPORTED_CURRENCIES, DEFAULT_CURRENCY

logger = get_logger(__name__)
router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "/upload",
    response_model=TransactionUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload Transactions CSV",
    description=(
        "Uploads a CSV file containing transaction data. Validates canonical columns "
        "(transaction_id, sender_id, receiver_id, amount, timestamp), rejects "
        "invalid records without silent corruption, creates a dataset-scoped state, "
        "constructs the transaction graph, and extracts behavioral/temporal features. "
        "An optional `currency` query parameter (ISO 4217 code, e.g. USD, INR, EUR, GBP) "
        "labels the dataset's amounts for display purposes — no conversion is performed. "
        "Defaults to USD if omitted (full backward compatibility)."
    ),
)
async def upload_transactions(
    file: UploadFile = File(..., description="CSV file containing transactions"),
    strict_mode: bool = Query(
        False,
        description="If True, any single invalid row aborts the entire dataset upload.",
    ),
    currency: str = Query(
        DEFAULT_CURRENCY,
        description=(
            f"ISO 4217 currency code for all amounts in this dataset. "
            f"Supported: {', '.join(sorted(SUPPORTED_CURRENCIES))}. "
            "Defaults to USD. This is a display label only — no conversion is applied."
        ),
    ),
) -> TransactionUploadResponse:
    """Accept, validate, preprocess, and load transaction CSV data into a new dataset."""
    if not file.filename.lower().endswith((".csv", ".txt")):
        raise ValidationException("Only CSV files (.csv) are accepted for transaction upload.")

    logger.info(f"Received file upload: {file.filename} (currency={currency})")
    content = await file.read()

    preprocessor = PreprocessingService(strict_mode=strict_mode)
    clean_df, errors, warnings = preprocessor.process_csv(content)

    # Save to processed data directory for reproducibility
    try:
        dest_path = settings.DATA_PROCESSED_DIR / "latest_transactions.csv"
        clean_df.to_csv(dest_path, index=False)
        logger.info(f"Persisted validated transactions to: {dest_path}")
    except Exception as e:
        logger.warning(f"Could not persist processed CSV to disk: {e}")

    # Create dataset-scoped runtime state; store currency alongside it
    dataset_id = dataset_registry.create_dataset(clean_df, currency=currency)
    store = dataset_registry.get(dataset_id)
    summary = store.get_transaction_summary()
    resolved_currency = dataset_registry.get_currency(dataset_id)

    # Inject currency into the nested summary so both top-level and summary.currency are consistent
    summary_dict = summary.model_dump()
    summary_dict["currency"] = resolved_currency
    summary_with_currency = summary.__class__(**summary_dict)

    return TransactionUploadResponse(
        message="Transactions processed and graph updated successfully.",
        dataset_id=dataset_id,
        status="complete",
        total_rows_parsed=len(clean_df) + len(errors),
        valid_transactions=len(clean_df),
        invalid_rows_count=len(errors),
        validation_errors=errors[:20],
        duplicate_warnings=warnings,
        summary=summary_with_currency,
        currency=resolved_currency,
    )


@router.get(
    "/{dataset_id}/status",
    response_model=DatasetStatusResponse,
    summary="Dataset Processing Status",
    description="Check processing status of a dataset by its unique dataset ID.",
)
async def get_dataset_status(dataset_id: str) -> DatasetStatusResponse:
    """Retrieve status of dataset processing."""
    dataset_registry.get(dataset_id)  # raises 404 if not found
    currency = dataset_registry.get_currency(dataset_id)
    return DatasetStatusResponse(dataset_id=dataset_id, status="complete", currency=currency)


@router.get(
    "/{dataset_id}/summary",
    response_model=TransactionSummaryResponse,
    summary="Transaction Statistics Summary",
    description="Returns aggregate statistical metrics for the specified dataset.",
)
async def get_transaction_summary(dataset_id: str) -> TransactionSummaryResponse:
    """Retrieve summary of transactions for a specific dataset."""
    store = dataset_registry.get(dataset_id)
    summary = store.get_transaction_summary()
    currency = dataset_registry.get_currency(dataset_id)
    # Merge currency into the summary dict to avoid duplicate-kwarg error
    summary_dict = summary.model_dump()
    summary_dict["currency"] = currency
    return TransactionSummaryResponse(**summary_dict)
