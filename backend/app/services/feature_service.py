"""
Feature Engineering Service.
Calculates behavioral, temporal, and fused graph features for financial entities.
Prepares clean numerical feature matrices for downstream anomaly detection models.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from ..core.logging import get_logger
from ..schemas.analytics import UserFeatures
from .graph_service import GraphService

logger = get_logger(__name__)

FEATURE_NAMES: List[str] = [
    "in_degree",
    "out_degree",
    "total_degree",
    "weighted_in_degree",
    "weighted_out_degree",
    "betweenness_centrality",
    "transaction_count",
    "total_sent",
    "total_received",
    "net_flow",
    "average_transaction_amount",
    "maximum_transaction_amount",
    "unique_receivers",
    "unique_senders",
    "transactions_per_day",
    "transactions_per_week",
    "average_time_between_transactions",
    "minimum_time_between_transactions",
    "maximum_time_between_transactions",
]


class FeatureService:
    """Service to extract structural, behavioral, and temporal features per entity."""

    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service
        self.user_features: Dict[str, UserFeatures] = {}

    def extract_features(self, transactions_df: pd.DataFrame) -> Dict[str, UserFeatures]:
        """
        Compute combined structural, behavioral, and temporal features for all users.
        """
        if transactions_df.empty:
            self.user_features = {}
            return self.user_features

        # Ensure datetime dtype
        if not pd.api.types.is_datetime64_any_dtype(transactions_df["timestamp"]):
            transactions_df["timestamp"] = pd.to_datetime(transactions_df["timestamp"])

        # 1. Structural features from the Graph Service
        structural_features = self.graph_service.get_all_structural_features()

        # All unique users across senders and receivers
        all_users = set(transactions_df["sender_id"].unique()).union(
            set(transactions_df["receiver_id"].unique())
        )

        logger.info(f"Extracting features for {len(all_users)} unique users...")

        # Pre-group transactions for efficient feature aggregation
        sent_grouped = transactions_df.groupby("sender_id")
        recv_grouped = transactions_df.groupby("receiver_id")

        features_dict: Dict[str, UserFeatures] = {}

        sorted_users = sorted(all_users, key=str)
        for user_id in sorted_users:
            user_str = str(user_id)

            # --- Behavioral Features ---
            # Sent aggregations
            if user_id in sent_grouped.groups:
                sent_df = sent_grouped.get_group(user_id)
                total_sent = float(sent_df["amount"].sum())
                unique_receivers = int(sent_df["receiver_id"].nunique())
            else:
                sent_df = pd.DataFrame()
                total_sent = 0.0
                unique_receivers = 0

            # Received aggregations
            if user_id in recv_grouped.groups:
                recv_df = recv_grouped.get_group(user_id)
                total_received = float(recv_df["amount"].sum())
                unique_senders = int(recv_df["sender_id"].nunique())
            else:
                recv_df = pd.DataFrame()
                total_received = 0.0
                unique_senders = 0

            # Combined user transactions
            if not sent_df.empty and not recv_df.empty:
                user_tx_df = pd.concat([sent_df, recv_df]).drop_duplicates(subset=["transaction_id"])
            elif not sent_df.empty:
                user_tx_df = sent_df
            else:
                user_tx_df = recv_df

            tx_count = len(user_tx_df)
            avg_amount = float(user_tx_df["amount"].mean()) if tx_count > 0 else 0.0
            max_amount = float(user_tx_df["amount"].max()) if tx_count > 0 else 0.0
            net_flow = total_received - total_sent

            # --- Temporal Features ---
            sorted_tx = user_tx_df.sort_values("timestamp")
            timestamps = sorted_tx["timestamp"].tolist()

            if tx_count <= 1:
                avg_time_between = 0.0
                min_time_between = 0.0
                max_time_between = 0.0
                tx_per_day = 1.0
                tx_per_week = 7.0
            else:
                deltas = [
                    (timestamps[i] - timestamps[i - 1]).total_seconds()
                    for i in range(1, len(timestamps))
                ]
                avg_time_between = float(np.mean(deltas))
                min_time_between = float(np.min(deltas))
                max_time_between = float(np.max(deltas))

                total_time_seconds = (timestamps[-1] - timestamps[0]).total_seconds()
                # Use at least 1 day as the divisor to prevent artificial explosion
                days_span = max(1.0, total_time_seconds / 86400.0)
                tx_per_day = float(tx_count / days_span)
                tx_per_week = float(tx_per_day * 7.0)

            # --- Structural / Graph Features ---
            struct = structural_features.get(user_str, {
                "in_degree": 0,
                "out_degree": 0,
                "total_degree": 0,
                "weighted_in_degree": 0.0,
                "weighted_out_degree": 0.0,
                "betweenness_centrality": 0.0,
            })

            # Vector ready for ML (Isolation Forest)
            feature_vector = [
                float(struct["in_degree"]),
                float(struct["out_degree"]),
                float(struct["total_degree"]),
                float(struct["weighted_in_degree"]),
                float(struct["weighted_out_degree"]),
                float(struct["betweenness_centrality"]),
                float(tx_count),
                float(round(total_sent, 2)),
                float(round(total_received, 2)),
                float(round(net_flow, 2)),
                float(round(avg_amount, 2)),
                float(round(max_amount, 2)),
                float(unique_receivers),
                float(unique_senders),
                float(round(tx_per_day, 4)),
                float(round(tx_per_week, 4)),
                float(round(avg_time_between, 2)),
                float(round(min_time_between, 2)),
                float(round(max_time_between, 2)),
            ]

            features_dict[user_str] = UserFeatures(
                user_id=user_str,
                in_degree=struct["in_degree"],
                out_degree=struct["out_degree"],
                total_degree=struct["total_degree"],
                weighted_in_degree=struct["weighted_in_degree"],
                weighted_out_degree=struct["weighted_out_degree"],
                betweenness_centrality=struct["betweenness_centrality"],
                transaction_count=tx_count,
                total_sent=round(total_sent, 2),
                total_received=round(total_received, 2),
                net_flow=round(net_flow, 2),
                average_transaction_amount=round(avg_amount, 2),
                maximum_transaction_amount=round(max_amount, 2),
                unique_receivers=unique_receivers,
                unique_senders=unique_senders,
                transactions_per_day=round(tx_per_day, 4),
                transactions_per_week=round(tx_per_week, 4),
                average_time_between_transactions=round(avg_time_between, 2),
                minimum_time_between_transactions=round(min_time_between, 2),
                maximum_time_between_transactions=round(max_time_between, 2),
                feature_vector=feature_vector,
            )

        self.user_features = features_dict
        logger.info(f"Feature extraction complete for {len(features_dict)} users.")
        return self.user_features

    def get_feature_matrix(self) -> Tuple[List[str], np.ndarray, List[str]]:
        """
        Export the feature matrix for ML modeling (e.g., Isolation Forest).

        :return: (user_ids, 2D numpy array of features, feature_names)
        """
        if not self.user_features:
            return [], np.empty((0, len(FEATURE_NAMES)), dtype=np.float32), FEATURE_NAMES

        user_ids = sorted(self.user_features.keys())
        matrix = np.array(
            [self.user_features[u].feature_vector for u in user_ids],
            dtype=np.float32,
        )

        # Defensive check: ensure no NaN or infinite values can reach the ML layer
        if np.isnan(matrix).any() or np.isinf(matrix).any():
            matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)

        return user_ids, matrix, FEATURE_NAMES
