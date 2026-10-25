"""Versioned in-memory frame cache for exact intervention recomputation.

This path avoids rebuilding the same timestamp-converted base DataFrame for each
omission. Graph construction, NetworkX centrality, and canonical features remain
the reference implementations; this is an exact preparation optimization, not
an incremental graph algorithm.
"""
from collections import OrderedDict
import networkx as nx
import numpy as np
from ...services.graph_service import GraphService
from ...services.feature_service import FeatureService, CANONICAL_TRANSFER_FEATURES
from ...services.research_protocol import canonical, sha

VERSION = "indexed-history-frame-v1"
GRAPH_VERSION = "graph-service-directed-weighted-v1"
FEATURE_SCHEMA = tuple(CANONICAL_TRANSFER_FEATURES)


class IndexedHistoryFrames:
    """Deterministic, bounded per-history frame cache with complete cache identity."""
    def __init__(self, history, seed=42, max_entries=32):
        self.history = history
        self.seed = int(seed)
        self.max_entries = int(max_entries)
        if self.max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._base = history.frame()
        self._frames = OrderedDict()

    def identity(self, omitted):
        omitted = tuple(sorted(omitted))
        return sha(canonical({
            "method": VERSION,
            "dataset_sha256": self.history.dataset_sha256,
            "history_sha256": self.history.history_sha256,
            "cutoff": self.history.cutoff,
            "time_kind": self.history.time_kind,
            "account_universe": self.history.universe,
            "graph_construction_version": GRAPH_VERSION,
            "intervention_ids": omitted,
            "feature_schema": FEATURE_SCHEMA,
            "random_seed": self.seed,
        }))

    def frame(self, omitted=()):
        omitted = tuple(omitted)
        if len(set(omitted)) != len(omitted) or not set(omitted) <= {e.transaction_id for e in self.history.events}:
            raise ValueError("Omission must name unique eligible transaction IDs.")
        key = self.identity(omitted)
        if key in self._frames:
            self._frames.move_to_end(key)
            return self._frames[key].copy(deep=True)
        result = self._base.loc[~self._base.transaction_id.isin(omitted)].reset_index(drop=True).copy(deep=True)
        expected = [e.transaction_id for e in self.history.events if e.transaction_id not in set(omitted)]
        if result.transaction_id.tolist() != expected:
            raise RuntimeError("Cached-frame row order or membership mismatch.")
        self._frames[key] = result
        if len(self._frames) > self.max_entries:
            self._frames.popitem(last=False)
        return result.copy(deep=True)


def recompute_optimized(history, omitted=(), max_nodes=10000, frames=None):
    """Exact feature recomputation using cached timestamp conversion and row indexing."""
    if len(history.universe) > max_nodes:
        raise ValueError("Reference node limit exceeded; explicitly increase the measured-workload limit.")
    frames = frames or IndexedHistoryFrames(history)
    if frames.history is not history:
        raise ValueError("Frame cache belongs to a different History object.")
    frame = frames.frame(omitted)
    graph = GraphService()
    graph.build_graph(frame)
    missing = set(history.universe) - set(graph.graph)
    if missing:
        graph.graph.add_nodes_from(sorted(missing))
        graph._betweenness_cache = None
        graph._structural_features_cache = None
        graph._egonet_features_cache = None
    graph.compute_betweenness_centrality()
    if graph._betweenness_cache is None:
        raise RuntimeError("Centrality failed; legacy zero fallback cannot certify an intervention.")
    service = FeatureService(graph)
    service.extract_features(frame)
    ids, matrix, names = service.get_feature_matrix()
    if names[:19] != CANONICAL_TRANSFER_FEATURES:
        raise RuntimeError("Canonical feature schema changed.")
    vectors = {u: [0.0] * 19 for u in history.universe}
    vectors.update({u: matrix[i, :19].astype(float).tolist() for i, u in enumerate(ids)})
    if not all(np.isfinite(v).all() for v in vectors.values()):
        raise ValueError("Nonfinite intervention features.")
    n = len(history.universe)
    mode = {"mode": VERSION, "centrality": "exact" if n <= 2000 else "sampled",
            "k": None if n <= 2000 else (100 if n > 50000 else 500), "seed": 42,
            "node_order": list(graph.graph), "isolated_accounts": sorted(missing),
            "cache_key": frames.identity(omitted)}
    return vectors, mode


def exact_component_centrality(graph):
    """Exact directed normalized betweenness via weak components for n<=2000.

    Cross-component directed paths do not exist. Compute unnormalized within-
    component dependencies, then apply NetworkX's *global directed* scale
    1/((n-1)(n-2)); local component normalization would be incorrect.
    """
    n = graph.number_of_nodes()
    if n > 2000:
        raise ValueError("Component exact path is disabled where GraphFin uses sampled centrality.")
    result = {u: 0.0 for u in graph}
    if n <= 2:
        return result
    scale = 1.0 / ((n-1)*(n-2))
    for nodes in nx.weakly_connected_components(graph):
        component = graph.subgraph(nodes)
        raw = nx.betweenness_centrality(component, normalized=False, weight=None)
        for u, value in raw.items():
            result[u] = round(float(value)*scale, 6)
    return result


def recompute_component_optimized(history, omitted=(), max_nodes=10000, frames=None):
    """Experimental exact-component path, with sampled graphs falling back unchanged."""
    if len(history.universe) > max_nodes:
        raise ValueError("Reference node limit exceeded; explicitly increase the measured-workload limit.")
    if len(history.universe) > 2000:
        return recompute_optimized(history, omitted, max_nodes, frames)
    frames = frames or IndexedHistoryFrames(history)
    if frames.history is not history:
        raise ValueError("Frame cache belongs to a different History object.")
    frame = frames.frame(omitted)
    graph = GraphService()
    # Suppress the eager global call during construction; immediately install
    # mathematically equivalent global-normalized exact component results.
    graph.compute_betweenness_centrality = lambda *args, **kwargs: {}
    graph.build_graph(frame)
    graph.compute_betweenness_centrality = GraphService.compute_betweenness_centrality.__get__(graph, GraphService)
    missing = set(history.universe) - set(graph.graph)
    if missing:
        graph.graph.add_nodes_from(sorted(missing))
    graph._betweenness_cache = exact_component_centrality(graph.graph)
    service = FeatureService(graph)
    service.extract_features(frame)
    ids, matrix, names = service.get_feature_matrix()
    if names[:19] != CANONICAL_TRANSFER_FEATURES:
        raise RuntimeError("Canonical feature schema changed.")
    vectors = {u: [0.0] * 19 for u in history.universe}
    vectors.update({u: matrix[i, :19].astype(float).tolist() for i, u in enumerate(ids)})
    if not all(np.isfinite(v).all() for v in vectors.values()):
        raise ValueError("Nonfinite intervention features.")
    return vectors, {"mode": "weak-component-exact-v1", "centrality": "exact",
        "normalization": "global-directed-networkx-normalizer", "seed": None,
        "node_order": list(graph.graph), "isolated_accounts": sorted(missing),
        "cache_key": frames.identity(omitted)}
