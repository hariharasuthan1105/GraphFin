"""Artifact-only Phase6A replay/integrity verification; no graph experiments."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import joblib
import numpy as np
from backend.scripts.run_phase5h_specificity import read,save,verified_manifest
from backend.app.services.research_protocol import sha
from backend.app.services.artifact_integrity import verify_protected,protected_manifest
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.schemas import InterventionConfig
from backend.app.research.evidence_specificity.matching import StrictMatcher
from backend.app.research.evidence_specificity.scoring import FrozenBatchScorer
from backend.app.research.explanation_validation.diagnostics import select,sparsity,fidelity,paired


def main():
    parser=argparse.ArgumentParser();parser.add_argument("run");parser.add_argument("snapshot");parser.add_argument("zip");parser.add_argument("destination");args=parser.parse_args()
    run=(ROOT/args.run).resolve();m=verified_manifest(run)
    if m["status"]!="complete_bounded_explanation_pilot":raise ValueError("Incomplete run")
    for name,digest in m["code_sha256"].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError("Code mismatch: "+name)
    previous=read(Path(args.snapshot));changed=[n for n,h in previous.items() if sha((ROOT/n).read_bytes())!=h]
    if changed or verify_protected():raise ValueError("Historical files changed: "+str(changed))
    # ZIP paths are matched by a unique suffix, with byte-level digests.
    with zipfile.ZipFile(args.zip) as z:
        checked=[]
        for name in protected_manifest()["files"]:
            candidates=[p for p in z.namelist() if p.endswith("/"+name) or p==name]
            if len(candidates)!=1 or sha(z.read(candidates[0]))!=sha((ROOT/name).read_bytes()):raise ValueError("ZIP mismatch: "+name)
            checked.append(name)
    cfg=InterventionConfig(**read(ROOT/"data/results/v2/phase5g-feasibility-v1-recovery/pilot_selection.json")["config"])
    h=load_history((ROOT/"data/research/ibm_aml_medium_5k.csv").read_bytes(),cfg)
    if h.history_sha256!=m["provenance"]["history_sha256"]:raise ValueError("History differs")
    matcher=StrictMatcher(h,cfg.budget,m["config"]["matching"])
    plan=read(run/"selection_plan.json")
    for u,result in plan["selections"].items():
        assert result==select(h,cfg,u)
        assert plan["controls"][u]=={method:matcher.match(r) for method,r in result["methods"].items() if r}
    modelpath=ROOT/"data/results/v2/phase5-baselines-5k-v1/split-42-model-42/model.joblib"
    assert sha(modelpath.read_bytes())==m["provenance"]["model_sha256"]
    scorer=FrozenBatchScorer(joblib.load(modelpath)); rows=read(run/"explanations.json"); controls=read(run/"random_explanations.json")
    baseline=read(modelpath.parent/"scores.json")["E4"]
    for r in rows+controls:
        assert r["original_score"]==baseline[r["account_id"]]==float(scorer.score([r["original_features"]])[0])
        if r["available"]:
            assert r["intervened_score"]==float(scorer.score([r["intervened_features"]])[0])
            assert r["fidelity"]==fidelity(r["original_score"],r["intervened_score"])
            assert r["sparsity"]==sparsity(h,cfg,r["account_id"],r["omitted_transaction_ids"])
    assert paired(rows)==read(run/"paired_comparisons.json")
    variants=read(run/"stability.json")["variants"]
    for r in variants:
        assert float(scorer.score([r["variant_baseline_features"]])[0])==r["variant_baseline"]
        for a in r["methods"]:
            if a["original_available"] and a["variant_available"]:
                assert float(scorer.score([a["variant_features"]])[0])==a["variant_score"]
                assert fidelity(r["variant_baseline"],a["variant_score"])==a["variant_fidelity"]
    out=Path(args.destination);out.mkdir(exist_ok=False)
    save(out/"verification.json",{"snapshot_files_unchanged":len(previous),"protected_files":len(checked),"zip_matches":len(checked),
        "pilot_manifest_sha256":sha((run/"manifest.json").read_bytes()),"explanation_records":len(rows),"control_records":len(controls),
        "selection_and_matching_replay_exact":True,"original_scores_exact":True,"rescored_artifacts_exact":True,
        "paired_comparisons_exact":True,"variant_records":len(variants),"historical_mismatches":changed,
        "verification_script_sha256":sha(Path(__file__).read_bytes()),"snapshot_sha256":sha(Path(args.snapshot).read_bytes())})
    print(json.dumps(read(out/"verification.json")))


if __name__=="__main__":main()
