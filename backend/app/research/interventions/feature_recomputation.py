"""Global correctness reference, with GraphFin's existing seeded centrality policy."""
import numpy as np
from ...services.graph_service import GraphService
from ...services.feature_service import FeatureService, CANONICAL_TRANSFER_FEATURES


def recompute(history, omitted=(), max_nodes=10000):
    if len(history.universe) > max_nodes:
        raise ValueError("Reference node limit exceeded; explicitly increase the measured-workload limit.")
    frame = history.frame(omitted)
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
    assert names[:19] == CANONICAL_TRANSFER_FEATURES
    # An isolated account has zero structural/behavioral/temporal evidence.
    vectors = {u: [0.0] * 19 for u in history.universe}
    vectors.update({u: matrix[i, :19].astype(float).tolist() for i, u in enumerate(ids)})
    if not all(np.isfinite(v).all() for v in vectors.values()):
        raise ValueError("Nonfinite intervention features.")
    n = len(history.universe)
    mode = {"mode": "global-reference", "centrality": "exact" if n <= 2000 else "sampled",
            "k": None if n <= 2000 else (100 if n > 50000 else 500), "seed": 42,
            "node_order": list(graph.graph), "isolated_accounts": sorted(missing)}
    return vectors, mode
