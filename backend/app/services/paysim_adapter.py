"""
PaySim Dataset Adapter Service for GraphFin.
Exposes PaySim loading, normalization, and conversion functions.
"""
from pathlib import Path
from typing import Dict, Optional
import pandas as pd

from ..core.logging import get_logger

logger = get_logger(__name__)


def load_paysim_raw(
    input_path: Path | str,
    nrows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load raw PaySim transactions CSV into a normalized pandas DataFrame.
    """
    path = Path(input_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"PaySim raw dataset not found at {path}")

    df = pd.read_csv(path, nrows=nrows)
    required = ["step", "type", "amount", "nameOrig", "nameDest", "isFraud"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"PaySim CSV missing required column: '{col}'")

    # Filter invalid rows (self-transfers or non-positive amounts)
    df = df[df["nameOrig"] != df["nameDest"]].copy()
    df = df[df["amount"] > 0].copy()

    return df


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

