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
            self._summary_cache = None
            return self.graph

        G = nx.DiGraph()

        try:
            for _, row in transactions_df.iterrows():
                u = str(row["sender_id"])
                v = str(row["receiver_id"])
                amount = float(row["amount"])
                tx_id = str(row["transaction_id"])

                # Ensure nodes exist
                if not G.has_node(u):
                    G.add_node(u)
                if not G.has_node(v):
                    G.add_node(v)

                if G.has_edge(u, v):
                    G[u][v]["weight"] += amount
                    G[u][v]["count"] += 1
                    G[u][v]["transactions"].append(tx_id)
                else:
                    G.add_edge(
                        u,
                        v,
                        weight=amount,
                        count=1,
                        transactions=[tx_id]
                    )

            self.graph = G
            # Invalidate and precompute centrality at ingest time
            self._betweenness_cache = None
            self._structural_features_cache = None
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
                k = min(500, node_count)
                logger.info(f"Large graph ({node_count} nodes): approximating betweenness with k={k}")
                centrality = nx.betweenness_centrality(self.graph, k=k, normalized=True)
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
        """Calculate structural features for all nodes in the graph."""
        if self._structural_features_cache is not None:
            return self._structural_features_cache

        centrality = self.compute_betweenness_centrality()
        features = {}

        for node in self.graph.nodes():
            in_deg = int(self.graph.in_degree(node))
            out_deg = int(self.graph.out_degree(node))
            w_in_deg = round(float(self.graph.in_degree(node, weight="weight")), 2)
            w_out_deg = round(float(self.graph.out_degree(node, weight="weight")), 2)
            bc = centrality.get(node, 0.0)

            features[node] = {
                "in_degree": in_deg,
                "out_degree": out_deg,
                "total_degree": in_deg + out_deg,
                "weighted_in_degree": w_in_deg,
                "weighted_out_degree": w_out_deg,
                "betweenness_centrality": bc,
            }

        self._structural_features_cache = features
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
