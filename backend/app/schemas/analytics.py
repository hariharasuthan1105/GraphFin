"""
Analytics schemas for user graph, behavioral, and temporal feature sets.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class UserFeatures(BaseModel):
    """Unified user profile feature set for downstream anomaly detection."""
    user_id: str = Field(..., description="Unique entity/user identifier")

    # Structural / Graph features (NetworkX derived)
    in_degree: int = Field(..., description="Number of incoming transaction connections")
    out_degree: int = Field(..., description="Number of outgoing transaction connections")
    total_degree: int = Field(..., description="Sum of incoming and outgoing connections")
    weighted_in_degree: float = Field(..., description="Total volume received across all incoming edges")
    weighted_out_degree: float = Field(..., description="Total volume sent across all outgoing edges")
    betweenness_centrality: float = Field(..., description="Node betweenness centrality score in the network")

    # Behavioral features
    transaction_count: int = Field(..., description="Total number of transactions involving this user")
    total_sent: float = Field(..., description="Cumulative monetary amount sent")
    total_received: float = Field(..., description="Cumulative monetary amount received")
    net_flow: float = Field(..., description="Net flow = total_received - total_sent")
    average_transaction_amount: float = Field(..., description="Average amount across all user transactions")
    maximum_transaction_amount: float = Field(..., description="Maximum amount in a single transaction")
    unique_receivers: int = Field(..., description="Number of distinct counterparties sent to")
    unique_senders: int = Field(..., description="Number of distinct counterparties received from")

    # Temporal features
    transactions_per_day: float = Field(..., description="Average frequency of transactions per day")
    transactions_per_week: float = Field(..., description="Average frequency of transactions per week")
    average_time_between_transactions: float = Field(
        ..., description="Average duration (seconds) between successive transactions"
    )
    minimum_time_between_transactions: float = Field(
        ..., description="Minimum duration (seconds) between successive transactions"
    )
    maximum_time_between_transactions: float = Field(
        ..., description="Maximum duration (seconds) between successive transactions"
    )

    # Clean array representation for ML algorithms (e.g., Isolation Forest)
    feature_vector: Optional[List[float]] = Field(
        None, description="Raw ordered numerical feature vector for ML model ingestion"
    )


class UserAnalyticsResponse(BaseModel):
    """Paginated user feature collection response."""
    total_users: int = Field(..., description="Total number of evaluated users")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Page offset")
    users: List[UserFeatures] = Field(..., description="List of user feature records")
