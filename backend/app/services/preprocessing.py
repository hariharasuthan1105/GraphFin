"""
Transaction data preprocessing and validation service.
Ensures transaction records adhere to canonical schemas without silent data corruption.
"""
import io
from typing import Any, List, Optional, Tuple
import pandas as pd
from ..core.exceptions import ValidationException
from ..core.logging import get_logger
from ..utils.validators import validate_csv_columns, parse_datetime_flexible, validate_amount

logger = get_logger(__name__)


class PreprocessingService:
    """Service for parsing, validating, and cleaning transaction datasets."""

    def __init__(self, strict_mode: bool = False):
        """
        :param strict_mode: If True, any single invalid row aborts the entire upload.
                            If False, invalid rows are collected in a rejection log.
        """
        self.strict_mode = strict_mode

    def process_csv(self, file_content: bytes) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """
        Parse raw CSV bytes into a validated Pandas DataFrame.

        :param file_content: Raw byte string of uploaded CSV.
        :return: Tuple of (validated_dataframe, list_of_error_strings, list_of_warning_strings).
        :raises ValidationException: If file is empty, missing required headers,
                                     or has critical schema violations.
        """
        if not file_content or len(file_content.strip()) == 0:
            raise ValidationException("Uploaded CSV file is completely empty.")

        try:
            # Detect encoding and read dataframe
            df = pd.read_csv(io.BytesIO(file_content), dtype=str, skipinitialspace=True)
        except Exception as e:
            raise ValidationException(f"Failed to parse CSV file: {str(e)}")

        return self.process_dataframe(df)

    def process_dataframe(self, raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """
        Validate and sanitize transaction DataFrame.
        """
        if raw_df.empty:
            raise ValidationException("CSV contains headers but has no data rows.")

        # 1. Normalize column names (strip whitespace and lowercase)
        original_cols = raw_df.columns.tolist()
        col_mapping = {col: str(col).strip().lower() for col in original_cols}
        raw_df = raw_df.rename(columns=col_mapping)

        # 2. Check for required canonical columns
        is_valid, missing_cols = validate_csv_columns(raw_df.columns.tolist())
        if not is_valid:
            raise ValidationException(
                f"Missing mandatory columns: {', '.join(missing_cols)}. "
                "Required columns are: transaction_id, sender_id, receiver_id, amount, timestamp."
            )

        validation_errors: List[str] = []
        warnings: List[str] = []
        valid_rows: List[dict] = []

        # Keep track of transaction_ids seen in this batch to detect duplicates
        seen_tx_ids = set()
        # Keep track of (sender_id, receiver_id, amount, timestamp) tuples for soft duplicates
        seen_tx_tuples = set()

        for idx, row in raw_df.iterrows():
            row_num = idx + 2  # 1-indexed accounting for CSV header
            row_errors = []

            # Extract fields
            tx_id = str(row.get("transaction_id", "")).strip() if pd.notna(row.get("transaction_id")) else ""
            sender = str(row.get("sender_id", "")).strip() if pd.notna(row.get("sender_id")) else ""
            receiver = str(row.get("receiver_id", "")).strip() if pd.notna(row.get("receiver_id")) else ""
            raw_amount = row.get("amount")
            raw_timestamp = row.get("timestamp")

            # Validate transaction_id
            if not tx_id:
                row_errors.append("Empty or missing transaction_id.")
            elif tx_id in seen_tx_ids:
                row_errors.append(f"Duplicate transaction_id '{tx_id}' found in dataset.")
            else:
                seen_tx_ids.add(tx_id)

            # Validate sender and receiver
            if not sender:
                row_errors.append("Empty or missing sender_id.")
            if not receiver:
                row_errors.append("Empty or missing receiver_id.")
            if sender and receiver and sender == receiver:
                row_errors.append(f"Self-transfer detected (sender '{sender}' == receiver '{receiver}').")

            # Validate amount
            parsed_amount = None
            try:
                parsed_amount = validate_amount(raw_amount)
            except ValueError as ve:
                row_errors.append(str(ve))

            # Validate timestamp
            parsed_timestamp = None
            try:
                parsed_timestamp = parse_datetime_flexible(raw_timestamp)
            except ValueError as ve:
                row_errors.append(str(ve))

            if row_errors:
                err_msg = f"Row {row_num} (tx_id: '{tx_id or 'UNKNOWN'}'): " + "; ".join(row_errors)
                validation_errors.append(err_msg)
                if self.strict_mode:
                    raise ValidationException(
                        "Strict validation failure: " + err_msg,
                        details=validation_errors
                    )
                continue

            # Soft duplicate check for (sender_id, receiver_id, amount, timestamp)
            tx_tuple = (sender, receiver, parsed_amount, parsed_timestamp)
            if tx_tuple in seen_tx_tuples:
                warnings.append(
                    f"Row {row_num} duplicates the (sender, receiver, amount, timestamp) "
                    "of an earlier row; kept as a possible legitimate repeat transfer."
                )
            else:
                seen_tx_tuples.add(tx_tuple)

            # Optional metadata fields
            valid_record = {
                "transaction_id": tx_id,
                "sender_id": sender,
                "receiver_id": receiver,
                "amount": parsed_amount,
                "timestamp": parsed_timestamp,
                "transaction_type": str(row.get("transaction_type", "")).strip() if pd.notna(row.get("transaction_type")) else None,
                "merchant": str(row.get("merchant", "")).strip() if pd.notna(row.get("merchant")) else None,
                "location": str(row.get("location", "")).strip() if pd.notna(row.get("location")) else None,
                "device": str(row.get("device", "")).strip() if pd.notna(row.get("device")) else None,
            }
            valid_rows.append(valid_record)

        if not valid_rows:
            raise ValidationException(
                "All transaction rows failed validation. No valid records could be processed.",
                details=validation_errors[:20]  # First 20 errors
            )

        logger.info(
            f"Preprocessed dataset: {len(valid_rows)} valid transactions, "
            f"{len(validation_errors)} rejected rows, "
            f"{len(warnings)} duplicate warnings."
        )

        clean_df = pd.DataFrame(valid_rows)
        # Ensure correct datatypes
        clean_df["amount"] = clean_df["amount"].astype(float)
        clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"])

        return clean_df, validation_errors, warnings
