"""
IBM AMLSim Dataset Adapter for GraphFin.
Provides memory-safe ingestion, normalization, and label resolution for the
IBM AMLSim bank_mixed transaction network benchmark without altering raw data,
inventing labels, using precomputed features, or altering GraphFin's 19-feature methodology.
"""
from datetime import datetime
import gzip
import io
import os
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd

from ..core.config import settings
from ..core.exceptions import ValidationException
from ..core.logging import get_logger

logger = get_logger(__name__)

# Canonical dtypes for memory-safe ingestion
TRANSACTION_DTYPES = {
    "tran_id": "str",
    "orig_acct": "str",
    "bene_acct": "str",
    "tx_type": "str",
    "base_amt": "float64",
    "is_sar": "bool",
    "alert_id": "str",
}

ACCOUNT_DTYPES = {
    "acct_id": "str",
    "dsply_nm": "str",
    "type": "str",
    "acct_stat": "str",
    "acct_rptng_crncy": "str",
    "prior_sar_count": "bool",
    "branch_id": "str",
    "initial_deposit": "float64",
    "bank_id": "str",
}

ALERT_ACCOUNT_DTYPES = {
    "alert_id": "str",
    "alert_type": "str",
    "acct_id": "str",
    "acct_name": "str",
    "is_sar": "bool",
    "bank_id": "str",
}


class AMLSimAdapter:
    """
    Adapter service for IBM AMLSim datasets.

    Handles:
    1. Memory-safe reading of compressed transaction files (transactions.csv.gz).
    2. Column normalization into GraphFin's canonical schema.
    3. Account universe retrieval from accounts.csv.gz.
    4. Account-level ground-truth label extraction from alert_accounts.csv.gz
       (or sar_accounts.csv.gz if available).
    5. Dataset schema and integrity auditing.
    """

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the adapter with a path to the AMLSim bank_mixed data directory.
        If None, automatically resolves against project settings.
        """
        self.data_dir = self._resolve_data_dir(data_dir)
        logger.info(f"AMLSimAdapter initialized with data directory: {self.data_dir}")

    @staticmethod
    def _resolve_data_dir(data_dir: Optional[Union[str, Path]] = None) -> Path:
        """Resolve the active AMLSim bank_mixed data directory."""
        if data_dir is not None:
            p = Path(data_dir).resolve()
            if p.exists():
                return p
            raise FileNotFoundError(f"Specified AMLSim data directory does not exist: {p}")

        # Candidate standard paths in priority order
        candidates = [
            settings.DATA_RAW_DIR / "amlsim_bank_mixed" / "banks" / "v2.1" / "data" / "bank_mixed",
            settings.DATA_RAW_DIR / "aml_dataset" / "amlsim_bank_mixed" / "banks" / "v2.1" / "data" / "bank_mixed",
            settings.DATA_RAW_DIR / "amlsim_bank_mixed",
        ]

        for cand in candidates:
            if cand.exists():
                return cand.resolve()

        # Fallback to default expected path even if pending download
        return (settings.DATA_RAW_DIR / "amlsim_bank_mixed" / "banks" / "v2.1" / "data" / "bank_mixed").resolve()

    def _find_file(self, primary_name: str, alt_names: Optional[List[str]] = None) -> Path:
        """Locate a file (.csv.gz or .csv) within the data directory."""
        candidates = [primary_name] + (alt_names or [])
        for name in candidates:
            p = self.data_dir / name
            if p.exists() and p.is_file():
                return p

        # Check subdirectories if nested
        for name in candidates:
            for match in self.data_dir.rglob(name):
                # Ensure we avoid configuration paramFiles
                if "paramfiles" not in str(match).lower() and match.is_file():
                    return match

        raise FileNotFoundError(
            f"Could not locate '{primary_name}' in {self.data_dir}. "
            f"Searched candidates: {candidates}"
        )

    def get_file_paths(self) -> Dict[str, Optional[Path]]:
        """Return resolved paths to all AMLSim files."""
        paths: Dict[str, Optional[Path]] = {}
        for key, primary, alts in [
            ("transactions", "transactions.csv.gz", ["transactions.csv"]),
            ("accounts", "accounts.csv.gz", ["accounts.csv"]),
            ("alert_accounts", "alert_accounts.csv.gz", ["alert_accounts.csv"]),
            ("alert_transactions", "alert_transactions.csv.gz", ["alert_transactions.csv"]),
        ]:
            try:
                paths[key] = self._find_file(primary, alts)
            except FileNotFoundError:
                paths[key] = None

        # Check for dedicated sar_accounts file if present in the release
        try:
            paths["sar_accounts"] = self._find_file("sar_accounts.csv.gz", ["sar_accounts.csv"])
        except FileNotFoundError:
            paths["sar_accounts"] = None

        return paths

    def load_transactions(
        self,
        sample_size: Optional[int] = None,
        chunksize: Optional[int] = None,
    ) -> Union[pd.DataFrame, Generator[pd.DataFrame, None, None]]:
        """
        Load and normalize transactions from transactions.csv.gz into GraphFin schema.

        Column mapping:
          transaction_id      <- tran_id
          source_user_id      <- orig_acct
          destination_user_id <- bene_acct
          sender_id           <- orig_acct (GraphFin canonical pipeline compatibility)
          receiver_id         <- bene_acct (GraphFin canonical pipeline compatibility)
          amount              <- base_amt
          timestamp           <- tran_timestamp

        Preserved metadata (not fed to model feature extraction):
          tx_type
          bank_id (if available)
          is_sar (transaction-level label, excluded from features)
          alert_id

        :param sample_size: If specified, limit the number of ingested rows.
        :param chunksize: If specified, yield normalized DataFrames in chunks.
        :return: Normalized DataFrame or Generator of DataFrames.
        """
        tx_path = self._find_file("transactions.csv.gz", ["transactions.csv"])
        compression = "gzip" if str(tx_path).endswith(".gz") else None

        usecols = ["tran_id", "orig_acct", "bene_acct", "tx_type", "base_amt", "tran_timestamp", "is_sar", "alert_id"]

        def _normalize_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
            # Map canonical fields
            chunk["transaction_id"] = chunk["tran_id"].astype(str).str.strip()
            chunk["source_user_id"] = chunk["orig_acct"].astype(str).str.strip()
            chunk["destination_user_id"] = chunk["bene_acct"].astype(str).str.strip()
            # Canonical GraphFin aliases for downstream GraphService / Preprocessing compatibility
            chunk["sender_id"] = chunk["source_user_id"]
            chunk["receiver_id"] = chunk["destination_user_id"]

            chunk["amount"] = pd.to_numeric(chunk["base_amt"], errors="coerce")
            chunk["timestamp"] = pd.to_datetime(chunk["tran_timestamp"], utc=True)

            # Metadata retention
            chunk["transaction_type"] = chunk["tx_type"].astype(str).str.strip()
            # is_sar is preserved as metadata only, NEVER used in feature extraction
            chunk["is_sar"] = chunk["is_sar"].astype(bool)
            chunk["alert_id"] = chunk["alert_id"].astype(str).str.strip()

            cols_to_keep = [
                "transaction_id",
                "source_user_id",
                "destination_user_id",
                "sender_id",
                "receiver_id",
                "amount",
                "timestamp",
                "transaction_type",
                "tx_type",
                "is_sar",
                "alert_id",
            ]
            return chunk[cols_to_keep]

        if chunksize:
            def _chunk_generator() -> Generator[pd.DataFrame, None, None]:
                rows_read = 0
                for chunk in pd.read_csv(
                    tx_path,
                    compression=compression,
                    usecols=usecols,
                    dtype=TRANSACTION_DTYPES,
                    chunksize=chunksize,
                ):
                    if sample_size and rows_read + len(chunk) > sample_size:
                        chunk = chunk.iloc[: sample_size - rows_read]
                    norm_chunk = _normalize_chunk(chunk)
                    rows_read += len(norm_chunk)
                    yield norm_chunk
                    if sample_size and rows_read >= sample_size:
                        break

            return _chunk_generator()

        df = pd.read_csv(
            tx_path,
            compression=compression,
            usecols=usecols,
            dtype=TRANSACTION_DTYPES,
            nrows=sample_size,
        )
        return _normalize_chunk(df)

    def load_accounts(self) -> pd.DataFrame:
        """
        Load account data from accounts.csv.gz.
        Primary account identifier is acct_id.
        Excludes configuration accounts.csv under paramFiles.
        """
        acct_path = self._find_file("accounts.csv.gz", ["accounts.csv"])
        compression = "gzip" if str(acct_path).endswith(".gz") else None

        cols = [
            "acct_id",
            "dsply_nm",
            "type",
            "acct_stat",
            "acct_rptng_crncy",
            "prior_sar_count",
            "branch_id",
            "initial_deposit",
            "bank_id",
        ]

        df = pd.read_csv(
            acct_path,
            compression=compression,
            usecols=cols,
            dtype=ACCOUNT_DTYPES,
        )
        df["acct_id"] = df["acct_id"].astype(str).str.strip()
        df["prior_sar_count"] = df["prior_sar_count"].astype(bool)
        return df

    def load_account_labels(self, mode: str = "closed_world") -> pd.DataFrame:
        """
        Extract account-level ground-truth labels for evaluation.

        Label Sources:
        1. If dedicated sar_accounts.csv exists, use it as positive SAR accounts.
        2. Otherwise, use alert_accounts.csv.gz:
           - acct_id as account key
           - is_sar == True identifies SAR-labeled positive accounts
           - duplicate acct_id entries across alerts are deterministically aggregated
             via logical OR (is_sar.any()).

        Negative Label Semantics:
        - mode="closed_world" (Default):
          Accounts in accounts.csv.gz with prior_sar_count=False (non-SAR background
          accounts explicitly generated as normal traffic in AMLSim) are labeled 0.
          Produces a complete binary ground truth dataframe: user_id, label (0 or 1).
        - mode="positives_only" / mode="pu":
          Only confirmed SAR accounts are assigned label 1; all other accounts are omitted
          or marked unlabeled (None).

        :param mode: "closed_world" or "positives_only".
        :return: DataFrame with ['user_id', 'label'].
        """
        file_paths = self.get_file_paths()

        # Determine positive accounts
        positive_acct_ids: Set[str] = set()

        if file_paths.get("sar_accounts") is not None:
            # Dedicated SAR accounts file available
            sar_p = file_paths["sar_accounts"]
            comp = "gzip" if str(sar_p).endswith(".gz") else None
            sar_df = pd.read_csv(sar_p, compression=comp, dtype=str)
            # Find the main account ID column
            id_col = "MAIN_ACCOUNT_ID" if "MAIN_ACCOUNT_ID" in sar_df.columns else "acct_id"
            positive_acct_ids = set(sar_df[id_col].dropna().astype(str).str.strip())
            logger.info(f"Loaded {len(positive_acct_ids)} positive accounts from dedicated SAR file: {sar_p.name}")
        else:
            # Use alert_accounts.csv.gz
            alert_p = self._find_file("alert_accounts.csv.gz", ["alert_accounts.csv"])
            comp = "gzip" if str(alert_p).endswith(".gz") else None
            alert_df = pd.read_csv(
                alert_p,
                compression=comp,
                usecols=["alert_id", "acct_id", "is_sar"],
                dtype={"alert_id": "str", "acct_id": "str", "is_sar": "bool"},
            )
            alert_df["acct_id"] = alert_df["acct_id"].astype(str).str.strip()
            # Deterministic aggregation across multiple alerts: is_sar == True if any alert is true
            acct_sar_agg = alert_df.groupby("acct_id")["is_sar"].any()
            positive_acct_ids = set(acct_sar_agg[acct_sar_agg].index)
            logger.info(
                f"Loaded {len(positive_acct_ids)} positive SAR accounts from alert accounts file: {alert_p.name}"
            )

        if mode in ("positives_only", "pu"):
            records = [{"user_id": uid, "label": 1} for uid in sorted(positive_acct_ids)]
            return pd.DataFrame(records)

        if mode == "closed_world":
            # Load full account universe to establish legitimate negative labels
            accounts_df = self.load_accounts()
            all_accounts = set(accounts_df["acct_id"])

            # Cross-verify with prior_sar_count in accounts.csv
            acct_prior_sar = set(accounts_df[accounts_df["prior_sar_count"] == True]["acct_id"])
            if acct_prior_sar and acct_prior_sar != positive_acct_ids:
                logger.warning(
                    f"Discrepancy detected: alert_accounts positives ({len(positive_acct_ids)}) "
                    f"vs accounts.csv prior_sar_count=True ({len(acct_prior_sar)}). "
                    "Unifying confirmed SAR positives."
                )
                positive_acct_ids.update(acct_prior_sar)

            records = []
            for uid in sorted(all_accounts):
                lbl = 1 if uid in positive_acct_ids else 0
                records.append({"user_id": uid, "label": lbl})

            labels_df = pd.DataFrame(records)
            logger.info(
                f"Generated closed-world ground-truth: {len(labels_df)} accounts "
                f"({(labels_df['label'] == 1).sum()} positives, "
                f"{(labels_df['label'] == 0).sum()} negatives)."
            )
            return labels_df

        raise ValueError(f"Unknown label mode: '{mode}'. Expected 'closed_world' or 'positives_only'.")

    def export_labels_csv_bytes(self, mode: str = "closed_world") -> bytes:
        """Export normalized ground-truth labels as UTF-8 CSV bytes for LabelRegistry."""
        df = self.load_account_labels(mode=mode)
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")

    def audit_dataset(self) -> Dict[str, Any]:
        """
        Execute an exhaustive, memory-safe audit of the AMLSim dataset.

        Reports:
        - total transactions
        - unique accounts (senders, receivers, union)
        - unique source accounts
        - unique destination accounts
        - total labeled accounts
        - positive accounts
        - negative accounts
        - unlabeled accounts
        - transaction time range (start, end)
        - duplicate transaction IDs
        - missing required values
        """
        file_paths = self.get_file_paths()
        tx_path = self._find_file("transactions.csv.gz", ["transactions.csv"])
        comp = "gzip" if str(tx_path).endswith(".gz") else None

        total_transactions = 0
        seen_tx_ids: Set[str] = set()
        duplicate_tx_ids = 0
        source_accounts: Set[str] = set()
        dest_accounts: Set[str] = set()
        min_timestamp: Optional[pd.Timestamp] = None
        max_timestamp: Optional[pd.Timestamp] = None
        missing_required_counts: Dict[str, int] = {
            "tran_id": 0,
            "orig_acct": 0,
            "bene_acct": 0,
            "base_amt": 0,
            "tran_timestamp": 0,
        }

        chunksize = 200000
        for chunk in pd.read_csv(
            tx_path,
            compression=comp,
            usecols=["tran_id", "orig_acct", "bene_acct", "base_amt", "tran_timestamp"],
            dtype={"tran_id": "str", "orig_acct": "str", "bene_acct": "str", "base_amt": "float64", "tran_timestamp": "str"},
            chunksize=chunksize,
        ):
            total_transactions += len(chunk)

            # Missing value checks
            for col in missing_required_counts:
                missing_required_counts[col] += int(chunk[col].isna().sum())

            # Check duplicate IDs
            chunk_ids = chunk["tran_id"].dropna().astype(str).tolist()
            for tid in chunk_ids:
                if tid in seen_tx_ids:
                    duplicate_tx_ids += 1
                else:
                    seen_tx_ids.add(tid)

            # Unique senders / receivers
            source_accounts.update(chunk["orig_acct"].dropna().astype(str))
            dest_accounts.update(chunk["bene_acct"].dropna().astype(str))

            # Timestamps
            ts_series = pd.to_datetime(chunk["tran_timestamp"], utc=True, errors="coerce")
            chunk_min = ts_series.min()
            chunk_max = ts_series.max()
            if min_timestamp is None or (pd.notna(chunk_min) and chunk_min < min_timestamp):
                min_timestamp = chunk_min
            if max_timestamp is None or (pd.notna(chunk_max) and chunk_max > max_timestamp):
                max_timestamp = chunk_max

        all_tx_accounts = source_accounts.union(dest_accounts)

        # Account & label audit
        accounts_df = self.load_accounts()
        total_account_universe = len(accounts_df)
        universe_acct_ids = set(accounts_df["acct_id"])

        labels_df = self.load_account_labels(mode="closed_world")
        total_labeled_accounts = len(labels_df)
        positive_accounts = int((labels_df["label"] == 1).sum())
        negative_accounts = int((labels_df["label"] == 0).sum())
        unlabeled_accounts = len(universe_acct_ids - set(labels_df["user_id"]))

        audit_results = {
            "dataset_name": "IBM AMLSim bank_mixed v2.1",
            "data_directory": str(self.data_dir),
            "total_transactions": total_transactions,
            "unique_accounts": len(all_tx_accounts),
            "unique_source_accounts": len(source_accounts),
            "unique_destination_accounts": len(dest_accounts),
            "total_account_universe": total_account_universe,
            "total_labeled_accounts": total_labeled_accounts,
            "positive_accounts": positive_accounts,
            "negative_accounts": negative_accounts,
            "unlabeled_accounts": unlabeled_accounts,
            "positive_rate_percent": round(positive_accounts / max(total_labeled_accounts, 1) * 100, 4),
            "transaction_time_range": {
                "start": min_timestamp.isoformat() if min_timestamp is not None else None,
                "end": max_timestamp.isoformat() if max_timestamp is not None else None,
            },
            "duplicate_transaction_ids": duplicate_tx_ids,
            "missing_required_values": missing_required_counts,
            "files_audited": {k: str(v) if v else None for k, v in file_paths.items()},
        }
        return audit_results


def print_audit_report(results: Dict[str, Any]) -> None:
    """Print formatted terminal report of dataset audit."""
    print("=" * 70)
    print(f" DATASET AUDIT REPORT: {results['dataset_name']}")
    print("=" * 70)
    print(f"Data Directory : {results['data_directory']}")
    print(f"Transactions   : {results['total_transactions']:,}")
    print(f"Unique Accounts: {results['unique_accounts']:,}")
    print(f" - Source Accts: {results['unique_source_accounts']:,}")
    print(f" - Dest Accts  : {results['unique_destination_accounts']:,}")
    print(f"Account Universe: {results['total_account_universe']:,}")
    print("-" * 70)
    print(f"Labeled Accounts: {results['total_labeled_accounts']:,}")
    print(f" - Positive (SAR) : {results['positive_accounts']:,} ({results['positive_rate_percent']}%)")
    print(f" - Negative (Norm): {results['negative_accounts']:,}")
    print(f" - Unlabeled      : {results['unlabeled_accounts']:,}")
    print("-" * 70)
    time_range = results["transaction_time_range"]
    print(f"Time Range     : {time_range['start']}  -->  {time_range['end']}")
    print(f"Duplicate TxIDs: {results['duplicate_transaction_ids']}")
    print(f"Missing Values : {results['missing_required_values']}")
    print("=" * 70)


if __name__ == "__main__":
    adapter = AMLSimAdapter()
    audit = adapter.audit_dataset()
    print_audit_report(audit)
