"""
Graph summary and topological network endpoints.
"""
from fastapi import APIRouter, HTTPException, status
from ...core.logging import get_logger
from ...schemas.graph import GraphSummaryResponse, NodeMetrics
from ...services.dataset_registry import dataset_registry

logger = get_logger(__name__)
router = APIRouter(prefix="/graph", tags=["Graph Analysis"])


@router.get(
    "/{dataset_id}/summary",
    response_model=GraphSummaryResponse,
    summary="Transaction Graph Network Summary",
    description=(
        "Returns topological network statistics calculated using NetworkX for the specified dataset, "
        "including node count, directed edge count, graph density, connected components, "
        "and highest-degree hub nodes."
    ),
)
async def get_graph_summary(dataset_id: str) -> GraphSummaryResponse:
    """Retrieve topological summary of the directed transaction graph for a dataset."""
    store = dataset_registry.get(dataset_id)
    return store.get_graph_summary()


@router.get(
    "/{dataset_id}/nodes/{user_id}",
    response_model=NodeMetrics,
    summary="Node Structural Metrics",
    description=(
        "Retrieve structural graph metrics (in/out degree, weighted volume, betweenness centrality) "
        "for a specific entity within a dataset."
    ),
)
async def get_node_metrics(dataset_id: str, user_id: str) -> NodeMetrics:
    """Retrieve NetworkX structural metrics for a single node within a dataset."""
    store = dataset_registry.get(dataset_id)
    if not store.graph_service.graph.has_node(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User node '{user_id}' not found in the transaction graph.",
        )

    features = store.graph_service.get_node_structural_features(user_id)
    return NodeMetrics(user_id=user_id, **features)
