from dataclasses import replace
from decimal import Decimal
import json
import numpy as np
import pytest
from sklearn.ensemble import IsolationForest
from backend.app.services.research_protocol import ROOT
from backend.app.services.artifact_integrity import verify_protected
from backend.app.research.interventions.historical_evidence import Event, History, load_history
from backend.app.research.interventions.schemas import Budget, InterventionConfig
from backend.app.research.interventions.feature_recomputation import recompute
from backend.app.research.feasibility_gate.focal_features import FocalRecomputer
from backend.app.research.evidence_specificity.matching import StrictMatcher
from backend.app.research.evidence_specificity.scoring import summarize, ranks, FrozenBatchScorer, median


def fixture(amounts=(10,10,10,10,10,10)):
    events=tuple(Event(f"t{i}","A",f"B{i}",str(x),i,i) for i,x in enumerate(amounts))
    return History(events,"dataset-test","history-test",tuple(["A",*[f"B{i}" for i in range(len(events))],"ISO"]),99,"simulation_hour")


def matcher(h=None, **updates):
    policy=json.loads((ROOT/"docs/research/configs/phase5h_specificity_v2.json").read_bytes())["matching"]
    policy.update(updates)
    return StrictMatcher(h or fixture(),Budget(max_count=2,max_fraction=.5,max_amount_fraction=.5,min_retained=1,max_interventions=2),policy)


def omission(ids=("t0",), family="temporal"):
    return {"focal_account":"A","omitted_transaction_ids":list(ids),"family":family,"candidate_key":"test"}


def pair(i, family, ds, dc):
    return {"match_id":str(i),"family":family,"status":"matched","structured_delta":ds,"control_deltas":dc}


def test_strict_count_fraction_money_and_determinism():
    m=matcher(); s=omission(); a=m.match(s)
    assert a==m.match(s) and a["status"]=="matched" and a["feasible_count"]==5
    ids=[c["omitted_transaction_ids"] for c in a["controls"]]
    assert len({tuple(x) for x in ids})==2 and ["t0"] not in ids
    for c in a["controls"]:
        v=c["assessment"]
        assert v["structured_valid"] and v["control_valid"] and v["comparable"]
        assert v["omitted_count_equal"] and v["omitted_fraction_equal"]
        assert Decimal(v["amount_absolute_difference"])<=Decimal(v["amount_allowed_difference"])
    assert m.assess("A",["t0"],["t1","t2"])["reason"]=="count_mismatch"
    assert not m.assess("A",["t0"],["foreign"])["comparable"]
    assert not m.assess("A",["t0"],["t0"])["comparable"]


@pytest.mark.parametrize("amount,expected",[(10.6,True),(10.600001,False)])
def test_decimal_absolute_caliper_boundary(amount,expected):
    # Total exactly 60: 1% permits 0.6, tighter than the 10% of 10 limit.
    h=fixture((10,str(amount),str(Decimal(40)-Decimal(str(amount))),10))
    assert matcher(h).assess("A",["t0"],["t1"])["comparable"] is expected


def test_relative_caliper_and_invalid_budgets():
    m=matcher(fixture((1,1.1,1.100001,100,100,100)))
    assert m.assess("A",["t0"],["t1"])["comparable"]
    assert not m.assess("A",["t0"],["t2"])["comparable"]
    assert not m.assess("A",["t0"],["t1","t2","t3"])["control_valid"]


def test_sparse_unmatched_and_search_bound_no_relaxation():
    m=matcher(fixture((10,10)))
    assert m.match(omission())["reason"]=="fewer_than_two_distinct_feasible_controls"
    assert m.match(omission())["controls"]==[]
    assert matcher(enumeration_limit=1).match(omission())["reason"]=="search_space_exceeds_bound"
    nohistory={**omission(),"focal_account":"ISO"}
    assert m.match(nohistory)["status"]=="unmatched"


def test_cutoff_population_and_seed_are_in_match_identity():
    h=fixture(); a=matcher(h).match(omission())
    for alternative in [replace(h,cutoff=100),replace(h,universe=h.universe+("Z",)),replace(h,history_sha256="changed")]:
        assert matcher(alternative).match(omission())["context_sha256"]!=a["context_sha256"]
    assert matcher(h,control_seed=2903).match(omission())["match_id"]!=a["match_id"]
    # Source event ordering cannot select different controls when IDs/context agree.
    assert matcher(replace(h,events=tuple(reversed(h.events)))).match(omission())==a


def test_family_balancing_uses_medians_of_matched_sets():
    rows=[pair(1,"temporal",2,[1,3]),pair(2,"temporal",4,[1,1]),pair(3,"counterparty",-2,[0,0]),
          {"match_id":"4","family":"budgeted","status":"unmatched","reason":"none"}]
    s=summarize(.25,rows)
    assert s["families"]["temporal"]["excess"]==2
    assert s["families"]["counterparty"]["excess"]==-2
    assert s["excess"]==0 and s["score"]==.25 and s["available_families"]==2
    assert s==summarize(.25,list(reversed(rows)))


def test_missing_zero_negative_and_zero_weight_identity():
    assert summarize(-.2,[])["fallback_reason"]=="no_valid_structured_interventions"
    assert summarize(-.2,[{"family":"temporal","status":"unmatched"}])["score"]==-.2
    assert summarize(.2,[pair(1,"temporal",0,[0,0])])["excess"]==0
    assert summarize(.2,[pair(1,"temporal",-.5,[0,0])])["score"]<.2
    raw={"B":-.2,"A":-.2,"C":.3}
    zero={u:summarize(s,[pair(1,"temporal",9,[0,0])],0)["score"] for u,s in raw.items()}
    assert zero==raw and ranks(zero)==ranks(raw) and ranks(zero)["A"]<ranks(zero)["B"]


def test_large_and_nonfinite_arithmetic_fails_explicitly():
    assert median([1e308,1e308])==1e308
    assert median([-1e308,1e308])==0
    assert summarize(0,[pair(1,"temporal",1e100,[0,0])])["score"]==1e100
    with pytest.raises(FloatingPointError): summarize(1e308,[pair(1,"temporal",1e308,[0,0])])
    with pytest.raises(FloatingPointError): summarize(1,[pair(1,"temporal",1e-30,[0,0])])
    with pytest.raises(FloatingPointError): summarize(0,[pair(1,"temporal",float("nan"),[0,0])])
    with pytest.raises(ValueError): summarize(0,[pair(1,"temporal",1,[0])])


def test_frozen_batch_no_fit_and_reference_feature_equivalence(monkeypatch):
    cfg=InterventionConfig(dataset_id="fixture",source_identity="fixture-v1",time_kind="simulation_hour",cutoff="9",window_size=3,window_unit="hours")
    h=load_history((ROOT/"docs/research/fixtures/phase3_transactions.csv").read_bytes(),cfg)
    vectors,_=recompute(h); training=np.asarray(list(vectors.values()),dtype=np.float32)
    # Only the unit fixture model is fitted, before exercising the inference-only API.
    model=IsolationForest(random_state=42,n_estimators=8,n_jobs=1).fit(training)
    def forbidden(*args,**kwargs): raise AssertionError("No fitting permitted in frozen scoring")
    monkeypatch.setattr(IsolationForest,"fit",forbidden)
    scorer=FrozenBatchScorer(model); local=FocalRecomputer(h)
    ref,_=recompute(h,("t1",)); actual,_=local.vector("A",("t1",))
    np.testing.assert_array_equal(actual,ref["A"])
    scores=scorer.verify_batch([actual,ref["A"],vectors["A"]])
    assert scores[0]==scores[1]
    np.testing.assert_array_equal(scores,scorer.verify_batch([actual,ref["A"],vectors["A"]]))
    with pytest.raises(ValueError): scorer.score([[1,2]])


def test_append_only_writer_and_preserved_originals(tmp_path):
    from backend.scripts.run_phase5h_specificity import save
    p=tmp_path/"new.json";save(p,{"a":1});before=p.read_bytes()
    with pytest.raises(FileExistsError): save(p,{"a":2})
    assert p.read_bytes()==before and verify_protected()==[]


def test_saved_phase5g_rows_integrate_with_unmodified_v1_statistics():
    from backend.scripts.run_phase5h_specificity import v1_statistics_for_account
    from backend.app.research.crest.schemas import CrestConfig
    from backend.app.research.crest.frozen_scorer import EmpiricalCalibrator
    folder=ROOT/"data/results/v2/phase5g-feasibility-v1-recovery"
    rows=[json.loads(line) for line in (folder/"pilot_interventions.jsonl").read_bytes().splitlines()]
    structured=[r for r in rows if r["kind"]=="structured"]
    cal=json.loads((ROOT/"data/results/v2/phase5-baselines-5k-v1/split-42-model-42/calibration.json").read_bytes())
    cfg=CrestConfig(**cal["config"]); empirical=EmpiricalCalibrator(cal["reference"])
    for u in sorted({r["focal_account"] for r in structured}):
        own=[r for r in structured if r["focal_account"]==u]
        summary=v1_statistics_for_account(u,own[0]["raw_baseline"],structured,empirical,cfg)
        assert summary["available_interventions"]==len(own)
        for f,stat in summary["families"].items():
            assert stat["valid_count"]==sum(r["family"]==f for r in own)
            assert all(v["omitted_fraction_range"][0]>=0 and v["omitted_amount_fraction_range"][1]<=.5
                       for v in stat["strata"].values())
