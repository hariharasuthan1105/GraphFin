import numpy as np
import pytest
from backend.app.services.research_protocol import ROOT
from backend.app.research.interventions.schemas import InterventionConfig, Budget
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.feature_recomputation import recompute
from backend.app.research.interventions.intervention_engine import budget_check
from backend.app.research.feasibility_gate.raw_scoring import TrainingAffine, raw_modes
from backend.app.research.feasibility_gate.focal_features import FocalRecomputer
from backend.app.research.feasibility_gate.pilot_design import CandidateIndex, matched_random, select_cohort


def history(sampled=False):
    cfg=InterventionConfig(dataset_id="fixture",source_identity="fixture-v1",time_kind="simulation_hour",
        cutoff="9",window_size=3,window_unit="hours",known_accounts=tuple(f"I{i:04}" for i in range(2001)) if sampled else ("ISOLATED",),
        budget=Budget(max_count=2,max_fraction=.5,max_amount_fraction=.5,min_retained=1,max_interventions=2))
    return load_history((ROOT/"docs/research/fixtures/phase3_transactions.csv").read_bytes(),cfg),cfg


@pytest.mark.parametrize("sampled",[False,True])
def test_focal_exact_equivalence_all_features_and_scenarios(sampled):
    h,cfg=history(sampled); focal=FocalRecomputer(h)
    for omitted in [(),("t1",),("t1","t2"),("t3","t4")]:
        expected,mode=recompute(h,omitted)
        for account in ["A","B","X","ISOLATED" if not sampled else "I0000"]:
            actual,meta=focal.vector(account,omitted)
            np.testing.assert_array_equal(actual,expected[account])
            assert meta["k"]==mode["k"] and meta["seed"]==mode["seed"]
        repeated,_=focal.vector("A",omitted,use_cache=False)
        np.testing.assert_array_equal(repeated,expected["A"])
    with pytest.raises(ValueError): focal.vector("A",("unknown",))
    with pytest.raises(ValueError): focal.vector("UNKNOWN")


def test_affine_rank_identity_ties_and_source_only_fallbacks():
    for train in [[-2.,-1.,0.,1.,2.],[1.,1.,1.],[0.,0.,0.,0.,8.]]:
        cal=TrainingAffine(train); raw=np.array([-4.,-1.,-1.,0.,2.,5.])
        z=cal.transform(raw)
        assert list(np.argsort(raw,kind="stable"))==list(np.argsort(z,kind="stable"))
        assert z[1]==z[2] and cal.scale>0
        for value in z:
            modes=raw_modes(value,{},alpha=0,beta=0)
            assert all(s==value for s in modes["scores"].values())
    # Distinct negative tiny values can disappear under a large subtraction.
    cal=TrainingAffine([1.,1.,1.])
    with pytest.raises(FloatingPointError): cal.transform([0.,np.nextafter(0.,1.)])
    with pytest.raises(ValueError): TrainingAffine([])


def test_raw_sensitivity_sign_robustness_fallback_no_clipping():
    stats=raw_modes(4.,{"counterparty":[.5,-.1],"temporal":[.2]})
    assert stats["sensitivity"]>0 and 0<stats["robustness"]<1
    assert stats["scores"]["RAW_SENSITIVITY"]>4
    assert stats["scores"]["RAW_ROBUSTNESS"]<4
    assert raw_modes(-4.,{"counterparty":[.1,.2]})["scores"]["RAW_ROBUSTNESS"]==-4
    assert raw_modes(4.,{"budgeted":[.2]})["fallbacks"]["RAW_HYBRID"]==["robustness_unavailable"]


def test_matched_controls_deterministic_and_budget_valid():
    h,cfg=history(); index=CandidateIndex(h,cfg)
    for row in index.bounded("A"):
        if row["status"]!="accepted": continue
        a=matched_random(index.incident["A"],row,cfg.budget)
        b=matched_random(index.incident["A"],row,cfg.budget)
        assert a==b and a["status"]=="accepted"
        assert len(a["omitted_transaction_ids"])==len(row["omitted_transaction_ids"])
        assert budget_check(index.incident["A"],a["omitted_transaction_ids"],cfg.budget)[0] is None


def test_selection_label_free_and_independent_of_dict_iteration():
    h,cfg=history(); index=CandidateIndex(h,cfg)
    scores={u:float(i) for i,u in enumerate(h.universe)}
    a=select_cohort(scores,index,per_stratum=1)
    b=select_cohort(dict(reversed(list(scores.items()))),index,per_stratum=1)
    assert a==b
    assert {r["score_stratum"] for r in a}=={"low","middle","high"}


def test_focal_extremes_parallel_repeated_times_and_cache_defensive_copy():
    lines=["source_row_id,sender_id,receiver_id,amount,step",
           "0,A,B,0.000001,1","1,A,B,1000000000000,1","2,B,A,0.01,1",
           "3,X,Y,3,2","4,Y,X,4,2"]
    lines.extend(f"{i+5},A,C{i},0.015,{i%3}" for i in range(30))
    cfg=InterventionConfig(dataset_id="extreme",source_identity="extreme-v1",time_kind="simulation_hour",
        cutoff="10",window_size=3,window_unit="hours",known_accounts=("ISOLATED",))
    h=load_history(("\n".join(lines)+"\n").encode(),cfg); f=FocalRecomputer(h)
    omitted=(h.events[0].transaction_id,h.events[3].transaction_id)
    reference,_=recompute(h,omitted)
    for u in h.universe:
        actual,_=f.vector(u,omitted)
        np.testing.assert_array_equal(actual,reference[u])
    original,_=f.vector("A",omitted);original[0]=-100
    actual,meta=f.vector("A",omitted)
    assert actual[0]>=0 and meta["cache_hit"]


def test_new_output_writer_is_append_only(tmp_path):
    from backend.scripts.run_phase5g_gate import save
    p=tmp_path/"artifact.json";save(p,{"status":"partial"})
    before=p.read_bytes()
    with pytest.raises(FileExistsError):save(p,{"status":"complete"})
    assert p.read_bytes()==before
