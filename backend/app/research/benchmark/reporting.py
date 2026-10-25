"""Produce tables solely from completed, hash-verified Phase 5 stages."""
import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from ...services.research_protocol import sha
from .protocol import read
from .runner import verify, output, save, complete
from .metrics import order


def csv_table(path, rows):
    if not rows:
        path.write_text("")
        return
    columns = sorted(set().union(*(row.keys() for row in rows)))
    with path.open("w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f,columns)
        writer.writeheader()
        writer.writerows(rows)


def report(protocol_path, runs, destination):
    start = time.perf_counter()
    p,ph=read(protocol_path)
    comparisons,explanations,relationships,cases,controls = [],[],[],[],[]
    sources = {}
    for run in runs:
        m=verify(run,ph)
        sources[str(run)] = sha((run/"manifest.json").read_bytes())
        for trial in json.loads((run/"results.json").read_bytes()):
            common={"tier":m["tier"],"scope":m["scope"],"split_seed":trial["split_seed"],"model_seed":trial["model_seed"]}
            for method,result in trial["methods"].items():
                ci=result["paired_vs_E4"]
                row={**common,"method":method,**{k:result[k] for k in [
                    "count","positives","prevalence","average_precision","ap_over_prevalence","roc_auc",
                    "tied_accounts","tie_groups","coverage","fallback_rate","intervention_availability_rate"]},
                    "delta_AP_vs_E4":ci["difference"] if ci else None,
                    "ci_low":ci["interval95"][0] if ci and ci["interval95"] else None,
                    "ci_high":ci["interval95"][1] if ci and ci["interval95"] else None,
                    "valid_bootstraps":ci["valid"] if ci else None,"rejected_bootstraps":ci["rejected"] if ci else None}
                for k,v in result["top_k"].items():
                    row.update({f"{key}@{k}":value for key,value in v.items()})
                comparisons.append(row)
            sub=run/trial["key"]
            if not (sub/"profiles.json").exists():
                continue
            profiles=json.loads((sub/"profiles.json").read_bytes())
            accounts=json.loads((sub/"accounts.json").read_bytes())
            scores=json.loads((sub/"scores.json").read_bytes())
            control=json.loads((sub/"control.json").read_bytes())
            controls.append({**common,**control["metadata"]})
            ids=sorted(accounts)
            base_rank={u:i+1 for i,u in enumerate(order(ids,scores["E6_BASE"]))}
            hybrid_rank={u:i+1 for i,u in enumerate(order(ids,scores["E6_HYBRID"]))}
            strata=defaultdict(list)
            for u,stats in accounts.items():
                for family,f in stats["families"].items():
                    explanations.append({**common,"account_alias":sha(u.encode())[:12],"family":family,
                        "valid":f["valid_count"],"rejected":f["rejected_count"],
                        "median_signed_change":f["median_signed_change"],"median_absolute_change":f["median_absolute_change"],
                        "robustness":f["robustness"],"robustness_status":f["robustness_status"]})
                    for budget,value in f["strata"].items():
                        c=value["concentration"]
                        strata[(family,budget)].append((c,hybrid_rank[u]-base_rank[u]))
            for (family,budget),values in strata.items():
                defined=[(c["value"],d) for c,d in values if c["value"] is not None]
                correlation=None
                if len(defined)>=3 and len({a for a,b in defined})>1 and len({b for a,b in defined})>1:
                    correlation=float(spearmanr([a for a,b in defined],[b for a,b in defined]).statistic)
                relationships.append({**common,"family":family,"budget_stratum":budget,
                    "accounts":len(values),"defined_concentration":len(defined),
                    "mean_concentration":float(np.mean([a for a,b in defined])) if defined else None,
                    "spearman_concentration_vs_hybrid_rank_displacement":correlation,
                    "interpretation":"descriptive conditional diagnostic, no ranking contribution or causal claim"})
            if profiles:
                r=min(profiles,key=lambda r:(-r["absolute_change"],r["focal_account"],r["intervention_id"]))
                cases.append({**common,"selection":"maximum absolute calibrated change; no label selection",
                    "account_alias":sha(r["focal_account"].encode())[:12],"family":r["family"],
                    "intervention_id":r["intervention_id"],"omitted_count":r["omitted_count"],
                    "omitted_fraction":r["omitted_fraction"],"omitted_amount_fraction":r["omitted_amount_fraction"],
                    "raw_before":r["raw_baseline_score"],"raw_after":r["raw_intervened_score"],
                    "q_before":r["calibrated_baseline_score"],"q_after":r["calibrated_intervened_score"],
                    "signed_change":r["signed_change"],"feature_difference":r["feature_difference"],
                    "interpretation":"only observed detector sensitivity; no financial-misconduct allegation"})
    csv_table(destination/"comparisons.csv",comparisons)
    csv_table(destination/"ablations.csv",[r for r in comparisons if r["method"].startswith("ABLATION")])
    csv_table(destination/"explanation_coverage.csv",explanations)
    csv_table(destination/"concentration_relationship.csv",relationships)
    csv_table(destination/"negative_control.csv",controls)
    save(destination/"case_studies.json",cases)
    save(destination/"comparisons.json",comparisons)
    return complete(destination,ph,"phase5-tables",{"source_manifests":sources,
        "primary_e6_hypothesis":"inconclusive; full-coverage E6 not completed"},start)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol",type=Path)
    parser.add_argument("run_id")
    parser.add_argument("runs",nargs="+",type=Path)
    args=parser.parse_args()
    print(json.dumps(report(args.protocol,args.runs,output(args.run_id))["source_manifests"],indent=2))
