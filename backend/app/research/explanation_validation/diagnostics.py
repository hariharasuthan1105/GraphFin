"""Deterministic, outcome-blind evidence selection and signed diagnostics."""
from dataclasses import replace
from decimal import Decimal
from itertools import combinations
import math
import statistics

from ...services.research_protocol import canonical, sha
from ..interventions.intervention_engine import budget_check
from ..feasibility_gate.pilot_design import CandidateIndex

VERSION = "phase6a-explanation-diagnostics-v1"


def fidelity(original, intervened):
    if not all(math.isfinite(x) for x in (original, intervened)):
        raise ValueError("Finite frozen scores required.")
    result = original - intervened
    if not math.isfinite(result):
        raise ValueError("Score difference overflow.")
    return result


def jaccard(left, right):
    a, b = set(left), set(right)
    return len(a & b) / len(a | b) if a | b else 1.0


def sparsity(history, cfg, focal, ids):
    incident = [e for e in history.events if focal in (e.sender, e.receiver)]
    reason, facts = budget_check(incident, ids, cfg.budget)
    if reason:
        raise ValueError("Invalid explanation: " + reason)
    chosen = [e for e in incident if e.transaction_id in set(ids)]
    amount = sum((Decimal(e.amount) for e in chosen), Decimal(0))
    total = sum((Decimal(e.amount) for e in incident), Decimal(0))
    width = cfg.window_size * (1 if history.time_kind == "simulation_hour" else (3600 if cfg.window_unit == "hours" else 1)*10**9)
    return {**facts, "omitted_amount": str(amount), "historical_amount": str(total),
            "historical_count": len(incident),
            "counterparties": len({e.receiver if e.sender == focal else e.sender for e in chosen}),
            "time_blocks": len({(history.cutoff-e.time)//width for e in chosen})}


def select(history, cfg, focal):
    """Whole groups only. A/B lexicographic; C/D maximize size, never score."""
    index = CandidateIndex(history, cfg)
    pool, rejected = [], []
    for family, key, ids in index.candidates(focal):
        if family not in ("counterparty", "temporal"):
            continue
        row = {"focal_account": focal, "family": family, "candidate_key": key,
               "omitted_transaction_ids": sorted(ids)}
        reason, _ = budget_check(index.incident[focal], ids, cfg.budget)
        if reason:
            rejected.append({**row, "reason": reason})
        else:
            pool.append({**row, "sparsity": sparsity(history, cfg, focal, ids)})
    tie = lambda r: (r["family"], str(r["candidate_key"]), r["omitted_transaction_ids"])
    pool.sort(key=tie)
    chosen = {}
    for method, family in (("A", "counterparty"), ("B", "temporal")):
        choices = [r for r in pool if r["family"] == family]
        chosen[method] = choices[0] if choices else None
    chosen["C"] = min(pool, key=lambda r: (-Decimal(r["sparsity"]["omitted_amount"]), tie(r))) if pool else None
    chosen["D"] = min(pool, key=lambda r: (-r["sparsity"]["omitted_count"], tie(r))) if pool else None
    return {"methods": chosen, "eligible": pool, "rejected": rejected}


def compatible(a, b):
    """Symmetric direct-method caliper. Identical evidence is comparable."""
    if a["historical_count"] != b["historical_count"] or a["historical_amount"] != b["historical_amount"]:
        return False
    aa, ba, total = (Decimal(x) for x in (a["omitted_amount"], b["omitted_amount"], a["historical_amount"]))
    return a["omitted_count"] == b["omitted_count"] and abs(aa-ba) <= min(Decimal(".01")*total, Decimal(".1")*min(aa, ba))


def summary(values, population):
    if population < len(values):
        raise ValueError("Invalid coverage denominator.")
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Nonfinite fidelity.")
    return {"available": len(values), "population": population,
            "coverage": len(values)/population if population else None,
            "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "median_absolute": statistics.median(map(abs, values)) if values else None,
            "positive_fraction": sum(v > 0 for v in values)/len(values) if values else None}


def paired(rows):
    result = []
    for a, b in combinations(rows, 2):
        if a["account_id"] != b["account_id"] or not a["available"] or not b["available"]:
            continue
        ok = compatible(a["sparsity"], b["sparsity"])
        result.append({"account_id": a["account_id"], "left": a["method"], "right": b["method"],
                       "comparable": ok, "reason": None if ok else "count_or_monetary_caliper",
                       "fidelity_difference": a["fidelity"]-b["fidelity"] if ok else None})
    return result


def shadow(history, events):
    """In-memory perturbation provenance, never rewrite a dataset."""
    events = tuple(events)
    identity = [[e.transaction_id,e.sender,e.receiver,e.amount,e.time] for e in events]
    return replace(history, events=events, history_sha256=sha(canonical(identity)))
