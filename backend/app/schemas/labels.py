"""
Pydantic schemas for ground-truth label ingestion and summary reporting.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class DatasetLabelsSummaryResponse(BaseModel):
    """Summary of ground-truth labels attached to a dataset."""

    dataset_id: str = Field(..., description="UUID of the dataset")
    total_labels_uploaded: int = Field(..., description="Total rows in the uploaded label file")
    matched_count: int = Field(..., description="Number of labels matched to existing dataset entities")
    unmatched_count: int = Field(..., description="Number of label rows rejected because entity ID was not found")
    positive_count: int = Field(..., description="Number of positive (anomalous) labels")
    negative_count: int = Field(..., description="Number of negative (normal) labels")
    prevalence_rate: float = Field(
        ...,
        description="Prevalence rate of positive labels among matched entities (positives / matched)",
    )
    rejected_errors: List[str] = Field(
        default_factory=list,
        description="Detailed rejection messages for unmatched or unparseable label rows",
    )
