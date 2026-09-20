"""
Dataset Train/Test Entity-Level Split Service.
Manages deterministic user/entity-level partitions for held-out evaluation.
Restricts model fitting and percentile explainability statistics strictly to
the train partition entities.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.model_selection import train_test_split

from ..core.config import settings
from ..core.exceptions import NotFoundException, ValidationException
from ..core.logging import get_logger
from ..schemas.split import SplitAssignment, SplitSummaryResponse
from .dataset_registry import dataset_registry
from .label_registry import label_registry

logger = get_logger(__name__)


class SplitService:
    """Service managing dataset-scoped entity-level train/test partitions."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or settings.DATA_PROCESSED_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # In-memory split registry keyed by (dataset_id, split_label)
        self._splits: Dict[Tuple[str, str], SplitAssignment] = {}

    def _get_split_path(self, dataset_id: str, split_label: str) -> Path:
        clean_split = (split_label or "default").strip()
        return self.storage_dir / f"{dataset_id}__{clean_split}_split.json"

    def create_split(
        self,
        dataset_id: str,
        test_size: float = 0.3,
        random_state: int = 42,
        stratify_by_label: bool = True,
        split_label: str = "default",
    ) -> SplitAssignment:
        """
        Create a deterministic entity-level train/test split for a dataset.

        :param dataset_id: UUID of the dataset
        :param test_size: Proportion of entities allocated to the test set (0.0 < test_size < 1.0)
        :param random_state: Seed for deterministic splitting
        :param stratify_by_label: Whether to preserve label prevalence across partitions
        :param split_label: Identifier for this split configuration (default: "default")
        :return: SplitAssignment with partition metrics and entity ID lists
        """
        clean_split = (split_label or "default").strip()
        if not clean_split:
            clean_split = "default"

        if not (0.0 < test_size < 1.0):
            raise ValidationException(
                f"Invalid test_size {test_size}. Must be strictly between 0.0 and 1.0."
            )

        # 1. Verify dataset exists
        store = dataset_registry.get(dataset_id)
        dataset_user_ids, _, _ = store.get_feature_matrix()

        if len(dataset_user_ids) == 0:
            raise ValidationException(
                f"Cannot create split: dataset '{dataset_id}' contains no users or transactions."
            )

        # 2. Verify ground-truth labels exist (raises NotFoundException if missing)
        labels = label_registry.get_labels(dataset_id)

        if not labels:
            raise ValidationException(
                f"No ground-truth labels found for dataset '{dataset_id}'. "
                "A held-out evaluation split requires ground-truth labels to be uploaded first."
            )

        # 3. Restrict partition to entities with known ground-truth labels
        valid_user_ids = sorted([uid for uid in dataset_user_ids if uid in labels])

        if len(valid_user_ids) < 2:
            raise ValidationException(
                f"Dataset '{dataset_id}' has only {len(valid_user_ids)} labeled entities. "
                "At least 2 labeled entities are required to create a train/test split."
            )

        y = [1 if labels[uid] else 0 for uid in valid_user_ids]
        pos_count = sum(y)
        neg_count = len(y) - pos_count

        stratified = False
        warning: Optional[str] = None

        # 4. Attempt stratified split if requested and both classes have >= 2 instances
        if stratify_by_label and pos_count >= 2 and neg_count >= 2:
            try:
                train_uids, test_uids = train_test_split(
                    valid_user_ids,
                    test_size=test_size,
                    random_state=random_state,
                    stratify=y,
                )
                stratified = True
            except Exception as e:
                logger.warning(
                    f"Stratification failed for dataset '{dataset_id}' ({e}). "
                    "Falling back to unstratified split."
                )
                train_uids, test_uids = train_test_split(
                    valid_user_ids,
                    test_size=test_size,
                    random_state=random_state,
                    stratify=None,
                )
                stratified = False
                warning = f"Stratification failed ({str(e)}); fell back to unstratified split."
        else:
            train_uids, test_uids = train_test_split(
                valid_user_ids,
                test_size=test_size,
                random_state=random_state,
                stratify=None,
            )
            stratified = False
            if stratify_by_label:
                warning = (
                    f"Stratification disabled: both classes must have at least 2 members "
                    f"(found positive={pos_count}, negative={neg_count}). Fell back to unstratified split."
                )
                logger.info(warning)

        # Sort partitioned IDs for reproducible presentation & deterministic iteration
        train_uids = sorted(train_uids)
        test_uids = sorted(test_uids)

        train_pos = sum(1 for uid in train_uids if labels[uid])
        train_neg = len(train_uids) - train_pos
        train_prev = round(train_pos / len(train_uids), 4) if train_uids else 0.0

        test_pos = sum(1 for uid in test_uids if labels[uid])
        test_neg = len(test_uids) - test_pos
        test_prev = round(test_pos / len(test_uids), 4) if test_uids else 0.0

        overall_prev = round(pos_count / len(valid_user_ids), 4) if valid_user_ids else 0.0

        now_iso = datetime.now(timezone.utc).isoformat()

        assignment = SplitAssignment(
            dataset_id=dataset_id,
            split_label=clean_split,
            total_users=len(valid_user_ids),
            train_count=len(train_uids),
            test_count=len(test_uids),
            train_positive_count=train_pos,
            train_negative_count=train_neg,
            test_positive_count=test_pos,
            test_negative_count=test_neg,
            train_prevalence=train_prev,
            test_prevalence=test_prev,
            overall_prevalence=overall_prev,
            stratified=stratified,
            test_size=test_size,
            random_state=random_state,
            warning=warning,
            created_at=now_iso,
            train_user_ids=train_uids,
            test_user_ids=test_uids,
        )

        key = (dataset_id, clean_split)
        self._splits[key] = assignment

        # Persist to disk for durable experiments
        try:
            split_file = self._get_split_path(dataset_id, clean_split)
            split_file.write_text(json.dumps(assignment.model_dump(), indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Could not persist split assignment to disk: {e}")

        logger.info(
            f"Created entity split '{clean_split}' for dataset '{dataset_id}': "
            f"train={len(train_uids)} (pos={train_pos}), test={len(test_uids)} (pos={test_pos}), "
            f"stratified={stratified}"
        )

        return assignment

    def get_split(self, dataset_id: str, split_label: str = "default") -> SplitAssignment:
        """
        Retrieve stored split assignment with train/test entity IDs.
        Raises NotFoundException if the split has not been created.
        """
        clean_split = (split_label or "default").strip()
        key = (dataset_id, clean_split)

        if key in self._splits:
            return self._splits[key]

        # Check disk cache
        split_file = self._get_split_path(dataset_id, clean_split)
        if split_file.exists():
            try:
                data = json.loads(split_file.read_text(encoding="utf-8"))
                assignment = SplitAssignment(**data)
                self._splits[key] = assignment
                return assignment
            except Exception as e:
                logger.warning(f"Could not restore split assignment from {split_file}: {e}")

        raise NotFoundException(
            f"Split assignment '{clean_split}' not found for dataset '{dataset_id}'. "
            f"Please create it first via POST /api/v1/datasets/{dataset_id}/splits."
        )

    def get_split_summary(self, dataset_id: str, split_label: str = "default") -> SplitSummaryResponse:
        """Retrieve stored split summary without raw user ID lists."""
        full_split = self.get_split(dataset_id, split_label)
        return SplitSummaryResponse(**full_split.model_dump(exclude={"train_user_ids", "test_user_ids"}))

    def has_split(self, dataset_id: str, split_label: str = "default") -> bool:
        """Check if a split exists in memory or on disk."""
        clean_split = (split_label or "default").strip()
        key = (dataset_id, clean_split)
        if key in self._splits:
            return True
        return self._get_split_path(dataset_id, clean_split).exists()

    def list_splits(self, dataset_id: str) -> List[SplitSummaryResponse]:
        """List all stored split assignments for a dataset."""
        dataset_registry.get(dataset_id)
        splits: Dict[str, SplitSummaryResponse] = {}

        # 1. From cache
        for (ds_id, sp_lbl), assignment in self._splits.items():
            if ds_id == dataset_id:
                splits[sp_lbl] = SplitSummaryResponse(
                    **assignment.model_dump(exclude={"train_user_ids", "test_user_ids"})
                )

        # 2. From disk files matching dataset_id__*_split.json
        prefix = f"{dataset_id}__"
        suffix = "_split.json"
        for p in self.storage_dir.glob(f"{prefix}*{suffix}"):
            raw_label = p.name[len(prefix) : -len(suffix)]
            if raw_label not in splits:
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    assignment = SplitAssignment(**data)
                    self._splits[(dataset_id, raw_label)] = assignment
                    splits[raw_label] = SplitSummaryResponse(
                        **assignment.model_dump(exclude={"train_user_ids", "test_user_ids"})
                    )
                except Exception as e:
                    logger.warning(f"Could not read split file {p}: {e}")

        return sorted(list(splits.values()), key=lambda s: s.split_label)

    def clear(self) -> None:
        """Clear all stored split assignments (used by tests)."""
        self._splits.clear()
        for p in self.storage_dir.glob("*_split.json"):
            try:
                p.unlink()
            except Exception as e:
                logger.warning(f"Could not remove split artifact {p}: {e}")
        logger.info("Split registry cleared.")


split_service = SplitService()
