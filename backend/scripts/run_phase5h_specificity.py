"""Bounded append-only E6_CREST_V2 pilot; reuse authenticated Phase 5G evidence."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import joblib
import networkx as nx
import numpy as np
import pandas as pd
import psutil
import sklearn
from backend.app.services.research_protocol import canonical, sha
from backend.app.services.artifact_integrity import verify_protected
from backend.app.research.benchmark.runner import verify
from backend.app.research.crest.schemas import CrestConfig
from backend.app.research.crest.frozen_scorer import EmpiricalCalibrator
from backend.app.research.crest.statistics import summarize as v1_summarize, influence, stratum, candidate_score
from backend.app.research.interventions.schemas import InterventionConfig
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.feature_recomputation import recompute
from backend.app.research.feasibility_gate.focal_features import FocalRecomputer
from backend.app.research.feasibility_gate.pilot_design import CandidateIndex, select_cohort
from backend.app.research.evidence_specificity.matching import StrictMatcher
from backend.app.research.evidence_specificity.scoring import FrozenBatchScorer, summarize, ranks

CONFIG = ROOT/"docs/research/configs/phase5h_specificity_v2.json"
G = ROOT/"data/results/v2/phase5g-feasibility-v1-recovery"
EXPECTED = "508a84edfc7eef3cf2a9b99d7b776533c49d742ef5215d18ce59a4e46ec6daff"


def read(path): return json.loads(path.read_bytes())


def save(path, value):
    with path.open("xb") as f: f.write(canonical(value))


def verified_manifest(directory, expected=None):
    m = read(directory/"manifest.json")
    if expected and sha((directory/"manifest.json").read_bytes()) != expected:
        raise ValueError("Input manifest identity changed.")
    for name, digest in m.get("artifacts", m.get("artifact_sha256", {})).items():
        path = (directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or sha(path.read_bytes()) != digest:
            raise ValueError("Upstream artifact identity mismatch: "+name)
    return m


def key(u, ids): return (u, tuple(sorted(ids)))


def v1_statistics_for_account(u, s0, structured, empirical, config):
    profiles = []
    for row in structured:
        if row["focal_account"] == u:
            q0, qm = empirical.transform([s0, row["raw_intervened"]])
            # Frozen v1 also needs omission fractions for its diagnostic strata.
            profiles.append({**row, "budget_stratum": stratum(row, config), **influence(q0, qm)})
    return v1_summarize(profiles, [], config)


def worker(dest):
    started = time.perf_counter(); p = read(CONFIG)
    source_code = {f.relative_to(ROOT).as_posix(): sha(f.read_bytes())
                   for f in (ROOT/"backend/app").rglob("*.py")}
    source_code[Path(__file__).relative_to(ROOT).as_posix()] = sha(Path(__file__).read_bytes())
    if sha((ROOT/"docs/research/configs/phase5_protocol_v1.json").read_bytes()) != EXPECTED:
        raise ValueError("Frozen protocol changed.")
    if verify_protected(): raise ValueError("Protected bytes changed.")
    gm = verified_manifest(G, p["pilot_manifest_sha256"])
    for name, digest in gm["code_sha256"].items():
        if sha((ROOT/name).read_bytes()) != digest: raise ValueError("Phase5G code changed.")
    base = ROOT/"data/results/v2/phase5-baselines-5k-v1"
    verify(base, EXPECTED); verify(ROOT/"data/results/v2/phase5-baselines-50k-v1", EXPECTED)
    split = base/"split-42-model-42"
    model_path = split/"model.joblib"
    if sha(model_path.read_bytes()) != gm["input_model_sha256"]: raise ValueError("Model identity mismatch.")
    model = joblib.load(model_path); scorer = FrozenBatchScorer(model)
    cal = read(split/"calibration.json"); crest_cfg = CrestConfig(**cal["config"])
    empirical = EmpiricalCalibrator(cal["reference"])
    baseline = read(split/"scores.json")["E4"]
    selection = read(G/"pilot_selection.json")
    cfg = InterventionConfig(**selection["config"])
    if cfg.budget.model_dump() != p["budget"]: raise ValueError("Budget mismatch.")
    dataset = ROOT/"data/research/ibm_aml_medium_5k.csv"
    content = dataset.read_bytes()
    if sha(content) != gm["dataset_sha256"]: raise ValueError("Dataset mismatch.")
    history = load_history(content, cfg); local = FocalRecomputer(history)
    cohort = select_cohort(baseline, CandidateIndex(history,cfg),2,1901)
    if cohort != selection["accounts"]: raise ValueError("Label-free cohort does not replay.")
    for r in cohort:
        n = r["incident_count"]
        r["activity_group"] = "low" if n < 5 else "middle" if n < 30 else "high"
        if r["account_id"] not in crest_cfg.evaluation_ids or r["account_id"] in crest_cfg.train_ids:
            raise ValueError("Pilot must be held out from frozen model training.")
    if {r["activity_group"] for r in cohort} != {"low","middle","high"}:
        raise ValueError("Fixed reused cohort lacks declared activity coverage.")
    save(dest/"cohort.json", {"accounts":cohort,"selection_labels_used":False,
         "source_train_ids_sha256":sha(canonical(crest_cfg.train_ids)),
         "heldout_ids_sha256":sha(canonical(crest_cfg.evaluation_ids)),
         "history_sha256":history.history_sha256,"cutoff":history.cutoff})
    old_rows = [json.loads(line) for line in (G/"pilot_interventions.jsonl").read_bytes().splitlines()]
    structured = [r for r in old_rows if r["kind"] == "structured"]
    old_controls = {r["pair_id"]:r for r in old_rows if r["kind"] == "control"}
    matcher = StrictMatcher(history,cfg.budget,p["matching"])
    matching_start = time.perf_counter()
    plans = [matcher.match(r) for r in structured]
    if plans != [matcher.match(r) for r in structured]: raise AssertionError("Matching replay failed.")
    matching_seconds = time.perf_counter()-matching_start
    # Selection/tolerances and all control identities fixed before new v2 outcomes.
    save(dest/"matching_plan.json", {"plans":plans,"matching_and_replay_seconds":matching_seconds,
                                  "rule":p["matching"],"outcomes_used":False})
    cache = {}; base_vectors = {}; diagnosis = []
    for r in old_rows:
        u = r["focal_account"]; ids = r["omitted_transaction_ids"]
        if local.identity(u,ids) != r["recomputation"]["cache_key"]:
            raise ValueError("History-aware reused feature identity mismatch.")
        k = key(u,ids); v = r["intervened_features"]
        if k in cache and cache[k]["vector"] != v: raise ValueError("Conflicting cached vectors.")
        cache[k] = {"vector":v,"origin":"verified_phase5g","raw":r["raw_intervened"]}
        if u in base_vectors and base_vectors[u] != r["baseline_features"]: raise ValueError("Baseline vector conflict.")
        base_vectors[u] = r["baseline_features"]
    old_scored = scorer.verify_batch([r["intervened_features"] for r in old_rows])
    if not np.array_equal(old_scored, [r["raw_intervened"] for r in old_rows]):
        raise AssertionError("Authenticated legacy vector scoring differs.")
    for u,v in base_vectors.items():
        if float(scorer.score([v])[0]) != baseline[u]: raise AssertionError("Original E4 changed.")
    for r, plan in zip(structured, plans):
        c = old_controls[r["pair_id"]]; u = r["focal_account"]
        assess = matcher.assess(u,r["omitted_transaction_ids"],c["omitted_transaction_ids"])
        diagnosis.append({"account_id":u,"family":r["family"],"original_pair_id":r["pair_id"],
            "structured":r,"old_control":c,"strict_assessment":assess,
            "raw_pair_excess":r["raw_signed_change"]-c["raw_signed_change"],
            "above_noise_threshold":abs(r["raw_signed_change"]-c["raw_signed_change"])>p["numerical_diagnostic_threshold"],
            "new_match_id":plan["match_id"],"new_status":plan["status"]})
    save(dest/"phase5g_pair_diagnosis.json",diagnosis)
    required = set(key(r["focal_account"],r["omitted_transaction_ids"]) for r in structured)
    for plan in plans:
        required.update(key(plan["focal_account"],c["omitted_transaction_ids"]) for c in plan["controls"])
    fresh_keys = sorted(required-cache.keys()); reference_checks = []; stages = []; checked = set()
    score_stratum = {r["account_id"]:r["score_stratum"] for r in cohort}
    for i,k in enumerate(fresh_keys):
        if time.perf_counter()-started > p["wall_budget_seconds"]: raise TimeoutError("Phase5H budget exhausted.")
        u, ids = k; vector, meta = local.vector(u,ids)
        cache[k] = {"vector":vector,"origin":"fresh_focal","recomputation":meta}
        stages.append({"account_id":u,"omitted_ids":ids,**meta})
        with (dest/"fresh_vectors.jsonl").open("ab") as f:
            f.write(canonical({"account_id":u,"omitted_ids":ids,"vector":vector,"timing":meta})+b"\n")
        s = score_stratum[u]
        if s not in checked:
            check_start = time.perf_counter(); ref,_ = recompute(history,ids)
            replay,_ = local.vector(u,ids,use_cache=False)
            if vector != ref[u] or vector != replay: raise AssertionError("Feature equivalence/replay failed.")
            values = scorer.verify_batch([vector,ref[u],replay])
            if len(set(map(float,values))) != 1: raise AssertionError("Reference score mismatch.")
            reference_checks.append({"account_id":u,"stratum":s,"omitted_ids":ids,
                "max_abs_feature_error":0.0,"max_abs_score_error":0.0,
                "seconds":time.perf_counter()-check_start})
            checked.add(s)
        print(f"new control scenario {i+1}/{len(fresh_keys)}, elapsed {time.perf_counter()-started:.1f}s",flush=True)
    required = sorted(required)
    vectors = [cache[k]["vector"] for k in required]
    t = time.perf_counter(); batch = scorer.verify_batch(vectors); scoring_seconds = time.perf_counter()-t
    for k, raw in zip(required,batch): cache[k]["raw"] = float(raw)
    comparisons = []
    for original, plan in zip(structured,plans):
        u=plan["focal_account"]; s0=baseline[u]
        ss=cache[key(u,plan["structured_ids"])]["raw"]
        controls=[{**c,"raw_intervened":cache[key(u,c["omitted_transaction_ids"])]["raw"],
                    "delta":s0-cache[key(u,c["omitted_transaction_ids"])]["raw"]} for c in plan["controls"]]
        comparisons.append({**plan,"raw_e4":s0,"structured_score":ss,"structured_delta":s0-ss,
            "controls":controls,"control_deltas":[c["delta"] for c in controls],
            "original_pair_id":original["pair_id"]})
    save(dest/"comparisons.json",comparisons)
    account_results=[]; full_scores={"E4":dict(baseline),"E6_CREST_V2":dict(baseline)}
    full_scores["E6_BASE_V1"] = dict(zip(sorted(baseline),map(float,empirical.transform([baseline[u] for u in sorted(baseline)]))))
    full_scores["E6_HYBRID_V1"] = dict(full_scores["E6_BASE_V1"])
    g_accounts={r["account_id"]:r for r in read(G/"pilot_accounts.json")}
    for entry in cohort:
        u=entry["account_id"]; s0=baseline[u]; cp=[r for r in comparisons if r["focal_account"]==u]
        result=summarize(s0,cp,p["ranking"]["lambda"])
        if result != summarize(s0,list(reversed(cp)),p["ranking"]["lambda"]): raise AssertionError("Aggregation order dependence.")
        if summarize(s0,cp,0)["score"] != s0: raise AssertionError("Zero-weight identity failed.")
        v1=v1_statistics_for_account(u,s0,structured,empirical,crest_cfg)
        v1score,v1missing=candidate_score(full_scores["E6_BASE_V1"][u],v1,"E6_HYBRID",crest_cfg.alpha,crest_cfg.beta)
        full_scores["E6_HYBRID_V1"][u]=v1score; full_scores["E6_CREST_V2"][u]=result["score"]
        account_results.append({**entry,**result,"matched_interventions":sum(r["status"]=="matched" for r in cp),
            "v1_statistics":v1,"v1_hybrid":v1score,"v1_fallback":v1missing,
            "phase5g_affine_hybrid":g_accounts[u]["structured"]["scores"]["RAW_HYBRID"]})
    pilot_ids=[r["account_id"] for r in cohort]
    small_scores={name:{u:values[u] for u in pilot_ids} for name,values in full_scores.items()}
    small_scores["PHASE5G_AFFINE_HYBRID"]={r["account_id"]:r["phase5g_affine_hybrid"] for r in account_results}
    small_ranks={name:ranks(s) for name,s in small_scores.items()}; full_ranks={name:ranks(s) for name,s in full_scores.items()}
    ranking_summary={name:{"changed_pilot_ranks_vs_e4":sum(rs[u]!=small_ranks["E4"][u] for u in pilot_ids),
        "changed_full_ranks_vs_e4":sum(full_ranks[name][u]!=full_ranks["E4"][u] for u in baseline) if name in full_ranks else None}
        for name,rs in small_ranks.items()}
    save(dest/"account_statistics.json",account_results)
    save(dest/"rankings.json",{"pilot_scores":small_scores,"pilot_ranks":small_ranks,
        "full_scores":full_scores,"full_ranks":full_ranks,"summary":ranking_summary,
        "warning":"Full scores retain explicit nonselected fallback; changed rank count is not intervention coverage"})
    zero_checks=[]
    for tier in ("5k","50k"):
        for seed in (42,123,7,2024,99,555):
            raw=read(ROOT/f"data/results/v2/phase5-baselines-{tier}-v1/split-{seed}-model-42/scores.json")["E4"]
            zero={u:summarize(s,[],0)["score"] for u,s in raw.items()}
            if zero!=raw or ranks(zero)!=ranks(raw): raise AssertionError("12-split zero identity failed.")
            zero_checks.append({"tier":tier,"seed":seed,"accounts":len(raw),"scores_exact":True,"ranks_exact":True})
    save(dest/"zero_weight_checks.json",zero_checks)
    save(dest/"reference_checks.json",reference_checks)
    save(dest/"scored_vectors.json",[{"account_id":k[0],"omitted_ids":k[1],**cache[k]} for k in required])
    costs=[r["total_seconds"] for r in stages]
    g_costs=[r["recomputation"]["total_seconds"] for r in old_rows if not r["recomputation"]["cache_hit"]]
    mean_cold=float(np.mean(costs)) if costs else float(np.mean(g_costs))
    # Include all structured scenarios, even unmatched; caller may later avoid those
    # under a separately fixed protocol, but this projection makes no such reduction.
    cold_per_account=len(required)/len(cohort)*mean_cold+matching_seconds/len(cohort)
    projections=[{"accounts":n,"cold_same_5k_seconds":cold_per_account*n,
        "within_1800_scenario":cold_per_account*n<=1800,"measured":False,
        "qualification":"same 5K eligible mix; excludes startup/reference checks, not a bound" if n!=14998 else "same-5K-cost counterfactual only; 50K unprofiled, 10000-node guard retained"} for n in (250,500,1500,14998)]
    summary={"accounts":6,"eligible_phase5g_accounts":6,"valid_structured_interventions":len(structured),
        "matched_structured":sum(r["status"]=="matched" for r in plans),
        "unmatched_reasons":dict(Counter(r["reason"] for r in plans if r["status"]!="matched")),
        "matched_controls":sum(len(r["controls"]) for r in plans),
        "matched_family_counts":dict(Counter(r["family"] for r in plans if r["status"]=="matched")),
        "old_pairs_comparable_under_new_calipers":sum(r["strict_assessment"]["comparable"] for r in diagnosis),
        "old_pairs_above_noise":sum(r["above_noise_threshold"] for r in diagnosis),
        "accounts_with_excess_above_noise":sum(abs(r["excess"] or 0)>p["numerical_diagnostic_threshold"] for r in account_results),
        "fallback_accounts":sum(r["fallback_reason"] is not None for r in account_results),
        "changed_scores":sum(r["score_changed"] for r in account_results),"ranking":ranking_summary,
        "unique_required_scenarios":len(required),"fresh_scenarios":len(fresh_keys),
        "reused_scenarios":len(required)-len(fresh_keys),"fresh_recompute_seconds":sum(costs),
        "matching_with_repeat_seconds":matching_seconds,"batch_with_singleton_verification_seconds":scoring_seconds,
        "mean_fresh_scenario_seconds":mean_cold,"cold_per_account_scenario_seconds":cold_per_account,
        "projections":projections,"reference_checks":len(reference_checks),
        "fixed_matching_replay_exact":True,"batch_singleton_scores_exact":True,
        "memory":psutil.Process().memory_info()._asdict(),"elapsed_seconds":time.perf_counter()-started,
        "scope":"Label-free feasibility; no detector metrics; no claim of evidence specificity as fraud causation"}
    save(dest/"summary.json",summary)
    if verify_protected(): raise ValueError("Protected bytes changed after run.")
    if any(sha((ROOT/n).read_bytes())!=h for n,h in source_code.items()): raise ValueError("Code changed during run.")
    if sha(CONFIG.read_bytes()) != sha((dest/"config.json").read_bytes()):
        # The saved config is canonical JSON; compare semantic identity below.
        if read(CONFIG)!=read(dest/"config.json"): raise ValueError("Configuration changed during run.")
    manifest={"status":"complete_bounded_pilot","stage":"phase5h-evidence-specificity-v2",
        "project_title":p["project_title"],"configuration":p,"config_source_sha256":sha(CONFIG.read_bytes()),
        "parent_protocol_sha256":EXPECTED,"input_phase5g_manifest_sha256":sha((G/"manifest.json").read_bytes()),
        "model_sha256":sha(model_path.read_bytes()),"calibration_sha256":sha((split/"calibration.json").read_bytes()),
        "dataset_sha256":sha(content),"history_sha256":history.history_sha256,
        "input_baseline_manifest_sha256":sha((base/"manifest.json").read_bytes()),
        "code_sha256":source_code,"artifacts":{f.name:sha(f.read_bytes()) for f in dest.iterdir() if f.is_file()},
        "software":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"networkx":nx.__version__,"sklearn":sklearn.__version__},
        "total_seconds":time.perf_counter()-started,"memory":psutil.Process().memory_info()._asdict()}
    save(dest/"manifest.json",manifest)
    print(json.dumps({"run":str(dest),"seconds":manifest["total_seconds"],"matched":summary["matched_structured"],
        "fresh":len(fresh_keys),"ranking":ranking_summary}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("run_id");parser.add_argument("--worker",action="store_true")
    args=parser.parse_args()
    if not args.run_id.startswith("phase5h-") or not args.run_id.replace("-","").isalnum(): raise ValueError("New phase5h run ID required.")
    dest=ROOT/"data/results/v2"/args.run_id
    if args.worker:
        try: worker(dest)
        except Exception as exc:
            save(dest/"incomplete.json",{"status":"failed","type":type(exc).__name__,"reason":str(exc)})
            raise
        return
    p=read(CONFIG)
    if not 0 < p["wall_budget_seconds"] <= 1800: raise ValueError("Maximum budget is 1800 seconds.")
    dest.mkdir(exist_ok=False);save(dest/"config.json",p)
    child=subprocess.Popen([sys.executable,"-u",str(Path(__file__).resolve()),args.run_id,"--worker"],cwd=ROOT)
    try: code=child.wait(timeout=p["wall_budget_seconds"])
    except subprocess.TimeoutExpired:
        child.kill();child.wait();save(dest/"timeout.json",{"status":"incomplete","budget":p["wall_budget_seconds"]})
        raise SystemExit(124)
    raise SystemExit(code)


if __name__ == "__main__": main()
