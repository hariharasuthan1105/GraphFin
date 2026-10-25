import json
from pathlib import Path
import numpy as np
import pytest
from sklearn.metrics import average_precision_score
from backend.app.research.benchmark.metrics import aligned, metrics, paired_bootstrap, stability
from backend.app.research.benchmark.analysis import aggregate, permuted_control, make_profiles
from backend.app.research.benchmark.protocol import read
from backend.app.research.benchmark.runner import verify, output
from backend.app.research.crest.schemas import CrestConfig, MODES
from backend.app.services.research_protocol import ROOT, canonical, sha
from backend.app.research.crest.monotonic_calibration import SourceLogisticCalibration


def cfg():
    return CrestConfig(source_dataset_id="x",evaluation_dataset_id="x",split_id="s",
        source_manifest_sha256="a"*64,evaluation_manifest_sha256="a"*64,
        train_ids=("a","b"),evaluation_ids=("c","d"))


def test_exploratory_logistic_calibration_is_source_fit_and_rank_preserving():
    calibrator = SourceLogisticCalibration([-3.0, -1.0, 0.0, 1.0, 3.0])
    raw = np.array([-2.0, -2.0, -0.5, 0.0, 2.0])
    mapped = calibrator.transform(raw)
    assert mapped[0] == mapped[1]
    assert np.all(np.diff(mapped[[0, 2, 3, 4]]) > 0)
    assert len(np.unique(mapped)) == len(np.unique(raw))
    assert calibrator.metadata()["fit_population"] == "source-training raw scores only"
    with pytest.raises(FloatingPointError, match="tie"):
        calibrator.transform(np.array([1e9, 1e9+1.0]))


def row(family,ident,delta,u="c"):
    return {"family":family,"intervention_id":ident,"focal_account":u,
        "budget_stratum":"n=1;f=0;a=0","signed_change":delta,"absolute_change":abs(delta),
        "positive_influence":max(delta,0),"negative_influence":max(-delta,0),
        "calibrated_baseline_score":.5,"calibrated_intervened_score":.5-delta,
        "omitted_count":1,"omitted_fraction":.25,"omitted_amount_fraction":.25}


@pytest.mark.parametrize("labels,scores",[
    ({"a":1},{"a":.1,"b":.2}),({"a":1,"b":2},{"a":.1,"b":.2}),
    ({"a":1,"b":0},{"a":float("nan"),"b":.2})])
def test_exact_population(labels,scores):
    with pytest.raises(ValueError):
        aligned(["a","b"],labels,scores)


def test_alignment_and_ties():
    ids = ["b","a","d","c"]
    labels = {"a":1,"b":0,"c":1,"d":0}
    scores = dict.fromkeys(ids,.5)
    result = metrics(ids,labels,scores)
    assert result["average_precision"]==.5
    assert result["tied_accounts"]==4
    assert result["top_k"]["10"]=={"requested_k":10,"effective_k":4,"retrieved_positives":2,"precision":.5,"recall":1.0}
    assert metrics(list(reversed(ids)),labels,scores)==result


def test_paired_bootstrap_manual():
    ids = list("abcd")
    labels = dict(zip(ids,[1,0,1,0]))
    a,b = dict(zip(ids,[.8,.8,.2,.1])),dict(zip(ids,[.8,.2,.2,.1]))
    actual = paired_bootstrap(ids,labels,a,b,31,50)
    rng = np.random.RandomState(31)
    y=np.array([1,0,1,0]); aa=np.array(list(a.values())); bb=np.array(list(b.values()))
    values=[]
    for _ in range(50):
        idx=np.concatenate([rng.choice([0,2],2,replace=True),rng.choice([1,3],2,replace=True)])
        values.append(average_precision_score(y[idx],aa[idx])-average_precision_score(y[idx],bb[idx]))
    assert actual["interval95"]==np.quantile(values,[.025,.975]).tolist()
    assert actual["valid"]==50 and actual["rejected"]==0
    assert paired_bootstrap(ids,labels,a,a,31,50)["interval95"]==[0,0]


@pytest.mark.parametrize("ys,defined", [([0,0,0],False),([1,0,0],True),([1,1,1],True)])
def test_rare_positive_policy(ys,defined):
    ids=list("abc"); labels=dict(zip(ids,ys)); scores=dict(zip(ids,[.4,.3,.2]))
    ci=paired_bootstrap(ids,labels,scores,scores,4,10)
    assert (ci["interval95"] is not None)==defined
    assert ci["valid"]==(10 if defined else 0)
    assert (metrics(ids,labels,scores)["average_precision"] is not None)==defined


def test_ablations_and_fallback():
    rows=[row("counterparty","1",.2),row("counterparty","2",.2),row("temporal","3",-.4)]
    scores,coverage,accounts=aggregate(["c","d"],{"c":.5,"d":.7},rows,[],cfg())
    assert set(MODES)<=scores.keys()
    assert accounts["c"]["sensitivity"]==pytest.approx(-.1)
    assert scores["ABLATION_COUNTERPARTY"]["c"]==pytest.approx(.525)
    assert scores["ABLATION_TEMPORAL"]["c"]==.5  # one candidate: robustness unavailable
    assert scores["ABLATION_BUDGETED"]["c"]==.5
    assert scores["E6_HYBRID"]["d"]==.7
    assert coverage["E6_HYBRID"]["fallback_rate"]==.5
    assert scores["ABLATION_CANDIDATE_WEIGHTED"]["c"]!=scores["E6_HYBRID"]["c"]


def test_control_matches_budgets_and_is_label_free():
    rows=[row("counterparty",str(i),i*.05,u="c" if i%2 else "d") for i in range(6)]
    first,info=permuted_control(rows,22)
    second,_=permuted_control(list(reversed(rows)),22)
    assert first==second and info["records"]==6
    lookup={r["intervention_id"]:r for r in rows}
    for r in first:
        before=lookup[r["intervention_id"]]
        assert [r[k] for k in ["family","omitted_count","omitted_fraction","omitted_amount_fraction"]]==[
            before[k] for k in ["family","omitted_count","omitted_fraction","omitted_amount_fraction"]]


def test_ranking_stability_requires_identity():
    a={"a":1,"b":1,"c":0}; b={"a":0,"b":1,"c":1}
    assert stability(list(a),a,a)["mean_absolute_rank_displacement"]==0
    assert stability(list(a),a,a)["spearman_ordinal_ranks"]==1
    assert stability(list(a),a,b)["mean_absolute_rank_displacement"]>0
    with pytest.raises(ValueError):
        stability(["a","b"],a,b)


def test_protocol_frozen_and_explicit(tmp_path):
    p,h=read(ROOT/"docs/research/configs/phase5_protocol_v1.json")
    assert p["detector"]=={"n_estimators":100,"max_samples":"auto","contamination":.005,"n_jobs":1}
    assert p["weights"]["alpha"]==p["weights"]["beta"]==.25
    assert p["primary"]["split_seeds"]==[42,123,7,2024,99,555]
    assert "exploratory" in p and "primary" in p
    path=tmp_path/"protocol.json"; path.write_bytes(canonical(p))
    path.with_suffix(".sha256").write_text(h)
    read(path)
    path.write_bytes(b"{}")
    with pytest.raises(ValueError):
        read(path)


def test_manifest_and_append_only(tmp_path,monkeypatch):
    import backend.app.research.benchmark.runner as runner
    monkeypatch.setattr(runner,"ROOT",tmp_path)
    (tmp_path/"data/results/v2").mkdir(parents=True)
    dest=output("test")
    with pytest.raises(FileExistsError):
        output("test")
    save=dest/"scores.json"; save.write_bytes(b"{}")
    (dest/"manifest.json").write_bytes(canonical({"preregistered_protocol_sha256":"h","artifact_sha256":{"scores.json":sha(b"{}")}}))
    verify(dest,"h")
    save.write_bytes(b"[]")
    with pytest.raises(ValueError):
        verify(dest,"h")


def test_missing_intervention_score_rejected():
    with pytest.raises(ValueError):
        make_profiles([{"status":"accepted"}],{}, {},[],[],cfg())


def test_zero_weights_in_all_ablations():
    c=cfg().model_copy(update={"alpha":0,"beta":0})
    scores,_,_=aggregate(["c","d"],{"c":.5,"d":.7},[],[],c)
    assert all(s=={"c":.5,"d":.7} for s in scores.values())


def test_runner_isolation_and_replay(tmp_path,monkeypatch):
    import backend.app.research.benchmark.runner as runner
    from sklearn.ensemble import IsolationForest
    p,ph=read(ROOT/"docs/research/configs/phase5_protocol_v1.json")
    # A tiny test-only protocol, never a benchmark result.
    p["primary"]["split_seeds"]=[42]
    p["uncertainty"]["draws"]=10
    features=tmp_path/"features"; features.mkdir()
    ids=list("abcdefgh")
    x=np.arange(8*23,dtype=np.float32).reshape(8,23)
    np.save(features/"features.npy",x,allow_pickle=False)
    runner.save(features/"population.json",{"ids":ids,"labels":dict(zip(ids,[0,0,0,1,0,1,0,0]))})
    runner.save(features/"splits.json",{"42":{"train_ids":ids[:4],"test_ids":ids[4:]}})
    runner.save(features/"manifest.json",{"preregistered_protocol_sha256":ph,"tier":"5k",
        "source":{},"artifact_sha256":{f.name:sha(f.read_bytes()) for f in features.iterdir()}})
    original=IsolationForest.fit
    fitted=[]
    def guarded(self,values,y=None,**kwargs):
        assert y is None and len(values)==4
        assert np.max(values)<np.min(x[4:])  # all rows must be source training
        assert self.n_estimators==100 and self.random_state==42 and self.contamination==.005
        fitted.append(values.shape[1])
        return original(self,values,y,**kwargs)
    monkeypatch.setattr(IsolationForest,"fit",guarded)
    a,b=tmp_path/"a",tmp_path/"b"; a.mkdir(); b.mkdir()
    runner.evaluate(p,ph,features,a)
    runner.evaluate(p,ph,features,b)
    assert fitted==[19,6,14,11,4]*2
    key="split-42-model-42"
    for name in ["scores.json","results.json","calibration.json","model.joblib"]:
        assert (a/key/name).read_bytes()==(b/key/name).read_bytes()
    runner.verify(a,ph)
    # Alter evaluation labels only: rankings/model remain invariant.
    population=json.loads((features/"population.json").read_bytes())
    for u in ids[4:]:
        population["labels"][u]=1-population["labels"][u]
    runner.save(features/"population.json",population)
    manifest=json.loads((features/"manifest.json").read_bytes())
    manifest["artifact_sha256"]["population.json"]=sha((features/"population.json").read_bytes())
    runner.save(features/"manifest.json",manifest)
    c=tmp_path/"c"; c.mkdir()
    runner.evaluate(p,ph,features,c)
    assert (a/key/"scores.json").read_bytes()==(c/key/"scores.json").read_bytes()
