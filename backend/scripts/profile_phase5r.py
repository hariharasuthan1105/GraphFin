"""Bounded synthetic profiling for the Phase 5R recomputation pathway.

Runs only 500- and 1,500-row synthetic histories. It does not read labels or
modify frozen research outputs. Results are created in a new output directory.
"""
import argparse, gc, io, json, random, time, tracemalloc
from pathlib import Path
import sys
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))
import networkx as nx
import numpy as np
import pandas as pd
import psutil
from sklearn.ensemble import IsolationForest
from backend.app.research.interventions.schemas import Budget, InterventionConfig
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.feature_recomputation import recompute
from backend.app.research.interventions.optimized_recomputation import (
    IndexedHistoryFrames, recompute_optimized, recompute_component_optimized,
)
from backend.app.services.graph_service import GraphService
from backend.app.services.feature_service import FeatureService
from backend.app.services.research_protocol import ROOT, PROTOCOL, canonical, sha


def workload(n, pattern, seed=2718):
    rng = random.Random(seed + n + (0 if pattern == "sparse" else 10000))
    node_count = n if pattern == "sparse" else max(25, int(n ** .5))
    rows = ["source_row_id,sender_id,receiver_id,amount,step"]
    for i in range(n):
        u = rng.randrange(node_count)
        v = (u + rng.randrange(1, node_count)) % node_count
        amount = "1000000000000" if i % 97 == 0 else ("0.000001" if i % 89 == 0 else str(1 + (i % 13)))
        rows.append(f"{i+1},A{u:05},A{v:05},{amount},{i % 168}")
    raw = ("\n".join(rows) + "\n").encode()
    cfg = InterventionConfig(dataset_id=f"synthetic-{n}-{pattern}", source_identity="phase5r-profile-v1",
        time_kind="simulation_hour", cutoff="1000", window_size=24, window_unit="hours",
        budget=Budget(max_count=2, max_fraction=.5, min_retained=1, max_interventions=2))
    return raw, load_history(raw, cfg), cfg


def profile(n, pattern):
    raw, history, cfg = workload(n, pattern)
    process = psutil.Process()
    omitted = tuple(e.transaction_id for e in history.events[:min(2, len(history.events))])
    frames = IndexedHistoryFrames(history, seed=42)
    times = {}
    start = time.perf_counter(); frame = history.frame(omitted); times["reference_filter_and_frame_seconds"] = time.perf_counter()-start
    start = time.perf_counter(); cached_frame = frames.frame(omitted); times["optimized_indexed_frame_seconds"] = time.perf_counter()-start
    assert frame.reset_index(drop=True).equals(cached_frame)
    # Isolate graph construction from centrality, then measure the same
    # directed/weighted degree operations and FeatureService-style aggregates.
    graph_service = GraphService()
    graph_service.compute_betweenness_centrality = lambda *args, **kwargs: {}
    t = time.perf_counter(); graph = graph_service.build_graph(frame); times["graph_construction_excluding_centrality_seconds"] = time.perf_counter()-t
    t = time.perf_counter()
    _ = dict(graph.in_degree()); _ = dict(graph.out_degree())
    _ = dict(graph.in_degree(weight="weight")); _ = dict(graph.out_degree(weight="weight"))
    times["degree_and_weighted_degree_seconds"] = time.perf_counter()-t
    t = time.perf_counter(); _ = nx.betweenness_centrality(graph, normalized=True, seed=42)
    times["standalone_centrality_seconds"] = time.perf_counter()-t
    t = time.perf_counter(); _ = graph_service.get_all_egonet_features()
    times["egonet_features_seconds"] = time.perf_counter()-t
    t = time.perf_counter()
    df=frame.copy(); df["sender_str"]=df.sender_id.astype(str); df["receiver_str"]=df.receiver_id.astype(str)
    _=df.groupby("sender_str").agg(total_sent=("amount","sum"),unique_receivers=("receiver_str","nunique"),sent_count=("amount","count"),sent_max=("amount","max"))
    _=df.groupby("receiver_str").agg(total_received=("amount","sum"),unique_senders=("sender_str","nunique"),recv_count=("amount","count"),recv_max=("amount","max"))
    times["behavioral_groupby_seconds"] = time.perf_counter()-t
    t = time.perf_counter()
    tx=pd.concat([df[["sender_str","timestamp","amount"]].rename(columns={"sender_str":"user_id"}),
                  df[["receiver_str","timestamp","amount"]].rename(columns={"receiver_str":"user_id"})],ignore_index=True)
    tx=tx.sort_values(["user_id","timestamp"]); tx["prev_ts"]=tx.groupby("user_id")["timestamp"].shift(1)
    tx["delta"]=(tx.timestamp-tx.prev_ts).dt.total_seconds()
    _=tx.groupby("user_id").agg(tx_count=("timestamp","count"),min_ts=("timestamp","min"),max_ts=("timestamp","max"),
        avg_amount=("amount","mean"),max_amount=("amount","max"),avg_delta=("delta","mean"),min_delta=("delta","min"),max_delta=("delta","max"))
    times["temporal_sort_and_aggregation_seconds"] = time.perf_counter()-t
    bc_time = [0.0]
    original_bc = nx.betweenness_centrality
    def timed_bc(*a, **kw):
        t = time.perf_counter()
        try: return original_bc(*a, **kw)
        finally: bc_time[0] += time.perf_counter()-t
    nx.betweenness_centrality = timed_bc
    try:
        before_rss = process.memory_info().rss
        gc.collect(); tracemalloc.start()
        t = time.perf_counter(); ref, ref_mode = recompute(history, omitted); times["reference_total_feature_extraction_seconds"] = time.perf_counter()-t
        ref_peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
        times["reference_betweenness_seconds"] = bc_time[0]
        bc_time[0] = 0.0
        gc.collect(); tracemalloc.start()
        t = time.perf_counter(); opt, opt_mode = recompute_optimized(history, omitted, frames=frames); times["optimized_total_feature_extraction_seconds"] = time.perf_counter()-t
        opt_peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
        times["optimized_betweenness_seconds"] = bc_time[0]
        bc_time[0] = 0.0
        gc.collect(); tracemalloc.start()
        t = time.perf_counter(); component, component_mode = recompute_component_optimized(history, omitted, frames=frames); times["component_exact_total_feature_extraction_seconds"] = time.perf_counter()-t
        times["component_exact_betweenness_seconds"] = bc_time[0]
        component_peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    finally:
        nx.betweenness_centrality = original_bc
    max_abs = max(abs(a-b) for account in ref for a,b in zip(ref[account], opt[account]))
    component_max_abs = max(abs(a-b) for account in ref for a,b in zip(ref[account], component[account]))
    if max_abs != 0.0 or component_max_abs != 0.0:
        raise AssertionError(f"Feature mismatch: indexed={max_abs}, component={component_max_abs}")
    # Candidate enumeration for the highest-incident account, using the frozen rules.
    engine = object.__new__(__import__("backend.app.research.interventions.intervention_engine", fromlist=["InterventionEngine"]).InterventionEngine)
    from collections import defaultdict
    engine.history, engine.config, engine.incident = history, cfg, defaultdict(list)
    for event in history.events:
        engine.incident[event.sender].append(event); engine.incident[event.receiver].append(event)
    focal = min(engine.incident, key=lambda x: (-len(engine.incident[x]), x))
    t = time.perf_counter(); candidates = list(engine.candidates(focal)); times["candidate_enumeration_seconds"] = time.perf_counter()-t
    matrix = np.asarray([opt[u] for u in sorted(opt)], dtype=np.float32)
    split = max(2, int(.7*len(matrix)))
    model = IsolationForest(n_estimators=100, max_samples="auto", contamination=.005, random_state=42, n_jobs=1).fit(matrix[:split])
    t = time.perf_counter(); _ = model.decision_function(matrix[split:]); times["frozen_if_scoring_seconds"] = time.perf_counter()-t
    serialized = canonical({"omitted":omitted,"features":opt,"mode":opt_mode})
    times["serialization_seconds"] = 0.0
    t = time.perf_counter(); serialized = canonical({"omitted":omitted,"features":opt,"mode":opt_mode}); times["serialization_seconds"] = time.perf_counter()-t
    return {"transactions":n,"accounts":len(history.universe),"pattern":pattern,"focal_incident_count":len(engine.incident[focal]),
        "candidate_groups":len(candidates),"accepted_omission_count":len(omitted),"timings":times,
        "reference_peak_traced_bytes":ref_peak,"optimized_peak_traced_bytes":opt_peak,
        "component_exact_peak_traced_bytes":component_peak,
        "indexed_base_frame_bytes":int(frames._base.memory_usage(index=True,deep=True).sum()),
        "process_rss_before_bytes":before_rss,"process_rss_after_bytes":process.memory_info().rss,
        "serialized_feature_record_bytes":len(serialized),"maximum_absolute_feature_deviation":max_abs,
        "component_exact_maximum_absolute_feature_deviation":component_max_abs,
        "exact_feature_equivalence":True,"feature_schema_size":19,"reference_centrality_mode":ref_mode["centrality"],
        "optimized_centrality_mode":opt_mode["centrality"],"workload_sha256":sha(raw)}


def main():
    p=argparse.ArgumentParser(); p.add_argument("run_id"); a=p.parse_args()
    if not a.run_id.replace("-", "").isalnum(): raise ValueError("Invalid run ID")
    out=ROOT/"data/results/v2"/a.run_id; out.mkdir(exist_ok=False)
    results=[profile(n,pattern) for n in (500,1500) for pattern in ("sparse","dense")]
    protocol_path=ROOT/"docs/research/configs/phase5_protocol_v1.json"
    result={"stage":"phase5r-bounded-scalability-profile-v1","protocol_sha256":sha(protocol_path.read_bytes()),
        "method":"synthetic label-free 500/1500 transaction workloads; local timing, NetworkX and sklearn versions recorded",
        "software":{"python":__import__("sys").version,"networkx":nx.__version__,"pandas":pd.__version__,"numpy":np.__version__},"results":results}
    (out/"profile.json").write_bytes(canonical(result))
    print(json.dumps({"directory":str(out),"profile":str(out/"profile.json"),"results":results},indent=2),flush=True)

if __name__=="__main__": main()
