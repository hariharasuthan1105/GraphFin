"""
Transaction schemas and validation models.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


class TransactionBase(BaseModel):
    """Canonical transaction schema."""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    sender_id: str = Field(..., description="Identifier of sending entity/account")
    receiver_id: str = Field(..., description="Identifier of receiving entity/account")
    amount: float = Field(..., gt=0, description="Transaction monetary amount (must be > 0)")
    timestamp: datetime = Field(..., description="Transaction execution timestamp")

    # Optional metadata fields
    transaction_type: Optional[str] = Field(None, description="e.g., transfer, payment, cash_out")
    merchant: Optional[str] = Field(None, description="Optional merchant name or code")
    location: Optional[str] = Field(None, description="Transaction location or IP location")
    device: Optional[str] = Field(None, description="Device fingerprint or identifier")

    @field_validator("transaction_id", "sender_id", "receiver_id")
    @classmethod
    def check_non_empty_string(cls, v: str, info) -> str:
        cleaned = str(v).strip()
        if not cleaned:
            raise ValueError(f"{info.field_name} cannot be empty or whitespace.")
        return cleaned

    @field_validator("amount")
    @classmethod
    def check_positive_amount(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError("Amount must be greater than zero.")
        return round(float(v), 2)

    @model_validator(mode="after")
    def check_sender_different_from_receiver(self):
        if self.sender_id == self.receiver_id:
            raise ValueError("Sender and receiver cannot be the same entity (self-transfers not permitted).")
        return self


class TransactionCreate(TransactionBase):
    """Schema used when creating a single transaction via API."""
    pass


class TransactionInDB(TransactionBase):
    """Schema representing stored transaction."""
    created_at: Optional[datetime] = None


class TimeRange(BaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class TransactionSummaryResponse(BaseModel):
    """Summary of ingested transactions."""
    transactions: int = Field(..., description="Total count of valid transactions")
    users: int = Field(..., description="Total count of distinct entities/users")
    total_amount: float = Field(..., description="Total cumulative monetary volume")
    average_amount: float = Field(..., description="Average transaction amount")
    min_amount: float = Field(..., description="Minimum transaction amount")
    max_amount: float = Field(..., description="Maximum transaction amount")
    time_range: TimeRange = Field(default_factory=TimeRange)
    currency: str = Field(default="USD", description="ISO 4217 currency code for all amounts in this dataset")


class DatasetStatusResponse(BaseModel):
    """Status response for dataset processing/availability."""
    dataset_id: str
    status: str
    currency: str = Field(default="USD", description="ISO 4217 currency code for this dataset")


class TransactionUploadResponse(BaseModel):
    """Response returned upon CSV transaction file upload."""
    message: str
    dataset_id: str
    status: str = "complete"
    total_rows_parsed: int
    valid_transactions: int
    invalid_rows_count: int
    validation_errors: List[str] = []
    duplicate_warnings: List[str] = []
    summary: TransactionSummaryResponse
    currency: str = Field(default="USD", description="ISO 4217 currency code stored for this dataset")
