"""
Real-Time Streaming Simulation REST API Endpoints.
Provides endpoints to start, stop, and monitor real-time transaction streaming simulation.
"""
from fastapi import APIRouter, Body, status

from ...core.logging import get_logger
from ...schemas.stream import StreamStartRequest, StreamStateResponse
from ...services.stream_simulator import stream_simulator

logger = get_logger(__name__)

router = APIRouter(prefix="/stream", tags=["Streaming Simulation"])


@router.post(
    "/{dataset_id}/start",
    response_model=StreamStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Streaming Simulation",
    description=(
        "Starts a background incremental replay simulation for the given dataset_id at a controlled rate, "
        "periodically rebuilding the graph and re-scoring with the specified pre-trained model."
    ),
)
async def start_stream(
    dataset_id: str,
    payload: StreamStartRequest = Body(
        default_factory=StreamStartRequest,
        description="Configuration for streaming simulation playback and rescoring.",
    ),
) -> StreamStateResponse:
    """Start transaction stream simulation session."""
    logger.info(
        f"Request to start streaming simulation for dataset '{dataset_id}' with experiment '{payload.experiment_label}'."
    )
    return stream_simulator.start_simulation(dataset_id, payload)


@router.post(
    "/{dataset_id}/stop",
    response_model=StreamStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop Streaming Simulation",
    description="Stops an active streaming simulation session for the specified dataset_id.",
)
async def stop_stream(dataset_id: str) -> StreamStateResponse:
    """Stop active streaming simulation session."""
    logger.info(f"Request to stop streaming simulation for dataset '{dataset_id}'.")
    return stream_simulator.stop_simulation(dataset_id)


@router.get(
    "/{dataset_id}/state",
    response_model=StreamStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Streaming Simulation State",
    description="Returns the current progress, revealed counts, graph state, and latest scoring results.",
)
async def get_stream_state(dataset_id: str) -> StreamStateResponse:
    """Get snapshot of current or completed streaming simulation state."""
    return stream_simulator.get_state(dataset_id)
