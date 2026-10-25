import json
import shutil
from pathlib import Path
import numpy as np
import pytest
from pydantic import ValidationError
from sklearn.ensemble import IsolationForest
from backend.app.research.crest.schemas import CrestConfig, MODES
from backend.app.research.crest.frozen_scorer import FrozenE4, EmpiricalCalibrator, matrix
from backend.app.research.crest.statistics import influence, stratum, summarize, concentration, candidate_score, rank_accounts
from backend.app.research.crest.artifacts import load_bundle
from backend.app.research.crest.runner import run
from backend.app.research.interventions.schemas import InterventionConfig, Budget
from backend.app.research.interventions.artifact_writer import write_run
from backend.app.services.research_protocol import ROOT, PROTOCOL, ResearchConfig, InputSpec, fit_and_score, sha, canonical
from backend.app.services.feature_service import CANONICAL_TRANSFER_FEATURES as NAMES


def config(**updates):
    fields = dict(source_dataset_id="synthetic-source",evaluation_dataset_id="synthetic-source",
        split_id="explicit-heldout-v1",source_manifest_sha256="0"*64,evaluation_manifest_sha256="0"*64,
        train_ids=("A","B","C","F","X","Y"),evaluation_ids=("D","E","ISOLATED"),n_estimators=20)
    fields.update(updates)
    return CrestConfig(**fields)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("crest-interventions")
    data = (ROOT/"docs/research/fixtures/phase3_transactions.csv").read_bytes()
    cfg = InterventionConfig(dataset_id="synthetic-source",source_identity="phase3-synthetic-demo-v1",
        time_kind="simulation_hour",cutoff="9",window_unit="hours",window_size=1,
        known_accounts=("ISOLATED",),budget=Budget(max_count=1,max_fraction=.5,min_retained=1,max_interventions=12))
    write_run(data,cfg,["A","B","C","D","E","F","X","Y","ISOLATED"],root,"input")
    return root/"input"


def bound_config(bundle, **updates):
    digest = sha((bundle/"manifest.json").read_bytes())
    return config(source_manifest_sha256=digest,evaluation_manifest_sha256=digest,**updates)


def test_e4_raw_orientation_and_original_protocol_identity():
    cfg = config()
    x = np.random.RandomState(5).normal(size=(6,19)).astype(np.float32)
    test = np.random.RandomState(7).normal(size=(8,19)).astype(np.float32)
    scorer = FrozenE4(x,cfg,NAMES)
    raw,_ = scorer.score(test,NAMES,scorer.identity)
    np.testing.assert_array_equal(raw,-scorer.model.decision_function(test))
    spec = InputSpec(dataset_id="unit",family="custom",transactions="unused",transactions_sha256="unused",
                     labels="unused",labels_sha256="unused",label_set_id="unused",
                     label_definition="not loaded",provenance_status="declared_not_independently_verified")
    e4 = ResearchConfig(source=spec,experiment="E4",model_seed=cfg.model_seed,n_estimators=cfg.n_estimators,
                        max_samples=cfg.max_samples,contamination=cfg.contamination)
    expected,_,_ = fit_and_score(x,[test],e4)
    np.testing.assert_array_equal(raw,expected[0])


def test_calibration_ties_boundaries_source_only():
    calibrator = EmpiricalCalibrator([0,1,1,2])
    np.testing.assert_array_equal(calibrator.transform([-1,0,1,2,3]),[0,.125,.5,.875,1])
    np.testing.assert_array_equal(EmpiricalCalibrator([4,4]).transform([3,4,5]),[0,.5,1])
    before = calibrator.reference.copy()
    calibrator.transform([-100,100]*30)
    np.testing.assert_array_equal(before,calibrator.reference)
    with pytest.raises(ValueError):
        calibrator.reference[0] = -5
    assert np.all(np.diff(calibrator.transform(np.linspace(-3,4,100))) >= 0)


@pytest.mark.parametrize("values", [[],[float("nan")],[float("inf")]])
def test_bad_calibration_rejected(values):
    with pytest.raises(ValueError):
        EmpiricalCalibrator(values)


def test_frozen_score_batch_and_identity_no_refitting(monkeypatch):
    cfg = config()
    data = np.arange(114).reshape(6,19)
    scorer = FrozenE4(data,cfg,NAMES)
    monkeypatch.setattr(scorer.model,"fit",lambda *a,**k: pytest.fail("Refit forbidden"))
    for batch in [1,2,100]:
        scores,q = scorer.score(data,NAMES,scorer.identity,batch)
        np.testing.assert_array_equal(scores,scorer.training_scores)
        np.testing.assert_array_equal(q,scorer.calibrator.transform(scorer.training_scores))
    wrong = dict(scorer.identity,split_id="wrong")
    with pytest.raises(ValueError,match="identity mismatch"):
        scorer.score(data,NAMES,wrong)


@pytest.mark.parametrize("names,data", [(list(reversed(NAMES)),[[0]*19]),(NAMES,[[0]*18]),(NAMES,[[float("nan")]*19])])
def test_exact_schema_finite_features(names,data):
    with pytest.raises(ValueError):
        matrix(data,names)


@pytest.mark.parametrize("original,after,expected", [(.8,.2,.6),(.2,.8,-.6),(.5,.5,0)])
def test_signed_profile(original,after,expected):
    r = influence(original,after)
    assert r["signed_change"] == pytest.approx(expected)
    assert r["positive_influence"] == pytest.approx(max(expected,0))
    assert r["negative_influence"] == pytest.approx(max(-expected,0))
    assert r["absolute_change"] == pytest.approx(abs(expected))


def row(delta,family="counterparty",count=1,fraction=.25,amount=.25):
    return {**influence(.5,.5-delta),"family":family,"omitted_count":count,
            "omitted_fraction":fraction,"omitted_amount_fraction":amount}


def grouped(rows,cfg):
    return [{**r,"budget_stratum":stratum(r,cfg)} for r in rows]


def test_equal_family_weight_unequal_counts_and_bounds():
    cfg = config()
    rows = grouped([row(.2)]*10+[row(-.4,"temporal")]*2,cfg)
    s = summarize(rows,[],cfg)
    assert s["sensitivity"] == pytest.approx(-.1)
    assert s["robustness"] == pytest.approx(.7)
    assert s["families"]["budgeted"]["robustness"] is None
    assert 0 <= s["robustness"] <= 1
    assert summarize(grouped([row(1)]*2,cfg),[],cfg)["robustness"] == 0


@pytest.mark.parametrize("values,status,expected", [
    ([],"insufficient_interventions",None),([.3],"insufficient_interventions",None),
    ([0,0],"zero_positive_influence",None),([.1,.3],"defined",.625),([.4,0],"defined",1)])
def test_concentration_edges(values,status,expected):
    result = concentration([{"positive_influence":v} for v in values],2)
    assert result["status"] == status
    assert result["value"] == pytest.approx(expected) if expected is not None else result["value"] is None


def test_budget_strata_never_pool_unequal_counts():
    cfg = config()
    rows = grouped([row(.1),row(.3),row(.4,count=2,fraction=.5,amount=.5)],cfg)
    stats = summarize(rows,[],cfg)
    strata = stats["families"]["counterparty"]["strata"]
    assert len(strata)==2
    assert strata[rows[0]["budget_stratum"]]["concentration"]["value"] == pytest.approx(.625)
    assert strata[rows[2]["budget_stratum"]]["concentration"]["value"] is None
    selected = cfg.model_copy(update={"ranking_stratum":rows[2]["budget_stratum"]})
    assert summarize(rows,[],selected)["sensitivity"] == pytest.approx(.4)


@pytest.mark.parametrize("mode",MODES)
def test_zero_weights_exact_baseline_and_stable_ties(mode):
    cfg = config(alpha=0,beta=0)
    unavailable = summarize([],[],cfg)
    accounts = [{"account_id":u,"calibrated_score":q,"statistics":unavailable} for u,q in [("z",.3),("b",.8),("a",.8)]]
    ranked = rank_accounts(accounts,mode,cfg)
    assert [r["account_id"] for r in ranked] == ["a","b","z"]
    assert [r["final_score"] for r in ranked] == [.8,.8,.3]
    assert rank_accounts(list(reversed(accounts)),mode,cfg) == ranked


def test_modes_formula_and_insufficient_fallback():
    stats = {"sensitivity":.2,"robustness":.6}
    assert candidate_score(.8,stats,"E6_HYBRID",.25,.5)[0] == pytest.approx(.69)
    assert candidate_score(.8,stats,"E6_SENSITIVITY",.25,.5)[0] == pytest.approx(.85)
    assert candidate_score(.8,stats,"E6_ROBUSTNESS",.25,.5)[0] == pytest.approx(.64)
    assert candidate_score(.8,stats,"E6_CONCENTRATION_DIAGNOSTIC",999,999)[0] == .8
    empty = summarize([],[],config())
    for mode in ["E6_HYBRID","E6_ROBUSTNESS","E6_SENSITIVITY"]:
        score,warnings = candidate_score(.8,empty,mode,.25,.25)
        assert score == .8 and warnings
    assert empty["robustness"] is None
    partial = summarize(grouped([row(.2)],config()),[],config())
    assert partial["robustness"] is None
    assert candidate_score(.8,partial,"E6_HYBRID",.25,.25)[0] == .8
    assert candidate_score(.9,stats,"E6_SENSITIVITY",10,0)[0] == 1
    unavailable = summarize([], [{"reason":"no_historical_evidence","status":"rejected"}],config())
    assert unavailable["rejected_interventions"] == 1
    assert all(f["candidate_count"]==0 for f in unavailable["families"].values())


@pytest.mark.parametrize("changes", [{"alpha":-1},{"beta":float("nan")},{"train_ids":("D","E")},
    {"fraction_edges":(0,.5,.5,1)},{"min_robustness_per_family":1},{"batch_size":0}])
def test_invalid_config(changes):
    with pytest.raises(ValidationError):
        config(**changes)


def test_verified_bundle_rejects_corruption_and_schema(bundle,tmp_path):
    cfg = bound_config(bundle)
    loaded = load_bundle(bundle,cfg.source_manifest_sha256,cfg.source_dataset_id)
    assert len(loaded["baseline"])==9
    with pytest.raises(ValueError,match="checksum"):
        load_bundle(bundle,"0"*64,cfg.source_dataset_id)
    with pytest.raises(ValueError,match="dataset"):
        load_bundle(bundle,cfg.source_manifest_sha256,"wrong")
    clone = tmp_path/"clone"
    shutil.copytree(bundle,clone)
    (clone/"baseline.json").write_bytes(b"{}")
    with pytest.raises(ValueError,match="checksum"):
        load_bundle(clone,cfg.source_manifest_sha256,cfg.source_dataset_id)
    m = json.loads((clone/"manifest.json").read_bytes())
    m["feature_schema"]["selected"] = list(reversed(NAMES))
    raw = canonical(m)
    (clone/"manifest.json").write_bytes(raw)
    with pytest.raises(ValueError,match="schema"):
        load_bundle(clone,sha(raw),cfg.source_dataset_id)


def test_complete_run_no_labels_graph_recompute_or_heldout_fit(bundle,tmp_path,monkeypatch):
    from backend.app.services.label_registry import label_registry
    from backend.app.services.graph_service import GraphService
    monkeypatch.setattr(label_registry,"get_labels",lambda *a: pytest.fail("Labels forbidden"))
    monkeypatch.setattr(GraphService,"build_graph",lambda *a: pytest.fail("Feature artifacts must be reused"))
    cfg = bound_config(bundle)
    actual_fit, calls = IsolationForest.fit, []
    def fit(self,x,*args,**kwargs):
        calls.append(np.asarray(x).copy())
        return actual_fit(self,x,*args,**kwargs)
    monkeypatch.setattr(IsolationForest,"fit",fit)
    result = run(cfg,bundle,bundle,tmp_path,"one")
    source = json.loads((bundle/"baseline.json").read_text())["focal_features"]
    assert len(calls)==1
    np.testing.assert_array_equal(calls[0],np.asarray([source[u] for u in sorted(cfg.train_ids)],dtype=np.float32))
    assert result["protocol"]==PROTOCOL and result["model_identity"]["split_id"]==cfg.split_id
    for name,digest in result["artifact_sha256"].items():
        assert sha((tmp_path/"one"/name).read_bytes())==digest
    accounts = json.loads((tmp_path/"one/accounts.json").read_text())
    isolated = next(a for a in accounts if a["account_id"]=="ISOLATED")
    assert isolated["statistics"]["robustness"] is None
    assert isolated["most_influential_omission"] is None


def test_saved_config_replay_and_output_guard(bundle,tmp_path):
    cfg = bound_config(bundle)
    a = run(cfg,bundle,bundle,tmp_path,"a")
    saved = json.loads((tmp_path/"a/config.json").read_text())
    b = run(CrestConfig(**saved["configuration"]),tmp_path/"a"/saved["source_directory"],
            tmp_path/"a"/saved["evaluation_directory"],tmp_path,"b")
    for name in ["accounts.json","rankings.json","calibration.json","intervention_scores.jsonl"]:
        assert a["artifact_sha256"][name] == b["artifact_sha256"][name]
    assert a["model_id"]==b["model_id"] and a["model_sha256"]==b["model_sha256"]
    with pytest.raises(FileExistsError):
        run(cfg,bundle,bundle,tmp_path,"a")
    with pytest.raises(ValueError):
        run(cfg,bundle,bundle,ROOT/"data/results","historical")


def test_missing_training_membership_fails(bundle,tmp_path):
    cfg = bound_config(bundle,train_ids=("MISSING","OTHER"))
    with pytest.raises(ValueError,match="membership"):
        run(cfg,bundle,bundle,tmp_path,"bad")
    assert not (tmp_path/"bad").exists()


def test_target_representation_cannot_refit_source_calibration(bundle,tmp_path):
    cfg = bound_config(bundle)
    first = run(cfg,bundle,bundle,tmp_path,"source-evaluation")
    data = (ROOT/"docs/research/fixtures/phase3_transactions.csv").read_bytes().replace(b",10,",b",1000,")
    target_cfg = InterventionConfig(dataset_id="different-target",source_identity="explicit-target-fixture",
        time_kind="simulation_hour",cutoff="9",window_unit="hours",window_size=1,
        known_accounts=("ISOLATED",),budget=Budget(max_count=1,max_fraction=.5,min_retained=1))
    write_run(data,target_cfg,["D","E","ISOLATED"],tmp_path,"target")
    target = tmp_path/"target"
    changed = bound_config(bundle,evaluation_dataset_id="different-target")
    changed = changed.model_copy(update={"evaluation_manifest_sha256":sha((target/"manifest.json").read_bytes())})
    second = run(changed,bundle,target,tmp_path,"target-evaluation")
    assert first["model_id"]==second["model_id"] and first["model_sha256"]==second["model_sha256"]
    assert (tmp_path/"source-evaluation/calibration.json").read_bytes()==(tmp_path/"target-evaluation/calibration.json").read_bytes()


def test_demo_reuses_verified_features(tmp_path,monkeypatch):
    from backend.scripts import demonstrate_phase4 as demo
    from backend.app.services.graph_service import GraphService
    path,digest,reused = demo.prepare_demo(tmp_path)
    assert not reused
    monkeypatch.setattr(demo,"write_run",lambda *a,**k:pytest.fail("Matching evidence must be reused"))
    monkeypatch.setattr(GraphService,"build_graph",lambda *a:pytest.fail("No graph recomputation"))
    assert demo.prepare_demo(tmp_path)==(path,digest,True)


@pytest.mark.parametrize("mutation",["cutoff","datahash","coverage","baseline","budget","identity"])
def test_semantically_incompatible_artifacts_rejected(bundle,tmp_path,mutation):
    clone = tmp_path/"input"
    shutil.copytree(bundle,clone)
    m = json.loads((clone/"manifest.json").read_text())
    if mutation=="cutoff":
        m["historical_cutoff"]["boundary"]="<"
    elif mutation=="datahash":
        m["source"]["transactions_sha256"]="unknown"
    elif mutation=="coverage":
        m["results"]["accepted"]+=1
    else:
        records = [json.loads(x) for x in (clone/"interventions.jsonl").read_text().splitlines()]
        record = next(x for x in records if x["status"]=="accepted")
        if mutation=="baseline":
            record["baseline_features"][0]+=1
        elif mutation=="budget":
            record["omitted_count"]+=100
        else:
            record["intervention_id"]="wrong"
        content = b"".join(canonical(x)+b"\n" for x in records)
        (clone/"interventions.jsonl").write_bytes(content)
        m["artifact_sha256"]["interventions.jsonl"]=sha(content)
    raw = canonical(m)
    (clone/"manifest.json").write_bytes(raw)
    with pytest.raises(ValueError):
        load_bundle(clone,sha(raw),"synthetic-source")
