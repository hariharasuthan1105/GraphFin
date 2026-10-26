"""Public bounded graph contracts. No original account/transaction identities."""
from typing import Literal
from pydantic import BaseModel, ConfigDict


class PublicGraph(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class GraphExperiment(PublicGraph):
    experiment_id: str
    method: str
    version: str
    split_seed: int
    model_seed: int


class GraphDataset(PublicGraph):
    dataset_id: str
    name: str
    tier: str
    status: Literal['verified','unavailable']
    provenance_status: Literal['partially_verified','unresolved']
    reason: str | None
    graph_id: str | None
    version: str
    dataset_sha256: str | None
    index_sha256: str | None
    snapshot_identity: str | None
    time_start: float | None
    time_end: float | None
    time_semantics: str
    amount_unit: str
    total_nodes: int | None
    total_edges: int | None
    approved_scope_nodes: int
    experiments: list[GraphExperiment]


class GraphCatalog(PublicGraph):
    datasets: list[GraphDataset]
    limitations: list[str]


class GraphAnchor(PublicGraph):
    node_ref: str
    display_id: str
    role: str


class GraphSession(PublicGraph):
    session_id: str
    expires_in_seconds: int
    query_budget: int
    dataset: GraphDataset
    experiment: GraphExperiment
    anchors: list[GraphAnchor]
    focus_ref: str


class ExplorerNode(PublicGraph):
    node_ref: str
    display_id: str
    node_type: Literal['account']
    in_degree: int
    out_degree: int
    neighbors: int
    received_amount: float
    sent_amount: float
    ranking_status: Literal['available','unavailable_population','unavailable_temporal']
    anomaly_score: float | None
    saved_rank: int | None
    diagnostic_ids: list[str]
    diagnostic_status: str


class ExplorerEdge(PublicGraph):
    edge_ref: str
    source_ref: str
    target_ref: str
    direction: Literal['sender_to_receiver']
    transaction_count: int
    amount: float
    first_time: str
    last_time: str
    reciprocal_in_snapshot: bool


class GraphNeighborhood(PublicGraph):
    schema_version: Literal['graphfin-neighborhood-v1']
    graph_id: str
    dataset_id: str
    tier: str
    version: str
    snapshot_identity: str
    dataset_sha256: str
    index_sha256: str
    status: Literal['verified']
    provenance_status: Literal['partially_verified']
    experiment: GraphExperiment
    focus_ref: str
    nodes: list[ExplorerNode]
    edges: list[ExplorerEdge]
    depth: int
    direction: str
    start: float
    end: float
    min_count: int
    min_amount: float
    temporal_subset: bool
    scope_nodes: int
    max_nodes: int
    max_edges: int
    truncated: bool
    truncation_reasons: list[str]
    remaining_queries: int
    remaining_node_grants: int
    query_seconds: float
    amount_unit: str
    limitations: list[str]
