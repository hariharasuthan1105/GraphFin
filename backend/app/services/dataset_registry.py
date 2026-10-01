"""
Dataset Registry Service.
Manages dataset-scoped runtime StateStore instances.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import uuid
import pandas as pd
from ..core.exceptions import NotFoundException
from ..core.logging import get_logger
from .state_store import StateStore

logger = get_logger(__name__)

# Supported ISO 4217 currency codes accepted at upload time.
SUPPORTED_CURRENCIES = {"USD", "INR", "EUR", "GBP"}
DEFAULT_CURRENCY = "USD"

# PaySim Dataset Metadata
PAYSIM_DATASET_ID = "paysim"
PAYSIM_UUID_ALIAS = "e8d9c7b6-a5f4-4e3d-b2c1-a09876543210"

PAYSIM_METADATA: Dict[str, Any] = {
    "id": "paysim",
    "name": "PaySim",
    "display_name": "Research — PaySim",
    "source_type": "raw_transaction",
    "entity_level": "account",
    "paper_reportable": False,
    "betweenness_strategy": {
        "method": "approximate",
        "k": 100,
        "random_state": 42,
    },
}


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

    def load_paysim(self) -> StateStore:
        """
        Load the PaySim research dataset into memory from disk.
        Registers both 'paysim' and its legacy UUID alias.
        """
        if PAYSIM_DATASET_ID in self._datasets:
            return self._datasets[PAYSIM_DATASET_ID]

        from ..core.config import settings
        tx_path = settings.DATA_DIR / "research" / "paysim_transactions.csv"
        lbl_path = settings.DATA_DIR / "research" / "paysim_account_labels.csv"
        if not lbl_path.exists():
            lbl_path = settings.DATA_DIR / "research" / "paysim_labels.csv"

        if not tx_path.exists():
            # Try raw file conversion as fallback
            raw_path = settings.DATA_RAW_DIR / "PS_20174392719_1491204439457_log.csv"
            if raw_path.exists():
                from .paysim_adapter import load_paysim_raw
                logger.info(f"Converting raw PaySim dataset from {raw_path}...")
                df = load_paysim_raw(raw_path)
            else:
                raise NotFoundException(f"PaySim dataset transaction file not found at {tx_path}")
        else:
            logger.info(f"Loading PaySim transactions from {tx_path} (subsample for memory safety)...")
            df = pd.read_csv(tx_path, nrows=10000)


        store = StateStore()
        store.load_transactions(df)

        self._datasets[PAYSIM_DATASET_ID] = store
        self._datasets[PAYSIM_UUID_ALIAS] = store
        self._currencies[PAYSIM_DATASET_ID] = "USD"
        self._currencies[PAYSIM_UUID_ALIAS] = "USD"

        # Load ground-truth labels if available
        if lbl_path.exists():
            try:
                from .label_registry import label_registry
                lbl_bytes = lbl_path.read_bytes()
                label_registry.store_labels_from_csv(PAYSIM_DATASET_ID, lbl_bytes)
                label_registry.store_labels_from_csv(PAYSIM_UUID_ALIAS, lbl_bytes)
                logger.info(f"Loaded PaySim ground-truth labels from {lbl_path}")
            except Exception as e:
                logger.warning(f"Could not load PaySim ground-truth labels: {e}")

        logger.info(
            f"PaySim dataset successfully registered (ID='{PAYSIM_DATASET_ID}') "
            f"with {len(df)} transactions and {len(store.feature_service.user_features)} accounts."
        )
        return store

    def get(self, dataset_id: str) -> StateStore:
        """
        Return the StateStore for the specified dataset_id,
        or raise NotFoundException (404) if the id does not exist.
        """
        # Alias resolution for PaySim
        if dataset_id in (PAYSIM_DATASET_ID, PAYSIM_UUID_ALIAS):
            return self.load_paysim()

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
                    if dataset_id not in self._currencies:
                        self._currencies[dataset_id] = DEFAULT_CURRENCY
                    return store
            except Exception as e:
                logger.debug(f"Could not load dataset CSV from disk: {e}")

        if store is None:
            raise NotFoundException(f"Dataset '{dataset_id}' not found.")
        return store

    def is_loaded(self, dataset_id: str) -> bool:
        """Check if dataset is loaded into memory without triggering auto-load."""
        if dataset_id == PAYSIM_UUID_ALIAS:
            dataset_id = PAYSIM_DATASET_ID
        return dataset_id in self._datasets

    def get_currency(self, dataset_id: str) -> str:
        """
        Return the ISO 4217 currency code stored for this dataset.
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

