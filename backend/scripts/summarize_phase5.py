"""Verify completed Phase 5 baseline artifacts and report matched E4/E6_BASE results.

This does not score the incomplete intervention cohort or fit models. It derives
new, append-only tables from checksum-verified Phase 5 stages.
"""
import argparse
import csv
import json
from pathlib import Path

from backend.app.research.benchmark.metrics import metrics, paired_bootstrap, stability
from backend.app.research.benchmark.protocol import read
from backend.app.research.benchmark.runner import verify, output, save, complete
from backend.app.services.research_protocol import ROOT, sha


def write_csv(path, rows):
    cols = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


def build(protocol_path, run_id):
    started = __import__("time").perf_counter()
    p, ph = read(protocol_path)
    v2 = ROOT / "data/results/v2"
    feature_runs = {tier: v2/f"phase5-features-{tier}-v1" for tier in ["5k", "50k"]}
    baseline_runs = {
        "5k": v2/"phase5-baselines-5k-v1",
        "50k": v2/"phase5-baselines-50k-v1",
    }
    verified = {}
    for tier in feature_runs:
        fm = verify(feature_runs[tier], ph)
        bm = verify(baseline_runs[tier], ph)
        if fm["tier"] != tier or bm["tier"] != tier or bm["scope"] != "full-heldout-baselines-only":
            raise ValueError("Tier or experiment-scope identity mismatch.")
        ds = p["datasets"][tier]
        source = fm["source"]
        if (source["dataset_id"] != ds["dataset_id"] or
            source["transactions_sha256"] != ds["transactions_sha256"] or
            source["labels_sha256"] != ds["labels_sha256"] or
            source["label_set_id"] != ds["label_set_id"] or
            source["label_definition"] != ds["label_definition"] or
            source["provenance_status"] != ds["provenance_status"]):
            raise ValueError("Dataset or label identity differs from frozen protocol.")
        if bm["feature_manifest_sha256"] != sha((feature_runs[tier]/"manifest.json").read_bytes()):
            raise ValueError("Baseline stage references a different feature manifest.")
        if fm["feature_schema"] != ["in_degree", "out_degree", "total_degree", "weighted_in_degree",
            "weighted_out_degree", "betweenness_centrality", "transaction_count", "total_sent",
            "total_received", "net_flow", "average_transaction_amount", "maximum_transaction_amount",
            "unique_receivers", "unique_senders", "transactions_per_day", "transactions_per_week",
            "average_time_between_transactions", "minimum_time_between_transactions",
            "maximum_time_between_transactions", "egonet_node_count", "egonet_edge_count",
            "egonet_density", "circular_flow_indicator"]:
            raise ValueError("Unexpected 23-feature matrix schema or order.")
        verified[tier] = (fm, bm)

    full_rows, per_seed, source_hashes = [], {}, {}
    expected_methods = {"E0", "E1", "E2", "E3", "E4", "E5", "E6_BASE"}
    for tier, (fm, bm) in verified.items():
        fdir, bdir = feature_runs[tier], baseline_runs[tier]
        pop = json.loads((fdir/"population.json").read_bytes())
        splits = json.loads((fdir/"splits.json").read_bytes())
        ids, labels = pop["ids"], pop["labels"]
        if ids != sorted(ids) or set(ids) != set(labels) or any(y not in (0, 1) for y in labels.values()):
            raise ValueError("Population or binary label alignment invalid.")
        results = json.loads((bdir/"results.json").read_bytes())
        if len(results) != len(p["primary"]["split_seeds"]):
            raise ValueError("Missing or duplicate baseline split runs.")
        seen = set()
        for trial in results:
            seed = trial["split_seed"]
            if seed in seen or set(trial["methods"]) != expected_methods:
                raise ValueError("Duplicate split or incomplete E0-E6_BASE methods.")
            seen.add(seed)
            split = splits[str(seed)]
            train, test = split["train_ids"], split["test_ids"]
            if set(train) & set(test) or set(train) | set(test) != set(ids):
                raise ValueError("Invalid train/test account membership.")
            expected_test_size = 1500 if tier == "5k" else 14998
            if len(test) != expected_test_size:
                raise ValueError("Held-out account count differs from the verified active population.")
            expected_truth = {u: labels[u] for u in test}
            positive = sum(expected_truth.values())
            if positive != split["test_positives"]:
                raise ValueError("Stored split positive count mismatch.")
            scores_path = bdir/trial["key"]/"scores.json"
            score_map = json.loads(scores_path.read_bytes())
            if set(score_map) != expected_methods or any(set(x) != set(test) for x in score_map.values()):
                raise ValueError("Score arrays do not exactly cover held-out accounts.")
            calibration = json.loads((bdir/trial["key"]/"calibration.json").read_bytes())
            config = calibration["config"]
            if (config["model_seed"] != trial["model_seed"] or config["train_ids"] != train or
                config["evaluation_ids"] != test or config["n_estimators"] != p["detector"]["n_estimators"] or
                config["max_samples"] != p["detector"]["max_samples"] or
                config["contamination"] != p["detector"]["contamination"]):
                raise ValueError("Model configuration or membership differs from protocol.")
            per_seed[trial["key"]] = {"tier": tier, "seed": seed, "test_ids": test,
                "labels": expected_truth, "scores": score_map}
            for method in sorted(expected_methods):
                observed = metrics(test, expected_truth, score_map[method])
                stored = trial["methods"][method]
                for key in ["count", "positives", "prevalence", "average_precision", "roc_auc"]:
                    if observed[key] != stored[key]:
                        raise ValueError(f"Stored metric mismatch for {tier}/{seed}/{method}/{key}.")
                full_rows.append({"tier": tier, "scope": "full-heldout-baselines-only",
                    "split_seed": seed, "model_seed": trial["model_seed"], "method": method,
                    **{k: observed[k] for k in ["count", "positives", "prevalence", "average_precision",
                        "ap_over_prevalence", "roc_auc", "tied_accounts", "tie_groups"]},
                    **{f"{metric}@{k}": value for k, row in observed["top_k"].items()
                       for metric, value in row.items()}})
        if seen != set(p["primary"]["split_seeds"]):
            raise ValueError("Baseline split seeds differ from frozen protocol.")
        source_hashes[tier] = {"features_manifest": sha((fdir/"manifest.json").read_bytes()),
            "baseline_manifest": sha((bdir/"manifest.json").read_bytes())}

    # Exact frozen cohort from split 42. Reuse the already scored full held-out
    # arrays, restrict every method to those IDs, and recompute matched metrics.
    feature_dir, baseline_dir = feature_runs["5k"], baseline_runs["5k"]
    split = json.loads((feature_dir/"splits.json").read_bytes())["42"]
    cohort = split["cohort_ids"]
    population = json.loads((feature_dir/"population.json").read_bytes())
    labels = population["labels"]
    cohort_truth = {u: labels[u] for u in cohort}
    cohort_scores = json.loads((baseline_dir/"split-42-model-42"/"scores.json").read_bytes())
    cohort_rows, restricted = [], {}
    for method in sorted(expected_methods):
        score = {u: cohort_scores[method][u] for u in cohort}
        restricted[method] = score
        m = metrics(cohort, cohort_truth, score)
        cohort_rows.append({"tier": "5k", "scope": "exploratory-fixed-250-cohort",
            "split_seed": 42, "model_seed": 42, "method": method,
            **{k: m[k] for k in ["count", "positives", "prevalence", "average_precision",
                "ap_over_prevalence", "roc_auc", "tied_accounts", "tie_groups", "coverage"]},
            **{f"{metric}@{k}": value for k, row in m["top_k"].items()
               for metric, value in row.items()},
            "intervention_availability_rate": None, "fallback_rate": None})
    paired = paired_bootstrap(cohort, cohort_truth, restricted["E6_BASE"], restricted["E4"],
        p["uncertainty"]["bootstrap_seed"], p["uncertainty"]["draws"])
    cal_stability = stability(cohort, restricted["E4"], restricted["E6_BASE"])

    summary_rows, paired_rows = [], []
    for tier in ["5k", "50k"]:
        for method in sorted(expected_methods):
            values = [r["average_precision"] for r in full_rows if r["tier"] == tier and r["method"] == method]
            summary_rows.append({"tier": tier, "scope": "full-heldout-baselines-only", "method": method,
                "runs": len(values), "mean_ap": sum(values)/len(values),
                "median_ap": __import__("statistics").median(values),
                "sample_sd_ap": __import__("statistics").stdev(values),
                "min_ap": min(values), "max_ap": max(values)})
        for trial in json.loads((baseline_runs[tier]/"results.json").read_bytes()):
            result = trial["methods"]["E6_BASE"]["paired_vs_E4"]
            paired_rows.append({"tier": tier, "scope": "full-heldout-baselines-only",
                "split_seed": trial["split_seed"], "model_seed": trial["model_seed"],
                "positives": trial["methods"]["E4"]["positives"],
                "prevalence": trial["methods"]["E4"]["prevalence"],
                "delta_AP_E6_BASE_minus_E4": result["difference"],
                "ci_low": result["interval95"][0] if result["interval95"] else None,
                "ci_high": result["interval95"][1] if result["interval95"] else None,
                "bootstrap_valid": result["valid"], "bootstrap_rejected": result["rejected"],
                "bootstrap_seed": result["seed"], "bootstrap_draws": result["requested"]})

    # Verify the independent 5K replay's scientific score/result artifacts.
    replay = v2/"phase5-baselines-5k-replay-v1"
    rm = verify(replay, ph)
    replay_checks = {}
    for rel in ["results.json", "summary.json", "split-42-model-42/scores.json",
                "split-42-model-42/calibration.json"]:
        replay_checks[rel] = (baseline_dir/rel).read_bytes() == (replay/rel).read_bytes()
    if not all(replay_checks.values()):
        raise ValueError("5K baseline replay scientific artifacts differ.")

    dest = output(run_id)
    write_csv(dest/"full_heldout_baselines.csv", full_rows)
    write_csv(dest/"six_seed_summary.csv", summary_rows)
    write_csv(dest/"paired_e6base_vs_e4.csv", paired_rows)
    write_csv(dest/"matched_exploratory_cohort.csv", cohort_rows)
    save(dest/"matched_paired_uncertainty.json", {"comparison": "E6_BASE minus raw E4",
        "cohort_size": len(cohort), "positives": sum(cohort_truth.values()), "prevalence": sum(cohort_truth.values())/len(cohort),
        "result": paired, "interpretation": "descriptive only; one positive conditions away positive identity uncertainty"})
    save(dest/"cohort_calibration_ranking_stability.json", cal_stability)
    save(dest/"coverage_and_missing_experiments.json", {
        "intervention_directory": "data/results/v2/phase5-interventions-v1",
        "partial_rows": 318, "partial_focal_accounts": 149, "families_present": ["counterparty"],
        "completion_manifest": False, "scored": False,
        "reason": "The protocol requires a complete fixed cohort before score evaluation; partial subset would violate it.",
        "full_coverage_e6": "not run; frozen feasibility gate exceeds 1800 seconds and 50K exceeds 10000-node guard",
        "unavailable": ["E6_SENSITIVITY", "E6_ROBUSTNESS", "E6_HYBRID", "E6_CONCENTRATION_DIAGNOSTIC",
            "intervention-family ablations", "candidate-count-weighted ablation", "score-permutation negative control",
            "intervention explanation coverage", "E6 model-seed ranking stability"]})
    save(dest/"execution_matrix.json", {"protocol_sha256": ph,
        "feature_manifests": {t: sha((feature_runs[t]/"manifest.json").read_bytes()) for t in feature_runs},
        "baseline_manifests": {t: sha((baseline_runs[t]/"manifest.json").read_bytes()) for t in baseline_runs},
        "replay_manifest_sha256": sha((replay/"manifest.json").read_bytes()),
        "replay_equal_scientific_artifacts": replay_checks,
        "cohort_ids_sha256": sha(json.dumps(cohort, ensure_ascii=False, separators=(",", ":")).encode()),
        "cohort_size": len(cohort), "cohort_positives": sum(cohort_truth.values()),
        "cohort_selection": "protocol split 42 held-out stratified random sample seed 31415; no ranking/performance selection",
        "all_full_baseline_splits": sorted(p["primary"]["split_seeds"])})
    return complete(dest, ph, "phase5-results-review", {"source_manifests": source_hashes,
        "review_script_sha256": sha(Path(__file__).resolve().read_bytes()),
        "cohort_positive_count": sum(cohort_truth.values()), "scope": "full baselines plus matched cohort calibration comparison",
        "e6_hypothesis": "inconclusive; intervention modes not evaluated"}, started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("run_id")
    args = parser.parse_args()
    print(json.dumps(build(args.protocol, args.run_id), indent=2))


if __name__ == "__main__":
    main()
