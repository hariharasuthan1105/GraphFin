"""
Pydantic schemas for real-time streaming simulation.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StreamStartRequest(BaseModel):
    """Configuration for starting a streaming simulation session."""
    experiment_label: str = Field(
        default="default",
        description="Trained anomaly detection experiment label to use for scoring.",
    )
    transactions_per_tick: int = Field(
        default=50,
        ge=1,
        description="Number of transactions revealed per simulation tick.",
    )
    tick_interval_seconds: float = Field(
        default=2.0,
        ge=0.01,
        description="Seconds to pause between consecutive ticks.",
    )
    rescoring_interval_ticks: int = Field(
        default=5,
        ge=1,
        description="Number of ticks between full graph rebuild, feature extraction, and re-scoring.",
    )
    split_label: Optional[str] = Field(
        default=None,
        description="Optional split label to locate the trained model artifact.",
    )


class StreamNode(BaseModel):
    id: str
    degree: int = 1
    status: str = "normal"
    risk_score: float = 0.0


class StreamEdge(BaseModel):
    source: str
    target: str
    amount: float = 0.0
    transactions: int = 1


class StreamScoredEntity(BaseModel):
    user_id: str
    raw_score: float
    prediction: int
    status: str
    risk_score: float
    reasons: List[str] = []


class StreamScoringSummary(BaseModel):
    total_users: int
    suspicious_count: int
    normal_count: int
    rescore_tick: int
    users: List[StreamScoredEntity] = []


class StreamStateResponse(BaseModel):
    """Snapshot of active or last-completed streaming simulation state."""
    dataset_id: str
    status: str = Field(..., description="'idle' | 'running' | 'stopped' | 'complete'")
    current_tick: int = 0
    transactions_revealed: int = 0
    total_transactions: int = 0
    current_entity_count: int = 0
    last_rescoring_tick: Optional[int] = None
    transactions_per_tick: int = 50
    tick_interval_seconds: float = 2.0
    rescoring_interval_ticks: int = 5
    experiment_label: str = "default"
    scoring_results: Optional[StreamScoringSummary] = None
    newly_flagged_entities: List[StreamScoredEntity] = []
    graph_nodes: List[StreamNode] = []
    graph_edges: List[StreamEdge] = []
    error: Optional[str] = None
    message: Optional[str] = None
