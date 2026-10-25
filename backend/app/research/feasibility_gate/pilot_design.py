"""Label-free pilot cohort selection and count-matched random omissions."""
from collections import defaultdict
import numpy as np
from ...services.research_protocol import canonical, sha
from ..interventions.intervention_engine import InterventionEngine, budget_check
from ..interventions.historical_evidence import event_time


class CandidateIndex:
    """Reuse frozen candidate enumeration without recomputing baseline features."""
    candidates = InterventionEngine.candidates

    def __init__(self, history, config):
        if history.cutoff!=event_time(config.cutoff,config.time_kind) or history.time_kind!=config.time_kind:
            raise ValueError("History/config mismatch.")
        self.history,self.config = history,config
        self.incident = defaultdict(list)
        for e in history.events:
            self.incident[e.sender].append(e); self.incident[e.receiver].append(e)

    def bounded(self, focal):
        counts = defaultdict(int)
        rows = []
        for family,key,omitted in self.candidates(focal):
            reason,facts = budget_check(self.incident[focal],omitted,self.config.budget)
            if reason is None and counts[family]>=self.config.budget.max_interventions:
                reason = "max_interventions"
            if reason is None: counts[family]+=1
            rows.append({"focal_account":focal,"family":family,"candidate_key":key,
                "omitted_transaction_ids":list(omitted),"status":"accepted" if reason is None else "rejected",
                "reason":reason,**facts})
        return rows


def select_cohort(scores, index, per_stratum=2, seed=1901):
    ordered = sorted(scores,key=lambda u:(float(scores[u]),u))
    strata = np.array_split(np.asarray(ordered,dtype=object),3)
    selected = []
    for name,ids in zip(("low","middle","high"),strata):
        candidates = sorted(ids,key=lambda u:sha(canonical(["phase5g-selection-v1",seed,name,str(u)])))
        eligible = []
        for u in candidates:
            u=str(u)
            if len(index.incident[u])<2: continue
            records=index.bounded(u)
            if any(r["status"]=="accepted" for r in records):
                eligible.append({"account_id":u,"score_stratum":name,"raw_baseline_score":float(scores[u]),
                                 "incident_count":len(index.incident[u])})
            if len(eligible)==per_stratum: break
        if len(eligible)!=per_stratum:
            raise ValueError("Insufficient eligible accounts in fixed score stratum.")
        selected.extend(eligible)
    return selected


def matched_random(incident, structured, budget, seed=1902, attempts=128):
    identity=["phase5g-random-control-v1",seed,structured["focal_account"],structured["family"],
              structured["candidate_key"],structured["omitted_transaction_ids"]]
    pair_id=sha(canonical(identity))
    rng=np.random.RandomState(int(pair_id[:8],16))
    count=len(structured["omitted_transaction_ids"])
    ids=[e.transaction_id for e in incident]
    for attempt in range(attempts):
        omitted=sorted(rng.choice(ids,size=count,replace=False).tolist())
        reason,facts=budget_check(incident,omitted,budget)
        if reason is None:
            return {"pair_id":pair_id,"focal_account":structured["focal_account"],
                "matched_structured_family":structured["family"],"candidate_key":structured["candidate_key"],
                "omitted_transaction_ids":omitted,"attempts":attempt+1,"status":"accepted",**facts,
                "same_omission_as_structured":omitted==sorted(structured["omitted_transaction_ids"])}
    return {"pair_id":pair_id,"status":"unmatched","reason":"bounded_random_rejection_limit", "attempts":attempts}
