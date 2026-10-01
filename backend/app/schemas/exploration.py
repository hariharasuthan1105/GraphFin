"""
PaySim Exploration schemas.
Descriptive statistics for the production PaySim 10K slice.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExplorationTransactionStats(BaseModel):
    count: int = Field(..., description="Number of transactions in the production slice")
    total_amount: float = Field(..., description="Total monetary amount of all transactions")
    mean_amount: float = Field(..., description="Mean transaction amount")
    median_amount: float = Field(..., description="Median transaction amount")
    min_amount: float = Field(..., description="Minimum transaction amount")
    max_amount: float = Field(..., description="Maximum transaction amount")


class ExplorationAccountStats(BaseModel):
    count: int = Field(..., description="Number of unique accounts in the production slice")
    fraud_involved: int = Field(..., description="Accounts labeled as fraud-involved")
    normal: int = Field(..., description="Accounts labeled as normal")


class ExplorationNetworkStats(BaseModel):
    nodes: int = Field(..., description="Number of graph nodes")
    edges: int = Field(..., description="Number of directed graph edges")
    density: float = Field(..., description="Graph density")
    weakly_connected_components: int = Field(..., description="Number of weakly connected components")


class ExplorationTemporalStats(BaseModel):
    min_step: Optional[int] = Field(None, description="Minimum simulated time step")
    max_step: Optional[int] = Field(None, description="Maximum simulated time step")
    unique_steps: Optional[int] = Field(None, description="Number of unique time steps")


class AmountBucket(BaseModel):
    bucket: str = Field(..., description="Amount range label")
    count: int = Field(..., description="Number of transactions in this range")


class StepCount(BaseModel):
    step: int = Field(..., description="Simulated time step")
    count: int = Field(..., description="Number of transactions at this step")


class FraudVsNormal(BaseModel):
    label: str = Field(..., description="fraud-involved or normal")
    count: int = Field(..., description="Number of accounts with this label")


class TopAccount(BaseModel):
    account_id: str = Field(..., description="Account identifier")
    transaction_count: int = Field(..., description="Number of transactions")
    total_amount: float = Field(..., description="Total monetary amount")


class FeatureStat(BaseModel):
    feature_name: str = Field(..., description="Name of the feature")
    group: str = Field(..., description="Feature group: graph / behavioral / temporal")
    mean: float = Field(..., description="Mean value across all accounts")
    std: float = Field(..., description="Standard deviation")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    pct_missing: float = Field(..., description="Percentage of missing/zero values")


class PaySimExplorationResponse(BaseModel):
    """Full descriptive exploration response for the PaySim production 10K slice."""
    dataset_id: str = Field("paysim", description="Dataset identifier")
    scope: str = Field("production_slice", description="Scope descriptor")
    status: str = Field("loaded", description="Loading status")
    transactions: ExplorationTransactionStats
    accounts: ExplorationAccountStats
    network: ExplorationNetworkStats
    temporal: ExplorationTemporalStats
    amount_distribution: List[AmountBucket] = Field(
        default_factory=list,
        description="Histogram buckets of transaction amounts",
    )
    transactions_by_step: List[StepCount] = Field(
        default_factory=list,
        description="Transaction counts per simulated time step (sampled for large step counts)",
    )
    fraud_vs_normal: List[FraudVsNormal] = Field(
        default_factory=list,
        description="Fraud-involved vs normal account breakdown",
    )
    top_senders: List[TopAccount] = Field(
        default_factory=list,
        description="Top 10 accounts by outgoing transaction count",
    )
    top_receivers: List[TopAccount] = Field(
        default_factory=list,
        description="Top 10 accounts by incoming transaction count",
    )
    feature_summary: List[FeatureStat] = Field(
        default_factory=list,
        description="Descriptive statistics for all 19 GraphFin features",
    )


class PaySimExplorationNotLoadedResponse(BaseModel):
    """Returned when PaySim is not currently loaded."""
    dataset_id: str = "paysim"
    status: str = "not_loaded"
    message: str = "PaySim production slice is not currently loaded."
