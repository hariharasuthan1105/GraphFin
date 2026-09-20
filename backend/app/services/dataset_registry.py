"""
Dataset Registry Service.
Manages dataset-scoped runtime StateStore instances.
"""
from typing import Dict
import uuid
import pandas as pd
from ..core.exceptions import NotFoundException
from ..core.logging import get_logger
from .state_store import StateStore

logger = get_logger(__name__)

# Supported ISO 4217 currency codes accepted at upload time.
# All amounts are stored as-is (no conversion); currency is a display-label only.
SUPPORTED_CURRENCIES = {"USD", "INR", "EUR", "GBP"}
DEFAULT_CURRENCY = "USD"


class DatasetRegistry:
    """Registry managing multiple dataset-scoped StateStore instances."""

    def __init__(self):
        self._datasets: Dict[str, StateStore] = {}
        self._currencies: Dict[str, str] = {}  # dataset_id -> ISO 4217 code

    def create_dataset(self, df: pd.DataFrame, currency: str = DEFAULT_CURRENCY) -> str:
        """
        Create a new StateStore instance, load the dataframe into it,
        store it under a new UUID4 dataset_id, and return the dataset_id.
        Currency must be a supported ISO 4217 code; defaults to USD.
        """
        currency = currency.upper().strip()
        if currency not in SUPPORTED_CURRENCIES:
            logger.warning(
                f"Unsupported currency code '{currency}'; falling back to USD."
            )
            currency = DEFAULT_CURRENCY

        dataset_id = str(uuid.uuid4())
        store = StateStore()
        store.load_transactions(df)
        self._datasets[dataset_id] = store
        self._currencies[dataset_id] = currency

        try:
            from ..core.config import settings
            csv_path = settings.DATA_PROCESSED_DIR / f"{dataset_id}.csv"
            df.to_csv(csv_path, index=False)
        except Exception as e:
            logger.debug(f"Could not save dataset CSV to disk: {e}")

        logger.info(
            f"Created dataset '{dataset_id}' with {len(df)} transactions "
            f"in registry (currency={currency})."
        )
        return dataset_id

    def get(self, dataset_id: str) -> StateStore:
        """
        Return the StateStore for the specified dataset_id,
        or raise NotFoundException (404) if the id does not exist.
        """
        store = self._datasets.get(dataset_id)
        if store is None:
            try:
                from ..core.config import settings
                csv_path = settings.DATA_PROCESSED_DIR / f"{dataset_id}.csv"
                if csv_path.exists():
                    df = pd.read_csv(csv_path)
                    store = StateStore()
                    store.load_transactions(df)
                    self._datasets[dataset_id] = store
                    # Currency not persisted to disk in this iteration —
                    # datasets reloaded from CSV fall back to USD (the IBM AML default).
                    if dataset_id not in self._currencies:
                        self._currencies[dataset_id] = DEFAULT_CURRENCY
                    return store
            except Exception as e:
                logger.debug(f"Could not load dataset CSV from disk: {e}")

        if store is None:
            raise NotFoundException(f"Dataset '{dataset_id}' not found.")
        return store

    def get_currency(self, dataset_id: str) -> str:
        """
        Return the ISO 4217 currency code stored for this dataset.
        Defaults to USD for any dataset not found in the currency map
        (e.g. datasets created before this feature, or reloaded from disk).
        """
        return self._currencies.get(dataset_id, DEFAULT_CURRENCY)

    def get_transaction_count(self, dataset_id: str) -> int:
        """Return the number of transactions loaded in the dataset store."""
        try:
            store = self.get(dataset_id)
            return len(store.transactions_df)
        except Exception:
            return 0

    def clear(self) -> None:
        """Reset the whole registry (used by tests)."""
        self._datasets.clear()
        self._currencies.clear()
        logger.info("Dataset registry cleared.")


dataset_registry = DatasetRegistry()
