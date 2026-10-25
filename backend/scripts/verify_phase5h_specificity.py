"""Verify two completed Phase5H pilots, original bytes and independent summaries."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from backend.app.services.research_protocol import canonical, sha
from backend.app.services.artifact_integrity import protected_manifest, verify_protected
from backend.scripts.run_phase5h_specificity import verified_manifest, read, save


def main():
    p=argparse.ArgumentParser()
    for name in ("run","replay","snapshot","source_zip","output"): p.add_argument(name)
    a=p.parse_args(); run=Path(a.run).resolve(); replay=Path(a.replay).resolve()
    manifests=[]
    for folder in (run,replay):
        m=verified_manifest(folder)
        if m["status"]!="complete_bounded_pilot": raise ValueError("Incomplete pilot.")
        for name,h in m["code_sha256"].items():
            if sha((ROOT/name).read_bytes())!=h: raise ValueError("Code fingerprint mismatch.")
        manifests.append(m)
    scientific=["cohort.json","comparisons.json","account_statistics.json","rankings.json","zero_weight_checks.json","phase5g_pair_diagnosis.json"]
    for name in scientific:
        if read(run/name)!=read(replay/name): raise AssertionError("Scientific replay differs: "+name)
    if read(run/"matching_plan.json")["plans"]!=read(replay/"matching_plan.json")["plans"]:
        raise AssertionError("Matching differs.")
    vectors=[]
    for folder in (run,replay):
        vectors.append([{k:r[k] for k in ("account_id","omitted_ids","vector","raw")} for r in read(folder/"scored_vectors.json")])
    if vectors[0]!=vectors[1]: raise AssertionError("Fresh/reused feature-score replay differs.")
    accounts=read(run/"account_statistics.json"); comps=read(run/"comparisons.json")
    all_controls=[]
    for r in comps:
        if r["structured_delta"]!=r["raw_e4"]-r["structured_score"]: raise AssertionError("Delta mismatch.")
        if r["status"]=="matched":
            if len(r["controls"])!=2: raise AssertionError("Control support mismatch.")
            for c in r["controls"]:
                if not c["assessment"]["comparable"]: raise AssertionError("Invalid comparison.")
                if c["delta"]!=r["raw_e4"]-c["raw_intervened"]: raise AssertionError("Control delta mismatch.")
                all_controls.append((r["focal_account"],tuple(c["omitted_transaction_ids"])))
    effects=[]
    for u in accounts:
        fs=[]
        for family in ("counterparty","temporal","budgeted"):
            rows=[r for r in comps if r["focal_account"]==u["account_id"] and r["family"]==family and r["status"]=="matched"]
            if rows:
                value=float(np.median([r["structured_delta"] for r in rows])-np.median([c["delta"] for r in rows for c in r["controls"]]))
                if value!=u["families"][family]["excess"]: raise AssertionError("Independent family calculation mismatch.")
                fs.append(value);effects.append(value)
        if fs and not np.isclose(np.mean(fs),u["excess"],rtol=0,atol=1e-16):
            raise AssertionError("Independent family mean mismatch.")
    before=read(Path(a.snapshot));changed=[n for n,h in before.items() if not (ROOT/n).exists() or sha((ROOT/n).read_bytes())!=h]
    if changed or verify_protected(): raise AssertionError("Preserved files changed.")
    protected=protected_manifest()["files"]
    with zipfile.ZipFile(a.source_zip) as z:
        for name,h in protected.items():
            choices=[n for n in z.namelist() if n==name or n.endswith("/"+name)]
            if len(choices)!=1 or sha(z.read(choices[0]))!=h: raise AssertionError("ZIP provenance mismatch.")
    old=read(run/"phase5g_pair_diagnosis.json")
    summary=read(run/"summary.json")
    review={"manifest_hashes":[sha((f/"manifest.json").read_bytes()) for f in (run,replay)],
        "verifier_sha256":sha(Path(__file__).read_bytes()),"scientific_json_replays":scientific,
        "matching_exact":True,"feature_score_rows_exact":len(vectors[0]),
        "independent_family_statistics_verified":len(effects),"family_nonzero_above_1e_minus12":sum(abs(x)>1e-12 for x in effects),
        "control_observations":len(all_controls),"unique_control_scenarios":len(set(all_controls)),
        "old_pair_max_abs_raw_difference":max(abs(r["raw_pair_excess"]) for r in old),
        "old_comparable_pair_excess":[r["raw_pair_excess"] for r in old if r["strict_assessment"]["comparable"]],
        "old_rejection_reasons":{reason:sum(r["strict_assessment"]["reason"]==reason for r in old) for reason in sorted({str(r["strict_assessment"]["reason"]) for r in old if r["strict_assessment"]["reason"] is not None})},
        "preserved_snapshot_files":len(before),"protected_zip_matches":len(protected),
        "run_seconds":[m["total_seconds"] for m in manifests],"coverage":summary["matched_structured"],
        "scientific_note":"Deterministic mechanics and matching, not fraud effectiveness or independent sampling."}
    dest=Path(a.output).resolve();dest.mkdir(exist_ok=False);save(dest/"review.json",review)
    print(json.dumps(review))


if __name__=="__main__":main()
