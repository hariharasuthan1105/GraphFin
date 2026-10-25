"""Bounded, label-free CREST demonstration; reuse matching Phase 3 evidence.

python -m backend.scripts.demonstrate_phase4 data/results/v2 phase4-demo
"""
import argparse
import json
import time
import tracemalloc
from pathlib import Path
from backend.app.services.research_protocol import ROOT, canonical, sha
from backend.app.research.interventions.schemas import InterventionConfig, Budget
from backend.app.research.interventions.artifact_writer import write_run
from backend.app.research.crest.schemas import CrestConfig
from backend.app.research.crest.artifacts import load_bundle
from backend.app.research.crest.runner import run


def prepare_demo(root):
    directory = root/"phase4-demo-inputs-v1"
    content = (ROOT/"docs/research/fixtures/phase3_transactions.csv").read_bytes()
    cfg = InterventionConfig(dataset_id="phase4-synthetic-demo",source_identity="phase3-synthetic-demo-v1",
        time_kind="simulation_hour",cutoff="9",window_unit="hours",window_size=1,
        known_accounts=("ISOLATED",),budget=Budget(max_count=1,max_fraction=.5,min_retained=1,max_interventions=12))
    focals = ["A","B","C","D","E","F","ISOLATED","X","Y"]
    reused = directory.exists()
    if not reused:
        write_run(content,cfg,focals,root,directory.name)
    digest = sha((directory/"manifest.json").read_bytes())
    bundle = load_bundle(directory,digest,cfg.dataset_id)
    expected = json.loads(canonical({**cfg.model_dump(),"focal_accounts":sorted(focals)}))
    if bundle["manifest"]["configuration"] != expected or bundle["manifest"]["source"]["transactions_sha256"] != sha(content):
        raise ValueError("Existing demo evidence does not match prespecified fixture/configuration.")
    return directory,digest,reused


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root",type=Path)
    parser.add_argument("prefix")
    args = parser.parse_args()
    root = args.output_root.resolve()
    if root.is_relative_to(ROOT) and not root.is_relative_to(ROOT/"data/results/v2"):
        raise ValueError("Use versioned output root.")
    if not args.prefix.replace("-","").replace("_","").isalnum():
        raise ValueError("Invalid prefix.")
    evidence = root/(args.prefix+"-evidence")
    evidence.mkdir(parents=True,exist_ok=False)
    prepare_start = time.perf_counter()
    source,digest,reused = prepare_demo(root)
    prepare_seconds = time.perf_counter()-prepare_start
    config = CrestConfig(source_dataset_id="phase4-synthetic-demo",evaluation_dataset_id="phase4-synthetic-demo",
        source_manifest_sha256=digest,evaluation_manifest_sha256=digest,split_id="explicit-synthetic-holdout-v1",
        train_ids=("A","B","C","F","X","Y"),evaluation_ids=("D","E","ISOLATED"),
        model_seed=42,n_estimators=100,contamination=.005,alpha=.25,beta=.25)
    measures, manifests = [], []
    for suffix in ["a","b"]:
        tracemalloc.start()
        start = time.perf_counter()
        m = run(config,source,source,root,args.prefix+"-"+suffix)
        elapsed, peak = time.perf_counter()-start,tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        manifests.append(m)
        measures.append({"run":suffix,"wall_seconds":elapsed,"peak_traced_python_bytes":peak,
                         "stage_timings":m["timing_seconds"]})
    fields = ["accounts.json","intervention_scores.jsonl","rankings.json","calibration.json","model.joblib"]
    equality = {name:manifests[0]["artifact_sha256"][name]==manifests[1]["artifact_sha256"][name] for name in fields}
    assert all(equality.values())
    accounts = json.loads((root/(args.prefix+"-a")/"accounts.json").read_text())
    profiles = [{"account_id":a["account_id"],"raw_s0":a["raw_baseline_score"],"q0":a["calibrated_score"],
                 "D":a["statistics"]["sensitivity"],"R":a["statistics"]["robustness"],
                 "valid_interventions":a["statistics"]["available_interventions"]} for a in accounts]
    result = {"prepare_seconds":prepare_seconds,"existing_phase3_artifacts_reused":reused,
        "phase3_manifest_sha256":digest,"repeat_artifact_equality":equality,"measurements":measures,
        "profiles":profiles,"memory_scope":"tracemalloc Python allocation peaks, not total process/native RSS",
        "protocol":"prespecified explicit six training/three evaluation IDs, no labels, no weight tuning",
        "interpretation":"Observed model sensitivity only; no accuracy or novelty claims"}
    (evidence/"demonstration.json").write_bytes(canonical(result))
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
