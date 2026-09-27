"""
Graph Construction and Network Metric Calculation Service.
Constructs directed weighted transaction graphs using NetworkX and computes structural metrics.
"""
from typing import Any, Dict, List, Optional
import networkx as nx
import pandas as pd
from ..core.exceptions import GraphProcessingException
from ..core.logging import get_logger

logger = get_logger(__name__)


class GraphService:
    """Service for constructing and analyzing transaction graphs."""

    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()
        self._betweenness_cache: Optional[Dict[str, float]] = None
        self._structural_features_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._egonet_features_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._summary_cache: Optional[Dict[str, Any]] = None

    def build_graph(self, transactions_df: pd.DataFrame) -> nx.DiGraph:
        """
        Construct a directed weighted graph from validated transaction DataFrame.

        - Node: User/Account ID
        - Directed Edge: (sender_id -> receiver_id)
        - Edge Weight: Cumulative monetary amount transferred
        - Edge Attributes: transaction_count, transaction_ids
        """
        if transactions_df.empty:
            self.graph = nx.DiGraph()
            self._betweenness_cache = {}
            self._structural_features_cache = {}
            self._egonet_features_cache = {}
            self._summary_cache = None
            return self.graph

        G = nx.DiGraph()

        try:
            senders = transactions_df["sender_id"].astype(str).tolist()
            receivers = transactions_df["receiver_id"].astype(str).tolist()
            amounts = transactions_df["amount"].astype(float).tolist()
            tx_ids = transactions_df["transaction_id"].astype(str).tolist()

            for u, v, amount, tx_id in zip(senders, receivers, amounts, tx_ids):
                if G.has_edge(u, v):
                    edge = G[u][v]
                    edge["weight"] += amount
                    edge["count"] += 1
                    edge["transactions"].append(tx_id)
                else:
                    G.add_edge(u, v, weight=amount, count=1, transactions=[tx_id])

            self.graph = G
            # Invalidate and precompute centrality at ingest time
            self._betweenness_cache = None
            self._structural_features_cache = None
            self._egonet_features_cache = None
            self._summary_cache = None
            self.compute_betweenness_centrality()

            logger.info(
                f"Graph constructed successfully: {G.number_of_nodes()} nodes, "
                f"{G.number_of_edges()} edges."
            )
            return self.graph

        except Exception as e:
            logger.error(f"Error during graph construction: {str(e)}", exc_info=True)
            raise GraphProcessingException(f"Failed to build transaction graph: {str(e)}")

    def compute_betweenness_centrality(self, sample_threshold: int = 2000) -> Dict[str, float]:
        """
        Compute betweenness centrality for all nodes.
        Uses exact computation for graphs <= sample_threshold nodes,
        and sampled approximation for very large graphs for latency safety.
        """
        if self._betweenness_cache is not None:
            return self._betweenness_cache

        if self.graph.number_of_nodes() == 0:
            self._betweenness_cache = {}
            return self._betweenness_cache

        node_count = self.graph.number_of_nodes()
        try:
            if node_count > sample_threshold:
                k = min(100 if node_count > 50000 else 500, node_count)
                logger.info(f"Large graph ({node_count} nodes): approximating betweenness with k={k}")
                centrality = nx.betweenness_centrality(self.graph, k=k, normalized=True, seed=42)
            else:
                centrality = nx.betweenness_centrality(self.graph, normalized=True)

            self._betweenness_cache = {
                node: round(float(score), 6) for node, score in centrality.items()
            }
            return self._betweenness_cache
        except Exception as e:
            logger.error(f"Error calculating betweenness centrality: {str(e)}")
            # Fallback to zeros on non-fatal error
            return {node: 0.0 for node in self.graph.nodes()}

    def get_node_structural_features(self, node: str) -> Dict[str, Any]:
        """Calculate all structural metrics for a given node."""
        if not self.graph.has_node(node):
            return {
                "in_degree": 0,
                "out_degree": 0,
                "total_degree": 0,
                "weighted_in_degree": 0.0,
                "weighted_out_degree": 0.0,
                "betweenness_centrality": 0.0,
            }

        centrality = self.compute_betweenness_centrality()

        in_deg = int(self.graph.in_degree(node))
        out_deg = int(self.graph.out_degree(node))
        w_in_deg = round(float(self.graph.in_degree(node, weight="weight")), 2)
        w_out_deg = round(float(self.graph.out_degree(node, weight="weight")), 2)
        bc = centrality.get(node, 0.0)

        return {
            "in_degree": in_deg,
            "out_degree": out_deg,
            "total_degree": in_deg + out_deg,
            "weighted_in_degree": w_in_deg,
            "weighted_out_degree": w_out_deg,
            "betweenness_centrality": bc,
        }

    def get_all_structural_features(self) -> Dict[str, Dict[str, Any]]:
        """Calculate structural features for all nodes in the graph efficiently."""
        if self._structural_features_cache is not None:
            return self._structural_features_cache

        G = self.graph
        centrality = self.compute_betweenness_centrality()

        in_deg_dict = dict(G.in_degree())
        out_deg_dict = dict(G.out_degree())
        w_in_deg_dict = dict(G.in_degree(weight="weight"))
        w_out_deg_dict = dict(G.out_degree(weight="weight"))

        features = {}
        for node in G.nodes():
            u_str = str(node)
            in_deg = int(in_deg_dict.get(node, 0))
            out_deg = int(out_deg_dict.get(node, 0))
            w_in_deg = round(float(w_in_deg_dict.get(node, 0.0)), 2)
            w_out_deg = round(float(w_out_deg_dict.get(node, 0.0)), 2)
            bc = centrality.get(node, 0.0)

            features[u_str] = {
                "in_degree": in_deg,
                "out_degree": out_deg,
                "total_degree": in_deg + out_deg,
                "weighted_in_degree": w_in_deg,
                "weighted_out_degree": w_out_deg,
                "betweenness_centrality": bc,
            }

        self._structural_features_cache = features
        return features

    def get_all_egonet_features(self) -> Dict[str, Dict[str, float]]:
        """
        Compute reduced-egonet features (single-edge leaf nodes removed)
        and random-walk-based circular-flow indicator for all nodes (Dumitrescu et al. egonet baseline).
        Optimized with degree short-circuiting for large graphs.
        """
        if self._egonet_features_cache is not None:
            return self._egonet_features_cache

        G = self.graph
        features = {}

        if G.number_of_nodes() == 0:
            self._egonet_features_cache = {}
            return self._egonet_features_cache

        in_adj = G.pred
        out_adj = G.succ

        # Precompute total degree per node
        tot_deg = {u: len(out_adj[u]) + len(in_adj[u]) for u in G.nodes()}

        for u in G.nodes():
            u_str = str(u)
            d_u = tot_deg[u]

            # Short-circuit degree <= 1 nodes (isolated or single-leaf node egonets)
            if d_u <= 1:
                features[u_str] = {
                    "egonet_node_count": 1.0,
                    "egonet_edge_count": 0.0,
                    "egonet_density": 0.0,
                    "circular_flow_indicator": 0.0,
                }
                continue

            succ = set(out_adj[u])
            pred = set(in_adj[u])
            neighbors_1hop = succ.union(pred)
            neighbors_1hop.add(u)

            leaves = set()
            for v in neighbors_1hop:
                if v == u:
                    continue
                if tot_deg[v] <= 1:
                    leaves.add(v)
                elif len((set(out_adj[v]).union(in_adj[v])).intersection(neighbors_1hop)) <= 1:
                    leaves.add(v)

            reduced_nodes = neighbors_1hop - leaves
            n_nodes = len(reduced_nodes)

            # Edges between reduced nodes
            n_edges = sum(
                1 for v in reduced_nodes
                for w in out_adj[v] if w in reduced_nodes
            )

            possible_edges = n_nodes * (n_nodes - 1)
            density = float(n_edges / possible_edges) if possible_edges > 0 else 0.0

            out_deg_u = len(succ)
            circular_flow = 0.0
            if out_deg_u > 0:
                for v in succ:
                    if u in out_adj[v]:
                        circular_flow += 1.0 / out_deg_u
                    out_deg_v = len(out_adj[v])
                    if out_deg_v > 0:
                        for w in out_adj[v]:
                            if w != u and u in out_adj[w]:
                                circular_flow += 1.0 / (out_deg_u * out_deg_v)

            features[u_str] = {
                "egonet_node_count": float(n_nodes),
                "egonet_edge_count": float(n_edges),
                "egonet_density": float(round(density, 6)),
                "circular_flow_indicator": float(round(circular_flow, 6)),
            }

        self._egonet_features_cache = features
        return features


    def get_graph_summary(self) -> Dict[str, Any]:
        """Get topological and descriptive summary of the network."""
        if self._summary_cache is not None:
            return self._summary_cache

        n_nodes = self.graph.number_of_nodes()
        n_edges = self.graph.number_of_edges()

        if n_nodes == 0:
            summary = {
                "nodes": 0,
                "edges": 0,
                "density": 0.0,
                "is_directed": True,
                "weakly_connected_components": 0,
                "strongly_connected_components": 0,
                "top_in_degree_nodes": [],
                "top_out_degree_nodes": [],
            }
            self._summary_cache = summary
            return summary

        density = round(float(nx.density(self.graph)), 6)
        wcc = nx.number_weakly_connected_components(self.graph)
        scc = nx.number_strongly_connected_components(self.graph)

        all_features = self.get_all_structural_features()
        sorted_in = sorted(
            all_features.items(),
            key=lambda item: (item[1]["in_degree"], item[1]["weighted_in_degree"]),
            reverse=True,
        )[:5]

        sorted_out = sorted(
            all_features.items(),
            key=lambda item: (item[1]["out_degree"], item[1]["weighted_out_degree"]),
            reverse=True,
        )[:5]

        top_in = [
            {"user_id": node, **metrics} for node, metrics in sorted_in
        ]
        top_out = [
            {"user_id": node, **metrics} for node, metrics in sorted_out
        ]

        summary = {
            "nodes": n_nodes,
            "edges": n_edges,
            "density": density,
            "is_directed": True,
            "weakly_connected_components": wcc,
            "strongly_connected_components": scc,
            "top_in_degree_nodes": top_in,
            "top_out_degree_nodes": top_out,
        }
        self._summary_cache = summary
        return summary
