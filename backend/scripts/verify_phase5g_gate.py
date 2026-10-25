"""Read-only scientific/integrity replay; exclusive new review output directory."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
from backend.app.services.research_protocol import canonical, sha
from backend.app.services.artifact_integrity import protected_manifest, verify_protected
from backend.app.research.feasibility_gate.raw_scoring import TrainingAffine, raw_modes


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run"); p.add_argument("snapshot"); p.add_argument("source_zip"); p.add_argument("output")
    args = p.parse_args()
    run = Path(args.run).resolve()
    read = lambda name: json.loads((run/name).read_bytes())
    manifest = read("manifest.json")
    assert manifest["status"] == "complete_bounded_pilot"
    for name, digest in manifest["artifacts"].items():
        assert sha((run/name).read_bytes()) == digest, name
    for name, digest in manifest["code_sha256"].items():
        assert sha((ROOT/name).read_bytes()) == digest, name
    before = json.loads(Path(args.snapshot).read_bytes())
    assert all(sha((ROOT/name).read_bytes()) == h for name, h in before.items())
    assert not verify_protected()
    protected = protected_manifest()["files"]
    with zipfile.ZipFile(args.source_zip) as z:
        for name, digest in protected.items():
            choices = [n for n in z.namelist() if n == name or n.endswith("/"+name)]
            assert len(choices) == 1, name
            assert sha(z.read(choices[0])) == digest, name
    base = ROOT/"data/results/v2/phase5-baselines-5k-v1/split-42-model-42"
    model = joblib.load(base/"model.joblib")
    affine = TrainingAffine(json.loads((base/"calibration.json").read_bytes())["reference"])
    rows = [json.loads(line) for line in (run/"pilot_interventions.jsonl").read_bytes().splitlines()]
    # Union check includes all held-out scores and every intervention score.
    scores = json.loads((base/"scores.json").read_bytes())["E4"]
    affine.transform([*scores.values(), *[r["raw_intervened"] for r in rows]])
    for r in rows:
        actual = float(-model.decision_function(np.asarray([r["intervened_features"]], dtype=np.float32))[0])
        assert actual == r["raw_intervened"]
        assert r["affine_signed_change"] == float(affine.transform([r["raw_baseline"]])[0]-affine.transform([actual])[0])
    for account in read("pilot_accounts.json"):
        for kind in ("structured", "control"):
            groups = {}
            for r in rows:
                if r["focal_account"] == account["account_id"] and r["kind"] == kind:
                    groups.setdefault(r["family"], []).append(r["affine_signed_change"])
            assert raw_modes(account["affine_baseline"], groups) == account[kind]
    uncached = [r for r in rows if not r["recomputation"]["cache_hit"]]
    mean_seconds = float(np.mean([r["recomputation"]["total_seconds"]+r["frozen_model_scoring_seconds"] for r in uncached]))
    accounts = read("pilot_accounts.json")
    mean_generation = float(np.mean([r["candidate_generation_seconds"] for r in accounts]))
    mean_accepted = float(np.mean([r["accepted_structured"] for r in accounts]))
    setup = read("runtime_projections.json")["measured_setup_seconds"]
    review = {"input_manifest_sha256": sha((run/"manifest.json").read_bytes()),
        "verifier_sha256": sha(Path(__file__).read_bytes()), "protected_zip_matches": len(protected),
        "preexisting_snapshot_matches": len(before), "all_manifest_artifacts_and_code_match": True,
        "saved_vector_score_replays": len(rows), "account_mode_replays": len(accounts)*2,
        "joint_heldout_intervention_affine_order": "preserved", "uncached_rows": len(uncached),
        "uncached_mean_recompute_and_score_seconds": mean_seconds,
        "global_share_uncached_recompute": sum(r["recomputation"]["graph_and_global_centrality_seconds"] for r in uncached)/sum(r["recomputation"]["total_seconds"] for r in uncached),
        "cache_free_scenarios_seconds": {str(n): setup+n*(mean_generation+mean_accepted*mean_seconds) for n in (250,500,1500,14998)},
        "projection_qualification": "Same 5K eligible mix; average uncached cost, not a bound or confidence interval; 50K unprofiled and guarded."}
    output = Path(args.output).resolve(); output.mkdir(exist_ok=False)
    with (output/"review.json").open("xb") as f: f.write(canonical(review))
    print(json.dumps(review))


if __name__ == "__main__":
    main()
