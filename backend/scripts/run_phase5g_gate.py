"""Bounded, label-free Phase 5G diagnosis, numerical checks and paired controls."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import tracemalloc

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import joblib
import networkx as nx
import numpy as np
import pandas as pd
import psutil
import sklearn
from backend.app.services.research_protocol import canonical, sha
from backend.app.services.artifact_integrity import verify_protected
from backend.app.research.benchmark.runner import verify
from backend.app.research.crest.frozen_scorer import EmpiricalCalibrator
from backend.app.research.crest.statistics import candidate_score
from backend.app.research.interventions.schemas import InterventionConfig, Budget
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.feature_recomputation import recompute
from backend.app.research.feasibility_gate.raw_scoring import TrainingAffine, raw_modes, FAMILIES
from backend.app.research.feasibility_gate.focal_features import FocalRecomputer
from backend.app.research.feasibility_gate.pilot_design import CandidateIndex, select_cohort, matched_random

CONFIG=ROOT/"docs/research/configs/phase5g_feasibility_v1.json"
EXPECTED="508a84edfc7eef3cf2a9b99d7b776533c49d742ef5215d18ce59a4e46ec6daff"


def save(path,data):
    with path.open("xb") as f: f.write(canonical(data))


def ranks(scores):
    return {u:i+1 for i,u in enumerate(sorted(scores,key=lambda u:(-float(scores[u]),u)))}


def describe(values):
    x=np.asarray(values,dtype=float)
    return {"count":len(x),"min":float(x.min()) if len(x) else None,
        "median":float(np.median(x)) if len(x) else None,"max":float(x.max()) if len(x) else None,
        "mean":float(x.mean()) if len(x) else None,"nonzero":int((x!=0).sum()),
        "above_1e-12":int((np.abs(x)>1e-12).sum())}


def diagnose(dest):
    folder=ROOT/"data/results/v2/phase5r-selective-top5-v1"
    m=json.loads((folder/"manifest.json").read_bytes())
    for name,digest in m["artifacts"].items():
        if sha((folder/name).read_bytes())!=digest: raise ValueError("Selective artifact checksum mismatch.")
    scores=json.loads((folder/"scores.json").read_bytes())
    stats=json.loads((folder/"evaluation.json").read_bytes())["account_diagnostics"]
    profiles=json.loads((folder/"profiles.json").read_bytes())
    selected=json.loads((folder/"selection.json").read_bytes())["selected_ids"]
    mode_names=[s for s in scores if s.startswith("E6_")]
    mode_ranks={s:ranks(scores[s]) for s in ["E4",*mode_names]}
    grouped=defaultdict(list)
    for r in profiles: grouped[r["focal_account"]].append(r)
    rows=[]
    for u in sorted(scores["E4"]):
        a=stats[u]; q=scores["E6_BASE"][u]; d=a["sensitivity"]; r=a["robustness"]
        modes={}; before_clip={}; fallbacks={}
        for mode in mode_names:
            score,missing=candidate_score(q,a,mode,.25,.25)
            if score!=scores[mode][u]: raise ValueError("Stored selective score does not replay.")
            use_d=mode in ("E6_SENSITIVITY","E6_HYBRID")
            use_r=mode in ("E6_ROBUSTNESS","E6_HYBRID")
            unclip=q if missing else q+(.25*d if use_d else 0)-(.25*q*(1-r) if use_r else 0)
            modes[mode]=score; before_clip[mode]=unclip; fallbacks[mode]=missing
        rows.append({"account_id":u,"selected":u in selected,"raw_e4":scores["E4"][u],"e6_base":q,
            "accepted_interventions":len(grouped[u]),"raw_signed_changes":[x["raw_baseline_score"]-x["raw_intervened_score"] for x in grouped[u]],
            "calibrated_signed_changes":[x["signed_change"] for x in grouped[u]],
            "sensitivity":d,"robustness":r,"families":a["families"],"scores":modes,
            "mode_minus_base":{mode:value-q for mode,value in modes.items()},
            "mode_pairwise_differences":{f"{a}-{b}":modes[a]-modes[b] for i,a in enumerate(mode_names) for b in mode_names[i+1:]},
            "ranks":{mode:rs[u] for mode,rs in mode_ranks.items()},
            "rank_minus_e6_base":{mode:rs[u]-mode_ranks["E6_BASE"][u] for mode,rs in mode_ranks.items()},
            "fallback_reasons":fallbacks,"score_before_clipping":before_clip,
            "clipping_occurred":{mode:before_clip[mode]!=modes[mode] for mode in mode_names},
            "sensitivity_term":.25*d if d is not None else None,
            "robustness_penalty":.25*q*(1-r) if r is not None else None})
    save(dest/"selective_account_diagnosis.json",rows)
    summary={"source_manifest_sha256":sha((folder/"manifest.json").read_bytes()),"accounts":len(rows),
        "selected_ids":selected,"raw_delta":describe([r["raw_baseline_score"]-r["raw_intervened_score"] for r in profiles]),
        "calibrated_delta":describe([r["signed_change"] for r in profiles]),
        "modes":{mode:{"changed_scores_vs_base":sum(r["mode_minus_base"][mode]!=0 for r in rows),
            "changed_ranks_vs_base":sum(r["rank_minus_e6_base"][mode]!=0 for r in rows),
            "fallback_accounts":sum(bool(r["fallback_reasons"][mode]) for r in rows),
            "clipped_accounts":sum(r["clipping_occurred"][mode] for r in rows)} for mode in mode_names}}
    save(dest/"selective_diagnosis_summary.json",summary)
    return summary


def affine_checks(dest):
    results=[]; arrays={}
    for tier in ("5k","50k"):
        folder=ROOT/f"data/results/v2/phase5-baselines-{tier}-v1"
        verify(folder,EXPECTED)
        for seed in (42,123,7,2024,99,555):
            key=f"split-{seed}-model-42"; d=folder/key
            cal=json.loads((d/"calibration.json").read_bytes())
            scores=json.loads((d/"scores.json").read_bytes())["E4"]
            ids=sorted(scores); raw=np.asarray([scores[u] for u in ids])
            transform=TrainingAffine(cal["reference"])
            transform.transform(np.r_[cal["reference"],raw])
            z=transform.transform(raw); transformed=dict(zip(ids,z))
            if ranks(scores)!=ranks(transformed): raise FloatingPointError("Affine ranking mismatch.")
            zero={u:raw_modes(float(value),{},alpha=0,beta=0)["scores"]["RAW_HYBRID"] for u,value in transformed.items()}
            if ranks(zero)!=ranks(scores): raise FloatingPointError("Zero weight rank mismatch.")
            label=f"{tier}_{seed}"
            arrays[label+"_ids"]=np.asarray(ids);arrays[label+"_raw"]=raw;arrays[label+"_affine"]=z
            results.append({"tier":tier,"split_seed":seed,"model_seed":42,"accounts":len(ids),
                "unique_raw":len(np.unique(raw)),"unique_affine":len(np.unique(z)),
                "order_identical":True,"zero_weight_order_identical":True,
                "calibration":transform.metadata(),"source_calibration_sha256":sha((d/"calibration.json").read_bytes())})
    np.savez(dest/"affine_scores.npz",**arrays)
    save(dest/"affine_checks.json",results)
    return results


def small_profiles(dest,model,seed):
    rows=[]
    for n in (500,1500):
        rng=np.random.RandomState(seed+n); lines=["source_row_id,sender_id,receiver_id,amount,step"]
        for i in range(n):
            a=int(rng.randint(n//2)); b=(a+int(rng.randint(1,n//2)))%(n//2)
            amount="1000000000000" if i%97==0 else "0.000001" if i%89==0 else str(i%13+1)
            lines.append(f"{i},U{a:04},U{b:04},{amount},{i%168}")
        cfg=InterventionConfig(dataset_id="phase5g-synthetic",source_identity="phase5g-synthetic-v1",
            time_kind="simulation_hour",cutoff="1000",window_size=24,window_unit="hours")
        raw=("\n".join(lines)+"\n").encode();h=load_history(raw,cfg);focal=h.events[0].sender;omitted=(h.events[0].transaction_id,)
        f=FocalRecomputer(h)
        tracemalloc.start(); t=time.perf_counter(); reference,_=recompute(h,omitted)
        ref_seconds=time.perf_counter()-t;ref_peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        tracemalloc.start();t=time.perf_counter();v,meta=f.vector(focal,omitted,use_cache=False)
        focal_seconds=time.perf_counter()-t;focal_peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        expected=np.asarray(reference[focal]);actual=np.asarray(v)
        maxdev=float(np.max(np.abs(expected-actual)))
        sr=-model.decision_function(np.asarray([expected],dtype=np.float32))[0]
        so=-model.decision_function(np.asarray([actual],dtype=np.float32))[0]
        if maxdev!=0 or sr!=so: raise AssertionError("Synthetic focal equivalence failure.")
        rows.append({"transactions":n,"accounts":len(h.universe),"workload_sha256":sha(raw),
            "reference_seconds":ref_seconds,"focal_seconds":focal_seconds,"ratio_reference_over_focal":ref_seconds/focal_seconds,
            "reference_peak_traced_bytes":ref_peak,"focal_peak_traced_bytes":focal_peak,
            "focal_timing":meta,"max_abs_feature_error":maxdev,"raw_score_error":float(abs(sr-so))})
    save(dest/"focal_profiles.json",rows)
    return rows


def pilot(dest,p,model,calibration,started):
    t=time.perf_counter()
    frozen=json.loads((ROOT/"docs/research/configs/phase5_protocol_v1.json").read_bytes())
    source=frozen["datasets"]["5k"];content=(ROOT/source["transactions"]).read_bytes()
    if sha(content)!=source["transactions_sha256"]: raise ValueError("Dataset changed.")
    # Timestamp extraction reads transaction evidence only; no label file is opened.
    table=pd.read_csv(ROOT/source["transactions"],dtype=str)
    cutoff=str(pd.to_datetime(table.timestamp).max())
    cfg=InterventionConfig(dataset_id=source["dataset_id"],source_identity="supplied-ibm-5k-phase5-v1",
        time_kind="timestamp_utc",cutoff=cutoff,window_size=p["window_hours"],window_unit="hours",
        intervention_seed=p["intervention_seed"],budget=Budget(**p["budget"]))
    h=load_history(content,cfg);index=CandidateIndex(h,cfg)
    folder=ROOT/"data/results/v2/phase5-baselines-5k-v1/split-42-model-42"
    scores=json.loads((folder/"scores.json").read_bytes())["E4"]
    cohort=select_cohort(scores,index,p["accounts_per_stratum"],p["selection_seed"])
    save(dest/"pilot_selection.json",{"rule":p["cohort"],"accounts":cohort,"labels_accessed":False,
        "selection_seconds":time.perf_counter()-t,"cutoff":cutoff,"config":cfg.model_dump()})
    affine=TrainingAffine(calibration["reference"]);empirical=EmpiricalCalibrator(calibration["reference"])
    local=FocalRecomputer(h);checks=[];all_rows=[];account_rows=[];replays=[]
    t=time.perf_counter();reference_baseline,_=recompute(h);reference_baseline_seconds=time.perf_counter()-t
    baseline_focals={entry["account_id"]:local.vector(entry["account_id"]) for entry in cohort}
    for entry in cohort:
        if time.perf_counter()-started>p["wall_budget_seconds"]: raise TimeoutError("Pilot budget exhausted.")
        u=entry["account_id"];v0,base_meta=baseline_focals[u]
        if v0!=reference_baseline[u]: raise AssertionError("Baseline focal features mismatch.")
        raw0=float(-model.decision_function(np.asarray([v0],dtype=np.float32))[0])
        if raw0!=scores[u]: raise AssertionError("Baseline frozen score mismatch.")
        z0=float(affine.transform([raw0])[0]);groups={kind:defaultdict(list) for kind in ("structured","control")}
        generation=time.perf_counter();candidates=index.bounded(u);generation=time.perf_counter()-generation
        accepted=[r for r in candidates if r["status"]=="accepted"]
        save(dest/f"candidates-{u}.json",candidates)
        timing={"structured":0.0,"control":0.0};one_checked=False
        for candidate in accepted:
            control=matched_random(index.incident[u],candidate,cfg.budget,p["control_seed"],p["random_attempts"])
            pair_id=control["pair_id"]
            for kind,item in [("structured",candidate),("control",control)]:
                if item["status"]!="accepted":
                    all_rows.append({**item,"kind":kind,"focal_account":u});continue
                t=time.perf_counter();omitted=tuple(item["omitted_transaction_ids"])
                vector,meta=local.vector(u,omitted)
                scoring=time.perf_counter();raw=float(-model.decision_function(np.asarray([vector],dtype=np.float32))[0]);scoring=time.perf_counter()-scoring
                delta_z=float(affine.transform([raw0,raw])[0]-affine.transform([raw0,raw])[1])
                q=empirical.transform([raw0,raw])
                row={**item,"kind":kind,"pair_id":pair_id,"family":candidate["family"],
                    "raw_baseline":raw0,"raw_intervened":raw,"raw_signed_change":raw0-raw,
                    "affine_signed_change":delta_z,"empirical_signed_change":float(q[0]-q[1]),
                    "baseline_features":v0,"intervened_features":vector,"recomputation":meta,
                    "frozen_model_scoring_seconds":scoring}
                all_rows.append(row);groups[kind][candidate["family"]].append(delta_z)
                timing[kind]+=time.perf_counter()-t
                with (dest/"pilot_interventions.jsonl").open("ab") as f:f.write(canonical(row)+b"\n")
                if kind=="structured" and not one_checked:
                    t=time.perf_counter();reference,_=recompute(h,omitted);ref_seconds=time.perf_counter()-t
                    maxdev=float(np.max(np.abs(np.asarray(reference[u])-np.asarray(vector))))
                    ref_score=float(-model.decision_function(np.asarray([reference[u]],dtype=np.float32))[0])
                    checks.append({"account_id":u,"omitted_ids":omitted,"max_abs_feature_error":maxdev,
                        "raw_score_error":abs(ref_score-raw),"reference_seconds":ref_seconds,"focal_seconds":meta["total_seconds"]})
                    if maxdev!=0 or ref_score!=raw:raise AssertionError("Actual 5K feature or score mismatch.")
                    one_checked=True
                    if entry["score_stratum"] not in {r["stratum"] for r in replays}:
                        again,replay_meta=local.vector(u,omitted,use_cache=False)
                        replay_score=float(-model.decision_function(np.asarray([again],dtype=np.float32))[0])
                        if again!=vector or replay_score!=raw:raise AssertionError("Uncached replay mismatch.")
                        replays.append({"stratum":entry["score_stratum"],"account_id":u,"exact_features":True,"exact_score":True,"seconds":replay_meta["total_seconds"]})
        account_rows.append({**entry,"raw_baseline":raw0,"affine_baseline":z0,"baseline_recompute":base_meta,
            "candidate_generation_seconds":generation,"accepted_structured":len(accepted),
            "accepted_control":sum(len(v) for v in groups["control"].values()),"processing_seconds":timing,
            "structured":raw_modes(z0,groups["structured"],p["alpha"],p["beta"]),
            "control":raw_modes(z0,groups["control"],p["alpha"],p["beta"])})
        print(f"pilot {entry['score_stratum']} {u}: {len(accepted)} structured, {sum(len(v) for v in groups['control'].values())} controls; elapsed {time.perf_counter()-started:.1f}s",flush=True)
    # Verify transformation order across the UNION, not merely each two-row call.
    affine.transform([s for r in all_rows if r["status"]=="accepted" for s in [r["raw_baseline"],r["raw_intervened"]]])
    base_scores={r["account_id"]:r["affine_baseline"] for r in account_rows};base_ranks=ranks(base_scores)
    full_affine=dict(zip(sorted(scores),affine.transform([scores[u] for u in sorted(scores)])))
    mode_summary={}
    for kind in ("structured","control"):
        mode_summary[kind]={}
        for mode in ("RAW_BASE","RAW_SENSITIVITY","RAW_ROBUSTNESS","RAW_HYBRID"):
            small={r["account_id"]:r[kind]["scores"][mode] for r in account_rows};small_ranks=ranks(small)
            full=dict(full_affine);full.update(small);full_ranks=ranks(full);original_ranks=ranks(full_affine)
            mode_summary[kind][mode]={"changed_pilot_scores":sum(small[u]!=base_scores[u] for u in small),
                "changed_pilot_ranks":sum(small_ranks[u]!=base_ranks[u] for u in small),
                "changed_full_population_ranks":sum(full_ranks[u]!=original_ranks[u] for u in full),
                "fallback_accounts":sum(bool(r[kind]["fallbacks"][mode]) for r in account_rows),
                "full_population_intervention_coverage":len(account_rows)/len(full),"pilot_ranks":small_ranks}
    valid=[r for r in all_rows if r["status"]=="accepted"]
    structured=[r for r in valid if r["kind"]=="structured"];controls={r["pair_id"]:r for r in valid if r["kind"]=="control"}
    pairs=[{"pair_id":r["pair_id"],"account_id":r["focal_account"],"family":r["family"],
        "structured_delta_z":r["affine_signed_change"],"control_delta_z":controls[r["pair_id"]]["affine_signed_change"],
        "signed_difference":r["affine_signed_change"]-controls[r["pair_id"]]["affine_signed_change"],
        "same_omission":controls[r["pair_id"]]["same_omission_as_structured"],
        "count_matched":r["omitted_count"]==controls[r["pair_id"]]["omitted_count"],
        "structured_amount_fraction":r["omitted_amount_fraction"],"control_amount_fraction":controls[r["pair_id"]]["omitted_amount_fraction"]}
        for r in structured if r["pair_id"] in controls]
    save(dest/"pilot_accounts.json",account_rows);save(dest/"reference_equivalence.json",checks)
    save(dest/"uncached_replay.json",replays);save(dest/"random_control_pairs.json",pairs)
    summary={"accounts":len(cohort),"families":dict(Counter(r["family"] for r in structured)),
        "accepted_structured":len(structured),"accepted_controls":len(controls),"matched_pairs":len(pairs),
        "same_omission_pairs":sum(r["same_omission"] for r in pairs),
        "structured_delta_z":describe([r["affine_signed_change"] for r in structured]),
        "control_delta_z":describe([r["affine_signed_change"] for r in controls.values()]),
        "paired_delta_difference":describe([r["signed_difference"] for r in pairs]),
        "accounts_with_nonzero_sensitivity":{kind:sum(abs(r[kind]["sensitivity"] or 0)>1e-12 for r in account_rows) for kind in ("structured","control")},
        "modes":mode_summary,"raw_affine_metadata":affine.metadata(),"reference_baseline_seconds":reference_baseline_seconds,
        "memory":psutil.Process().memory_info()._asdict(),"wall_elapsed_seconds":time.perf_counter()-started,
        "interpretation":"Scoring-behavior pilot only; eligible score-stratified selection, overlapping pairs, no labels or accuracy inference"}
    save(dest/"pilot_summary.json",summary)
    # These projections describe the same 5K graph; they cannot establish scaling
    # to a different graph. Per-account rates include cached duplicate omissions.
    per_account=[r["candidate_generation_seconds"]+r["processing_seconds"]["structured"] for r in account_rows]
    setup=reference_baseline_seconds+account_rows[0]["baseline_recompute"]["graph_and_global_centrality_seconds"]
    projections=[]
    for name,count in [("frozen_250",250),("larger_label_free_500",500),("full_5k_heldout",1500),("50k_heldout_same_cost_counterfactual",14998)]:
        projected=setup+count*float(np.mean(per_account))
        projections.append({"scope":name,"accounts":count,"projected_seconds":projected,
            "within_1800_scenario":projected<=1800,"measured":False,
            "qualification":"same 5K graph and eligible six-account mix only; no scaling law" if count!=14998 else "optimistic same-5K-cost counterfactual only; 49992-node graph not profiled, reference guard 10000 blocks it"})
    save(dest/"runtime_projections.json",{"measured_per_account_seconds":per_account,"measured_setup_seconds":setup,
        "measured_control_seconds":sum(r["processing_seconds"]["control"] for r in account_rows),
        "uncertainty":"Six eligible accounts; cache hits, degree mix and family availability affect rates. No confidence interval or linear-scaling claim.","projections":projections})
    return summary


def worker(dest):
    p=json.loads(CONFIG.read_bytes());started=time.perf_counter()
    if sha((ROOT/"docs/research/configs/phase5_protocol_v1.json").read_bytes())!=EXPECTED: raise ValueError("Frozen protocol hash changed.")
    if verify_protected():raise ValueError("Protected input bytes changed.")
    diagnose(dest);affine_checks(dest)
    folder=ROOT/"data/results/v2/phase5-baselines-5k-v1/split-42-model-42"
    calibration=json.loads((folder/"calibration.json").read_bytes());model=joblib.load(folder/"model.joblib")
    small_profiles(dest,model,p["synthetic_seed"])
    summary=pilot(dest,p,model,calibration,started)
    if verify_protected():raise ValueError("Protected input bytes changed after pilot.")
    code={f.relative_to(ROOT).as_posix():sha(f.read_bytes()) for f in (ROOT/"backend/app/research/feasibility_gate").glob("*.py")}
    code[Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__).read_bytes())
    manifest={"stage":"phase5g-feasibility-gate-v1","status":"complete_bounded_pilot",
        "project_title":p["project_title"],"protocol_sha256":sha(CONFIG.read_bytes()),"parent_protocol_sha256":EXPECTED,
        "configuration":p,"code_sha256":code,"dataset_sha256":sha((ROOT/"data/research/ibm_aml_medium_5k.csv").read_bytes()),
        "input_model_sha256":sha((folder/"model.joblib").read_bytes()),"input_calibration_sha256":sha((folder/"calibration.json").read_bytes()),
        "input_baseline_manifest_sha256":sha((folder.parent/"manifest.json").read_bytes()),
        "artifacts":{f.name:sha(f.read_bytes()) for f in dest.iterdir() if f.is_file()},
        "software":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"sklearn":sklearn.__version__,"networkx":nx.__version__},
        "total_seconds":time.perf_counter()-started,"memory":psutil.Process().memory_info()._asdict(),
        "scope":"No labels or accuracy metrics. Prior methods/results preserved. Original Phase 5 incomplete."}
    save(dest/"manifest.json",manifest)
    print(json.dumps({"directory":str(dest),"seconds":manifest["total_seconds"],"accepted_structured":summary["accepted_structured"],"accepted_controls":summary["accepted_controls"]}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("run_id");parser.add_argument("--worker",action="store_true");args=parser.parse_args()
    if not args.run_id.replace("-","").isalnum():raise ValueError("Invalid run ID")
    dest=ROOT/"data/results/v2"/args.run_id
    if args.worker:
        try:worker(dest)
        except Exception as exc:
            save(dest/"incomplete.json",{"status":"failed","error_type":type(exc).__name__,"error":str(exc)})
            raise
        return
    dest.mkdir(exist_ok=False)
    save(dest/"protocol.json",json.loads(CONFIG.read_bytes()))
    child=subprocess.Popen([sys.executable,"-u",str(Path(__file__).resolve()),args.run_id,"--worker"],cwd=ROOT)
    try: result=child.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        child.kill();child.wait()
        save(dest/"timeout.json",{"status":"incomplete","hard_wall_budget_seconds":1800,"reason":"worker killed at budget; partial artifacts not a completed pilot"})
        raise SystemExit(124)
    raise SystemExit(result)


if __name__=="__main__":main()
