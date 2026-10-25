"""Focal canonical features with unchanged global GraphFin centrality semantics."""
from collections import defaultdict
from time import perf_counter
import numpy as np
import pandas as pd
from ...services.graph_service import GraphService
from ...services.research_protocol import canonical, sha

VERSION = "indexed-focal-features-global-centrality-v1"


class FocalRecomputer:
    def __init__(self, history, max_nodes=10000):
        if len(history.universe)>max_nodes:
            raise ValueError("Reference node limit exceeded.")
        self.history = history
        self.base = history.frame()
        self.tx_index = {e.transaction_id:i for i,e in enumerate(history.events)}
        self.incident = defaultdict(list)
        for i,e in enumerate(history.events):
            if e.sender==e.receiver:
                raise ValueError("Self-transfers remain unsupported.")
            self.incident[e.sender].append(i); self.incident[e.receiver].append(i)
        self._graph_key = None
        self._graph = None
        self._vectors = {}

    def identity(self, focal, omitted):
        return sha(canonical([VERSION,self.history.dataset_sha256,self.history.history_sha256,
            self.history.cutoff,self.history.time_kind,self.history.universe,focal,sorted(omitted),
            "canonical19-float32-v1","graph-service-directed-weighted-v1",42]))

    def vector(self, focal, omitted=(), use_cache=True):
        start = perf_counter(); omitted = tuple(omitted)
        if focal not in self.history.universe: raise ValueError("Unknown focal account.")
        if len(set(omitted))!=len(omitted) or not set(omitted)<=self.tx_index.keys():
            raise ValueError("Unique eligible omission IDs required.")
        key = self.identity(focal, omitted)
        if use_cache and key in self._vectors:
            v,meta = self._vectors[key]
            return list(v), {**meta,"cache_hit":True,"total_seconds":perf_counter()-start}
        graph_key = tuple(sorted(omitted))
        t = perf_counter()
        keep = np.ones(len(self.base),dtype=bool)
        if omitted: keep[[self.tx_index[x] for x in omitted]] = False
        frame = self.base.loc[keep].reset_index(drop=True)
        frame_seconds = perf_counter()-t
        t = perf_counter()
        if not use_cache or self._graph_key!=graph_key:
            graph = GraphService(); graph.build_graph(frame)
            missing = set(self.history.universe)-set(graph.graph)
            if missing:
                graph.graph.add_nodes_from(sorted(missing))
                graph._betweenness_cache = None
                graph._structural_features_cache = None
                graph._egonet_features_cache = None
            graph.compute_betweenness_centrality()
            if graph._betweenness_cache is None:
                raise RuntimeError("Centrality failed; zero fallback cannot certify equivalence.")
            self._graph_key,self._graph = graph_key,graph
        graph = self._graph
        graph_seconds = perf_counter()-t
        t = perf_counter()
        positions = [i for i in self.incident[focal] if keep[i]]
        local = self.base.iloc[positions]
        vector = _local_vector(local, focal, graph)
        meta = {"version":VERSION,"cache_key":key,"cache_hit":False,
            "centrality":"exact" if len(self.history.universe)<=2000 else "sampled-reference-policy",
            "k":None if len(self.history.universe)<=2000 else (100 if len(self.history.universe)>50000 else 500),
            "seed":42,"node_order_sha256":sha(canonical(list(graph.graph))),
            "filter_frame_seconds":frame_seconds,"graph_and_global_centrality_seconds":graph_seconds,
            "focal_local_features_seconds":perf_counter()-t,"total_seconds":perf_counter()-start,
            "incident_retained":len(local),"account_universe":len(self.history.universe)}
        self._vectors[key] = (list(vector),meta)
        return vector,meta


def _local_vector(local, focal, graph):
    if local.empty: return [0.0]*19
    structural = graph.get_node_structural_features(focal)
    sent = local.loc[local.sender_id==focal]
    recv = local.loc[local.receiver_id==focal]
    # Pandas groupby retains the same compensated aggregation/rounding as the
    # canonical full-population implementation, applied only to focal events.
    sent_stats = sent.groupby("sender_id").agg(total=("amount","sum"),unique=("receiver_id","nunique"))
    recv_stats = recv.groupby("receiver_id").agg(total=("amount","sum"),unique=("sender_id","nunique"))
    sent_total = float(sent_stats.loc[focal,"total"]) if len(sent_stats) else 0.0
    recv_total = float(recv_stats.loc[focal,"total"]) if len(recv_stats) else 0.0
    tx = pd.concat([sent[["timestamp","amount"]],recv[["timestamp","amount"]]],ignore_index=True)
    tx["user_id"] = focal
    tx = tx.sort_values(["user_id","timestamp"])
    tx["prev_ts"] = tx.groupby("user_id")["timestamp"].shift(1)
    tx["delta"] = (tx.timestamp-tx.prev_ts).dt.total_seconds()
    stats = tx.groupby("user_id").agg(count=("timestamp","count"),minimum=("timestamp","min"),
        maximum=("timestamp","max"),average=("amount","mean"),max_amount=("amount","max"),
        avg_delta=("delta","mean"),min_delta=("delta","min"),max_delta=("delta","max")).loc[focal]
    count = int(stats["count"])
    days = max((stats["maximum"]-stats["minimum"]).total_seconds()/86400,1.0)
    rate = count/days if count>1 else float(count)
    gap = lambda name: float(np.round(stats[name],2)) if count>1 else 0.0
    values = [structural[n] for n in ["in_degree","out_degree","total_degree","weighted_in_degree","weighted_out_degree","betweenness_centrality"]]
    values += [count,np.round(sent_total,2),np.round(recv_total,2),np.round(recv_total-sent_total,2),
        np.round(stats["average"],2),np.round(stats["max_amount"],2),
        int(sent_stats.loc[focal,"unique"]) if len(sent_stats) else 0,
        int(recv_stats.loc[focal,"unique"]) if len(recv_stats) else 0,
        np.round(rate,4),np.round(rate*7,4),gap("avg_delta"),gap("min_delta"),gap("max_delta")]
    vector = np.asarray(values,dtype=np.float32)
    if vector.shape!=(19,) or not np.isfinite(vector).all():
        raise ValueError("Finite canonical focal vector required.")
    return vector.astype(float).tolist()
