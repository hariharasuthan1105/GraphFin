"""
Pydantic schemas for dataset train/test entity-level split management.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SplitCreateRequest(BaseModel):
    """Payload for creating a train/test entity-level split."""

    split_label: Optional[str] = Field(
        default="default",
        description="Unique identifier for the split configuration (e.g. 'default', 'split_80_20').",
    )
    test_size: Optional[float] = Field(
        default=0.3,
        gt=0.0,
        lt=1.0,
        description="Fraction of entities allocated to the test set (0.0 < test_size < 1.0).",
    )
    random_state: Optional[int] = Field(
        default=42,
        description="Seed for deterministic, reproducible random splitting.",
    )
    stratify_by_label: Optional[bool] = Field(
        default=True,
        description="Whether to preserve class balance across train and test partitions using ground-truth labels.",
    )

    @field_validator("split_label")
    @classmethod
    def validate_split_label(cls, v: Optional[str]) -> str:
        if not v or str(v).strip() == "":
            return "default"
        return str(v).strip()


class SplitSummaryResponse(BaseModel):
    """Compact summary of a dataset entity-level split assignment (without raw user lists)."""

    dataset_id: str = Field(..., description="UUID of the dataset")
    split_label: str = Field(..., description="Unique label identifying the split")
    total_users: int = Field(..., description="Total unique labeled entities included in the split")
    train_count: int = Field(..., description="Count of entities assigned to the training partition")
    test_count: int = Field(..., description="Count of entities assigned to the test partition")
    train_positive_count: int = Field(..., description="Number of positive (anomalous) entities in train partition")
    train_negative_count: int = Field(..., description="Number of negative (normal) entities in train partition")
    test_positive_count: int = Field(..., description="Number of positive (anomalous) entities in test partition")
    test_negative_count: int = Field(..., description="Number of negative (normal) entities in test partition")
    train_prevalence: float = Field(..., description="Proportion of positive entities in train partition")
    test_prevalence: float = Field(..., description="Proportion of positive entities in test partition")
    overall_prevalence: float = Field(..., description="Proportion of positive entities across all split users")
    stratified: bool = Field(..., description="Whether stratification by label succeeded")
    test_size: float = Field(..., description="Configured test size fraction")
    random_state: int = Field(..., description="Random seed used for splitting")
    warning: Optional[str] = Field(
        None,
        description="Warning documentation if stratification was disabled or fell back to unstratified split",
    )
    created_at: Optional[str] = Field(None, description="ISO timestamp of split creation")


class SplitAssignment(SplitSummaryResponse):
    """Complete split assignment including full entity ID lists for train and test partitions."""

    train_user_ids: List[str] = Field(..., description="List of entity IDs assigned to the train partition")
    test_user_ids: List[str] = Field(..., description="List of entity IDs assigned to the test partition")
