"""Bounded, append-only explanation pilot; frozen E4, no fitting or rankings."""
import argparse
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
import psutil
import sklearn
import networkx as nx
import pandas as pd
from backend.scripts.run_phase5h_specificity import read, save, verified_manifest
from backend.app.services.research_protocol import canonical, sha
from backend.app.services.artifact_integrity import verify_protected
from backend.app.research.interventions.schemas import InterventionConfig
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.feature_recomputation import recompute
from backend.app.research.feasibility_gate.focal_features import FocalRecomputer
from backend.app.research.feasibility_gate.pilot_design import CandidateIndex, select_cohort
from backend.app.research.evidence_specificity.matching import StrictMatcher
from backend.app.research.evidence_specificity.scoring import FrozenBatchScorer
from backend.app.research.explanation_validation.diagnostics import select, sparsity, fidelity, summary, paired, shadow, jaccard

CONFIG = ROOT/"docs/research/configs/phase6a_explanations_v1.json"
G = ROOT/"data/results/v2/phase5g-feasibility-v1-recovery"
H = ROOT/"data/results/v2/phase5h-specificity-v2-pilot-v2"


def reference_key(required, account):
    # Missing explanations are part of the cohort, not grounds for replacement.
    return next((k for k in sorted(required) if k[0]==account),(account,()))


def worker(dest):
    start = time.perf_counter(); p = read(CONFIG)
    code = {f.relative_to(ROOT).as_posix():sha(f.read_bytes()) for f in (ROOT/"backend/app").rglob("*.py")}
    code.update({f.relative_to(ROOT).as_posix():sha(f.read_bytes()) for f in (ROOT/"backend/scripts").glob("*.py")})
    if verify_protected(): raise ValueError("Protected bytes changed.")
    if sha((ROOT/"docs/research/configs/phase5_protocol_v1.json").read_bytes()) != p["parent_protocol_sha256"]:
        raise ValueError("Historical protocol changed.")
    gm = verified_manifest(G,p["phase5g_manifest_sha256"])
    hm = verified_manifest(H,p["phase5h_manifest_sha256"])
    for manifest in (gm,hm):
        for name,digest in manifest["code_sha256"].items():
            if sha((ROOT/name).read_bytes()) != digest: raise ValueError("Prior implementation changed: "+name)
    split = ROOT/"data/results/v2/phase5-baselines-5k-v1/split-42-model-42"
    verified_manifest(split.parent)
    model_path = split/"model.joblib"; model_hash = sha(model_path.read_bytes())
    if model_hash != gm["input_model_sha256"] or model_hash != hm["model_sha256"]: raise ValueError("Model mismatch.")
    scorer = FrozenBatchScorer(joblib.load(model_path))
    selection = read(G/"pilot_selection.json"); cfg = InterventionConfig(**selection["config"])
    if cfg.budget.model_dump() != p["budget"]: raise ValueError("Budget mismatch.")
    content = (ROOT/"data/research/ibm_aml_medium_5k.csv").read_bytes()
    if sha(content) != gm["dataset_sha256"]: raise ValueError("Dataset mismatch.")
    t = time.perf_counter(); history = load_history(content,cfg); local = FocalRecomputer(history)
    index = CandidateIndex(history,cfg); matcher = StrictMatcher(history,cfg.budget,p["matching"])
    indexing_seconds = time.perf_counter()-t
    baseline = read(split/"scores.json")["E4"]; cohort = selection["accounts"]
    if cohort != select_cohort(baseline,index,2,p["cohort_seed"]): raise ValueError("Cohort replay differs.")
    cal = read(split/"calibration.json")["config"]
    for r in cohort:
        if r["account_id"] not in cal["evaluation_ids"] or r["account_id"] in cal["train_ids"]: raise ValueError("Training overlap.")
    provenance = {"dataset_sha256":sha(content),"history_sha256":history.history_sha256,
        "model_sha256":model_hash,"split_seed":p["split_seed"],"model_seed":p["model_seed"],
        "graph_seed":p["graph_seed"],"control_seed":p["matching"]["control_seed"],
        "heldout_ids_sha256":sha(canonical(cal["evaluation_ids"])),"labels_used":False,
        "cutoff":cfg.cutoff,"algorithm":p["version"],"feature_count":19}
    save(dest/"cohort.json",{"accounts":cohort,"provenance":provenance})
    cache = {}; base_vectors = {}
    key = lambda u,ids: (u,tuple(sorted(ids)))
    old_rows = [json.loads(line) for line in (G/"pilot_interventions.jsonl").read_bytes().splitlines()]
    for r in old_rows:
        u=r["focal_account"]; ids=r["omitted_transaction_ids"]
        if local.identity(u,ids) != r["recomputation"]["cache_key"]: raise ValueError("Cache context mismatch.")
        cache[key(u,ids)]={"vector":r["intervened_features"],"raw":r["raw_intervened"],"origin":"verified_phase5g"}
        base_vectors[u]=r["baseline_features"]
    for r in read(H/"scored_vectors.json"):
        k=key(r["account_id"],r["omitted_ids"])
        if "recomputation" in r and local.identity(*k) != r["recomputation"]["cache_key"]:
            raise ValueError("Phase5H cache context mismatch.")
        if k in cache and cache[k]["vector"] != r["vector"]: raise ValueError("Cache conflict.")
        cache[k]={"vector":r["vector"],"raw":r["raw"],"origin":"verified_phase5h"}
    if not np.array_equal(scorer.verify_batch([r["vector"] for r in cache.values()]),[r["raw"] for r in cache.values()]):
        raise AssertionError("Reused scores differ.")
    for u,v in base_vectors.items():
        if float(scorer.score([v])[0]) != baseline[u]: raise AssertionError("Original E4 changed.")
    selections={}; plans={}; candidate_seconds={}
    for entry in cohort:
        u=entry["account_id"]; t=time.perf_counter(); selections[u]=select(history,cfg,u)
        plans[u]={m:matcher.match(row) for m,row in selections[u]["methods"].items() if row}
        candidate_seconds[u]=time.perf_counter()-t
        if selections[u] != select(history,cfg,u): raise AssertionError("Selection replay differs.")
        if plans[u] != {m:matcher.match(row) for m,row in selections[u]["methods"].items() if row}:
            raise AssertionError("Control replay differs.")
    save(dest/"selection_plan.json",{"selections":selections,"controls":plans,"outcomes_used":False})
    required=set()
    for u,result in selections.items():
        for m,row in result["methods"].items():
            if row:
                required.add(key(u,row["omitted_transaction_ids"]))
                required.update(key(u,c["omitted_transaction_ids"]) for c in plans[u][m]["controls"])
    fresh=sorted(required-cache.keys()); stages=[]; references=[]
    representatives=[]; seen=set()
    for r in cohort:
        if r["score_stratum"] not in seen: representatives.append(r["account_id"]); seen.add(r["score_stratum"])
    # Feasibility first: one original focal scenario, full reference, uncached replay.
    probe = fresh[0] if fresh else sorted(required)[0]
    t=time.perf_counter(); v,meta=local.vector(*probe,use_cache=False); ref,_=recompute(history,probe[1]); replay,_=local.vector(*probe,use_cache=False)
    if v != ref[probe[0]] or v != replay: raise AssertionError("Feasibility feature equivalence failed.")
    if probe in cache and cache[probe]["vector"] != v: raise AssertionError("Historical cache mismatch.")
    probe_seconds=time.perf_counter()-t
    projected=2*meta["total_seconds"]*(len(fresh)+50)+probe_seconds
    save(dest/"feasibility.json",{"probe_account":probe[0],"omitted_ids":probe[1],"seconds":probe_seconds,
        "focal_seconds":meta["total_seconds"],"remaining_scenario_allowance":len(fresh)+50,
        "conservative_projected_seconds":projected,"wall_budget_seconds":p["wall_budget_seconds"],
        "max_abs_feature_error":0,"fixed_replay_exact":True})
    if projected > p["wall_budget_seconds"]-(time.perf_counter()-start): raise TimeoutError("Feasibility projection exceeds remaining budget.")
    print(f"feasibility passed; {len(required)} unique scenarios, {len(fresh)} fresh; projected {projected:.1f}s",flush=True)
    for k in fresh:
        v,meta=local.vector(*k,use_cache=False); cache[k]={"vector":v,"origin":"fresh_focal","recomputation":meta}
        stages.append({"account_id":k[0],"omitted_ids":k[1],**meta})
        save(dest/f"fresh-{len(stages):03d}.json",{"account_id":k[0],"omitted_ids":k[1],**cache[k]})
        print(f"fresh {len(stages)}/{len(fresh)}; elapsed {time.perf_counter()-start:.1f}s",flush=True)
    t=time.perf_counter(); values=scorer.verify_batch([cache[k]["vector"] for k in sorted(required)])
    scoring_seconds=time.perf_counter()-t
    for k,value in zip(sorted(required),values): cache[k]["raw"]=float(value)
    for u in representatives:
        k=reference_key(required,u)
        expected=cache[k] if k in cache else {"vector":base_vectors[u],"raw":baseline[u]}
        t=time.perf_counter(); full,_=recompute(history,k[1]); replay,meta=local.vector(*k,use_cache=False)
        if expected["vector"] != full[u] or replay != full[u]: raise AssertionError("Reference/replay discrepancy.")
        if not np.array_equal(scorer.verify_batch([full[u],replay]),[expected["raw"]]*2): raise AssertionError("Score replay differs.")
        references.append({"account_id":u,"omitted_ids":k[1],"feature_error":0,"score_error":0,"seconds":time.perf_counter()-t})
    t=time.perf_counter(); rows=[]; controls=[]
    for entry in cohort:
        u=entry["account_id"]
        for method,row in selections[u]["methods"].items():
            base={"account_id":u,"method":method,"original_score":baseline[u],"original_features":base_vectors[u],"provenance":provenance}
            if not row:
                rows.append({**base,"available":False,"valid":None,"reason":"no_eligible_whole_group"}); continue
            scored=cache[key(u,row["omitted_transaction_ids"])]; plan=plans[u][method]
            delta=fidelity(baseline[u],scored["raw"])
            rows.append({**base,**row,"available":True,"valid":True,"reason":None,
                "intervened_features":scored["vector"],"intervened_score":scored["raw"],"fidelity":delta,
                "cache_origin":scored["origin"],"recomputation":scored.get("recomputation"),
                "control_status":plan["status"],"control_reason":plan["reason"],
                "mean_matched_control_fidelity":float(np.mean([baseline[u]-cache[key(u,c['omitted_transaction_ids'])]['raw'] for c in plan['controls']])) if plan['controls'] else None})
            for c in plan["controls"]:
                sc=cache[key(u,c["omitted_transaction_ids"])]
                controls.append({**base,"method":"E_"+method,"anchor":method,"available":True,"valid":True,
                    "omitted_transaction_ids":c["omitted_transaction_ids"],"assessment":c["assessment"],
                    "sparsity":sparsity(history,cfg,u,c["omitted_transaction_ids"]),
                    "intervened_features":sc["vector"],"intervened_score":sc["raw"],
                    "fidelity":fidelity(baseline[u],sc["raw"]),"cache_origin":sc["origin"]})
    comparisons=paired(rows)
    for r in rows:
        if r.get("mean_matched_control_fidelity") is not None:
            r["matched_fidelity_difference"]=r["fidelity"]-r["mean_matched_control_fidelity"]
    aggregation_seconds=time.perf_counter()-t
    save(dest/"explanations.json",rows); save(dest/"random_explanations.json",controls); save(dest/"paired_comparisons.json",comparisons)
    save(dest/"reference_checks.json",references)
    save(dest/"scored_vectors.json",[{"account_id":k[0],"omitted_ids":k[1],**cache[k]} for k in sorted(required)])
    # Stability concerns remain observable: do not canonicalize GraphService's node order.
    stability=[]; variant_stages=[]
    reversed_history=shadow(history,reversed(history.events)); reversed_local=FocalRecomputer(reversed_history)
    for u in representatives:
        incident=index.incident[u]
        target=min(incident,key=lambda e:sha(canonical([p["synthetic_seed"],u,e.transaction_id])))
        changed=replace(target,amount=str(Decimal(target.amount)*Decimal("1.01")))
        synthetic=shadow(history,[changed if e.transaction_id==target.transaction_id else e for e in history.events])
        for name,h,recomputer in (("equivalent_reverse",reversed_history,reversed_local),("amount_plus_one_percent",synthetic,FocalRecomputer(synthetic))):
            v0,meta=recomputer.vector(u); variant_stages.append({"variant":name,"account_id":u,**meta})
            s0=float(scorer.score([v0])[0]); alternative=select(h,cfg,u); vm=StrictMatcher(h,cfg.budget,p["matching"])
            observations=[]
            for method,orig in selections[u]["methods"].items():
                new=alternative["methods"][method]
                out={"method":method,"original_available":orig is not None,"variant_available":new is not None}
                if orig and new:
                    ids=new["omitted_transaction_ids"]; v,meta=recomputer.vector(u,ids); variant_stages.append({"variant":name,"account_id":u,**meta})
                    s=float(scorer.score([v])[0]); original=next(r for r in rows if r["account_id"]==u and r["method"]==method)
                    newplan=vm.match(new); oldplan=plans[u][method]
                    out.update({"original_ids":orig["omitted_transaction_ids"],"variant_ids":ids,
                        "jaccard":jaccard(orig["omitted_transaction_ids"],ids),"variant_features":v,
                        "variant_score":s,"variant_fidelity":fidelity(s0,s),"original_fidelity":original["fidelity"],
                        "fidelity_change":fidelity(s0,s)-original["fidelity"],
                        "control_status":newplan["status"],"control_sets":newplan["controls"],
                        "control_set_union_jaccard":jaccard([i for c in oldplan["controls"] for i in c["omitted_transaction_ids"]],[i for c in newplan["controls"] for i in c["omitted_transaction_ids"]]) if oldplan['controls'] and newplan['controls'] else None})
                observations.append(out)
            stability.append({"account_id":u,"variant":name,"history_sha256":h.history_sha256,
                "mutation":None if name=="equivalent_reverse" else {"transaction_id":target.transaction_id,"before":target.amount,"after":changed.amount},
                "original_baseline":baseline[u],"variant_baseline":s0,"baseline_score_change":s0-baseline[u],
                "variant_baseline_features":v0,"baseline_feature_max_error":float(np.max(np.abs(np.asarray(v0)-base_vectors[u]))),"methods":observations})
            print(f"stability {u} {name}; elapsed {time.perf_counter()-start:.1f}s",flush=True)
    similarities=[]
    for u,result in selections.items():
        for family in ("counterparty","temporal"):
            eligible=[r for r in result["eligible"] if r["family"]==family]
            similarities.append({"account_id":u,"family":family,"eligible_groups":len(eligible),
                "first_two_jaccard":jaccard(eligible[0]["omitted_transaction_ids"],eligible[1]["omitted_transaction_ids"]) if len(eligible)>1 else None})
    save(dest/"stability.json",{"variants":stability,"eligible_group_similarity":similarities,"fixed_selection_and_matching_replay_exact":True})
    save(dest/"timings.json",{"indexing_seconds":indexing_seconds,"candidate_seconds":candidate_seconds,
        "fresh_recomputations":stages,"variant_recomputations":variant_stages,"scoring_seconds":scoring_seconds,
        "aggregation_seconds":aggregation_seconds,"reference_checks_seconds":sum(r["seconds"] for r in references),
        "feasibility_seconds":probe_seconds,"memory":psutil.Process().memory_info()._asdict()})
    metrics={m:summary([r["fidelity"] for r in rows if r["method"]==m and r["available"]],len(cohort)) for m in "ABCD"}
    random_metrics={m:summary([float(np.mean([c["fidelity"] for c in controls if c["account_id"]==u and c["anchor"]==m])) for u in selections if plans[u].get(m,{}).get("status")=="matched"],len(cohort)) for m in "ABCD"}
    per_account={u:{"incremental_candidate_and_feature_seconds":candidate_seconds[u]+sum(r["total_seconds"] for r in stages if r["account_id"]==u),
        "unique_required_scenarios":sum(k[0]==u for k in required)} for u in selections}
    costs=[s["total_seconds"] for s in stages] or [meta["total_seconds"]]
    mean_cost=float(np.mean(costs)); cold=mean_cost*len(required)/len(cohort)
    save(dest/"summary.json",{"methods":metrics,"random_per_anchor_account_mean":random_metrics,
        "matched_differences":{m:summary([r["matched_fidelity_difference"] for r in rows if r["method"]==m and "matched_fidelity_difference" in r],len(cohort)) for m in "ABCD"},
        "accounts":len(cohort),"unique_required_scenarios":len(required),"fresh_scenarios":len(fresh),"reused_scenarios":len(required)-len(fresh),
        "per_account":per_account,"mean_fresh_scenario_seconds":mean_cost,"cold_per_account_projected_seconds":cold,
        "cold_250_projected_seconds":250*cold,"elapsed_seconds":time.perf_counter()-start,
        "notes":"Random means are paired-account means of two controls, not independent observations. No ranking, fraud labels, retraining, accuracy or inferential statistics."})
    if verify_protected() or any(sha((ROOT/n).read_bytes())!=h for n,h in code.items()): raise ValueError("Preservation check failed.")
    if read(CONFIG)!=p: raise ValueError("Config changed during run.")
    save(dest/"manifest.json",{"status":"complete_bounded_explanation_pilot","project_title":p["project_title"],
        "config":p,"provenance":provenance,"code_sha256":code,
        "software":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"networkx":nx.__version__,"sklearn":sklearn.__version__},
        "artifacts":{f.name:sha(f.read_bytes()) for f in dest.iterdir() if f.is_file()},"elapsed_seconds":time.perf_counter()-start})
    print(f"COMPLETE {time.perf_counter()-start:.1f}s",flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("run_id"); parser.add_argument("--worker",action="store_true"); args=parser.parse_args()
    if not args.run_id.startswith("phase6a-") or not args.run_id.replace("-","").isalnum(): raise ValueError("Phase6A run ID required.")
    dest=ROOT/"data/results/v2"/args.run_id
    if args.worker:
        try: worker(dest)
        except Exception as e:
            save(dest/"incomplete.json",{"exception":type(e).__name__,"reason":str(e)}); raise
        return
    p=read(CONFIG)
    if not 0<p["wall_budget_seconds"]<=1800: raise ValueError("Invalid wall budget.")
    dest.mkdir(exist_ok=False); save(dest/"config.json",p)
    child=subprocess.Popen([sys.executable,"-u",str(Path(__file__).resolve()),args.run_id,"--worker"],cwd=ROOT)
    try: code=child.wait(timeout=p["wall_budget_seconds"])
    except subprocess.TimeoutExpired:
        child.kill();child.wait();save(dest/"timeout.json",{"budget_seconds":p["wall_budget_seconds"]});raise SystemExit(124)
    raise SystemExit(code)


if __name__=="__main__": main()
