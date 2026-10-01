"""
PaySim Exploration Service.
Computes descriptive statistics for the production PaySim 10K slice.
Results are cached after the first computation to avoid redundant Pandas operations.
"""
from typing import Optional
from ..core.logging import get_logger
from ..schemas.exploration import (
    PaySimExplorationResponse,
    ExplorationTransactionStats,
    ExplorationAccountStats,
    ExplorationNetworkStats,
    ExplorationTemporalStats,
    AmountBucket,
    StepCount,
    FraudVsNormal,
    TopAccount,
    FeatureStat,
)

logger = get_logger(__name__)

# Feature group mapping for 19 canonical GraphFin features
_FEATURE_GROUPS = {
    "in_degree": "graph",
    "out_degree": "graph",
    "total_degree": "graph",
    "weighted_in_degree": "graph",
    "weighted_out_degree": "graph",
    "betweenness_centrality": "graph",
    "transaction_count": "behavioral",
    "total_sent": "behavioral",
    "total_received": "behavioral",
    "net_flow": "behavioral",
    "average_transaction_amount": "behavioral",
    "maximum_transaction_amount": "behavioral",
    "unique_receivers": "behavioral",
    "unique_senders": "behavioral",
    "transactions_per_day": "temporal",
    "transactions_per_week": "temporal",
    "average_time_between_transactions": "temporal",
    "minimum_time_between_transactions": "temporal",
    "maximum_time_between_transactions": "temporal",
}

# Amount histogram bucket boundaries (USD)
_AMOUNT_BUCKETS = [
    (0, 1_000, "0–1K"),
    (1_000, 10_000, "1K–10K"),
    (10_000, 50_000, "10K–50K"),
    (50_000, 100_000, "50K–100K"),
    (100_000, 500_000, "100K–500K"),
    (500_000, float("inf"), "500K+"),
]


class PaySimExplorationService:
    """
    Computes and caches the PaySim exploration response.
    Reuses cached graph summary and feature matrix already held in the StateStore.
    Does NOT recompute betweenness centrality.
    """

    def __init__(self):
        self._cache: Optional[PaySimExplorationResponse] = None

    def invalidate(self) -> None:
        """Clear the cached exploration result (e.g. after dataset reload)."""
        self._cache = None

    def compute(self, store, label_registry=None) -> PaySimExplorationResponse:
        """
        Compute or return cached exploration statistics for the PaySim production slice.

        :param store: StateStore for 'paysim' dataset (already loaded).
        :param label_registry: Optional LabelRegistry to read fraud/normal account counts.
        :return: PaySimExplorationResponse
        """
        if self._cache is not None:
            logger.debug("Returning cached PaySim exploration response.")
            return self._cache

        import numpy as np
        import pandas as pd

        logger.info("Computing PaySim exploration statistics (first request, caching result)...")

        df = store.transactions_df.copy()

        # ------------------------------------------------------------------ #
        # 1. Transaction stats
        # ------------------------------------------------------------------ #
        amounts = df["amount"].astype(float)
        tx_stats = ExplorationTransactionStats(
            count=len(df),
            total_amount=round(float(amounts.sum()), 2),
            mean_amount=round(float(amounts.mean()), 2),
            median_amount=round(float(amounts.median()), 2),
            min_amount=round(float(amounts.min()), 2),
            max_amount=round(float(amounts.max()), 2),
        )

        # ------------------------------------------------------------------ #
        # 2. Account stats from label registry
        # ------------------------------------------------------------------ #
        total_accounts = len(store.feature_service.user_features)
        fraud_count = 0
        normal_count = 0

        if label_registry is not None:
            try:
                summary = label_registry.get_summary("paysim")
                fraud_count = summary.positive_count
                normal_count = summary.negative_count
            except Exception:
                pass

        if fraud_count == 0 and normal_count == 0:
            normal_count = total_accounts

        account_stats = ExplorationAccountStats(
            count=total_accounts,
            fraud_involved=fraud_count,
            normal=normal_count,
        )

        # ------------------------------------------------------------------ #
        # 3. Network stats — reuse already-computed graph summary (no recompute)
        # ------------------------------------------------------------------ #
        g_summary = store.graph_service.get_graph_summary()
        network_stats = ExplorationNetworkStats(
            nodes=g_summary.get("nodes", 0),
            edges=g_summary.get("edges", 0),
            density=round(g_summary.get("density", 0.0), 6),
            weakly_connected_components=g_summary.get("weakly_connected_components", 0),
        )

        # ------------------------------------------------------------------ #
        # 4. Temporal stats — use 'step' column if available, else timestamp
        # ------------------------------------------------------------------ #
        min_step = max_step = unique_steps = None
        if "step" in df.columns:
            step_series = df["step"].dropna().astype(int)
            if not step_series.empty:
                min_step = int(step_series.min())
                max_step = int(step_series.max())
                unique_steps = int(step_series.nunique())

        temporal_stats = ExplorationTemporalStats(
            min_step=min_step,
            max_step=max_step,
            unique_steps=unique_steps,
        )

        # ------------------------------------------------------------------ #
        # 5. Amount distribution histogram
        # ------------------------------------------------------------------ #
        amount_dist = []
        for lo, hi, label in _AMOUNT_BUCKETS:
            if hi == float("inf"):
                cnt = int((amounts >= lo).sum())
            else:
                cnt = int(((amounts >= lo) & (amounts < hi)).sum())
            amount_dist.append(AmountBucket(bucket=label, count=cnt))

        # ------------------------------------------------------------------ #
        # 6. Transactions by step (sampled to ≤ 50 points for large steps)
        # ------------------------------------------------------------------ #
        tx_by_step: list[StepCount] = []
        if "step" in df.columns and min_step is not None:
            step_counts = df.groupby("step").size().reset_index(name="count")
            if len(step_counts) > 50:
                step_counts = step_counts.sample(n=50, random_state=42).sort_values("step")
            for _, row in step_counts.iterrows():
                tx_by_step.append(StepCount(step=int(row["step"]), count=int(row["count"])))

        # ------------------------------------------------------------------ #
        # 7. Fraud vs normal
        # ------------------------------------------------------------------ #
        fraud_vs_normal = [
            FraudVsNormal(label="fraud-involved", count=fraud_count),
            FraudVsNormal(label="normal", count=normal_count),
        ]

        # ------------------------------------------------------------------ #
        # 8. Top senders / top receivers (vectorized groupby)
        # ------------------------------------------------------------------ #
        sender_col = "sender_id" if "sender_id" in df.columns else df.columns[0]
        receiver_col = "receiver_id" if "receiver_id" in df.columns else df.columns[1]
        amount_col = "amount"

        sent_stats = (
            df.groupby(sender_col)[amount_col]
            .agg(transaction_count="count", total_amount="sum")
            .sort_values("transaction_count", ascending=False)
            .head(10)
        )
        top_senders = [
            TopAccount(
                account_id=str(idx),
                transaction_count=int(row["transaction_count"]),
                total_amount=round(float(row["total_amount"]), 2),
            )
            for idx, row in sent_stats.iterrows()
        ]

        recv_stats = (
            df.groupby(receiver_col)[amount_col]
            .agg(transaction_count="count", total_amount="sum")
            .sort_values("transaction_count", ascending=False)
            .head(10)
        )
        top_receivers = [
            TopAccount(
                account_id=str(idx),
                transaction_count=int(row["transaction_count"]),
                total_amount=round(float(row["total_amount"]), 2),
            )
            for idx, row in recv_stats.iterrows()
        ]

        # ------------------------------------------------------------------ #
        # 9. Feature summary (19 canonical features from cached feature matrix)
        # ------------------------------------------------------------------ #
        feature_summary: list[FeatureStat] = []
        try:
            user_ids, matrix, feature_names = store.get_feature_matrix()
            n_total = matrix.shape[0]
            for j, fname in enumerate(feature_names[:19]):
                col = matrix[:, j]
                n_missing = int(np.isnan(col).sum() + np.isinf(col).sum())
                pct_missing = round((n_missing / n_total * 100.0), 2) if n_total > 0 else 0.0
                clean_col = col[np.isfinite(col)]
                feature_summary.append(
                    FeatureStat(
                        feature_name=fname,
                        group=_FEATURE_GROUPS.get(fname, "other"),
                        mean=round(float(clean_col.mean()) if len(clean_col) else 0.0, 4),
                        std=round(float(clean_col.std()) if len(clean_col) else 0.0, 4),
                        min=round(float(clean_col.min()) if len(clean_col) else 0.0, 4),
                        max=round(float(clean_col.max()) if len(clean_col) else 0.0, 4),
                        pct_missing=pct_missing,
                    )
                )
        except Exception as e:
            logger.warning(f"Could not compute feature summary: {e}")

        # ------------------------------------------------------------------ #
        # Cache and return
        # ------------------------------------------------------------------ #
        result = PaySimExplorationResponse(
            dataset_id="paysim",
            scope="production_slice",
            status="loaded",
            transactions=tx_stats,
            accounts=account_stats,
            network=network_stats,
            temporal=temporal_stats,
            amount_distribution=amount_dist,
            transactions_by_step=tx_by_step,
            fraud_vs_normal=fraud_vs_normal,
            top_senders=top_senders,
            top_receivers=top_receivers,
            feature_summary=feature_summary,
        )
        self._cache = result
        logger.info("PaySim exploration statistics cached.")
        return result


# Module-level singleton
paysim_exploration_service = PaySimExplorationService()
