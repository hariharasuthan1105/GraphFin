"""Analyze frozen E6_BASE ties and source-only monotonic calibration, no refitting labels."""
import json, sys
from pathlib import Path
import numpy as np
from sklearn.metrics import average_precision_score
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from backend.app.research.crest.monotonic_calibration import SourceLogisticCalibration
from backend.app.services.research_protocol import canonical, sha

def main():
    run="phase5r-monotonic-calibration-v4"
    out=ROOT/"data/results/v2"/run; out.mkdir(exist_ok=False)
    protocol=json.loads((ROOT/"docs/research/configs/phase5_protocol_v1.json").read_bytes())
    rows=[]
    for tier in ("5k","50k"):
        stage=ROOT/f"data/results/v2/phase5-baselines-{tier}-v1"
        features=ROOT/f"data/results/v2/phase5-features-{tier}-v1"
        population=json.loads((features/"population.json").read_bytes())
        ids=population["ids"]; labels=population["labels"]
        for seed in protocol["primary"]["split_seeds"]:
            key=f"split-{seed}-model-42"; folder=stage/key
            scores=json.loads((folder/"scores.json").read_bytes())
            calibration=json.loads((folder/"calibration.json").read_bytes())
            raw=scores["E4"]; base=scores["E6_BASE"]
            eval_ids=sorted(raw)
            y=np.asarray([labels[u] for u in eval_ids],dtype=np.int8)
            r=np.asarray([raw[u] for u in eval_ids],dtype=np.float64)
            q=np.asarray([base[u] for u in eval_ids],dtype=np.float64)
            train_raw=np.asarray(calibration["reference"],dtype=np.float64)
            cal=SourceLogisticCalibration(train_raw)
            calibration_status="strict_rank_preserving"
            try:
                mapped=cal.transform(r)
            except FloatingPointError:
                # Preserve a diagnostic-only transform so its collision count
                # is visible; it is explicitly not accepted as a calibration.
                calibration_status="rejected_numerical_tie"
                z=(r-cal.location)/cal.scale
                mapped=np.exp(-np.logaddexp(0.0,-z))
            distinct_raw=len(np.unique(r)); distinct_q=len(np.unique(q)); distinct_mapped=len(np.unique(mapped))
            def order(s): return sorted(range(len(s)),key=lambda i:(-float(s[i]),eval_ids[i]))
            raw_order=order(r); q_order=order(q); mapped_order=order(mapped)
            raw_rank={u:i for i,u in enumerate([eval_ids[i] for i in raw_order])}
            q_rank={u:i for i,u in enumerate([eval_ids[i] for i in q_order])}
            k=min(10,len(y)); p_raw=float(y[raw_order[:k]].mean()); p_q=float(y[q_order[:k]].mean())
            rows.append({"tier":tier,"split_seed":seed,"population":len(y),"positives":int(y.sum()),
                "prevalence":float(y.mean()),"raw_unique_scores":distinct_raw,"e6_base_unique_scores":distinct_q,
                "e6_base_distinct_score_loss":distinct_raw-distinct_q,
                "e6_base_ap":float(average_precision_score(y,q)),"e4_ap":float(average_precision_score(y,r)),
                "e6_base_p_at_10":p_q,"e4_p_at_10":p_raw,
                "e6_base_mean_abs_rank_displacement":float(np.mean([abs(raw_rank[u]-q_rank[u]) for u in eval_ids])),
                "e6_base_max_abs_rank_displacement":int(max(abs(raw_rank[u]-q_rank[u]) for u in eval_ids)),
                "monotonic_calibration_unique_scores":distinct_mapped,"monotonic_new_ties":distinct_raw-distinct_mapped,
                "monotonic_ap":float(average_precision_score(y,mapped)),"monotonic_p_at_10":float(y[mapped_order[:k]].mean()),
                "monotonic_rank_identical_to_e4":mapped_order==raw_order,
                "monotonic_calibration_status":calibration_status,
                "calibration":cal.metadata(),"train_score_count":len(train_raw),
                "evaluation_membership_sha256":sha(canonical(eval_ids))})
    (out/"results.json").write_bytes(canonical(rows))
    manifests=[]
    for tier in ("5k","50k"):
        d=json.loads((ROOT/f"data/results/v2/phase5-features-{tier}-v1/manifest.json").read_bytes())
        manifests.append({"tier":tier,"dataset_id":protocol["datasets"][tier]["dataset_id"],
            "transactions_sha256":protocol["datasets"][tier]["transactions_sha256"],
            "labels_sha256":protocol["datasets"][tier]["labels_sha256"],
            "feature_manifest_sha256":sha((ROOT/f"data/results/v2/phase5-features-{tier}-v1/manifest.json").read_bytes())})
    manifest={"stage":"phase5r-monotonic-calibration-exploratory-v1","protocol_sha256":sha((ROOT/"docs/research/configs/phase5_protocol_v1.json").read_bytes()),
        "baseline_result_sources":["phase5-baselines-5k-v1","phase5-baselines-50k-v1"],"datasets":manifests,
        "algorithm_version":"source-logistic-rank-preserving-v3","fit_policy":"training score reference in each frozen split calibration artifact; no evaluation labels used for parameters",
        "output":"results.json","output_sha256":sha((out/"results.json").read_bytes()),"splits":len(rows),
        "strict_rank_preservation_valid_splits":sum(r["monotonic_calibration_status"]=="strict_rank_preserving" for r in rows),
        "strict_rank_preservation_rejected_splits":sum(r["monotonic_calibration_status"]!="strict_rank_preserving" for r in rows)}
    (out/"manifest.json").write_bytes(canonical(manifest))
    print(json.dumps({"directory":str(out),"manifest":manifest,"results":rows},indent=2),flush=True)
if __name__=="__main__": main()
