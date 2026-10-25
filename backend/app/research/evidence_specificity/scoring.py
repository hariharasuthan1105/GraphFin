"""Raw E4 matched-control excess; no fitting, calibration, labels or clipping."""
import math
import numpy as np

VERSION = "raw-e4-family-median-excess-v2"
FAMILIES = ("counterparty", "temporal", "budgeted")


def finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise FloatingPointError("Nonfinite specificity arithmetic.")
    return value


def median(values):
    ordered = sorted(finite(v) for v in values)
    if not ordered:
        raise ValueError("Median requires observations.")
    n = len(ordered)
    if n % 2: return ordered[n//2]
    a, b = ordered[n//2-1:n//2+1]
    return a if a == b else finite(a/2+b/2)


def summarize(s0, comparisons, weight=1.0):
    s0, weight = finite(s0), finite(weight)
    if weight < 0: raise ValueError("Nonnegative weight required.")
    families = {}; excess = []
    for row in comparisons:
        if row["family"] not in FAMILIES: raise ValueError("Unknown family.")
    for family in FAMILIES:
        all_rows = sorted([r for r in comparisons if r["family"] == family], key=lambda r: str(r.get("match_id", "")))
        matched = [r for r in all_rows if r["status"] == "matched"]
        ds, dc = [], []
        for r in matched:
            if len(r["control_deltas"]) != 2:
                raise ValueError("Exactly two controls required for each matched omission.")
            ds.append(finite(r["structured_delta"]))
            dc.extend(finite(v) for v in r["control_deltas"])
        ms, mc = (median(ds), median(dc)) if ds else (None, None)
        effect = finite(ms-mc) if ds else None
        if effect is not None: excess.append(effect)
        families[family] = {"structured_count": len(all_rows), "matched_structured_count": len(matched),
            "control_count": len(dc), "structured_deltas": ds, "control_deltas": dc,
            "structured_median": ms, "control_median": mc, "excess": effect,
            "status": "available" if ds else "no_fully_matched_interventions"}
    E = finite(math.fsum(v/len(excess) for v in excess)) if excess else None
    fallback = None if excess else ("no_valid_structured_interventions" if not comparisons else "no_fully_matched_interventions")
    addition = 0.0 if E is None or weight == 0 else finite(weight*E)
    score = s0 if addition == 0 else finite(s0+addition)
    if addition != 0 and score == s0:
        raise FloatingPointError("Nonzero specificity addition absorbed by float64 rounding.")
    return {"version": VERSION, "raw_e4": s0, "families": families, "available_families": len(excess),
            "excess": E, "weight": weight, "contribution": addition, "score": score,
            "fallback_reason": fallback, "intervention_required": weight != 0,
            "score_changed": score != s0}


def ranks(scores):
    for v in scores.values(): finite(v)
    return {u: i+1 for i,u in enumerate(sorted(scores, key=lambda u: (-scores[u],u)))}


class FrozenBatchScorer:
    """Inference-only interface. The caller must authenticate model provenance."""
    def __init__(self, model):
        if getattr(model, "n_features_in_", None) != 19:
            raise ValueError("Frozen canonical 19-feature model required.")
        self.model = model

    def score(self, vectors):
        x = np.asarray(vectors, dtype=np.float32)
        if x.ndim != 2 or x.shape[1] != 19 or not np.isfinite(x).all():
            raise ValueError("Finite canonical19 matrix required.")
        if not len(x): return np.asarray([], dtype=float)
        values = -self.model.decision_function(x)
        if not np.isfinite(values).all(): raise FloatingPointError("Nonfinite frozen model score.")
        return values

    def verify_batch(self, vectors):
        batch = self.score(vectors)
        single = np.asarray([self.score([v])[0] for v in vectors])
        if not np.array_equal(batch, single):
            raise FloatingPointError("Batch scoring differs from singleton scoring.")
        return batch
