"""
Health check endpoint.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "financial-anomaly-detection-api"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the operational status and service name of the backend API.",
)
async def check_health() -> HealthResponse:
    """Return backend health status."""
    return HealthResponse()
