"""Phase 5 ablations compose unchanged Phase 4 statistics; no label argument."""
from collections import defaultdict
import numpy as np
from ...services.research_protocol import canonical, sha
from ..crest.statistics import influence, stratum, summarize, candidate_score
from ..crest.schemas import MODES

FAMILIES = ("counterparty", "temporal", "budgeted")


def permuted_control(profiles, seed):
    """Permute intervened percentiles within family/count/fraction/amount strata.

    A score-placebo control, not a newly claimed physical omission or explanation.
    Its candidate count, budgets and evidence availability match the observed set.
    """
    groups = defaultdict(list)
    for r in profiles:
        groups[(r["family"],r["budget_stratum"])].append(r)
    result, changed = [], 0
    for key in sorted(groups):
        rows = sorted(groups[key],key=lambda r:(r["focal_account"],r["intervention_id"]))
        donors = sorted(rows,key=lambda r:sha(canonical([seed,r["intervention_id"]])))
        for r,d in zip(rows,donors):
            q = d["calibrated_intervened_score"]
            changed += r["intervention_id"] != d["intervention_id"]
            result.append({**r,"calibrated_intervened_score":q,
                **influence(r["calibrated_baseline_score"],q),
                "control_donor":d["intervention_id"],"control":"stratum-score-permutation-v1"})
    return result, {"records":len(result),"donor_changed":changed,
                    "definition":"score placebo; not a factual intervention explanation"}


def aggregate(ids, q0, profiles, rejected, config):
    by_account = defaultdict(list)
    rejects = defaultdict(list)
    for r in profiles:
        by_account[r["focal_account"]].append(r)
    for r in rejected:
        rejects[r["focal_account"]].append(r)
    scores = {mode:{} for mode in MODES}
    scores.update({f"ABLATION_{f.upper()}":{} for f in FAMILIES})
    scores["ABLATION_CANDIDATE_WEIGHTED"] = {}
    coverage = {name:{"fallback_count":0,"available_accounts":0} for name in scores}
    accounts = {}
    for u in ids:
        rows = by_account[u]
        stats = summarize(rows,rejects[u],config,FAMILIES)
        accounts[u] = stats
        choices = [(m,stats,m) for m in MODES]
        for f in FAMILIES:
            single = summarize([r for r in rows if r["family"]==f],
                               [r for r in rejects[u] if r.get("family")==f],config,(f,))
            choices.append((f"ABLATION_{f.upper()}",single,"E6_HYBRID"))
        # Prespecified candidate-count-weighted mean of the SAME eligible family medians.
        weighted = dict(stats)
        for target,key in [("sensitivity","median_signed_change"),("robustness","robustness")]:
            eligible = [s for s in stats["families"].values() if s[key] is not None]
            weighted[target] = float(np.average([s[key] for s in eligible],
                weights=[s["valid_count"] for s in eligible])) if eligible else None
        choices.append(("ABLATION_CANDIDATE_WEIGHTED",weighted,"E6_HYBRID"))
        for name,s,mode in choices:
            score,warnings = candidate_score(q0[u],s,mode,config.alpha,config.beta)
            scores[name][u] = score
            coverage[name]["fallback_count"] += bool(warnings)
            coverage[name]["available_accounts"] += s["available_interventions"]>0
    for item in coverage.values():
        item["fallback_rate"] = item["fallback_count"]/len(ids)
        item["intervention_availability_rate"] = item["available_accounts"]/len(ids)
    return scores,coverage,accounts


def make_profiles(records, raw0, q0, raw, q, config):
    accepted = [r for r in records if r["status"]=="accepted"]
    if len(raw)!=len(accepted) or len(q)!=len(accepted):
        raise ValueError("Intervention score coverage mismatch.")
    result = []
    for r,s,p in zip(accepted,raw,q):
        u = r["focal_account"]
        result.append({**{k:v for k,v in r.items() if k!="runtime_seconds"},
            "raw_baseline_score":raw0[u],"raw_intervened_score":float(s),
            "calibrated_baseline_score":q0[u],"calibrated_intervened_score":float(p),
            **influence(q0[u],p),"budget_stratum":stratum(r,config)})
    return result
