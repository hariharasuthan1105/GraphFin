from typing import Optional
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """Request payload for exporting evaluation results to PDF, Word (DOCX), or CSV."""
    source: str = Field(
        ...,
        description="'official' for locked benchmark research results, or 'custom' for user-uploaded dataset evaluation.",
    )
    format: str = Field(
        ...,
        description="'pdf', 'docx', or 'csv'",
    )
    dataset_id: Optional[str] = Field(
        default=None,
        description="Dataset identifier (required when source='custom').",
    )
    experiment_label: Optional[str] = Field(
        default=None,
        description="Optional single experiment to evaluate. If omitted in custom mode, evaluates all experiments.",
    )
    split_label: Optional[str] = Field(
        default=None,
        description="Optional split label to locate the held-out test partition.",
    )
