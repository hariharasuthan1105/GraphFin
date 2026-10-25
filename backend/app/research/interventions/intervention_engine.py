"""Index candidates once; recompute one isolated view at a time, never global caches."""
from collections import defaultdict
from decimal import Decimal
from time import perf_counter
from ...services.research_protocol import canonical, sha
from .schemas import VERSION
from .feature_recomputation import recompute
from .historical_evidence import event_time


def budget_check(incident, candidate, budget):
    lookup = {e.transaction_id: e for e in incident}
    if not candidate or len(set(candidate)) != len(candidate) or not set(candidate) <= lookup.keys():
        return "empty_or_invalid_candidate", {}
    count = len(candidate)
    total_amount = sum((Decimal(e.amount) for e in incident), Decimal(0))
    omitted_amount = sum((Decimal(lookup[x].amount) for x in candidate), Decimal(0))
    facts = {"omitted_count": count, "omitted_fraction": count / len(incident),
             "omitted_amount_fraction": float(omitted_amount / total_amount)}
    if count > budget.max_count:
        return "max_count", facts
    if Decimal(count) > Decimal(str(budget.max_fraction)) * len(incident):
        return "max_fraction", facts
    if len(incident) - count < budget.min_retained:
        return "min_retained", facts
    if budget.max_amount_fraction is not None and omitted_amount > Decimal(str(budget.max_amount_fraction)) * total_amount:
        return "max_amount_fraction", facts
    return None, facts


class InterventionEngine:
    def __init__(self, history, config):
        if history.cutoff != event_time(config.cutoff, config.time_kind) or history.time_kind != config.time_kind:
            raise ValueError("History/config cutoff or time-kind mismatch.")
        self.history, self.config = history, config
        self.incident = defaultdict(list)
        for e in history.events:
            self.incident[e.sender].append(e)
            self.incident[e.receiver].append(e)
        self.baseline, self.mode = recompute(history, max_nodes=config.max_reference_nodes)

    def candidates(self, focal):
        events, cfg = self.incident[focal], self.config
        for family in cfg.families:
            groups = defaultdict(list)
            if family == "counterparty":
                for e in events:
                    groups[e.receiver if e.sender == focal else e.sender].append(e.transaction_id)
            elif family == "temporal":
                width = cfg.window_size * (1 if cfg.time_kind == "simulation_hour" else (3600 if cfg.window_unit == "hours" else 1) * 10**9)
                # Right-closed blocks (T-(b+1)w, T-bw]; ties always share a block.
                for e in events:
                    groups[str((self.history.cutoff - e.time) // width)].append(e.transaction_id)
            else:
                # Seeded hash order, greedily accept individual events within all budgets.
                ordered = sorted(events, key=lambda e: sha(canonical([VERSION, cfg.intervention_seed, focal, e.transaction_id])))
                selected = []
                for e in ordered:
                    proposed = selected + [e.transaction_id]
                    if budget_check(events, proposed, cfg.budget)[0] is None:
                        selected = proposed
                groups["seeded_greedy"] = selected
            for key in sorted(groups):
                yield family, key, tuple(sorted(groups[key]))

    def generate(self, focal):
        if focal not in self.history.universe:
            raise ValueError("Focal account must belong to historical or explicitly declared universe.")
        if not self.incident[focal]:
            yield {"focal_account": focal, "status": "rejected", "reason": "no_historical_evidence"}
            return
        accepted = 0
        for family, key, omitted in self.candidates(focal):
            start = perf_counter()
            reason, facts = budget_check(self.incident[focal], omitted, self.config.budget)
            if reason is None and accepted >= self.config.budget.max_interventions:
                reason = "max_interventions"
            base = {"focal_account": focal, "family": family, "candidate_key": key,
                    "omitted_transaction_ids": list(omitted), **facts}
            if reason:
                yield {**base, "status": "rejected", "reason": reason}
                continue
            vectors, mode = recompute(self.history, omitted, self.config.max_reference_nodes)
            accepted += 1
            identity = [VERSION, self.config.dataset_id, self.history.history_sha256,
                        self.history.cutoff, self.history.universe, focal, family, key, omitted,
                        self.config.model_dump()]
            yield {**base, "status": "accepted", "intervention_id": sha(canonical(identity)),
                   "baseline_features": self.baseline[focal], "intervened_features": vectors[focal],
                   "feature_difference": [b-a for a, b in zip(self.baseline[focal], vectors[focal])],
                   "recomputation": mode, "runtime_seconds": perf_counter()-start}
