"""Freeze once, verify on every execution, never select parameters from outcomes."""
import json
from pathlib import Path
from ...services.research_protocol import ROOT, PROTOCOL, canonical, sha

TITLE = "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions"
SEEDS = [42,123,7,2024,99,555]


def freeze(destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Protocol is immutable; use a distinct version.")
    datasets = {}
    for tier,stem in [("5k","ibm_aml_medium_5k"),("50k","ibm_aml_large_50k")]:
        tx = f"data/research/{stem}.csv"
        labels = f"data/research/{stem}_labels.csv"
        datasets[tier] = {"transactions":tx,"transactions_sha256":sha((ROOT/tx).read_bytes()),
            "labels":labels,"labels_sha256":sha((ROOT/labels).read_bytes()),
            "dataset_id":f"ibm-{tier}-supplied-v1","label_set_id":f"ibm-{tier}-retained-involvement-v1",
            "label_definition":"OR of retained-transaction laundering involvement; upstream raw evidence unavailable",
            "provenance_status":"declared_not_independently_verified"}
    p = {"protocol":PROTOCOL,"stage":"phase5-preregistered-benchmark","version":"phase5-v1",
        "project_title":TITLE,"datasets":datasets,"paysim":"excluded; provenance unresolved",
        "feature_schema":"canonical19-plus-egonet4-v1","preprocessing":"positive nonself; unchanged raw float32",
        "algorithms":{"E0":"e0-source-signed-zero-v2","E1-E5":"isolation-forest-raw-v2",
            "E6":"e6-crest-frozen-e4-v1","interventions":"transaction-evidence-omission-v1"},
        "primary":{"tiers":["5k","50k"],"split_seeds":SEEDS,"model_seed":42,"test_fraction":.3,
            "split_policy":"stratified entity holdout, sorted IDs; transductive full-observation graph",
            "E6_full_coverage":"planned, subject to feasibility gate; never substitute cohort result"},
        "exploratory":{"tier":"5k","split_seed":42,"model_seeds":SEEDS,
            "cohort_size":250,"cohort_seed":31415,
            "cohort_policy":"stratified random subset of the fixed held-out set, proportional class allocation; no score access",
            "label_use":"split/cohort stratification and metrics only; never fit or select weights",
            "scope":"feasibility-limited cohort; not full-dataset performance",
            "max_generation_seconds":1800},
        "detector":{"n_estimators":100,"max_samples":"auto","contamination":.005,"n_jobs":1},
        "weights":{"alpha":.25,"beta":.25,"justification":"prespecified quarter-scale bounded terms, not tuned",
            "primary_candidate":"E6_HYBRID","secondary":["E6_SENSITIVITY","E6_ROBUSTNESS","E6_BASE"],
            "zero_weight_identity":{"alpha":0,"beta":0}},
        "intervention":{"seed":17,"families":["counterparty","temporal","budgeted"],
            "family_execution":"separate unchanged Phase 3 engine configurations; cap two accepted per family",
            "budget":{"max_count":2,"max_fraction":.5,"max_amount_fraction":.5,"min_retained":1,"max_interventions":2},
            "window_hours":24,"cutoff":"maximum retained source timestamp; full-observation involvement labels, not future-outcome labels",
            "max_reference_nodes":10000,"minimum_robustness":2,"minimum_concentration":2,
            "fraction_edges":[0,.25,.5,.75,1],"amount_edges":[0,.25,.5,.75,1]},
        "ablation":{"A":"E4 versus E6_BASE","B":"BASE versus SENSITIVITY","C":"BASE versus ROBUSTNESS",
            "D":"BASE versus HYBRID","E-G":"each family alone using same frozen scores and budgets",
            "H":"all available families","I":"valid-count-weighted mean of eligible family medians versus equal-family mean",
            "J":"per-family/stratum concentration distribution and association with rank displacement; diagnostic only"},
        "negative_control":{"version":"stratum-score-permutation-v1","seed":8675309,
            "definition":"permute intervened calibrated scores within family/exact count/fraction bin/amount bin; recompute deltas from recipient q0",
            "scope":"arbitrary score placebo, not factual random omissions; same candidates/budgets/population",
            "compare":"negative-control hybrid versus structured hybrid; report donor-change rate"},
        "metrics":{"primary":"sklearn.average_precision_score","secondary":["ROC-AUC","AP/prevalence","P@K","R@K"],
            "K":[10,25,50,100],"tie_break":"descending score then Unicode lexical account ID",
            "no_positives":"AP, lift, recall and paired CI null; no zero sentinel",
            "one_class":"ROC-AUC null","k_exceeds_population":"use min(K,N), report effective K"},
        "uncertainty":{"bootstrap_seed":2718,"draws":1000,"interval":[.025,.975],
            "method":"paired stratified account bootstrap, fixed observed class counts; no refits",
            "limitation":"graph dependence ignored; one-positive intervals omit uncertainty over positive identities",
            "comparisons":"all E6/ablation/control versus raw E4; mode versus BASE; structured versus placebo"},
        "stability":{"model_seeds":"same 250 accounts; deterministic ordinal Spearman, top-K overlap/Jaccard, displacement",
            "split_seeds":"different populations; do not correlate full unmatched rankings"},
        "decision":{"support":"primary full-coverage hybrid AP difference positive consistently across seeds/tiers, positive paired intervals and compatible top-K retrieval; independent validation still required",
            "multiplicity":"secondary/ablation/control results descriptive; no winner selection or significance claim",
            "incomplete":"full-coverage E6 unavailable implies primary hypothesis inconclusive"},
        "resources":{"baseline_stage_timeout_seconds":600,"feature_generation_timeout_seconds":600,
            "intervention_stage_budget_seconds":1800,"full_e6_gate_seconds":1800,
            "memory":"RSS samples and OS peak when available; traced pilot separately",
            "failure":"leave incomplete manifest/metrics absent; do not score a performance-selected partial cohort"},
        "output_policy":"new data/results/v2 directories only; completed manifests last"}
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(canonical(p))
    destination.with_suffix(".sha256").write_text(sha(destination.read_bytes())+"\n")
    return p,sha(destination.read_bytes())


def read(path):
    path = Path(path)
    content = path.read_bytes()
    expected = path.with_suffix(".sha256").read_text().strip()
    if sha(content) != expected:
        raise ValueError("Preregistered protocol checksum changed.")
    return json.loads(content),expected
