from dataclasses import replace
import inspect
import json
import numpy as np
import pytest
from backend.app.services.research_protocol import ROOT
from backend.app.services.artifact_integrity import verify_protected
from backend.app.research.explanation_validation import diagnostics as d
from backend.app.research.interventions.schemas import InterventionConfig, Budget
from backend.app.research.interventions.historical_evidence import Event, History, load_history
from backend.app.research.evidence_specificity.matching import StrictMatcher
from backend.app.research.evidence_specificity.scoring import FrozenBatchScorer
from backend.scripts.run_phase5h_specificity import save


def fixture():
    events=tuple(Event(f"t{i}","A",f"B{i}",str(10+i),i,i) for i in range(6))
    h=History(events,"source","history",tuple(["A",*[f"B{i}" for i in range(6)],"ISO"]),10,"simulation_hour")
    c=InterventionConfig(dataset_id="test",source_identity="synthetic",time_kind="simulation_hour",cutoff="10",window_size=2,window_unit="hours",budget=Budget(max_count=2,max_fraction=.5,max_amount_fraction=.5,min_retained=1))
    return h,c


@pytest.mark.parametrize("a,b,expected",[(.2,.3,-.1),(.3,.2,.1),(0.,0.,0.)])
def test_signed_fidelity(a,b,expected):
    assert d.fidelity(a,b)==pytest.approx(expected)


@pytest.mark.parametrize("bad",[float("inf"),float("nan")])
def test_nonfinite_fidelity(bad):
    with pytest.raises(ValueError): d.fidelity(bad,0)


def test_whole_group_selection_and_sparsity():
    h,c=fixture(); result=d.select(h,c,"A")
    assert result["methods"]["A"]["omitted_transaction_ids"]==["t0"]
    assert result["methods"]["D"]["sparsity"]["omitted_count"]==2
    assert result["methods"]["C"]["sparsity"]["omitted_amount"]=="27"
    s=d.sparsity(h,c,"A",["t0","t1"])
    assert s["omitted_amount"]=="21" and s["historical_amount"]=="75"
    assert s["omitted_fraction"]==2/6 and s["omitted_amount_fraction"]==21/75
    assert s["counterparties"]==2 and s["time_blocks"]==2
    with pytest.raises(ValueError): d.sparsity(h,c,"A",["foreign"])


def test_selection_replay_order_and_missing():
    h,c=fixture(); before=d.select(h,c,"A")
    assert before==d.select(h,c,"A")==d.select(d.shadow(h,reversed(h.events)),c,"A")
    assert all(v is None for v in d.select(h,c,"ISO")["methods"].values())
    assert d.summary([],6)["mean"] is None and d.summary([],6)["coverage"]==0


def test_caliper_symmetric_and_identical_allowed():
    h,c=fixture(); a=d.sparsity(h,c,"A",["t0"]); b=d.sparsity(h,c,"A",["t1"])
    assert d.compatible(a,a)
    assert not d.compatible(a,b) and d.compatible(a,b)==d.compatible(b,a)
    assert not d.compatible(a,d.sparsity(h,c,"A",["t0","t1"]))


def test_strict_control_adapter_and_replay():
    h,c=fixture(); p=json.loads((ROOT/"docs/research/configs/phase6a_explanations_v1.json").read_bytes())
    h=d.shadow(h,[replace(e,amount="10") for e in h.events]); matcher=StrictMatcher(h,c.budget,p["matching"])
    row=d.select(h,c,"A")["methods"]["A"]; plan=matcher.match(row)
    assert plan==matcher.match(row) and plan["status"]=="matched"
    assert len(plan["controls"])==2
    for control in plan["controls"]: assert control["assessment"]["comparable"]


def test_jaccard_and_negative_summary():
    assert d.jaccard([],[])==1 and d.jaccard(["a"],["b"])==0
    assert d.jaccard(["a","b"],["b","c"])==1/3
    s=d.summary([-2,0,1],6)
    assert s["median"]==0 and s["median_absolute"]==1 and s["positive_fraction"]==1/3
    assert s["mean"]==pytest.approx(-1/3) and s["coverage"]==.5


def test_no_fit_frozen_score_adapter():
    class Frozen:
        n_features_in_=19
        def fit(self,*args): raise AssertionError("Must never fit")
        def decision_function(self,x): return np.asarray(x)[:,0]
    v=np.zeros((2,19)); v[:,0]=[.25,-.5]
    assert np.array_equal(FrozenBatchScorer(Frozen()).verify_batch(v),[-.25,.5])


def test_no_label_input_or_mutation():
    h,c=fixture(); original=h.events
    variant=d.shadow(h,[replace(e,amount="10.1") if e.transaction_id=="t0" else e for e in h.events])
    assert h.events==original and variant.history_sha256!=h.history_sha256
    assert set(inspect.signature(d.select).parameters)=={"history","cfg","focal"}


def test_append_only_and_protected(tmp_path):
    p=tmp_path/"artifact.json"; save(p,{"a":1})
    with pytest.raises(FileExistsError): save(p,{"a":2})
    assert json.loads(p.read_bytes())=={"a":1}
    assert verify_protected()==[]


def test_timestamp_blocks_match_existing_candidates():
    h,c=fixture()
    h=replace(h,time_kind="timestamp_utc",cutoff=10*3600*10**9,
              events=tuple(replace(e,time=e.time*3600*10**9) for e in h.events))
    c=c.model_copy(update={"time_kind":"timestamp_utc","cutoff":"1970-01-01 10:00:00"})
    for row in d.select(h,c,"A")["eligible"]:
        if row["family"]=="temporal": assert row["sparsity"]["time_blocks"]==1


def test_history_cutoff_excludes_future():
    _,c=fixture()
    data=b"transaction_id,sender_id,receiver_id,amount,step\na,A,B,10,1\nb,A,C,20,11\n"
    h=load_history(data,c)
    assert [e.transaction_id for e in h.events]==["a"]


def test_labels_do_not_select_evidence():
    _,c=fixture()
    header="transaction_id,sender_id,receiver_id,amount,step,is_fraud\n"
    first=load_history((header+"a,A,B,10,1,0\nb,A,C,10,2,1\n").encode(),c)
    second=load_history((header+"a,A,B,10,1,1\nb,A,C,10,2,0\n").encode(),c)
    assert first.history_sha256==second.history_sha256
    assert d.select(first,c,"A")==d.select(second,c,"A")


def test_paired_comparison_uses_same_population_and_budget():
    h,c=fixture(); s=d.sparsity(h,c,"A",["t0"])
    a={"account_id":"A","method":"A","available":True,"sparsity":s,"fidelity":-.2}
    b={**a,"method":"B","fidelity":.1}
    assert d.paired([a,b])[0]["fidelity_difference"]==pytest.approx(-.3)
    assert d.paired([a,{**b,"account_id":"B"}])==[]
    assert d.paired([a,{**b,"available":False}])==[]


def test_reference_account_without_explanation_keeps_baseline():
    from backend.scripts.run_phase6a_explanations import reference_key
    assert reference_key({("A",("t0",))},"MISSING")==("MISSING",())
    assert reference_key({("A",("t0",))},"A")==("A",("t0",))
