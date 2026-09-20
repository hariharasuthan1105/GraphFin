"""
Graph schemas and metric responses.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class NodeMetrics(BaseModel):
    user_id: str
    in_degree: int
    out_degree: int
    total_degree: int
    weighted_in_degree: float
    weighted_out_degree: float
    betweenness_centrality: float


class GraphSummaryResponse(BaseModel):
    """Statistical summary of the constructed transaction graph."""
    nodes: int = Field(..., description="Total number of unique user/account nodes")
    edges: int = Field(..., description="Total number of directed transaction edges")
    density: float = Field(..., description="Network density (actual edges / possible edges)")
    is_directed: bool = Field(True, description="Whether the graph is directed")
    weakly_connected_components: int = Field(..., description="Count of weakly connected subgraphs")
    strongly_connected_components: int = Field(..., description="Count of strongly connected subgraphs")
    top_in_degree_nodes: List[NodeMetrics] = Field(
        default_factory=list,
        description="Top nodes with highest incoming transaction connections",
    )
    top_out_degree_nodes: List[NodeMetrics] = Field(
        default_factory=list,
        description="Top nodes with highest outgoing transaction connections",
    )


class TopNodesResponse(BaseModel):
    nodes: List[NodeMetrics]
