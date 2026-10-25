"""Signed profiles, equal-family aggregates, stratified concentration, candidate fusion."""
from collections import Counter
import numpy as np

FAMILIES = ("counterparty","temporal","budgeted")


def bin_index(value, edges):
    # [0,e1], (e1,e2], ...; avoids ambiguous boundary assignments.
    return min(len(edges)-2, max(0, int(np.searchsorted(edges,value,side="left"))-1))


def stratum(record, config):
    return (f"n={record['omitted_count']};f={bin_index(record['omitted_fraction'],config.fraction_edges)};"
            f"a={bin_index(record['omitted_amount_fraction'],config.amount_edges)}")


def influence(q0, qm):
    delta = float(q0-qm)
    return {"signed_change":delta,"absolute_change":abs(delta),
            "positive_influence":max(delta,0.0),"negative_influence":max(-delta,0.0)}


def concentration(records, minimum):
    if len(records) < minimum:
        return {"value":None,"status":"insufficient_interventions","count":len(records)}
    positive = np.array([r["positive_influence"] for r in records],dtype=float)
    total = float(positive.sum())
    if total == 0:
        return {"value":None,"status":"zero_positive_influence","count":len(records)}
    return {"value":float(np.sum((positive/total)**2)),"status":"defined","count":len(records),
            "positive_count":int((positive>0).sum()),"total_positive_influence":total}


def summarize(records, rejected, config, expected_families=FAMILIES):
    summaries = {}
    for family in expected_families:
        all_rows = [r for r in records if r["family"]==family]
        rows = [r for r in all_rows if config.ranking_stratum is None or r["budget_stratum"]==config.ranking_stratum]
        rejects = [r for r in rejected if r.get("family")==family]
        account_reasons = dict(Counter(r.get("reason","unspecified") for r in rejected if "family" not in r))
        strata = {}
        for key in sorted({r["budget_stratum"] for r in all_rows}):
            group = [r for r in all_rows if r["budget_stratum"]==key]
            strata[key] = {"count":len(group),"median_signed_change":float(np.median([r["signed_change"] for r in group])),
                           "median_absolute_change":float(np.median([r["absolute_change"] for r in group])),
                           "omitted_fraction_range":[min(r["omitted_fraction"] for r in group),max(r["omitted_fraction"] for r in group)],
                           "omitted_amount_fraction_range":[min(r["omitted_amount_fraction"] for r in group),max(r["omitted_amount_fraction"] for r in group)],
                           "concentration":concentration(group,config.min_concentration_per_stratum)}
        available = bool(rows)
        robustness = 1-float(np.median([r["absolute_change"] for r in rows])) if len(rows)>=config.min_robustness_per_family else None
        summaries[family] = {"valid_count":len(rows),"all_valid_count":len(all_rows),"rejected_count":len(rejects),
            "excluded_by_stratum":len(all_rows)-len(rows),"candidate_count":len(all_rows)+len(rejects),
            "rejection_reasons":dict(Counter(r.get("reason","unspecified") for r in rejects)),
            "account_level_unavailability_reasons":account_reasons,
            "sensitivity_status":"defined" if available else "no_valid_interventions_in_selected_stratum",
            "median_signed_change":float(np.median([r["signed_change"] for r in rows])) if available else None,
            "median_absolute_change":float(np.median([r["absolute_change"] for r in rows])) if available else None,
            "max_positive_change":max((r["positive_influence"] for r in rows),default=None),
            "max_negative_change":max((r["negative_influence"] for r in rows),default=None),
            "robustness":robustness,"robustness_status":"defined" if robustness is not None else "insufficient_interventions",
            "strata":strata}
    ds = [r["median_signed_change"] for r in summaries.values() if r["median_signed_change"] is not None]
    rs = [r["robustness"] for r in summaries.values() if r["robustness"] is not None]
    return {"families":summaries,"sensitivity":float(np.mean(ds)) if ds else None,
            "robustness":float(np.mean(rs)) if rs else None,
            "sensitivity_family_count":len(ds),"robustness_family_count":len(rs),
            # No cross-stratum HHI scalar: incomparable candidate counts/budgets.
            "concentration":{"status":"family_and_budget_strata_only","by_family":{
                f:{s:v["concentration"] for s,v in x["strata"].items()} for f,x in summaries.items()}},
            "available_interventions":len(records),"rejected_interventions":len(rejected),
            "evidence_status":"unavailable" if not records else "partial" if len(rs)<len(expected_families) else "available"}


def candidate_score(q0, stats, mode, alpha, beta):
    use_d = mode in ("E6_SENSITIVITY","E6_HYBRID") and alpha != 0
    use_r = mode in ("E6_ROBUSTNESS","E6_HYBRID") and beta != 0
    missing = []
    if use_d and stats["sensitivity"] is None:
        missing.append("sensitivity_unavailable")
    if use_r and stats["robustness"] is None:
        missing.append("robustness_unavailable")
    if missing:
        return float(q0), missing
    score = q0 + (alpha*stats["sensitivity"] if use_d else 0) - (beta*q0*(1-stats["robustness"]) if use_r else 0)
    return float(np.clip(score,0,1)), []


def rank_accounts(accounts, mode, config):
    result = []
    for account in accounts:
        score, warnings = candidate_score(account["calibrated_score"],account["statistics"],mode,config.alpha,config.beta)
        result.append({**account,"mode":mode,"final_score":score,
                       "score_difference":score-account["calibrated_score"],"baseline_fallback_reasons":warnings})
    # Unicode code-point lexical ID order; stable, no dict iteration tie dependency.
    result.sort(key=lambda a:(-a["final_score"],a["account_id"]))
    return [{**r,"rank":i+1} for i,r in enumerate(result)]
