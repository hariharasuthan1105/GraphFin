"""
Real-Time Streaming Simulation Service.
Replays existing transactions at a controlled rate, periodically rebuilding
the graph and feature matrix, and re-scoring with a pre-trained, read-only
anomaly detection model.

STRICT ARTIFACT ISOLATION:
- Read-only model inference only (.decision_function() / .predict()).
- Never calls model.fit() or retrains.
- Never writes to settings.MODELS_DIR or settings.DATA_DIR / 'results'.
- Simulation runs are completely segregated from official research benchmarks.
"""
import threading
import time
from typing import Any, Dict, List, Optional, Set
import numpy as np
import pandas as pd

from ..core.config import settings
from ..core.exceptions import (
    ModelNotTrainedException,
    NotFoundException,
    ValidationException,
)
from ..core.logging import get_logger
from ..schemas.stream import (
    StreamEdge,
    StreamNode,
    StreamScoredEntity,
    StreamScoringSummary,
    StreamStartRequest,
    StreamStateResponse,
)
from .anomaly_service import anomaly_service, compute_risk_score
from .dataset_registry import dataset_registry
from .feature_service import FeatureService
from .graph_service import GraphService

logger = get_logger(__name__)


class StreamSimulatorService:
    """Service managing background streaming simulation sessions."""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._threads: Dict[str, threading.Thread] = {}

    def start_simulation(
        self, dataset_id: str, request: StreamStartRequest
    ) -> StreamStateResponse:
        """
        Start a background streaming replay simulation for the given dataset_id.
        Raises ValidationException if a simulation is already running for this dataset.
        """
        # 1. Check for active simulation
        existing_session = self._sessions.get(dataset_id)
        if existing_session and existing_session.get("status") == "running":
            thread = self._threads.get(dataset_id)
            if thread and thread.is_alive():
                raise ValidationException(
                    f"A simulation is already actively running for dataset '{dataset_id}'. "
                    "Stop the current simulation before starting a new one."
                )

        # 2. Verify source dataset exists and has transactions
        store = dataset_registry.get(dataset_id)
        if store.transactions_df.empty:
            raise ValidationException(
                f"Cannot start streaming simulation: dataset '{dataset_id}' contains no transactions."
            )

        # 3. Verify trained model exists (READ-ONLY check)
        clean_exp = (request.experiment_label or "default").strip()
        try:
            artifact = anomaly_service._load_artifact(
                dataset_id, clean_exp, request.split_label
            )
        except ModelNotTrainedException:
            raise ModelNotTrainedException(
                f"No trained model found for dataset '{dataset_id}' with experiment '{clean_exp}'. "
                "Train the model first before starting simulation playback."
            )

        if not artifact or ("model" not in artifact and artifact.get("model_type") != "StatisticalBaseline"):
            raise ModelNotTrainedException(
                f"Model artifact for '{clean_exp}' does not contain a valid trained model."
            )

        # 4. Prepare sorted transactions DataFrame
        df = store.transactions_df.copy()
        if "timestamp" in df.columns:
            df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.sort_values(by=["_ts"]).reset_index(drop=True)
            df = df.drop(columns=["_ts"], errors="ignore")
        else:
            df = df.reset_index(drop=True)

        total_tx = len(df)

        # 5. Initialize simulation session state
        session: Dict[str, Any] = {
            "dataset_id": dataset_id,
            "status": "running",
            "current_tick": 0,
            "transactions_revealed": 0,
            "total_transactions": total_tx,
            "current_entity_count": 0,
            "last_rescoring_tick": None,
            "transactions_per_tick": request.transactions_per_tick,
            "tick_interval_seconds": request.tick_interval_seconds,
            "rescoring_interval_ticks": request.rescoring_interval_ticks,
            "experiment_label": clean_exp,
            "split_label": request.split_label,
            "scoring_results": None,
            "newly_flagged_entities": [],
            "graph_nodes": [],
            "graph_edges": [],
            "error": None,
            "stop_requested": False,
            "previous_suspicious_set": set(),
        }
        self._sessions[dataset_id] = session

        # 6. Launch background worker thread
        thread = threading.Thread(
            target=self._run_simulation_thread,
            args=(dataset_id, df, request),
            daemon=True,
            name=f"stream-sim-{dataset_id}",
        )
        self._threads[dataset_id] = thread
        thread.start()

        logger.info(
            f"Started streaming simulation for dataset '{dataset_id}' "
            f"({total_tx} txs, exp='{clean_exp}', {request.transactions_per_tick} tx/tick, "
            f"interval={request.tick_interval_seconds}s, rescore_every={request.rescoring_interval_ticks} ticks)."
        )

        return self.get_state(dataset_id)

    def _run_simulation_thread(
        self, dataset_id: str, df: pd.DataFrame, request: StreamStartRequest
    ) -> None:
        """Background thread executing the incremental replay and periodic re-scoring."""
        total = len(df)

        try:
            while True:
                session = self._sessions.get(dataset_id)
                if not session or session.get("stop_requested"):
                    if session:
                        session["status"] = "stopped"
                    break

                session["current_tick"] += 1
                current_tick = session["current_tick"]
                revealed_count = min(
                    current_tick * request.transactions_per_tick, total
                )
                session["transactions_revealed"] = revealed_count

                # Current transaction window
                df_slice = df.iloc[:revealed_count]
                unique_users = set(df_slice["sender_id"]).union(
                    set(df_slice["receiver_id"])
                )
                session["current_entity_count"] = len(unique_users)

                # Incremental edge aggregation for graph visualizer
                edge_counts = (
                    df_slice.groupby(["sender_id", "receiver_id"])
                    .agg(
                        amount=("amount", "sum"),
                        count=("transaction_id", "count"),
                    )
                    .reset_index()
                )

                # Cap preview edges to top 200 for browser smoothness
                preview_edges = edge_counts.head(200)
                session["graph_edges"] = [
                    StreamEdge(
                        source=str(row["sender_id"]),
                        target=str(row["receiver_id"]),
                        amount=round(float(row["amount"]), 2),
                        transactions=int(row["count"]),
                    ).model_dump()
                    for _, row in preview_edges.iterrows()
                ]

                # Determine if rescoring is scheduled on this tick
                is_rescore_tick = (
                    current_tick % request.rescoring_interval_ticks == 0
                    or revealed_count == total
                )

                if is_rescore_tick:
                    try:
                        self._perform_rescore(
                            dataset_id, session, df_slice, current_tick
                        )
                    except Exception as e:
                        logger.error(
                            f"Error during streaming rescore (dataset '{dataset_id}', tick {current_tick}): {e}",
                            exc_info=True,
                        )
                        session["error"] = f"Rescoring failed: {str(e)}"

                # Check completion
                if revealed_count >= total:
                    session["status"] = "complete"
                    logger.info(
                        f"Streaming simulation completed for dataset '{dataset_id}' at tick {current_tick}."
                    )
                    break

                # Sleep until next tick
                time.sleep(request.tick_interval_seconds)

        except Exception as ex:
            logger.error(
                f"Unhandled error in simulation loop for dataset '{dataset_id}': {ex}",
                exc_info=True,
            )
            session = self._sessions.get(dataset_id)
            if session:
                session["status"] = "error"
                session["error"] = str(ex)

    def _perform_rescore(
        self,
        dataset_id: str,
        session: Dict[str, Any],
        df_slice: pd.DataFrame,
        current_tick: int,
    ) -> None:
        """
        Rebuild graph, compute features, and score with the PRE-TRAINED model in READ-ONLY mode.
        Does NOT fit, refit, or overwrite any model artifact.
        """
        clean_exp = session["experiment_label"]
        split_lbl = session["split_label"]

        # 1. READ-ONLY load of existing model artifact
        artifact = anomaly_service._load_artifact(
            dataset_id, clean_exp, split_lbl
        )
        model_type = artifact.get("model_type", "IsolationForest")

        # 2. Build graph and extract features for current revealed slice
        graph_svc = GraphService()
        graph_svc.build_graph(df_slice)
        feat_svc = FeatureService(graph_svc)
        feat_svc.extract_features(df_slice)
        curr_user_ids, full_matrix, _ = feat_svc.get_feature_matrix()

        if len(curr_user_ids) == 0:
            return

        user_results: List[StreamScoredEntity] = []
        newly_flagged: List[StreamScoredEntity] = []
        prev_suspicious: Set[str] = session.get("previous_suspicious_set", set())
        current_suspicious: Set[str] = set()

        # 3. Model Inference (READ-ONLY)
        if model_type == "IsolationForest":
            model = artifact["model"]
            meta_dict: Dict[str, Any] = artifact["metadata"]
            train_scores: np.ndarray = artifact["train_scores"]
            col_indices: List[int] = artifact["col_indices"]
            trained_features: List[str] = meta_dict["feature_names"]
            feature_stats: Dict[str, Dict[str, float]] = meta_dict["feature_stats"]

            X_sliced = full_matrix[:, col_indices]
            X_clean = np.nan_to_num(X_sliced, nan=0.0, posinf=0.0, neginf=0.0)

            # Strictly decision_function and predict — NEVER fit()
            decision_scores = model.decision_function(X_clean)
            predictions = model.predict(X_clean)

            for i, uid in enumerate(curr_user_ids):
                score = float(decision_scores[i])
                pred = int(predictions[i])
                is_susp = pred == -1
                status = "suspicious" if is_susp else "normal"
                risk = compute_risk_score(score, train_scores)

                user_feat = feat_svc.user_features.get(uid)
                feat_dict = user_feat.features if hasattr(user_feat, "features") else {}
                reasons = anomaly_service._generate_reasons_for_user(
                    feat_dict, feature_stats, trained_features, is_susp
                )

                item = StreamScoredEntity(
                    user_id=uid,
                    raw_score=round(score, 4),
                    prediction=pred,
                    status=status,
                    risk_score=risk,
                    reasons=reasons,
                )
                user_results.append(item)

                if is_susp:
                    current_suspicious.add(uid)
                    if uid not in prev_suspicious:
                        newly_flagged.append(item)

        elif model_type == "StatisticalBaseline":
            meta_dict = artifact["metadata"]
            trained_features = meta_dict["feature_names"]
            feature_stats = meta_dict["feature_stats"]
            z_threshold = artifact.get("z_threshold", 2.0)
            col_indices = artifact.get("col_indices", list(range(len(trained_features))))

            X_sliced = full_matrix[:, col_indices]
            X_clean = np.nan_to_num(X_sliced, nan=0.0, posinf=0.0, neginf=0.0)

            for i, uid in enumerate(curr_user_ids):
                user_vec = X_clean[i, :]
                z_scores = []
                for c_idx, f_name in enumerate(trained_features):
                    f_stat = feature_stats.get(f_name, {})
                    mean = f_stat.get("mean", 0.0)
                    std = f_stat.get("std", 1.0)
                    if std <= 1e-8:
                        z = 0.0
                    else:
                        z = abs(user_vec[c_idx] - mean) / std
                    z_scores.append(z)

                max_z = float(np.max(z_scores)) if len(z_scores) > 0 else 0.0
                is_susp = max_z >= z_threshold
                status = "suspicious" if is_susp else "normal"
                pred = -1 if is_susp else 1
                risk = float(round(min(100.0, (max_z / max(z_threshold * 2, 1.0)) * 100.0), 2))

                user_feat = feat_svc.user_features.get(uid)
                feat_dict = user_feat.features if hasattr(user_feat, "features") else {}
                reasons = anomaly_service._generate_reasons_for_user(
                    feat_dict, feature_stats, trained_features, is_susp
                )

                item = StreamScoredEntity(
                    user_id=uid,
                    raw_score=round(max_z, 4),
                    prediction=pred,
                    status=status,
                    risk_score=risk,
                    reasons=reasons,
                )
                user_results.append(item)

                if is_susp:
                    current_suspicious.add(uid)
                    if uid not in prev_suspicious:
                        newly_flagged.append(item)

        # 4. Update session state
        session["previous_suspicious_set"] = current_suspicious
        session["last_rescoring_tick"] = current_tick

        # Sort users descending by risk score
        user_results.sort(key=lambda u: u.risk_score, reverse=True)

        # Build graph node status map for frontend ForceGraph
        status_map = {u.user_id: (u.status, u.risk_score) for u in user_results}
        node_degrees = dict(graph_svc.graph.degree())
        session["graph_nodes"] = [
            StreamNode(
                id=node_id,
                degree=node_degrees.get(node_id, 1),
                status=status_map.get(node_id, ("normal", 0.0))[0],
                risk_score=status_map.get(node_id, ("normal", 0.0))[1],
            ).model_dump()
            for node_id in list(graph_svc.graph.nodes())[:250]
        ]

        susp_count = len(current_suspicious)
        norm_count = len(curr_user_ids) - susp_count

        session["scoring_results"] = StreamScoringSummary(
            total_users=len(curr_user_ids),
            suspicious_count=susp_count,
            normal_count=norm_count,
            rescore_tick=current_tick,
            users=user_results[:100],  # top 100 highest-risk
        ).model_dump()

        session["newly_flagged_entities"] = [
            e.model_dump() for e in newly_flagged
        ]

    def stop_simulation(self, dataset_id: str) -> StreamStateResponse:
        """Stop an ongoing simulation for dataset_id."""
        session = self._sessions.get(dataset_id)
        if not session:
            raise NotFoundException(
                f"No streaming simulation session found for dataset '{dataset_id}'."
            )

        session["stop_requested"] = True
        session["status"] = "stopped"

        thread = self._threads.get(dataset_id)
        if thread and thread.is_alive():
            thread.join(timeout=0.5)

        logger.info(f"Streaming simulation stopped for dataset '{dataset_id}'.")
        return self.get_state(dataset_id)

    def get_state(self, dataset_id: str) -> StreamStateResponse:
        """Retrieve current simulation state snapshot."""
        session = self._sessions.get(dataset_id)
        if not session:
            # Default idle state
            try:
                store = dataset_registry.get(dataset_id)
                total = len(store.transactions_df)
            except Exception:
                total = 0

            return StreamStateResponse(
                dataset_id=dataset_id,
                status="idle",
                total_transactions=total,
                message="No simulation currently running for this dataset.",
            )

        scoring_dict = session.get("scoring_results")
        scoring_summary = (
            StreamScoringSummary(**scoring_dict) if scoring_dict else None
        )

        newly_flagged = [
            StreamScoredEntity(**e)
            for e in session.get("newly_flagged_entities", [])
        ]
        nodes = [StreamNode(**n) for n in session.get("graph_nodes", [])]
        edges = [StreamEdge(**e) for e in session.get("graph_edges", [])]

        return StreamStateResponse(
            dataset_id=dataset_id,
            status=session.get("status", "idle"),
            current_tick=session.get("current_tick", 0),
            transactions_revealed=session.get("transactions_revealed", 0),
            total_transactions=session.get("total_transactions", 0),
            current_entity_count=session.get("current_entity_count", 0),
            last_rescoring_tick=session.get("last_rescoring_tick"),
            transactions_per_tick=session.get("transactions_per_tick", 50),
            tick_interval_seconds=session.get("tick_interval_seconds", 2.0),
            rescoring_interval_ticks=session.get("rescoring_interval_ticks", 5),
            experiment_label=session.get("experiment_label", "default"),
            scoring_results=scoring_summary,
            newly_flagged_entities=newly_flagged,
            graph_nodes=nodes,
            graph_edges=edges,
            error=session.get("error"),
        )

    def clear(self) -> None:
        """Cancel all running threads and clear sessions (used for test teardown)."""
        for session in self._sessions.values():
            session["stop_requested"] = True
            session["status"] = "stopped"
        for thread in self._threads.values():
            if thread.is_alive():
                thread.join(timeout=0.3)
        self._threads.clear()
        self._sessions.clear()


stream_simulator = StreamSimulatorService()
