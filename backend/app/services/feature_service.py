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



class FeatureService:
    """Service to extract structural, behavioral, temporal, and egonet features per entity."""

    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service
        self.user_features: Dict[str, UserFeatures] = {}
        self._feature_matrix_cache: Optional[Tuple[List[str], np.ndarray, List[str]]] = None

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

        features_dict: Dict[str, UserFeatures] = {}
        for uid in sorted_users:
            u_str = str(uid)
            u_row = u_df.loc[u_str]
            s_row = struct_df.loc[u_str] if u_str in struct_df.index else {}
            e_row = ego_df.loc[u_str] if u_str in ego_df.index else {}

            in_deg = int(s_row.get("in_degree", 0))
            out_deg = int(s_row.get("out_degree", 0))
            tot_deg = int(s_row.get("total_degree", 0))
            w_in_deg = float(round(s_row.get("weighted_in_degree", 0.0), 2))
            w_out_deg = float(round(s_row.get("weighted_out_degree", 0.0), 2))
            bc = float(s_row.get("betweenness_centrality", 0.0))

            tx_cnt = int(u_row["tx_count"])
            tot_s = float(round(u_row["total_sent"], 2))
            tot_r = float(round(u_row["total_received"], 2))
            net_f = float(round(u_row["net_flow"], 2))
            avg_a = float(round(u_row["avg_amount"], 2))
            max_a = float(round(u_row["max_amount"], 2))
            u_rec = int(u_row["unique_receivers"])
            u_snd = int(u_row["unique_senders"])

            t_day = float(round(u_row["tx_per_day"], 4))
            t_wk = float(round(u_row["tx_per_week"], 4))
            avg_t = float(round(u_row["avg_delta"] if tx_cnt > 1 else 0.0, 2))
            min_t = float(round(u_row["min_delta"] if tx_cnt > 1 else 0.0, 2))
            max_t = float(round(u_row["max_delta"] if tx_cnt > 1 else 0.0, 2))

            ego_n = float(e_row.get("egonet_node_count", 0.0))
            ego_e = float(e_row.get("egonet_edge_count", 0.0))
            ego_d = float(round(e_row.get("egonet_density", 0.0), 6))
            circ_f = float(round(e_row.get("circular_flow_indicator", 0.0), 6))

            feat_vec = [
                float(in_deg), float(out_deg), float(tot_deg),
                w_in_deg, w_out_deg, bc,
                float(tx_cnt), tot_s, tot_r, net_f, avg_a, max_a,
                float(u_rec), float(u_snd),
                t_day, t_wk, avg_t, min_t, max_t,
                ego_n, ego_e, ego_d, circ_f,
            ]

            features_dict[u_str] = UserFeatures(
                user_id=u_str,
                in_degree=in_deg,
                out_degree=out_deg,
                total_degree=tot_deg,
                weighted_in_degree=w_in_deg,
                weighted_out_degree=w_out_deg,
                betweenness_centrality=bc,
                transaction_count=tx_cnt,
                total_sent=tot_s,
                total_received=tot_r,
                net_flow=net_f,
                average_transaction_amount=avg_a,
                maximum_transaction_amount=max_a,
                unique_receivers=u_rec,
                unique_senders=u_snd,
                transactions_per_day=t_day,
                transactions_per_week=t_wk,
                average_time_between_transactions=avg_t,
                minimum_time_between_transactions=min_t,
                maximum_time_between_transactions=max_t,
                egonet_node_count=ego_n,
                egonet_edge_count=ego_e,
                egonet_density=ego_d,
                circular_flow_indicator=circ_f,
                feature_vector=feat_vec,
            )

        self.user_features = features_dict
        self._feature_matrix_cache = None
        logger.info(f"Feature extraction complete for {len(features_dict)} users.")
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
