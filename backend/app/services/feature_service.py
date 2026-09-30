"""
Feature Engineering Service.
Calculates behavioral, temporal, structural graph, and reduced-egonet features for financial entities.
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
    "egonet_node_count",
    "egonet_edge_count",
    "egonet_density",
    "circular_flow_indicator",
]

GRAPH_FEATURES: List[str] = FEATURE_NAMES[:6]
BEHAVIORAL_FEATURES: List[str] = FEATURE_NAMES[6:14]
TEMPORAL_FEATURES: List[str] = FEATURE_NAMES[14:19]
EGONET_FEATURES: List[str] = FEATURE_NAMES[19:23]
CANONICAL_TRANSFER_FEATURES: List[str] = FEATURE_NAMES[:19]

# Forbidden dataset-specific leakage columns that must never exist in features
FORBIDDEN_LEAKAGE_FEATURES: set = {
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFlaggedFraud",
    "type",
    "step",
}


def validate_19_feature_schema(feature_names: List[str]) -> bool:
    """
    Explicitly validate the canonical 19-feature schema order, names, and leakage safety.
    Fails loudly if schema order or names deviate, or if forbidden dataset-specific fields are present.
    """
    if len(feature_names) < 19:
        raise ValueError(
            f"Feature schema validation failed: Expected at least 19 canonical features, got {len(feature_names)}."
        )

    extracted_19 = feature_names[:19]
    if extracted_19 != CANONICAL_TRANSFER_FEATURES:
        raise ValueError(
            f"Feature schema validation failed! Feature names/order mismatch:\n"
            f"Expected: {CANONICAL_TRANSFER_FEATURES}\n"
            f"Actual  : {extracted_19}"
        )

    for fn in feature_names:
        if fn in FORBIDDEN_LEAKAGE_FEATURES:
            raise ValueError(
                f"Feature schema validation failed! Detected dataset-specific leakage feature: '{fn}'"
            )

    return True


class FeatureService:
    """Service to extract structural, behavioral, temporal, and egonet features per entity."""

    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service
        self.user_features: Dict[str, UserFeatures] = {}
        self._feature_matrix_cache: Optional[Tuple[List[str], np.ndarray, List[str]]] = None
        # Validate canonical schema on instantiation
        validate_19_feature_schema(FEATURE_NAMES)


    def extract_features(self, transactions_df: pd.DataFrame) -> Dict[str, UserFeatures]:
        """
        Compute combined structural, behavioral, temporal, and egonet features for all users.
        Runs once at dataset ingest and caches the results and feature matrix.
        """
        if transactions_df.empty:
            self.user_features = {}
            self._feature_matrix_cache = ([], np.empty((0, len(FEATURE_NAMES)), dtype=np.float32), FEATURE_NAMES)
            return self.user_features

        # Ensure datetime dtype
        df = transactions_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # 1. Structural & Egonet features from the Graph Service
        structural_features = self.graph_service.get_all_structural_features()
        egonet_features = self.graph_service.get_all_egonet_features()

        all_users = set(df["sender_id"].astype(str).unique()).union(
            set(df["receiver_id"].astype(str).unique())
        )

        logger.info(f"Extracting features for {len(all_users)} unique users...")

        df["sender_str"] = df["sender_id"].astype(str)
        df["receiver_str"] = df["receiver_id"].astype(str)

        # Vectorized Behavioral Aggregations
        sent_stats = df.groupby("sender_str").agg(
            total_sent=("amount", "sum"),
            unique_receivers=("receiver_str", "nunique"),
            sent_count=("amount", "count"),
            sent_max=("amount", "max"),
        )

        recv_stats = df.groupby("receiver_str").agg(
            total_received=("amount", "sum"),
            unique_senders=("sender_str", "nunique"),
            recv_count=("amount", "count"),
            recv_max=("amount", "max"),
        )

        # Vectorized Temporal Aggregations
        # Combine user transaction timestamps for time deltas
        sender_tx = df[["sender_str", "timestamp", "amount"]].rename(columns={"sender_str": "user_id"})
        receiver_tx = df[["receiver_str", "timestamp", "amount"]].rename(columns={"receiver_str": "user_id"})
        user_tx = pd.concat([sender_tx, receiver_tx], ignore_index=True)
        user_tx = user_tx.sort_values(["user_id", "timestamp"])

        # Compute time delta (seconds) between successive transactions for each user
        user_tx["prev_ts"] = user_tx.groupby("user_id")["timestamp"].shift(1)
        user_tx["delta"] = (user_tx["timestamp"] - user_tx["prev_ts"]).dt.total_seconds()

        temp_stats = user_tx.groupby("user_id").agg(
            tx_count=("timestamp", "count"),
            min_ts=("timestamp", "min"),
            max_ts=("timestamp", "max"),
            avg_amount=("amount", "mean"),
            max_amount=("amount", "max"),
            avg_delta=("delta", "mean"),
            min_delta=("delta", "min"),
            max_delta=("delta", "max"),
        )

        sorted_users = sorted(list(all_users), key=str)

        # Vectorized DataFrame construction across all users
        u_df = pd.DataFrame(index=sorted_users)
        u_df["total_sent"] = sent_stats["total_sent"].reindex(sorted_users).fillna(0.0)
        u_df["unique_receivers"] = sent_stats["unique_receivers"].reindex(sorted_users).fillna(0).astype(int)
        u_df["total_received"] = recv_stats["total_received"].reindex(sorted_users).fillna(0.0)
        u_df["unique_senders"] = recv_stats["unique_senders"].reindex(sorted_users).fillna(0).astype(int)

        u_df["tx_count"] = temp_stats["tx_count"].reindex(sorted_users).fillna(0).astype(int)
        u_df["avg_amount"] = temp_stats["avg_amount"].reindex(sorted_users).fillna(0.0)
        u_df["max_amount"] = temp_stats["max_amount"].reindex(sorted_users).fillna(0.0)
        u_df["avg_delta"] = temp_stats["avg_delta"].reindex(sorted_users).fillna(0.0)
        u_df["min_delta"] = temp_stats["min_delta"].reindex(sorted_users).fillna(0.0)
        u_df["max_delta"] = temp_stats["max_delta"].reindex(sorted_users).fillna(0.0)

        min_ts = temp_stats["min_ts"].reindex(sorted_users)
        max_ts = temp_stats["max_ts"].reindex(sorted_users)
        time_span_days = ((max_ts - min_ts).dt.total_seconds() / 86400.0).clip(lower=1.0).fillna(1.0)

        u_df["tx_per_day"] = np.where(u_df["tx_count"] > 1, u_df["tx_count"] / time_span_days, np.where(u_df["tx_count"] == 1, 1.0, 0.0))
        u_df["tx_per_week"] = u_df["tx_per_day"] * 7.0
        u_df["net_flow"] = u_df["total_received"] - u_df["total_sent"]

        # Structural & Egonet
        struct_df = pd.DataFrame.from_dict(structural_features, orient="index").reindex(sorted_users).fillna(0)
        ego_df = pd.DataFrame.from_dict(egonet_features, orient="index").reindex(sorted_users).fillna(0)

        for col in ["in_degree", "out_degree", "total_degree"]:
            if col in struct_df.columns:
                struct_df[col] = struct_df[col].astype(int)

        # Vectorized Feature Matrix Construction
        matrix = np.column_stack([
            struct_df.get("in_degree", pd.Series(0, index=sorted_users)).reindex(sorted_users).fillna(0).values,
            struct_df.get("out_degree", pd.Series(0, index=sorted_users)).reindex(sorted_users).fillna(0).values,
            struct_df.get("total_degree", pd.Series(0, index=sorted_users)).reindex(sorted_users).fillna(0).values,
            struct_df.get("weighted_in_degree", pd.Series(0.0, index=sorted_users)).reindex(sorted_users).fillna(0.0).round(2).values,
            struct_df.get("weighted_out_degree", pd.Series(0.0, index=sorted_users)).reindex(sorted_users).fillna(0.0).round(2).values,
            struct_df.get("betweenness_centrality", pd.Series(0.0, index=sorted_users)).reindex(sorted_users).fillna(0.0).values,
            u_df["tx_count"].values,
            u_df["total_sent"].round(2).values,
            u_df["total_received"].round(2).values,
            u_df["net_flow"].round(2).values,
            u_df["avg_amount"].round(2).values,
            u_df["max_amount"].round(2).values,
            u_df["unique_receivers"].values,
            u_df["unique_senders"].values,
            u_df["tx_per_day"].round(4).values,
            u_df["tx_per_week"].round(4).values,
            np.where(u_df["tx_count"] > 1, u_df["avg_delta"].round(2), 0.0),
            np.where(u_df["tx_count"] > 1, u_df["min_delta"].round(2), 0.0),
            np.where(u_df["tx_count"] > 1, u_df["max_delta"].round(2), 0.0),
            ego_df.get("egonet_node_count", pd.Series(0.0, index=sorted_users)).reindex(sorted_users).fillna(0.0).values,
            ego_df.get("egonet_edge_count", pd.Series(0.0, index=sorted_users)).reindex(sorted_users).fillna(0.0).values,
            ego_df.get("egonet_density", pd.Series(0.0, index=sorted_users)).reindex(sorted_users).fillna(0.0).round(6).values,
            ego_df.get("circular_flow_indicator", pd.Series(0.0, index=sorted_users)).reindex(sorted_users).fillna(0.0).round(6).values,
        ]).astype(np.float32)

        matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
        self._feature_matrix_cache = (sorted_users, matrix, FEATURE_NAMES)

        class LazyUserFeaturesDict(dict):
            def __init__(self, u_ids, mat):
                super().__init__()
                self.user_ids = u_ids
                self.user_idx_map = {uid: i for i, uid in enumerate(u_ids)}
                self.matrix = mat
                self._cache = {}

            def __len__(self):
                return len(self.user_ids)

            def __contains__(self, key):
                return str(key) in self.user_idx_map

            def keys(self):
                return self.user_ids

            def __getitem__(self, key):
                key_str = str(key)
                if key_str in self._cache:
                    return self._cache[key_str]
                if key_str not in self.user_idx_map:
                    raise KeyError(key_str)
                idx = self.user_idx_map[key_str]
                row = self.matrix[idx]
                feat_vec = [float(x) for x in row]
                uf = UserFeatures(
                    user_id=key_str,
                    in_degree=int(row[0]),
                    out_degree=int(row[1]),
                    total_degree=int(row[2]),
                    weighted_in_degree=float(row[3]),
                    weighted_out_degree=float(row[4]),
                    betweenness_centrality=float(row[5]),
                    transaction_count=int(row[6]),
                    total_sent=float(row[7]),
                    total_received=float(row[8]),
                    net_flow=float(row[9]),
                    average_transaction_amount=float(row[10]),
                    maximum_transaction_amount=float(row[11]),
                    unique_receivers=int(row[12]),
                    unique_senders=int(row[13]),
                    transactions_per_day=float(row[14]),
                    transactions_per_week=float(row[15]),
                    average_time_between_transactions=float(row[16]),
                    minimum_time_between_transactions=float(row[17]),
                    maximum_time_between_transactions=float(row[18]),
                    egonet_node_count=float(row[19]),
                    egonet_edge_count=float(row[20]),
                    egonet_density=float(row[21]),
                    circular_flow_indicator=float(row[22]),
                    feature_vector=feat_vec,
                )
                self._cache[key_str] = uf
                return uf

            def get(self, key, default=None):
                if str(key) in self:
                    return self[str(key)]
                return default

            def values(self):
                return [self[u] for u in self.user_ids]

            def items(self):
                return [(u, self[u]) for u in self.user_ids]

        self.user_features = LazyUserFeaturesDict(sorted_users, matrix)
        logger.info(f"Feature extraction complete for {len(sorted_users)} users.")
        return self.user_features

    def get_feature_matrix(self) -> Tuple[List[str], np.ndarray, List[str]]:
        """
        Export the feature matrix for ML modeling (e.g., Isolation Forest).
        Returns cached matrix computed at ingest time.

        :return: (user_ids, 2D numpy array of features, feature_names)
        """
        if self._feature_matrix_cache is not None:
            return self._feature_matrix_cache

        if not self.user_features:
            self._feature_matrix_cache = ([], np.empty((0, len(FEATURE_NAMES)), dtype=np.float32), FEATURE_NAMES)
            return self._feature_matrix_cache

        user_ids = sorted(self.user_features.keys())
        matrix = np.array(
            [self.user_features[u].feature_vector for u in user_ids],
            dtype=np.float32,
        )

        if np.isnan(matrix).any() or np.isinf(matrix).any():
            matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)

        self._feature_matrix_cache = (user_ids, matrix, FEATURE_NAMES)
        return self._feature_matrix_cache

    def get_feature_validation_summary(self) -> List[Dict[str, Any]]:
        """
        Generate feature validation summary table (feature name, mean, std, min, max, % missing).
        Used to sanity-check feature matrix before running experiments.
        """
        user_ids, matrix, feature_names = self.get_feature_matrix()
        if len(user_ids) == 0 or matrix.shape[0] == 0:
            return []

        summary = []
        for j, fname in enumerate(feature_names):
            col = matrix[:, j]
            n_total = len(col)
            n_missing = int(np.isnan(col).sum() + np.isinf(col).sum())
            pct_missing = round((n_missing / n_total * 100.0), 2) if n_total > 0 else 0.0

            summary.append({
                "feature_name": fname,
                "mean": float(round(np.mean(col), 4)),
                "std": float(round(np.std(col), 4)),
                "min": float(round(np.min(col), 4)),
                "max": float(round(np.max(col), 4)),
                "pct_missing": pct_missing,
            })
        return summary
