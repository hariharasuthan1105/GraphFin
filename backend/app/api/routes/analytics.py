"""
User Behavioral, Temporal, and Graph Analytics Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from ...core.logging import get_logger
from ...schemas.analytics import UserAnalyticsResponse, UserFeatures
from ...services.feature_service import FEATURE_NAMES
from ...services.dataset_registry import dataset_registry

logger = get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics & Features"])


class FeatureSchemaResponse(BaseModel):
    feature_count: int
    features: List[str]
    description: str


@router.get(
    "/features/schema",
    response_model=FeatureSchemaResponse,
    summary="Feature Schema for ML Pipeline",
    description="Returns the ordered list of features that comprise the feature vector for ML modeling.",
)
async def get_feature_schema() -> FeatureSchemaResponse:
    """Expose feature ordering and metadata for ML training integration."""
    return FeatureSchemaResponse(
        feature_count=len(FEATURE_NAMES),
        features=FEATURE_NAMES,
        description=(
            "Ordered numerical feature columns prepared for tabular and graph-enhanced "
            "unsupervised anomaly detection (e.g. Isolation Forest)."
        ),
    )


@router.get(
    "/{dataset_id}/users",
    response_model=UserAnalyticsResponse,
    summary="User Features List",
    description=(
        "Returns the fused structural (graph), behavioral (transaction statistics), "
        "and temporal (frequency, intervals) features calculated for users in the specified dataset. "
        "Prepared as tabular features ready for downstream anomaly detection models."
    ),
)
async def get_user_analytics(
    dataset_id: str,
    user_id: Optional[str] = Query(
        None, description="Filter for a specific user ID"
    ),
    limit: int = Query(50, ge=1, le=500, description="Page size limit"),
    offset: int = Query(0, ge=0, description="Page offset index"),
) -> UserAnalyticsResponse:
    """Retrieve computed user features for a dataset with pagination and optional single-user filtering."""
    store = dataset_registry.get(dataset_id)
    response = store.get_user_features(user_id=user_id, limit=limit, offset=offset)
    if user_id and response.total_users == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found in current analytics dataset.",
        )
    return response


@router.get(
    "/{dataset_id}/users/{user_id}",
    response_model=UserFeatures,
    summary="Single User Feature Record",
    description="Retrieve all structural, behavioral, and temporal features for a single entity in a dataset.",
)
async def get_single_user_features(dataset_id: str, user_id: str) -> UserFeatures:
    """Retrieve full feature record for a single entity in a dataset."""
    store = dataset_registry.get(dataset_id)
    user_feat = store.feature_service.user_features.get(user_id)
    if not user_feat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found in current analytics dataset.",
        )
    return user_feat
