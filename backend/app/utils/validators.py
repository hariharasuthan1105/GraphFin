"""
Data validation utilities for transaction ingestion and preprocessing.
"""
from datetime import datetime
from typing import Any, List, Set, Tuple
import pandas as pd
from ..core.exceptions import ValidationException

REQUIRED_COLUMNS: Set[str] = {
    "transaction_id",
    "sender_id",
    "receiver_id",
    "amount",
    "timestamp",
}


def validate_csv_columns(columns: List[str]) -> Tuple[bool, List[str]]:
    """
    Ensure the incoming CSV header contains all mandatory canonical columns.
    Column matching is case-insensitive and ignores leading/trailing whitespace.
    """
    normalized_cols = {str(col).strip().lower() for col in columns}
    missing = [req for req in REQUIRED_COLUMNS if req not in normalized_cols]
    if missing:
        return False, missing
    return True, []


def parse_datetime_flexible(value: Any) -> datetime:
    """
    Parse a datetime value from various formats (string ISO, unix timestamp, pd.Timestamp).
    Raises ValueError if conversion is impossible.
    """
    if pd.isna(value) or value is None:
        raise ValueError("Timestamp cannot be null or missing.")

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        # Treat as unix timestamp in seconds
        try:
            return datetime.fromtimestamp(value)
        except Exception as e:
            raise ValueError(f"Invalid unix timestamp value: {value} ({e})")

    val_str = str(value).strip()
    if not val_str:
        raise ValueError("Timestamp cannot be empty.")

    # Try pandas to_datetime for flexible parsing
    try:
        parsed = pd.to_datetime(val_str)
        return parsed.to_pydatetime()
    except Exception as e:
        raise ValueError(f"Could not parse timestamp '{val_str}': {e}")


def validate_amount(value: Any) -> float:
    """
    Validate and return float amount > 0.
    """
    if pd.isna(value) or value is None:
        raise ValueError("Amount cannot be null or missing.")

    try:
        amt = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Amount must be a numeric value, got: '{value}'")

    if amt <= 0:
        raise ValueError(f"Amount must be greater than zero, got: {amt}")

    return round(amt, 2)
