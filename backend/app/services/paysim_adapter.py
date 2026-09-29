"""
PaySim Dataset Adapter Service for GraphFin.
Exposes PaySim loading, normalization, timestamp conversion, and ground-truth label derivation.
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from ..core.logging import get_logger

logger = get_logger(__name__)

# Base epoch for PaySim step-to-time conversion (1 step = 1 hour)
PAYSIM_BASE_TIMESTAMP = datetime(2023, 1, 1, 0, 0, 0)

# Forbidden fields that MUST NOT leak into anomaly detection features
FORBIDDEN_LEAKAGE_COLUMNS = {
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFlaggedFraud",
}


def convert_step_to_timestamp(step: int | float) -> str:
    """
    Convert PaySim hourly 'step' into a deterministic ISO timestamp string.
    Rule: base_timestamp + step hours (base: 2023-01-01 00:00:00).
    """
    hours = int(step) if pd.notna(step) else 0
    dt = PAYSIM_BASE_TIMESTAMP + timedelta(hours=hours)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def load_paysim_raw(
    input_path: Path | str,
    nrows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load raw PaySim transactions CSV into a normalized GraphFin pandas DataFrame.
    
    Raw mapping:
      step       -> timestamp (base + step hours)
      nameOrig   -> sender_id
      nameDest   -> receiver_id
      amount     -> amount
      isFraud    -> is_fraud (transaction label)
      type       -> transaction_type (metadata only)
    
    Strictly excludes balance fields (oldbalanceOrg, newbalanceOrig, etc.)
    and handles self-transfers / non-positive amounts.
    """
    path = Path(input_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"PaySim raw dataset not found at {path}")

    df = pd.read_csv(path, nrows=nrows)
    required = ["step", "type", "amount", "nameOrig", "nameDest", "isFraud"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"PaySim raw CSV missing required column: '{col}'")

    # Ensure no leakage columns are passed downstream
    df = df.drop(columns=[c for c in FORBIDDEN_LEAKAGE_COLUMNS if c in df.columns], errors="ignore")

    # Filter invalid rows (self-transfers or non-positive amounts)
    senders = df["nameOrig"].astype(str).str.strip()
    receivers = df["nameDest"].astype(str).str.strip()
    amounts = pd.to_numeric(df["amount"], errors="coerce")

    valid_mask = (senders != receivers) & (amounts > 0) & (senders.str.len() > 1) & (receivers.str.len() > 1)
    clean_df = df[valid_mask].copy()

    # Apply mapping
    clean_df["sender_id"] = clean_df["nameOrig"].astype(str).str.strip()
    clean_df["receiver_id"] = clean_df["nameDest"].astype(str).str.strip()
    clean_df["amount"] = pd.to_numeric(clean_df["amount"], errors="coerce").round(2)
    clean_df["is_fraud"] = pd.to_numeric(clean_df["isFraud"], errors="coerce").fillna(0).astype(int)
    clean_df["transaction_type"] = clean_df["type"].astype(str).str.strip()

    # Deterministic step to timestamp conversion
    steps = pd.to_numeric(clean_df["step"], errors="coerce").fillna(0).astype(int)
    clean_df["timestamp"] = [convert_step_to_timestamp(s) for s in steps]

    # Assign transaction IDs
    n = len(clean_df)
    clean_df["transaction_id"] = [f"TX_PS_{i+1:08d}" for i in range(n)]

    # Final canonical columns for GraphFin state store (plus metadata transaction_type)
    canonical_cols = ["transaction_id", "sender_id", "receiver_id", "amount", "timestamp", "transaction_type", "is_fraud"]
    return clean_df[canonical_cols]


def derive_paysim_account_labels(df_tx: pd.DataFrame) -> Dict[str, int]:
    """
    Derive account-level ground truth labels from PaySim transaction-level isFraud/is_fraud flag.
    Rule: 'Any Involvement' — an account is positive (1) if it appears as sender or receiver
    in at least one transaction with isFraud = 1.
    """
    fraud_col = "is_fraud" if "is_fraud" in df_tx.columns else "isFraud"
    sender_col = "sender_id" if "sender_id" in df_tx.columns else "nameOrig"
    receiver_col = "receiver_id" if "receiver_id" in df_tx.columns else "nameDest"

    senders = df_tx[[sender_col, fraud_col]].rename(columns={sender_col: "account_id"})
    receivers = df_tx[[receiver_col, fraud_col]].rename(columns={receiver_col: "account_id"})
    combined = pd.concat([senders, receivers], ignore_index=True)
    
    # Max fraud flag per account
    account_labels = combined.groupby("account_id")[fraud_col].max().to_dict()
    return {acc: int(val) for acc, val in account_labels.items()}


