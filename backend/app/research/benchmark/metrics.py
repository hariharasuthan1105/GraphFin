"""Aligned account metrics and paired, class-count-conditioned uncertainty."""
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score


def aligned(ids, labels, scores):
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Nonempty unique account IDs required.")
    if set(ids) != set(labels) or set(ids) != set(scores):
        raise ValueError("Exact evaluation population and label coverage required.")
    y = np.asarray([labels[u] for u in ids], dtype=int)
    if any(labels[u] not in (0, 1) for u in ids):
        raise ValueError("Binary labels required.")
    s = np.asarray([scores[u] for u in ids], dtype=float)
    if not np.isfinite(s).all():
        raise ValueError("Finite scores required.")
    return y, s


def order(ids, scores):
    return sorted(ids, key=lambda u: (-scores[u], u))


def metrics(ids, labels, scores):
    y, s = aligned(ids, labels, scores)
    positives = int(y.sum())
    ap = float(average_precision_score(y, s)) if positives else None
    counts = np.unique(s, return_counts=True)[1]
    ranked = order(ids, scores)
    result = {"count":len(ids), "positives":positives, "prevalence":positives/len(ids),
        "average_precision":ap, "ap_over_prevalence":ap/(positives/len(ids)) if positives else None,
        "roc_auc":float(roc_auc_score(y,s)) if 0 < positives < len(ids) else None,
        "unique_scores":len(counts), "tied_accounts":int(counts[counts>1].sum()),
        "tie_groups":int((counts>1).sum()), "deterministic_rank_ties":0,
        "coverage":1.0, "top_k":{}}
    for k in [10,25,50,100]:
        used = min(k,len(ids))
        hits = sum(labels[u] for u in ranked[:used])
        result["top_k"][str(k)] = {"requested_k":k,"effective_k":used,"retrieved_positives":hits,
            "precision":hits/used,"recall":hits/positives if positives else None}
    return result


def paired_bootstrap(ids, labels, candidate, reference, seed=2718, draws=1000):
    y,a = aligned(ids,labels,candidate)
    _,b = aligned(ids,labels,reference)
    if draws < 1:
        raise ValueError("Positive resample count required.")
    positive, negative = np.flatnonzero(y), np.flatnonzero(y==0)
    common = {"procedure":"stratified paired accounts; conditions on class counts",
        "seed":seed,"requested":draws,"positives":len(positive),"negatives":len(negative)}
    if not len(positive):
        return {**common,"difference":None,"interval95":None,"valid":0,"rejected":draws,
                "reason":"no_positive_accounts"}
    rng = np.random.RandomState(seed)
    differences = []
    for _ in range(draws):
        idx = np.concatenate([rng.choice(positive,len(positive),replace=True),
                              rng.choice(negative,len(negative),replace=True)])
        differences.append(average_precision_score(y[idx],a[idx])-average_precision_score(y[idx],b[idx]))
    return {**common,"difference":float(average_precision_score(y,a)-average_precision_score(y,b)),
        "interval95":np.quantile(differences,[.025,.975]).tolist(),"valid":draws,"rejected":0}


def stability(ids, first, second):
    if set(ids) != set(first) or set(ids) != set(second):
        raise ValueError("Stability requires identical populations.")
    a,b = order(ids,first),order(ids,second)
    ra,rb = {u:i for i,u in enumerate(a)}, {u:i for i,u in enumerate(b)}
    # Correlation of deterministic ordinal ranks, including the declared tie rule.
    rho = float(spearmanr([ra[u] for u in ids],[rb[u] for u in ids]).statistic) if len(ids)>1 else None
    result = {"spearman_ordinal_ranks":rho,
        "mean_absolute_rank_displacement":float(np.mean([abs(ra[u]-rb[u]) for u in ids])),
        "max_absolute_rank_displacement":max(abs(ra[u]-rb[u]) for u in ids),"top_k":{}}
    for k in [10,25,50,100]:
        ka,kb = set(a[:k]),set(b[:k])
        result["top_k"][str(k)] = {"effective_k":len(ka),"overlap":len(ka&kb)/len(ka),
            "jaccard":len(ka&kb)/len(ka|kb)}
    return result
