"""Run a tiny score-only selected CREST probe, with full held-out fallback ranking.

The top five is fixed in the new protocol before evaluation labels are loaded.
This is exploratory selective inference, not full-population CREST.
"""
import io, json, sys, time
from pathlib import Path
import joblib, numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from backend.app.services.research_protocol import canonical, sha
from backend.app.research.interventions.schemas import InterventionConfig, Budget
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.intervention_engine import InterventionEngine
from backend.app.research.crest.frozen_scorer import EmpiricalCalibrator
from backend.app.research.benchmark.analysis import aggregate, make_profiles
from backend.app.research.benchmark.metrics import metrics, paired_bootstrap, stability

def save(path, value): path.write_bytes(canonical(value))

def main():
    title="Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions"
    run="phase5r-selective-top5-v1"; dest=ROOT/"data/results/v2"/run; dest.mkdir(exist_ok=False)
    started=time.perf_counter(); protocol=json.loads((ROOT/"docs/research/configs/phase5_protocol_v1.json").read_bytes())
    phash=sha((ROOT/"docs/research/configs/phase5_protocol_v1.json").read_bytes())
    feat=ROOT/"data/results/v2/phase5-features-5k-v1"; base=ROOT/"data/results/v2/phase5-baselines-5k-v1"
    fman=json.loads((feat/"manifest.json").read_bytes()); bman=json.loads((base/"manifest.json").read_bytes())
    if fman["preregistered_protocol_sha256"]!=phash or bman["preregistered_protocol_sha256"]!=phash:
        raise ValueError("Frozen protocol identity mismatch.")
    split=json.loads((feat/"splits.json").read_bytes())["42"]
    test_ids=split["test_ids"]; key="split-42-model-42"; folder=base/key
    baseline=json.loads((folder/"scores.json").read_bytes()); calibration=json.loads((folder/"calibration.json").read_bytes())
    raw0=baseline["E4"]; q0=baseline["E6_BASE"]
    # Prespecified deterministic selection uses only held-out baseline scores.
    selected=sorted(test_ids,key=lambda u:(-float(raw0[u]),u))[:5]
    matrix=np.load(feat/"features.npy",allow_pickle=False)
    source=json.loads((feat/"population.json").read_bytes())
    index={u:i for i,u in enumerate(source["ids"])}
    content=(ROOT/protocol["datasets"]["5k"]["transactions"]).read_bytes()
    if sha(content)!=protocol["datasets"]["5k"]["transactions_sha256"]: raise ValueError("Dataset hash mismatch.")
    frame=pd.read_csv(io.BytesIO(content),dtype=str)
    cutoff=str(pd.to_datetime(frame.timestamp).max())
    events=[]; configs={}; wall_budget=900.0
    with (dest/"interventions.jsonl").open("wb") as stream:
        for family in protocol["intervention"]["families"]:
            cfg=InterventionConfig(dataset_id=protocol["datasets"]["5k"]["dataset_id"],
                source_identity="supplied-ibm-5k-phase5-v1",time_kind="timestamp_utc",cutoff=cutoff,
                window_size=protocol["intervention"]["window_hours"],window_unit="hours",
                intervention_seed=protocol["intervention"]["seed"],families=(family,),
                budget=Budget(**protocol["intervention"]["budget"]))
            configs[family]=cfg.model_dump(); history=load_history(content,cfg); engine=InterventionEngine(history,cfg)
            for u in selected:
                if time.perf_counter()-started > wall_budget:
                    save(dest/"selection.json",{"selection":"top-5 E4 raw anomaly scores, ties lexical account ID","selected_ids":selected,
                        "selection_seed":None,"labels_accessed_before_selection":False})
                    save(dest/"incomplete.json",{"status":"incomplete","reason":"new selective-probe 900-second safety budget exceeded",
                        "elapsed_seconds":time.perf_counter()-started,"partial_record_count":len(events),
                        "performance_metrics":"not computed for incomplete selected-family coverage"})
                    return
                for row in engine.generate(u):
                    stream.write(canonical(row)+b"\n"); stream.flush(); events.append(row)
    save(dest/"selection.json",{"selection":"top-5 E4 raw anomaly scores, ties lexical account ID","selected_ids":selected,
        "selection_seed":None,"labels_accessed_before_selection":False,"population":"split-42 held-out 1,500 accounts"})
    save(dest/"configurations.json",configs)
    accepted=[r for r in events if r["status"]=="accepted"]
    model=joblib.load(folder/"model.joblib")
    values=np.asarray([r["intervened_features"] for r in accepted],dtype=np.float32).reshape(-1,19)
    raw_intervened=-model.decision_function(values) if len(values) else np.array([],dtype=float)
    calibrator=EmpiricalCalibrator(calibration["reference"]); q_intervened=calibrator.transform(raw_intervened)
    crest_config=calibration["config"]
    from backend.app.research.crest.schemas import CrestConfig
    c=CrestConfig(**crest_config)
    profiles=make_profiles(events,raw0,q0,raw_intervened,q_intervened,c)
    rejected=[r for r in events if r["status"]=="rejected"]
    scores,coverage,account_stats=aggregate(test_ids,q0,profiles,rejected,c)
    # All scores are now finalized. Only now read evaluation labels.
    labels={u:int(source["labels"][u]) for u in test_ids}
    rankings={"E4":raw0,**scores}
    rows={m:metrics(test_ids,labels,s) for m,s in rankings.items()}
    paired={m:paired_bootstrap(test_ids,labels,s,raw0,2718,1000) for m,s in scores.items()}
    stability_rows={m:stability(test_ids,raw0,s) for m,s in scores.items()}
    save(dest/"profiles.json",profiles); save(dest/"scores.json",rankings)
    save(dest/"evaluation.json",{"population":"complete split-42 held-out set","selection_count":len(selected),
        "intervention_account_coverage":len({r["focal_account"] for r in accepted}),"accepted_interventions":len(accepted),
        "rejected_candidates":len(rejected),"processing_seconds":time.perf_counter()-started,
        "methods":rows,"paired_vs_e4":paired,"rank_stability_vs_e4":stability_rows,
        "label_prevalence":sum(labels.values())/len(labels),"labels_used_only_after_scores_finalized":True,
        "account_diagnostics":account_stats,"coverage":coverage})
    artifacts={p.name:sha(p.read_bytes()) for p in dest.iterdir() if p.is_file()}
    manifest={"stage":"phase5r-selective-inference-exploratory-v1","project_title":title,
        "parent_phase5_protocol_sha256":phash,"selective_protocol":"phase5r-selective-top5-v1",
        "selection":"top-5 E4 raw anomaly scores over complete 5k split-42 held-out population; lexical tie-break; no labels",
        "selection_bias":"baseline-score-driven; selected population is not representative and has only 5 accounts",
        "fallback":"E6_BASE calibrated E4 scores for every nonselected held-out account",
        "dataset_sha256":protocol["datasets"]["5k"]["transactions_sha256"],
        "label_set_id":protocol["datasets"]["5k"]["label_set_id"],"label_sha256":protocol["datasets"]["5k"]["labels_sha256"],
        "feature_manifest_sha256":sha((feat/"manifest.json").read_bytes()),"baseline_manifest_sha256":sha((base/"manifest.json").read_bytes()),
        "algorithm_versions":{"interventions":"transaction-evidence-omission-v1","scoring":"e6-crest-frozen-e4-v1"},
        "seeds":{"model":42,"intervention":protocol["intervention"]["seed"],"bootstrap":2718},
        "configuration":{"selected_accounts":5,"families":protocol["intervention"]["families"],"alpha":protocol["weights"]["alpha"],
            "beta":protocol["weights"]["beta"],"wall_budget_seconds":wall_budget},
        "artifacts":artifacts,"total_seconds":time.perf_counter()-started,
        "scope_warning":"exploratory selective protocol, not equivalent to frozen full-population CREST; no general performance claim"}
    save(dest/"manifest.json",manifest)
    print(json.dumps({"directory":str(dest),"manifest":manifest,"evaluation":json.loads((dest/"evaluation.json").read_bytes())},indent=2),flush=True)

if __name__=="__main__": main()
