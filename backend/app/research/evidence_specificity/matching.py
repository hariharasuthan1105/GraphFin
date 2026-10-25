"""Label-free exact-count and Decimal monetary-caliper matching."""
from decimal import Decimal
from itertools import combinations
from math import comb
from ...services.research_protocol import canonical, sha
from ..interventions.intervention_engine import budget_check

VERSION = "same-account-decimal-caliper-two-controls-v1"


class StrictMatcher:
    def __init__(self, history, budget, policy):
        self.history, self.budget, self.policy = history, budget, dict(policy)
        self.absolute = Decimal(policy["absolute_amount_fraction_tolerance"])
        self.relative = Decimal(policy["relative_amount_tolerance"])
        if not (self.absolute.is_finite() and self.relative.is_finite()
                and 0 <= self.absolute <= 1 and 0 <= self.relative <= 1):
            raise ValueError("Finite monetary tolerances in [0,1] required.")
        if policy["controls_per_intervention"] != 2 or policy["same_omission_allowed"]:
            raise ValueError("This version requires two distinct nonidentical controls.")
        if policy["enumeration_limit"] < 1:
            raise ValueError("Positive search bound required.")
        self.incident = {u: [] for u in history.universe}
        for e in history.events:
            self.incident[e.sender].append(e); self.incident[e.receiver].append(e)
        self.context = sha(canonical([VERSION, history.history_sha256, history.dataset_sha256,
            history.cutoff, history.time_kind, history.universe, budget.model_dump(), self.policy]))

    def assess(self, focal, structured, control):
        if focal not in self.incident:
            raise ValueError("Unknown account.")
        incident = self.incident[focal]
        sr, sf = budget_check(incident, structured, self.budget)
        cr, cf = budget_check(incident, control, self.budget)
        base = {"structured_valid": sr is None, "control_valid": cr is None,
                "structured_facts": sf, "control_facts": cf, "context_sha256": self.context}
        if sr or cr:
            return {**base, "comparable": False, "reason": "invalid_structured:"+sr if sr else "invalid_control:"+cr}
        if set(structured) == set(control):
            return {**base, "comparable": False, "reason": "identical_omission"}
        if len(structured) != len(control):
            return {**base, "comparable": False, "reason": "count_mismatch"}
        amounts = {e.transaction_id: Decimal(e.amount) for e in incident}
        total = sum(amounts.values(), Decimal(0))
        sa = sum((amounts[x] for x in structured), Decimal(0))
        ca = sum((amounts[x] for x in control), Decimal(0))
        difference = abs(sa-ca)
        # Multiplicative Decimal comparisons avoid rounded ratio boundaries.
        allowed = min(self.absolute*total, self.relative*sa)
        return {**base, "comparable": difference <= allowed,
                "reason": None if difference <= allowed else "monetary_caliper",
                "historical_amount": str(total), "structured_amount": str(sa), "control_amount": str(ca),
                "amount_absolute_difference": str(difference), "amount_allowed_difference": str(allowed),
                "amount_fraction_difference": float(difference/total),
                "omitted_count_equal": True, "omitted_fraction_equal": True}

    def match(self, structured):
        u = structured["focal_account"]; ids = tuple(sorted(structured["omitted_transaction_ids"]))
        if u not in self.incident:
            raise ValueError("Unknown account.")
        incident = self.incident[u]
        reason, facts = budget_check(incident, ids, self.budget)
        identity = sha(canonical([self.context, u, structured["family"], structured["candidate_key"], ids]))
        base = {"match_id": identity, "focal_account": u, "family": structured["family"],
                "structured_ids": list(ids), "facts": facts, "context_sha256": self.context,
                "cutoff": self.history.cutoff, "history_sha256": self.history.history_sha256,
                "population_sha256": sha(canonical(self.history.universe))}
        if reason:
            return {**base, "status": "unmatched", "reason": "invalid_structured:"+reason, "controls": []}
        size = comb(len(incident), len(ids))
        if size > self.policy["enumeration_limit"]:
            return {**base, "status": "unmatched", "reason": "search_space_exceeds_bound",
                    "search_space": size, "feasible_count": None, "controls": []}
        pool = []
        for candidate in combinations(sorted(e.transaction_id for e in incident), len(ids)):
            assessment = self.assess(u, ids, candidate)
            if assessment["comparable"]:
                control_id = sha(canonical([VERSION, self.policy["control_seed"], identity, candidate]))
                pool.append({"control_id": control_id, "omitted_transaction_ids": list(candidate),
                             "assessment": assessment})
        pool.sort(key=lambda r: r["control_id"])
        enough = len(pool) >= 2
        return {**base, "status": "matched" if enough else "unmatched",
                "reason": None if enough else "fewer_than_two_distinct_feasible_controls",
                "search_space": size, "feasible_count": len(pool),
                "feasible_pool_sha256": sha(canonical(pool)), "controls": pool[:2] if enough else []}
