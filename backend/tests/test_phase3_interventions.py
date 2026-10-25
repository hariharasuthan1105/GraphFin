import json
from dataclasses import replace
from pathlib import Path
import networkx as nx
import numpy as np
from sklearn.ensemble import IsolationForest
import pytest
import numpy as np
from pydantic import ValidationError
from backend.app.research.interventions.schemas import Budget, InterventionConfig
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.intervention_engine import InterventionEngine, budget_check
from backend.app.research.interventions.feature_recomputation import recompute
from backend.app.research.interventions.optimized_recomputation import (
    IndexedHistoryFrames, recompute_optimized, recompute_component_optimized,
)
from backend.app.research.interventions.artifact_writer import write_run
from backend.app.services.feature_service import FeatureService
from backend.app.services.graph_service import GraphService
from backend.app.services.research_protocol import ROOT, PROTOCOL, sha

DATA = (ROOT/"docs/research/fixtures/phase3_transactions.csv").read_bytes()


def cfg(**changes):
    base = dict(dataset_id="test", source_identity="source-v1", time_kind="simulation_hour",
                cutoff="9", window_size=3, window_unit="hours", known_accounts=("ISOLATED",),
                budget=Budget(max_count=2, max_fraction=.5, max_amount_fraction=.5, min_retained=2))
    base.update(changes)
    return InterventionConfig(**base)


def stable(records):
    return [{k:v for k,v in r.items() if k != "runtime_seconds"} for r in records]


def test_three_families_determinism_no_mutation():
    config = cfg()
    history = load_history(DATA, config)
    before = history.events
    a = list(InterventionEngine(history, config).generate("A"))
    b = list(InterventionEngine(history, config).generate("A"))
    assert stable(a) == stable(b)
    assert {x["family"] for x in a if x["status"] == "accepted"} == {"counterparty", "temporal", "budgeted"}
    assert history.events == before and DATA == (ROOT/"docs/research/fixtures/phase3_transactions.csv").read_bytes()


def test_future_rows_do_not_change_history_or_intervention():
    config = cfg()
    appended = DATA + b"\nfuture,Z,Q,10000,100\n"
    left, right = load_history(DATA, config), load_history(appended, config)
    assert left.dataset_sha256 != right.dataset_sha256
    assert left.history_sha256 == right.history_sha256
    assert left.universe == right.universe and "Z" not in right.universe
    assert stable(InterventionEngine(left, config).generate("A")) == stable(InterventionEngine(right, config).generate("A"))
    assert all(e.time <= 9 for e in left.events)
    assert "t10" in {e.transaction_id for e in left.events}
    assert "t11" not in {e.transaction_id for e in left.events}
    header, body = DATA.split(b"\n", 1)
    inserted = load_history(header+b"\nfuture,Z,Q,10000,100\n"+body,config)
    assert inserted.history_sha256 == left.history_sha256
    assert stable(InterventionEngine(left,config).generate("A")) == stable(InterventionEngine(inserted,config).generate("A"))


def test_label_columns_irrelevant(monkeypatch):
    from backend.app.services.label_registry import label_registry
    monkeypatch.setattr(label_registry, "get_labels", lambda *a: pytest.fail("Label access forbidden"))
    variants = [b"source_row_id,sender_id,receiver_id,amount,step,label,isFraud\n1,A,B,1,1,0,0\n2,B,A,2,2,1,1\n",
                b"source_row_id,sender_id,receiver_id,amount,step,label,isFraud\n1,A,B,1,1,1,1\n2,B,A,2,2,0,0\n"]
    configs = cfg(budget=Budget(max_count=1, max_fraction=.5))
    histories = [load_history(x, configs) for x in variants]
    assert histories[0].events == histories[1].events
    assert stable(InterventionEngine(histories[0], configs).generate("A")) == stable(InterventionEngine(histories[1], configs).generate("A"))


def test_direction_duplicate_events_and_complete_counterparties():
    h = load_history(DATA, cfg())
    e = InterventionEngine(h, cfg())
    groups = {key: ids for family,key,ids in e.candidates("A") if family == "counterparty"}
    assert groups["B"] == ("t1", "t2") and groups["C"] == ("t3", "t4")
    kept = h.frame(groups["B"])
    assert set(kept.transaction_id) == {x.transaction_id for x in h.events} - {"t1","t2"}
    assert kept[kept.transaction_id == "t5"].sender_id.iloc[0] == "D"
    g = GraphService()
    g.build_graph(h.frame())
    assert g.graph["A"]["C"]["count"] == 2 and g.graph["A"]["C"]["weight"] == 14
    assert g.graph["A"]["B"]["weight"] == 10 and g.graph["B"]["A"]["weight"] == 12


def test_optimized_recomputation_matches_reference_for_all_features_and_cache_keys():
    config = cfg()
    history = load_history(DATA, config)
    engine = InterventionEngine(history, config)
    omissions = [(), ("t1",), ("t1", "t2"), ("t3", "t4")]
    cache = IndexedHistoryFrames(history, seed=42, max_entries=2)
    for omitted in omissions:
        reference_frame = history.frame(omitted)
        cached_frame = cache.frame(omitted)
        assert reference_frame.equals(cached_frame)
        expected, expected_mode = recompute(history, omitted)
        actual, actual_mode = recompute_optimized(history, omitted, frames=cache)
        component, component_mode = recompute_component_optimized(history, omitted, frames=cache)
        assert actual.keys() == expected.keys()
        for account in expected:
            np.testing.assert_allclose(actual[account], expected[account], rtol=0, atol=0)
        assert actual_mode["centrality"] == expected_mode["centrality"]
        assert actual_mode["seed"] == expected_mode["seed"]
        assert component_mode["centrality"] == expected_mode["centrality"]
        for account in expected:
            np.testing.assert_allclose(component[account], expected[account], rtol=0, atol=0)
        assert actual_mode["cache_key"] == cache.identity(omitted)
    assert cache.identity(("t1",)) != cache.identity(("t2",))
    assert cache.identity(("t1",)) != IndexedHistoryFrames(history, seed=43).identity(("t1",))
    assert list(engine.candidates("A"))
    # Identical canonical vectors must yield identical frozen-IF score arrays.
    feature_ids = sorted(expected)
    reference_matrix = np.asarray([expected[u] for u in feature_ids], dtype=np.float32)
    optimized_matrix = np.asarray([actual[u] for u in feature_ids], dtype=np.float32)
    detector = IsolationForest(n_estimators=25, max_samples="auto", contamination=.1, random_state=42, n_jobs=1)
    detector.fit(reference_matrix)
    np.testing.assert_array_equal(detector.decision_function(reference_matrix), detector.decision_function(optimized_matrix))


def test_optimized_recomputation_returns_isolated_copy_and_rejects_invalid_cache():
    history = load_history(DATA, cfg())
    cache = IndexedHistoryFrames(history)
    first = cache.frame()
    first.drop(first.index, inplace=True)
    assert len(cache.frame()) == len(history.events)
    with pytest.raises(ValueError):
        cache.frame(("unknown",))
    other = load_history(DATA + b"\nfuture,Z,Q,10,100\n", cfg())
    with pytest.raises(ValueError, match="different History"):
        recompute_optimized(history, frames=IndexedHistoryFrames(other))


def test_component_path_preserves_frozen_sampled_centrality_policy():
    universe = tuple(f"I{i:04}" for i in range(2001))
    config = cfg(known_accounts=universe)
    history = load_history(b"source_row_id,sender_id,receiver_id,amount,step\n", config)
    reference, reference_mode = recompute(history)
    optimized, optimized_mode = recompute_component_optimized(history)
    assert reference == optimized
    assert reference_mode["centrality"] == "sampled" and reference_mode["k"] == 500
    assert optimized_mode["centrality"] == "sampled" and optimized_mode["k"] == 500
    assert optimized_mode["seed"] == reference_mode["seed"] == 42


def test_generated_ids_keep_identical_events():
    data = b"source_row_id,sender_id,receiver_id,amount,step\n1,A,B,1.01,1\n2,A,B,1.01,1\n"
    h = load_history(data, cfg())
    assert len(h.events) == 2 and h.events[0].transaction_id != h.events[1].transaction_id
    assert h.events == load_history(data, cfg()).events
    assert h.events[0].amount == "1.01"
    with pytest.raises(ValueError,match="source_row_id"):
        load_history(b"sender_id,receiver_id,amount,step\nA,B,1,1\n",cfg())


@pytest.mark.parametrize("row", ["A,A,1,1", "A,B,0,1", "A,B,-1,1", "A,B,nan,1",
                                 "A,B,1,", "A,B,1,1.5", "A,B,1,-1"])
def test_invalid_events_fail_explicitly(row):
    with pytest.raises(Exception):
        load_history(("sender_id,receiver_id,amount,step\n"+row+"\n").encode(), cfg())


@pytest.mark.parametrize("changes", [{"window_size":0}, {"window_unit":"seconds"}, {"families":("temporal","temporal")},
                                     {"intervention_seed":-1}, {"budget":{"max_fraction":1.1}}, {"unknown":True}])
def test_invalid_configuration(changes):
    with pytest.raises(ValidationError):
        cfg(**changes)


def test_timestamp_and_simulation_interval_equivalence():
    sim = b"transaction_id,sender_id,receiver_id,amount,step\n1,A,B,2,1\n2,B,A,3,3\n"
    real = b"transaction_id,sender_id,receiver_id,amount,timestamp\n1,A,B,2,2022-09-01T01:00:00Z\n2,B,A,3,2022-09-01T03:00:00Z\n"
    a = recompute(load_history(sim, cfg()))[0]
    config = cfg(time_kind="timestamp_utc",cutoff="2022-09-01T03:00:00Z")
    b = recompute(load_history(real, config))[0]
    assert a == b and a["A"][16] == 7200
    bridged = load_history(real, cfg(simulation_timestamp_origin="2022-09-01T00:00:00Z"))
    assert recompute(bridged)[0] == a
    for value in ["", "bad", "NaT"]:
        with pytest.raises(Exception):
            load_history(real.replace(b"2022-09-01T01:00:00Z", value.encode()), config)


def test_repeated_times_and_empty_blocks():
    e = InterventionEngine(load_history(DATA, cfg()),cfg())
    groups = {key: ids for family,key,ids in e.candidates("A") if family == "temporal"}
    assert {"t3","t4"} <= set(groups["2"])
    assert groups["0"] == ("t10","t6")
    assert set(groups) == {"0","1","2"}


def test_no_history_and_one_event():
    config = cfg()
    e = InterventionEngine(load_history(b"transaction_id,sender_id,receiver_id,amount,step\nx,A,B,1,1\n", config), config)
    assert list(e.generate("ISOLATED"))[0]["reason"] == "no_historical_evidence"
    assert all(r["status"] == "rejected" for r in e.generate("A"))
    with pytest.raises(ValueError):
        list(e.generate("FUTURE_ACCOUNT"))


@pytest.mark.parametrize("budget,reason", [
    (Budget(max_count=1,max_fraction=1,min_retained=0), "max_count"),
    (Budget(max_count=10,max_fraction=.1,min_retained=0), "max_fraction"),
    (Budget(max_count=10,max_fraction=1,min_retained=7), "min_retained"),
    (Budget(max_count=10,max_fraction=1,min_retained=0,max_amount_fraction=.01), "max_amount_fraction")])
def test_group_rejected_whole(budget,reason):
    config = cfg(budget=budget)
    records = list(InterventionEngine(load_history(DATA,config),config).generate("A"))
    record = next(r for r in records if r["family"] == "counterparty" and r["candidate_key"] == "B")
    assert record["omitted_transaction_ids"] == ["t1","t2"] and record["reason"] == reason


def test_budget_limits_every_accepted_record():
    config = cfg(budget=Budget(max_count=2,max_fraction=.5,max_amount_fraction=.5,min_retained=2,max_interventions=2))
    engine = InterventionEngine(load_history(DATA, config), config)
    records = list(engine.generate("A"))
    accepted = [r for r in records if r["status"] == "accepted"]
    assert len(accepted) == 2 and any(r.get("reason") == "max_interventions" for r in records)
    for r in accepted:
        assert budget_check(engine.incident["A"], r["omitted_transaction_ids"], config.budget)[0] is None


def test_zero_intervention_baseline_and_disconnected_reference():
    config = cfg(known_accounts=())
    h = load_history(DATA,config)
    graph = GraphService()
    graph.build_graph(h.frame())
    features = FeatureService(graph)
    features.extract_features(h.frame())
    ids,matrix,_ = features.get_feature_matrix()
    actual,_ = recompute(h)
    np.testing.assert_array_equal([actual[x] for x in ids], matrix[:,:19])
    assert set(nx.weakly_connected_components(graph.graph).__next__()) != set(graph.graph)
    zero = cfg(budget=Budget(max_interventions=0))
    assert not any(r["status"] == "accepted" for r in InterventionEngine(load_history(DATA,zero),zero).generate("A"))


def test_isolates_preserved_global_normalization():
    content = b"transaction_id,sender_id,receiver_id,amount,step\n1,A,B,2,1\n2,B,C,3,2\n3,C,D,4,3\n"
    config = cfg(known_accounts=("EMPTY",),budget=Budget(max_fraction=1,min_retained=0))
    h = load_history(content,config)
    vectors, mode = recompute(h, ["1"])
    assert set(vectors) == set(h.universe) and vectors["A"] == [0.0]*19 and vectors["EMPTY"] == [0.0]*19
    reference = nx.DiGraph()
    reference.add_nodes_from(h.universe)
    reference.add_edges_from([("B","C"),("C","D")])
    centrality = nx.betweenness_centrality(reference)
    assert vectors["C"][5] == float(np.float32(round(centrality["C"],6)))
    assert vectors["C"][6:10] == [2,4,3,-1] and mode["centrality"] == "exact"
    all_zero,_ = recompute(h,["1","2","3"])
    assert all(v == [0.0]*19 for v in all_zero.values())


def test_all_changed_features_against_manual_omission():
    h = load_history(DATA,cfg())
    vectors,_ = recompute(h,["t1","t2"])
    reference = nx.DiGraph()
    reference.add_nodes_from(h.universe)
    reference.add_edges_from([("A","C"),("D","A"),("A","E"),("E","D"),("X","Y"),("Y","X"),("F","A")])
    bc = round(nx.betweenness_centrality(reference)["A"],6)
    expected = np.array([2,2,4,17,25,bc,5,25,17,-8,8.4,11,2,2,5,35,5400,0,7200],dtype=np.float32)
    np.testing.assert_array_equal(vectors["A"],expected.astype(float))
    with pytest.raises(ValueError,match="eligible"):
        recompute(h,["FUTURE"])
    with pytest.raises(ValueError,match="unique"):
        recompute(h,["t1","t1"])


def test_expensive_global_policy_and_fail_closed(monkeypatch):
    h = load_history(b"transaction_id,sender_id,receiver_id,amount,step\n1,A,B,1,1\n",cfg(known_accounts=tuple(f"N{i}" for i in range(2000))))
    with pytest.raises(ValueError,match="limit"):
        recompute(h,max_nodes=10)
    _, mode = recompute(h)
    assert mode["centrality"] == "sampled" and mode["k"] == 500 and mode["seed"] == 42
    monkeypatch.setattr(nx,"betweenness_centrality",lambda *a,**kw: (_ for _ in ()).throw(RuntimeError("failure")))
    with pytest.raises(RuntimeError,match="Centrality failed"):
        recompute(h)


def test_versioned_artifact_replay_and_append_only(tmp_path):
    a = write_run(DATA,cfg(),["A"],tmp_path,"a")
    raw = json.loads((tmp_path/"a/config.json").read_text())
    focal = raw.pop("focal_accounts")
    b = write_run(DATA,InterventionConfig(**raw),focal,tmp_path,"b")
    read = lambda p: [json.loads(x) for x in p.read_text().splitlines()]
    assert stable(read(tmp_path/"a/interventions.jsonl")) == stable(read(tmp_path/"b/interventions.jsonl"))
    assert a["protocol"] == PROTOCOL and a["source"]["labels"] == "not_read"
    assert a["source"]["transactions_sha256"] == sha(DATA)
    for name,digest in a["artifact_sha256"].items():
        assert sha((tmp_path/"a"/name).read_bytes()) == digest
    with pytest.raises(FileExistsError):
        write_run(DATA,cfg(),["A"],tmp_path,"a")
    with pytest.raises(ValueError):
        write_run(DATA,cfg(),["A"],ROOT/"data/results","forbidden")
