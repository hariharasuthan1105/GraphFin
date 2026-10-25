"""Append-only Phase 5 stages. Invoke via python -m ...benchmark.runner."""
import argparse
import io
import json
import platform
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import psutil
import sklearn
from sklearn.model_selection import train_test_split
from ...services.research_protocol import ROOT, PROTOCOL, canonical, sha, InputSpec, ResearchConfig, load_input, fit_and_score, GROUPS
from ...services.feature_service import CANONICAL_TRANSFER_FEATURES, FEATURE_NAMES
from ..interventions.schemas import InterventionConfig, Budget
from ..interventions.historical_evidence import load_history
from ..interventions.intervention_engine import InterventionEngine
from ..crest.schemas import CrestConfig
from ..crest.frozen_scorer import FrozenE4
from .protocol import read, TITLE
from .analysis import aggregate, make_profiles, permuted_control
from .metrics import metrics, paired_bootstrap, stability


def output(run_id):
    if not run_id.replace("-","").replace("_","").isalnum():
        raise ValueError("Invalid run ID.")
    path = ROOT/"data/results/v2"/run_id
    path.mkdir(exist_ok=False)
    return path


def save(path, data):
    path.write_bytes(canonical(data))


def complete(dest, protocol_hash, stage, extra, start):
    files = {p.name:sha(p.read_bytes()) for p in dest.iterdir() if p.is_file() and p.name!="manifest.json"}
    code = {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in (ROOT/"backend/app").rglob("*.py")}
    m = {"protocol":PROTOCOL,"project_title":TITLE,"stage":stage,"preregistered_protocol_sha256":protocol_hash,
        "artifact_sha256":files,"code_files":code,"code_sha256":sha(canonical(code)),
        "environment":{"python":platform.python_version(),"numpy":np.__version__,"sklearn":sklearn.__version__,
            "pandas":pd.__version__},"memory":psutil.Process().memory_info()._asdict(),
        "total_seconds":time.perf_counter()-start,"storage_bytes":sum(p.stat().st_size for p in dest.rglob("*") if p.is_file()),
        **extra}
    save(dest/"manifest.json",m)
    return m


def verify(directory, protocol_hash):
    m = json.loads((directory/"manifest.json").read_bytes())
    if m["preregistered_protocol_sha256"] != protocol_hash:
        raise ValueError("Protocol identity mismatch.")
    for name,digest in m["artifact_sha256"].items():
        path = (directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or sha(path.read_bytes())!=digest:
            raise ValueError("Stage artifact checksum mismatch.")
    return m


def spec_for(p,tier):
    s = p["datasets"][tier]
    return InputSpec(**s,family="ibm")


def prepare(p,ph,tier,dest):
    start = time.perf_counter()
    ids,x,y,meta = load_input(spec_for(p,tier),ROOT)
    if ids != sorted(ids):
        raise ValueError("Canonical sorted IDs required.")
    np.save(dest/"features.npy",x,allow_pickle=False)
    save(dest/"population.json",{"ids":ids,"labels":dict(zip(ids,map(int,y)))})
    splits = {}
    for seed in p["primary"]["split_seeds"]:
        tr,te = train_test_split(np.arange(len(ids)),test_size=.3,random_state=seed,stratify=y)
        tr,te = np.sort(tr),np.sort(te)
        split = {"train_ids":[ids[i] for i in tr],"test_ids":[ids[i] for i in te],
            "train_positives":int(y[tr].sum()),"test_positives":int(y[te].sum())}
        if seed==42 and tier=="5k":
            _,cohort = train_test_split(te,test_size=p["exploratory"]["cohort_size"],
                random_state=p["exploratory"]["cohort_seed"],stratify=y[te])
            split["cohort_ids"] = [ids[i] for i in sorted(cohort)]
            split["cohort_positives"] = int(y[cohort].sum())
        splits[str(seed)] = split
    save(dest/"splits.json",splits)
    return complete(dest,ph,"phase5-features",{"tier":tier,"source":meta,
        "feature_schema":FEATURE_NAMES,"feature_matrix_sha256":sha(x.tobytes())},start)


def interventions(p,ph,features,dest):
    start = time.perf_counter()
    fm = verify(features,ph)
    if fm["tier"]!="5k":
        raise ValueError("Only preregistered 5K exploratory interventions permitted.")
    pop = json.loads((features/"population.json").read_bytes())
    split = json.loads((features/"splits.json").read_bytes())["42"]
    # Labels are neither passed to the engine nor used in candidate selection.
    x = np.load(features/"features.npy",allow_pickle=False)
    reference = dict(zip(pop["ids"],x[:,:19].tolist()))
    content = (ROOT/p["datasets"]["5k"]["transactions"]).read_bytes()
    if sha(content)!=p["datasets"]["5k"]["transactions_sha256"]:
        raise ValueError("Transaction hash mismatch.")
    table = pd.read_csv(io.BytesIO(content),dtype=str)
    cutoff = str(pd.to_datetime(table.timestamp).max())
    configs,counts,times = {},{},[]
    accepted_total = rejected_total = 0
    generation_budget = p["exploratory"]["max_generation_seconds"]
    with (dest/"interventions.jsonl").open("wb") as handle:
        for family in p["intervention"]["families"]:
            cfg = InterventionConfig(dataset_id=p["datasets"]["5k"]["dataset_id"],
                source_identity="supplied-ibm-5k-phase5-v1",time_kind="timestamp_utc",cutoff=cutoff,
                window_size=p["intervention"]["window_hours"],window_unit="hours",
                intervention_seed=p["intervention"]["seed"],families=(family,),
                budget=Budget(**p["intervention"]["budget"]))
            configs[family] = cfg.model_dump()
            history = load_history(content,cfg)
            engine = InterventionEngine(history,cfg)
            if engine.baseline != reference:
                raise ValueError("Phase 3 baseline differs from baseline-method representation.")
            counts[family] = {}
            for index,u in enumerate(split["cohort_ids"]):
                if time.perf_counter()-start > generation_budget:
                    save(dest/"incomplete.json",{"reason":"preregistered generation budget exceeded",
                        "seconds":time.perf_counter()-start,"family":family,"completed_in_family":index,
                        "performance_metrics":"not computed for partial cohort"})
                    return {"incomplete":True,"directory":str(dest)}
                n = 0
                for row in engine.generate(u):
                    handle.write(canonical(row)+b"\n")
                    if row["status"]=="accepted":
                        accepted_total+=1
                        n+=1
                        times.append(row["runtime_seconds"])
                    else:
                        rejected_total+=1
                counts[family][u] = n
                if (index+1)%25==0:
                    print(f"{family}: {index+1}/{len(split['cohort_ids'])}; accepted={accepted_total}; elapsed={time.perf_counter()-start:.1f}s",flush=True)
    save(dest/"configurations.json",configs)
    save(dest/"coverage.json",counts)
    return complete(dest,ph,"phase5-interventions",{"feature_manifest_sha256":sha((features/"manifest.json").read_bytes()),
        "historical_cutoff":cutoff,"accepted":accepted_total,"rejected":rejected_total,
        "feature_recompute_seconds":sum(times),"mean_recompute_seconds":float(np.mean(times)) if times else None,
        "max_recompute_seconds":max(times,default=None),"scope":"exploratory 250 held-out accounts",
        "input_transactions":len(history.events),"accounts":len(history.universe)},start)


def evaluate(p,ph,features,dest,intervention_dir=None):
    start = time.perf_counter()
    fm = verify(features,ph)
    tier = fm["tier"]
    pop = json.loads((features/"population.json").read_bytes())
    splits = json.loads((features/"splits.json").read_bytes())
    ids,labels = pop["ids"],pop["labels"]
    x = np.load(features/"features.npy",allow_pickle=False)
    idx = {u:i for i,u in enumerate(ids)}
    records = []
    if intervention_dir:
        im = verify(intervention_dir,ph)
        if im["feature_manifest_sha256"] != sha((features/"manifest.json").read_bytes()):
            raise ValueError("Intervention feature identity mismatch.")
        records = [json.loads(line) for line in (intervention_dir/"interventions.jsonl").read_text().splitlines()]
        jobs = [(42,s) for s in p["exploratory"]["model_seeds"]]
    else:
        jobs = [(s,p["primary"]["model_seed"]) for s in p["primary"]["split_seeds"]]
    all_results,all_scores,all_memberships,timings = [],{}, {},{}
    for split_seed,model_seed in jobs:
        split = splits[str(split_seed)]
        train_ids = split["train_ids"]
        eval_ids = split["cohort_ids"] if intervention_dir else split["test_ids"]
        if set(train_ids)&set(eval_ids) or len(set(eval_ids))!=len(eval_ids):
            raise ValueError("Training/evaluation isolation failure.")
        tr,te = [idx[u] for u in train_ids],[idx[u] for u in eval_ids]
        truth = {u:labels[u] for u in eval_ids}
        key = f"split-{split_seed}-model-{model_seed}"
        sub = dest/key
        sub.mkdir()
        all_memberships[key] = {"train_ids":train_ids,"evaluation_ids":eval_ids}
        config = CrestConfig(source_dataset_id=p["datasets"][tier]["dataset_id"],
            evaluation_dataset_id=p["datasets"][tier]["dataset_id"],split_id=f"phase5-{tier}-{split_seed}",
            source_manifest_sha256=sha((features/"manifest.json").read_bytes()),
            evaluation_manifest_sha256=sha((features/"manifest.json").read_bytes()),
            train_ids=tuple(train_ids),evaluation_ids=tuple(eval_ids),model_seed=model_seed,
            n_estimators=p["detector"]["n_estimators"],max_samples=p["detector"]["max_samples"],
            contamination=p["detector"]["contamination"],
            alpha=p["weights"]["alpha"],beta=p["weights"]["beta"])
        t = time.perf_counter()
        detector = FrozenE4(x[tr,:19],config,CANONICAL_TRANSFER_FEATURES)
        fit_e4 = time.perf_counter()-t
        t = time.perf_counter()
        raw,q = detector.score(x[te,:19],CANONICAL_TRANSFER_FEATURES,detector.identity)
        baseline_seconds = time.perf_counter()-t
        scores = {"E4":dict(zip(eval_ids,map(float,raw))),"E6_BASE":dict(zip(eval_ids,map(float,q)))}
        coverage = {m:{"intervention_availability_rate":None,"fallback_rate":None} for m in scores}
        # Other baseline methods reuse the exact population and unchanged Phase 2 implementation.
        t = time.perf_counter()
        for method in ["E0","E1","E2","E3","E5"]:
            rc = ResearchConfig(source=spec_for(p,tier),experiment=method,model_seed=model_seed,
                contamination=p["detector"]["contamination"],n_estimators=p["detector"]["n_estimators"],
                max_samples=p["detector"]["max_samples"])
            cols = GROUPS[method]
            value,_,_ = fit_and_score(x[tr][:,cols],[x[te][:,cols]],rc)
            scores[method] = dict(zip(eval_ids,map(float,value[0])))
            coverage[method] = {"intervention_availability_rate":None,"fallback_rate":None}
        other_fit_score = time.perf_counter()-t
        intervention_seconds = aggregation_seconds = 0
        if intervention_dir:
            accepted = [r for r in records if r["status"]=="accepted"]
            t = time.perf_counter()
            values = np.asarray([r["intervened_features"] for r in accepted],dtype=np.float32).reshape(-1,19)
            sr,qr = detector.score(values,CANONICAL_TRANSFER_FEATURES,detector.identity)
            intervention_seconds = time.perf_counter()-t
            t = time.perf_counter()
            profiles = make_profiles(records,scores["E4"],scores["E6_BASE"],sr,qr,config)
            rejects = [r for r in records if r["status"]=="rejected"]
            extra,cov,accounts = aggregate(eval_ids,scores["E6_BASE"],profiles,rejects,config)
            scores.update(extra); coverage.update(cov)
            placebo,control_info = permuted_control(profiles,p["negative_control"]["seed"])
            ctrl,ctrl_cov,_ = aggregate(eval_ids,scores["E6_BASE"],placebo,rejects,config)
            scores["NEGATIVE_CONTROL"] = ctrl["E6_HYBRID"]
            coverage["NEGATIVE_CONTROL"] = ctrl_cov["E6_HYBRID"]
            save(sub/"profiles.json",profiles)
            save(sub/"accounts.json",accounts)
            save(sub/"control.json",{"metadata":control_info,"profiles":placebo})
            aggregation_seconds = time.perf_counter()-t
        # All rankings are finalized before evaluation functions receive labels.
        save(sub/"scores.json",scores)
        save(sub/"membership.json",all_memberships[key])
        save(sub/"calibration.json",{"reference":detector.calibrator.reference.tolist(),"model_id":detector.model_id,
            "identity":detector.identity,"training_matrix_sha256":detector.training_matrix_sha256,
            "source_manifest_kind":"phase5-features","config":config.model_dump()})
        joblib.dump(detector.model,sub/"model.joblib")
        t = time.perf_counter()
        rows = {}
        for method,s in scores.items():
            rows[method] = {**metrics(eval_ids,truth,s),**coverage[method],
                "paired_vs_E4":paired_bootstrap(eval_ids,truth,s,scores["E4"],
                    p["uncertainty"]["bootstrap_seed"],p["uncertainty"]["draws"]) if method not in ["E0","E1","E2","E3","E4","E5"] else None}
        if intervention_dir:
            ab = {m:paired_bootstrap(eval_ids,truth,scores[m],scores["E6_BASE"],2718,1000)
                  for m in ["E6_SENSITIVITY","E6_ROBUSTNESS","E6_HYBRID"]}
            ab["structured_vs_control"] = paired_bootstrap(eval_ids,truth,scores["E6_HYBRID"],scores["NEGATIVE_CONTROL"],2718,1000)
            save(sub/"paired_ablations.json",ab)
        save(sub/"results.json",rows)
        save(sub/"labels.json",truth)
        all_results.append({"split_seed":split_seed,"model_seed":model_seed,"key":key,"methods":rows})
        all_scores[key] = scores
        timings[key] = {"e4_fit":fit_e4,"baseline_score":baseline_seconds,"other_baseline_fit_and_score":other_fit_score,
            "intervention_score":intervention_seconds,"aggregation_artifact_write":aggregation_seconds,
            "evaluation_bootstrap":time.perf_counter()-t}
        print(f"{key} complete, n={len(eval_ids)}, positives={sum(truth.values())}",flush=True)
    summary = {}
    for method in all_results[0]["methods"]:
        values = [row["methods"][method]["average_precision"] for row in all_results]
        valid = [v for v in values if v is not None]
        summary[method] = {"runs":len(values),"defined":len(valid),"mean":float(np.mean(valid)) if valid else None,
            "median":float(np.median(valid)) if valid else None,"std_ddof1":float(np.std(valid,ddof=1)) if len(valid)>1 else None,
            "min":min(valid,default=None),"max":max(valid,default=None)}
    stability_rows = []
    if intervention_dir:
        keys = list(all_scores)
        for a_i,a in enumerate(keys):
            for b in keys[a_i+1:]:
                for method in all_scores[a]:
                    stability_rows.append({"first":a,"second":b,"method":method,
                        **stability(eval_ids,all_scores[a][method],all_scores[b][method])})
    save(dest/"results.json",all_results)
    save(dest/"summary.json",summary)
    save(dest/"stability.json",stability_rows)
    save(dest/"timings.json",timings)
    # Include nested artifacts, independently checksummed.
    nested = {f.relative_to(dest).as_posix():sha(f.read_bytes()) for f in dest.rglob("*") if f.is_file()}
    return complete(dest,ph,"phase5-evaluation",{"tier":tier,
        "scope":"exploratory-cohort" if intervention_dir else "full-heldout-baselines-only",
        "feature_manifest_sha256":sha((features/"manifest.json").read_bytes()),
        "intervention_manifest_sha256":sha((intervention_dir/"manifest.json").read_bytes()) if intervention_dir else None,
        "artifact_sha256":nested,"timings":timings,
        "planned_full_coverage_e6":"incomplete: feasibility gate","feature_info":fm["source"]},start)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage",choices=["prepare","interventions","evaluate"])
    ap.add_argument("protocol",type=Path)
    ap.add_argument("run_id")
    ap.add_argument("--tier",choices=["5k","50k"],default="5k")
    ap.add_argument("--features",type=Path)
    ap.add_argument("--interventions",type=Path)
    args = ap.parse_args()
    p,ph = read(args.protocol)
    dest = output(args.run_id)
    if args.stage=="prepare":
        result = prepare(p,ph,args.tier,dest)
    elif args.stage=="interventions":
        result = interventions(p,ph,args.features.resolve(),dest)
    else:
        result = evaluate(p,ph,args.features.resolve(),dest,args.interventions.resolve() if args.interventions else None)
    print(json.dumps({k:v for k,v in result.items() if k in ["stage","total_seconds","incomplete","accepted","rejected","scope"]}),flush=True)


if __name__=="__main__":
    main()
