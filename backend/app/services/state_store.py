"""
In-Memory Application State Store.
Maintains active datasets, graph structures, and extracted features across API requests.
"""
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from ..core.logging import get_logger
from ..schemas.transaction import TransactionSummaryResponse, TimeRange
from ..schemas.graph import GraphSummaryResponse
from ..schemas.analytics import UserAnalyticsResponse, UserFeatures
from .graph_service import GraphService
from .feature_service import FeatureService

logger = get_logger(__name__)


class StateStore:
    """Singleton store managing current runtime transaction state and graph models."""

    def __init__(self):
        self.transactions_df: pd.DataFrame = pd.DataFrame()
        self.graph_service: GraphService = GraphService()
        self.feature_service: FeatureService = FeatureService(self.graph_service)

    def load_transactions(self, df: pd.DataFrame) -> None:
        """
        Update runtime state with new transaction DataFrame.
        Constructs the graph and computes features immediately.
        """
        self.transactions_df = df.copy()

        # Build NetworkX graph
        self.graph_service.build_graph(self.transactions_df)

        # Extract behavioral, temporal, and graph features
        self.feature_service.extract_features(self.transactions_df)

        logger.info(
            f"State updated: {len(self.transactions_df)} transactions, "
            f"{self.graph_service.graph.number_of_nodes()} nodes, "
            f"{len(self.feature_service.user_features)} user feature records."
        )

    def get_transaction_summary(self) -> TransactionSummaryResponse:
        """Compute statistical transaction summary."""
        df = self.transactions_df

        if df.empty:
            return TransactionSummaryResponse(
                transactions=0,
                users=0,
                total_amount=0.0,
                average_amount=0.0,
                min_amount=0.0,
                max_amount=0.0,
                time_range=TimeRange(start=None, end=None),
            )

        unique_users = len(
            set(df["sender_id"].unique()).union(set(df["receiver_id"].unique()))
        )

        earliest = df["timestamp"].min().to_pydatetime() if pd.notna(df["timestamp"].min()) else None
        latest = df["timestamp"].max().to_pydatetime() if pd.notna(df["timestamp"].max()) else None

        return TransactionSummaryResponse(
            transactions=len(df),
            users=unique_users,
            total_amount=round(float(df["amount"].sum()), 2),
            average_amount=round(float(df["amount"].mean()), 2),
            min_amount=round(float(df["amount"].min()), 2),
            max_amount=round(float(df["amount"].max()), 2),
            time_range=TimeRange(start=earliest, end=latest),
        )

    def get_graph_summary(self) -> GraphSummaryResponse:
        """Compute structural graph summary."""
        summary = self.graph_service.get_graph_summary()
        return GraphSummaryResponse(**summary)

    def get_user_features(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> UserAnalyticsResponse:
        """Retrieve computed user features with pagination and filtering."""
        all_features = self.feature_service.user_features

        if user_id:
            user_feat = all_features.get(user_id)
            items = [user_feat] if user_feat else []
            return UserAnalyticsResponse(
                total_users=1 if user_feat else 0,
                limit=limit,
                offset=0,
                users=items,
            )

        all_items = list(all_features.values())
        paginated_items = all_items[offset : offset + limit]

        return UserAnalyticsResponse(
            total_users=len(all_items),
            limit=limit,
            offset=offset,
            users=paginated_items,
        )

    def get_feature_matrix(self) -> Tuple[List[str], np.ndarray, List[str]]:
        """Export the feature matrix for ML modeling (delegates to FeatureService)."""
        return self.feature_service.get_feature_matrix()

    def clear(self) -> None:
        """Reset state (useful for tests)."""
        self.transactions_df = pd.DataFrame()
        self.graph_service = GraphService()
        self.feature_service = FeatureService(self.graph_service)
