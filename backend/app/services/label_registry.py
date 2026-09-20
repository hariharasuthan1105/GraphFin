"""
Ground-Truth Label Registry Service.
Stores and manages user-level ground-truth fraud/anomaly labels per dataset.
Labels are maintained strictly for downstream evaluation and are NEVER fed
into feature matrices or training pipelines.
"""
import io
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd

from ..core.exceptions import NotFoundException, ValidationException
from ..core.logging import get_logger
from ..schemas.labels import DatasetLabelsSummaryResponse
from .dataset_registry import dataset_registry

logger = get_logger(__name__)

# Canonical boolean string mappings (case-insensitive)
POSITIVE_LABEL_VARIANTS: Set[str] = {
    "1",
    "1.0",
    "true",
    "t",
    "yes",
    "y",
    "fraud",
    "fraudulent",
    "suspicious",
    "anomaly",
    "anomalous",
}

NEGATIVE_LABEL_VARIANTS: Set[str] = {
    "0",
    "0.0",
    "false",
    "f",
    "no",
    "n",
    "normal",
    "legitimate",
    "legit",
    "non-fraud",
}


def parse_label_value(raw_val: object) -> bool:
    """
    Parse a raw label value into a boolean.
    Raises ValueError if unparseable.
    """
    if raw_val is None or pd.isna(raw_val):
        raise ValueError("Missing or NaN label value.")

    # Numeric conversion if already bool or int
    if isinstance(raw_val, bool):
        return raw_val

    clean_str = str(raw_val).strip().lower()

    if clean_str in POSITIVE_LABEL_VARIANTS:
        return True
    if clean_str in NEGATIVE_LABEL_VARIANTS:
        return False

    raise ValueError(
        f"Unrecognized label value '{raw_val}'. Accepted positive: {sorted(list(POSITIVE_LABEL_VARIANTS))}; "
        f"negative: {sorted(list(NEGATIVE_LABEL_VARIANTS))}."
    )


class LabelRegistry:
    """Registry managing dataset-scoped ground-truth labels for evaluation."""

    def __init__(self):
        # Key: dataset_id -> {user_id: bool}
        self._labels: Dict[str, Dict[str, bool]] = {}
        # Key: dataset_id -> DatasetLabelsSummaryResponse
        self._summaries: Dict[str, DatasetLabelsSummaryResponse] = {}

    def store_labels_from_csv(
        self,
        dataset_id: str,
        csv_content: bytes,
        user_id_col: str = "user_id",
        label_col: str = "label",
        strict: bool = False,
    ) -> DatasetLabelsSummaryResponse:
        """
        Parse, normalize, validate, and store ground-truth labels for a dataset.

        :param dataset_id: UUID of the dataset
        :param csv_content: Raw byte contents of uploaded labels CSV
        :param user_id_col: Column name containing entity/user ID
        :param label_col: Column name containing label
        :param strict: If True, any unknown user_id causes entire upload rejection.
        """
        # 1. Verify dataset exists and retrieve its entity list
        store = dataset_registry.get(dataset_id)
        dataset_user_ids, _, _ = store.get_feature_matrix()
        valid_entities_set = set(dataset_user_ids)

        if not csv_content or len(csv_content.strip()) == 0:
            raise ValidationException("Uploaded label CSV is empty.")

        try:
            df = pd.read_csv(io.BytesIO(csv_content), dtype=str, skipinitialspace=True)
        except Exception as e:
            raise ValidationException(f"Failed to parse label CSV: {str(e)}")

        # Clean column names (strip whitespace and lower)
        col_map = {col: str(col).strip() for col in df.columns}
        df = df.rename(columns=col_map)

        # Match columns case-insensitively
        actual_cols_lower = {col.lower(): col for col in df.columns}
        user_col_target = user_id_col.strip().lower()
        label_col_target = label_col.strip().lower()

        if user_col_target not in actual_cols_lower:
            raise ValidationException(
                f"Missing user ID column '{user_id_col}' in uploaded label file. "
                f"Available columns: {list(df.columns)}."
            )
        if label_col_target not in actual_cols_lower:
            raise ValidationException(
                f"Missing label column '{label_col}' in uploaded label file. "
                f"Available columns: {list(df.columns)}."
            )

        user_col_actual = actual_cols_lower[user_col_target]
        label_col_actual = actual_cols_lower[label_col_target]

        total_rows = len(df)
        if total_rows == 0:
            raise ValidationException("Label CSV contains headers but no data rows.")

        matched_labels: Dict[str, bool] = {}
        rejected_errors: List[str] = []
        positive_count = 0
        negative_count = 0

        for row_idx, row in df.iterrows():
            row_num = row_idx + 2  # 1-indexed header + 1
            raw_uid = row[user_col_actual]
            raw_lbl = row[label_col_actual]

            if pd.isna(raw_uid) or str(raw_uid).strip() == "":
                msg = f"Row {row_num}: Missing or blank user ID."
                rejected_errors.append(msg)
                continue

            uid_clean = str(raw_uid).strip()

            # Check if user exists in the dataset's feature matrix
            if uid_clean not in valid_entities_set:
                msg = f"Row {row_num}: user_id '{uid_clean}' does not exist in dataset '{dataset_id}' feature matrix."
                rejected_errors.append(msg)
                continue

            # Parse boolean label
            try:
                bool_lbl = parse_label_value(raw_lbl)
            except ValueError as e:
                msg = f"Row {row_num}: {str(e)}"
                rejected_errors.append(msg)
                continue

            # Explicit duplicate user detection
            if uid_clean in matched_labels:
                msg = f"Row {row_num}: Duplicate user_id '{uid_clean}' detected in uploaded CSV."
                rejected_errors.append(msg)
                logger.warning(msg)
                if strict:
                    continue
                old_lbl = matched_labels[uid_clean]
                if old_lbl:
                    positive_count -= 1
                else:
                    negative_count -= 1

            matched_labels[uid_clean] = bool_lbl
            if bool_lbl:
                positive_count += 1
            else:
                negative_count += 1

        unmatched_count = total_rows - len(matched_labels)

        if strict and len(rejected_errors) > 0:
            raise ValidationException(
                f"Rejected label upload: {len(rejected_errors)} invalid or unmatched rows found.",
                details=rejected_errors,
            )

        if len(matched_labels) == 0:
            raise ValidationException(
                "No label rows matched entities in the dataset.",
                details=rejected_errors,
            )

        prevalence = round(positive_count / len(matched_labels), 4) if matched_labels else 0.0

        summary = DatasetLabelsSummaryResponse(
            dataset_id=dataset_id,
            total_labels_uploaded=total_rows,
            matched_count=len(matched_labels),
            unmatched_count=unmatched_count,
            positive_count=positive_count,
            negative_count=negative_count,
            prevalence_rate=prevalence,
            rejected_errors=rejected_errors,
        )

        self._labels[dataset_id] = matched_labels
        self._summaries[dataset_id] = summary

        try:
            from ..core.config import settings
            lbl_file = settings.DATA_PROCESSED_DIR / f"{dataset_id}_labels.csv"
            lbl_file.write_bytes(csv_content)
        except Exception as e:
            logger.debug(f"Could not persist label CSV to disk: {e}")

        logger.info(
            f"Stored {len(matched_labels)} ground-truth labels for dataset '{dataset_id}' "
            f"({positive_count} positive, {negative_count} negative, {unmatched_count} rejected)."
        )

        return summary

    def has_labels(self, dataset_id: str) -> bool:
        """Check if labels exist for a dataset in-memory or on disk."""
        if dataset_id in self._labels:
            return True
        try:
            from ..core.config import settings
            lbl_file = settings.DATA_PROCESSED_DIR / f"{dataset_id}_labels.csv"
            return lbl_file.exists()
        except Exception:
            return False

    def get_labels(self, dataset_id: str) -> Dict[str, bool]:
        """
        Retrieve dictionary of user_id -> bool labels for a dataset.
        Raises NotFoundException if no labels have been uploaded.
        """
        # Ensure dataset exists
        dataset_registry.get(dataset_id)
        if dataset_id not in self._labels:
            # Check disk fallback
            try:
                from ..core.config import settings
                lbl_file = settings.DATA_PROCESSED_DIR / f"{dataset_id}_labels.csv"
                if lbl_file.exists():
                    self.store_labels_from_csv(dataset_id, lbl_file.read_bytes())
            except Exception as e:
                logger.debug(f"Could not restore labels from disk: {e}")

        if dataset_id not in self._labels:
            raise NotFoundException(
                f"No ground-truth labels found for dataset '{dataset_id}'. "
                f"Please upload labels first via POST /api/v1/datasets/{dataset_id}/labels."
            )
        return self._labels[dataset_id]

    def get_summary(self, dataset_id: str) -> DatasetLabelsSummaryResponse:
        """
        Retrieve stored label summary for a dataset.
        Raises NotFoundException if no labels have been uploaded.
        """
        dataset_registry.get(dataset_id)
        if dataset_id not in self._summaries:
            # Try reloading labels
            try:
                self.get_labels(dataset_id)
            except Exception:
                pass

        if dataset_id not in self._summaries:
            raise NotFoundException(
                f"No ground-truth labels have been uploaded for dataset '{dataset_id}'."
            )
        return self._summaries[dataset_id]

    def clear(self) -> None:
        """Clear all stored labels (used by tests)."""
        self._labels.clear()
        self._summaries.clear()
        logger.info("Label registry cleared.")


label_registry = LabelRegistry()
