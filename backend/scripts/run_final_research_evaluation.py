"""
Final E0-E4 Research Benchmark Runner with Multi-Seed Robustness Evaluation for GraphFin.
Executes the definitive experimental configuration on two locked-in IBM AML dataset scales:
  - Medium Real Tier: 5,000 accounts (prevalence 0.4%, contamination = 0.004)
  - Large Real Tier: 49,992 accounts (prevalence ~0.498%, contamination = 0.005)

Multi-Seed Robustness Check:
  Evaluates 6 seeds total: 42 ('research-split'), 123, 7, 2024, 99, 555 across 5 experiments x 2 scales
  = 60 evaluation runs total.
  Calculates mean, std, min, max for ROC-AUC, PR-AUC, F1, Precision, and Recall across seeds.
  Evaluates whether single-seed (seed=42) feature group rankings hold up or are driven by small positive count noise.

Outputs:
  - data/results/final_e0_e4_comparison.json and .csv (canonical 10-row baseline for seed 42)
  - data/results/final_multiseed_robustness.json and .csv (complete 60-run log + aggregated multi-seed statistics)
"""

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
import numpy as np

import httpx

if sys.stdout:
    sys.stdout.reconfigure(line_buffering=True)

BASE_URL = "http://127.0.0.1:8000/api/v1"
TIMEOUT = 900.0  # 15 minutes timeout to accommodate large dataset upload and feature extraction
SEEDS = [42, 123, 7, 2024, 99, 555]


def wait_for_server(base_url: str, timeout: float = 60.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"{base_url}/health", timeout=3.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


def ensure_server_running(repo_root: Path) -> Optional[subprocess.Popen]:
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=3.0)
        if resp.status_code == 200:
            print("FastAPI server is already running and healthy.", flush=True)
            return None
    except Exception:
        pass

    print("FastAPI server not detected. Starting uvicorn instance...", flush=True)
    server_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--no-access-log",
    ]

    scratch_dir = repo_root / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    server_log_path = scratch_dir / "uvicorn_server.log"
    server_log_file = open(server_log_path, "a", encoding="utf-8")

    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    server_proc = subprocess.Popen(
        server_cmd,
        cwd=str(repo_root),
        stdout=server_log_file,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=flags,
    )

    if not wait_for_server(BASE_URL, timeout=60.0):
        raise RuntimeError("FastAPI server failed to start within 60 seconds.")

    print("FastAPI server successfully started.", flush=True)
    return server_proc


def run_tier_pipeline(
    client: httpx.Client,
    tier_name: str,
    tx_file: Path,
    lbl_file: Path,
    contamination: float,
    seeds: List[int] = SEEDS,
) -> Dict[str, Any]:
    print("\n" + "=" * 80, flush=True)
    print(f"STARTING RESEARCH PIPELINE FOR TIER: {tier_name.upper()}", flush=True)
    print(f"Transactions CSV: {tx_file}", flush=True)
    print(f"Labels CSV:       {lbl_file}", flush=True)
    print(f"Empirical Contamination: {contamination}", flush=True)
    print(f"Seeds: {seeds}", flush=True)
    print("=" * 80, flush=True)

    # 1. Upload Transactions (once per tier)
    t0 = time.time()
    print(f"[{tier_name}] 1. Uploading transactions...", flush=True)
    with open(tx_file, "rb") as f:
        resp = client.post("/transactions/upload", files={"file": (tx_file.name, f, "text/csv")})
    upload_time = round(time.time() - t0, 2)

    if resp.status_code != 200:
        raise RuntimeError(f"Failed to upload transactions for {tier_name}: HTTP {resp.status_code}: {resp.text}")

    upload_data = resp.json()
    dataset_id = upload_data["dataset_id"]
    tx_count = upload_data.get("valid_transactions", 0)
    print(f"[{tier_name}] Upload complete in {upload_time}s. dataset_id = {dataset_id}, transactions = {tx_count}", flush=True)

    # 2. Upload Ground-Truth Labels (once per tier)
    t0 = time.time()
    print(f"[{tier_name}] 2. Uploading ground-truth labels...", flush=True)
    with open(lbl_file, "rb") as f:
        resp = client.post(f"/datasets/{dataset_id}/labels", files={"file": (lbl_file.name, f, "text/csv")})
    label_time = round(time.time() - t0, 2)

    if resp.status_code != 200:
        raise RuntimeError(f"Failed to upload labels for {tier_name}: HTTP {resp.status_code}: {resp.text}")

    label_data = resp.json()
    total_labels = label_data["total_labels_uploaded"]
    matched_labels = label_data["matched_count"]
    pos_labels = label_data["positive_count"]
    neg_labels = label_data["negative_count"]
    prev_rate = label_data["prevalence_rate"]

    print(
        f"[{tier_name}] Labels uploaded in {label_time}s: {matched_labels} matched / {total_labels} uploaded "
        f"({pos_labels} positive, {neg_labels} negative, prevalence: {prev_rate:.4f}%)",
        flush=True,
    )

    experiment_configs = [
        {
            "label": "E0_graph_baseline",
            "type": "baseline",
            "feature_groups": ["graph"],
            "features": ["pagerank", "in_degree", "out_degree", "total_degree", "betweenness_centrality", "clustering_coefficient"],
        },
        {
            "label": "E1_graph_ml",
            "type": "ml",
            "feature_groups": ["graph"],
            "contamination": contamination,
        },
        {
            "label": "E2_graph_behavioral_ml",
            "type": "ml",
            "feature_groups": ["graph", "behavioral"],
            "contamination": contamination,
        },
        {
            "label": "E3_graph_temporal_ml",
            "type": "ml",
            "feature_groups": ["graph", "temporal"],
            "contamination": contamination,
        },
        {
            "label": "E4_full_graphfin",
            "type": "ml",
            "feature_groups": ["graph", "behavioral", "temporal"],
            "contamination": contamination,
        },
    ]

    all_seed_runs: List[Dict[str, Any]] = []
    seed_split_summaries: Dict[int, Dict[str, Any]] = {}
    canonical_seed42_results: List[Dict[str, Any]] = []

    # 3. Iterate over each seed to create partition, train all 5 models, and evaluate
    for seed in seeds:
        split_lbl = "research-split" if seed == 42 else f"research-split-{seed}"
        print(f"\n--- [{tier_name}] Seed {seed}: Creating split '{split_lbl}' ---", flush=True)
        t0 = time.time()
        split_payload = {
            "split_label": split_lbl,
            "test_size": 0.30,
            "random_state": seed,
            "stratify_by_label": True,
        }
        resp = client.post(f"/datasets/{dataset_id}/splits", json=split_payload)
        split_time = round(time.time() - t0, 2)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to create split '{split_lbl}' for {tier_name}: HTTP {resp.status_code}: {resp.text}")

        split_data = resp.json()
        train_total = split_data.get("train_count", 0)
        train_pos = split_data.get("train_positive_count", 0)
        train_neg = split_data.get("train_negative_count", 0)
        test_total = split_data.get("test_count", 0)
        test_pos = split_data.get("test_positive_count", 0)
        test_neg = split_data.get("test_negative_count", 0)
        stratified = split_data.get("stratified", False)

        print(
            f"[{tier_name}] Split '{split_lbl}' (seed={seed}) in {split_time}s:\n"
            f"   TRAIN: {train_total} total ({train_pos} positive, {train_neg} negative)\n"
            f"   TEST:  {test_total} total ({test_pos} positive, {test_neg} negative)",
            flush=True,
        )
        assert test_pos > 0, f"Critical: test partition has zero positive labels for {tier_name} seed {seed}!"

        seed_split_summaries[seed] = {
            "split_label": split_lbl,
            "seed": seed,
            "train_total": train_total,
            "train_pos": train_pos,
            "train_neg": train_neg,
            "test_total": test_total,
            "test_pos": test_pos,
            "test_neg": test_neg,
            "stratified": stratified,
        }

        # Train & evaluate each experiment under this split
        for exp in experiment_configs:
            exp_label = exp["label"]
            t0 = time.time()

            if exp["type"] == "baseline":
                req_body = {
                    "experiment_label": exp_label,
                    "z_threshold": 2.0,
                    "feature_groups": exp["feature_groups"],
                    "split_label": split_lbl,
                }
                resp = client.post(f"/anomalies/{dataset_id}/baseline", json=req_body)
            else:
                req_body = {
                    "experiment_label": exp_label,
                    "feature_groups": exp["feature_groups"],
                    "contamination": exp["contamination"],
                    "random_state": 42,
                    "split_label": split_lbl,
                }
                resp = client.post(f"/anomalies/{dataset_id}/train", json=req_body)

            train_time = round(time.time() - t0, 2)
            if resp.status_code != 200:
                raise RuntimeError(f"Training failed for {exp_label} (split='{split_lbl}'): HTTP {resp.status_code}: {resp.text}")

            train_data = resp.json()
            meta = train_data["model_metadata"]

            # Evaluate on held-out test partition
            t0 = time.time()
            eval_resp = client.get(f"/evaluation/{dataset_id}/{exp_label}?split_label={split_lbl}")
            eval_time = round(time.time() - t0, 2)
            if eval_resp.status_code != 200:
                raise RuntimeError(f"Evaluation failed for {exp_label} (split='{split_lbl}'): HTTP {eval_resp.status_code}: {eval_resp.text}")

            m = eval_resp.json()
            cm = m.get("confusion_matrix") or {}
            tp = cm.get("tp", 0)
            fp = cm.get("fp", 0)
            tn = cm.get("tn", 0)
            fn = cm.get("fn", 0)

            record = {
                "scale": tier_name,
                "dataset_id": dataset_id,
                "experiment_label": exp_label,
                "seed": seed,
                "method": m.get("method", meta.get("method")),
                "feature_groups": exp["feature_groups"],
                "feature_count": m["feature_count"],
                "contamination": meta.get("contamination"),
                "evaluation_mode": m["evaluation_mode"],
                "split_label": split_lbl,
                "test_total": test_total,
                "test_positive": test_pos,
                "test_negative": test_neg,
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "precision": m["precision"],
                "recall": m["recall"],
                "f1_score": m["f1_score"],
                "accuracy": m["accuracy"],
                "roc_auc": m["roc_auc"],
                "pr_auc": m["pr_auc"],
            }
            all_seed_runs.append(record)
            if seed == 42:
                canonical_seed42_results.append(record)

            print(
                f"   [{exp_label} | seed={seed:<4}] "
                f"PR-AUC={m['pr_auc'] if m['pr_auc'] is not None else 0.0:.4f}, "
                f"ROC-AUC={m['roc_auc'] if m['roc_auc'] is not None else 0.0:.4f}, "
                f"F1={m['f1_score']:.4f}, Prec={m['precision']:.4f}, Rec={m['recall']:.4f}, "
                f"TP={tp}, FP={fp}, TestPos={test_pos}",
                flush=True,
            )

    # 4. Integrity check: verify that retraining under other split_labels did not corrupt research-split (seed 42)
    print(f"\n[{tier_name}] Verifying research-split integrity across all 5 models...", flush=True)
    for exp_rec in canonical_seed42_results:
        exp_lbl = exp_rec["experiment_label"]
        check_resp = client.get(f"/evaluation/{dataset_id}/{exp_lbl}?split_label=research-split")
        assert check_resp.status_code == 200, f"Integrity check failed: could not evaluate {exp_lbl} on research-split"
        cm_check = check_resp.json()
        assert abs(cm_check["pr_auc"] - exp_rec["pr_auc"]) < 1e-5, (
            f"Integrity check failed for {exp_lbl}: PR-AUC changed from {exp_rec['pr_auc']} to {cm_check['pr_auc']}"
        )
        assert abs(cm_check["roc_auc"] - exp_rec["roc_auc"]) < 1e-5, (
            f"Integrity check failed for {exp_lbl}: ROC-AUC changed from {exp_rec['roc_auc']} to {cm_check['roc_auc']}"
        )
    print(f"[{tier_name}] Research-split integrity verified: all 5 models remain 100% stable and intact.", flush=True)

    # 5. Compute multi-seed summary statistics per experiment
    summary_stats = []
    for exp in experiment_configs:
        exp_lbl = exp["label"]
        runs = [r for r in all_seed_runs if r["experiment_label"] == exp_lbl]
        roc_aucs = [r["roc_auc"] for r in runs if r["roc_auc"] is not None]
        pr_aucs = [r["pr_auc"] for r in runs if r["pr_auc"] is not None]
        f1s = [r["f1_score"] for r in runs]
        precs = [r["precision"] for r in runs]
        recs = [r["recall"] for r in runs]
        test_pos_by_seed = {r["seed"]: r["test_positive"] for r in runs}

        def compute_stats(arr):
            if not arr:
                return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
            mean = float(np.mean(arr))
            std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            return {
                "mean": round(mean, 4),
                "std": round(std, 4),
                "min": round(float(np.min(arr)), 4),
                "max": round(float(np.max(arr)), 4),
            }

        roc_stats = compute_stats(roc_aucs)
        pr_stats = compute_stats(pr_aucs)
        f1_stats = compute_stats(f1s)
        prec_stats = compute_stats(precs)
        rec_stats = compute_stats(recs)

        summary_stats.append({
            "scale": tier_name,
            "dataset_id": dataset_id,
            "experiment_label": exp_lbl,
            "feature_groups": exp["feature_groups"],
            "feature_count": runs[0]["feature_count"],
            "contamination": contamination if exp["type"] == "ml" else None,
            "num_seeds": len(runs),
            "roc_auc": roc_stats,
            "pr_auc": pr_stats,
            "f1_score": f1_stats,
            "precision": prec_stats,
            "recall": rec_stats,
            "test_pos_by_seed": test_pos_by_seed,
            "single_seed_42": {
                "roc_auc": runs[0]["roc_auc"],
                "pr_auc": runs[0]["pr_auc"],
                "f1_score": runs[0]["f1_score"],
            },
        })

    return {
        "tier_name": tier_name,
        "dataset_id": dataset_id,
        "tx_count": tx_count,
        "matched_labels": matched_labels,
        "pos_labels": pos_labels,
        "neg_labels": neg_labels,
        "prevalence": prev_rate,
        "splits": seed_split_summaries,
        "canonical_seed42_results": canonical_seed42_results,
        "all_seed_runs": all_seed_runs,
        "summary_stats": summary_stats,
    }


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_dir = repo_root / "data"
    research_dir = data_dir / "research"
    results_dir = data_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    med_tx = research_dir / "ibm_aml_medium_5k.csv"
    med_lbl = research_dir / "ibm_aml_medium_5k_labels.csv"
    large_tx = research_dir / "ibm_aml_large_50k.csv"
    large_lbl = research_dir / "ibm_aml_large_50k_labels.csv"

    for p in [med_tx, med_lbl, large_tx, large_lbl]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required permanent fixture: {p}")

    server_proc = ensure_server_running(repo_root)

    try:
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            # 1. Run Medium Tier (5k accounts, 0.4% prevalence, contamination=0.004, 6 seeds)
            med_out = run_tier_pipeline(
                client=client,
                tier_name="medium_real (5,000 accounts)",
                tx_file=med_tx,
                lbl_file=med_lbl,
                contamination=0.004,
                seeds=SEEDS,
            )

            # 2. Run Large Tier (49,992 accounts in graph, ~0.498% prevalence, contamination=0.005, 6 seeds)
            large_out = run_tier_pipeline(
                client=client,
                tier_name="large_real (49,992 accounts)",
                tx_file=large_tx,
                lbl_file=large_lbl,
                contamination=0.005,
                seeds=SEEDS,
            )

            # -------------------------------------------------------------
            # EXPORT 1: Canonical 10-row baseline table (seed 42, research-split)
            # -------------------------------------------------------------
            all_canonical_rows = med_out["canonical_seed42_results"] + large_out["canonical_seed42_results"]
            json_out_path = results_dir / "final_e0_e4_comparison.json"
            csv_out_path = results_dir / "final_e0_e4_comparison.csv"

            export_payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "benchmark_title": "GraphFin Final E0-E4 Benchmark on IBM AML HI-Small Subsamples",
                "tiers": {
                    "medium_real": {
                        "dataset_id": med_out["dataset_id"],
                        "accounts": med_out["matched_labels"],
                        "positives": med_out["pos_labels"],
                        "negatives": med_out["neg_labels"],
                        "prevalence": med_out["prevalence"],
                        "contamination": 0.004,
                        "train_test_split": {
                            "train": {
                                "total": med_out["splits"][42]["train_total"],
                                "pos": med_out["splits"][42]["train_pos"],
                                "neg": med_out["splits"][42]["train_neg"],
                            },
                            "test": {
                                "total": med_out["splits"][42]["test_total"],
                                "pos": med_out["splits"][42]["test_pos"],
                                "neg": med_out["splits"][42]["test_neg"],
                            },
                        },
                    },
                    "large_real": {
                        "dataset_id": large_out["dataset_id"],
                        "accounts": large_out["matched_labels"],
                        "positives": large_out["pos_labels"],
                        "negatives": large_out["neg_labels"],
                        "prevalence": large_out["prevalence"],
                        "contamination": 0.005,
                        "train_test_split": {
                            "train": {
                                "total": large_out["splits"][42]["train_total"],
                                "pos": large_out["splits"][42]["train_pos"],
                                "neg": large_out["splits"][42]["train_neg"],
                            },
                            "test": {
                                "total": large_out["splits"][42]["test_total"],
                                "pos": large_out["splits"][42]["test_pos"],
                                "neg": large_out["splits"][42]["test_neg"],
                            },
                        },
                    },
                },
                "total_configurations_evaluated": len(all_canonical_rows),
                "experiments": all_canonical_rows,
            }

            with open(json_out_path, "w", encoding="utf-8") as f:
                json.dump(export_payload, f, indent=2)

            csv_fields = [
                "scale",
                "dataset_id",
                "experiment_label",
                "method",
                "feature_groups",
                "feature_count",
                "contamination",
                "evaluation_mode",
                "split_label",
                "test_total",
                "test_positive",
                "test_negative",
                "tp",
                "fp",
                "tn",
                "fn",
                "precision",
                "recall",
                "f1_score",
                "accuracy",
                "roc_auc",
                "pr_auc",
            ]

            with open(csv_out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csv_fields)
                writer.writeheader()
                for row in all_canonical_rows:
                    row_copy = dict(row)
                    row_copy.pop("seed", None)
                    row_copy["feature_groups"] = "+".join(row_copy["feature_groups"])
                    writer.writerow(row_copy)

            print("\n" + "=" * 100, flush=True)
            print("CONSOLIDATED 10-ROW E0-E4 COMPARISON TABLE SAVED", flush=True)
            print(f"JSON: {json_out_path}", flush=True)
            print(f"CSV:  {csv_out_path}", flush=True)
            print("=" * 100, flush=True)

            # -------------------------------------------------------------
            # EXPORT 2: Multi-Seed Robustness Summary (60 runs total)
            # -------------------------------------------------------------
            all_60_runs = med_out["all_seed_runs"] + large_out["all_seed_runs"]
            all_summary_stats = med_out["summary_stats"] + large_out["summary_stats"]

            multiseed_json_path = results_dir / "final_multiseed_robustness.json"
            multiseed_csv_path = results_dir / "final_multiseed_robustness.csv"

            robustness_payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "title": "GraphFin Multi-Seed Robustness Evaluation (6 Seeds x 5 Models x 2 Scales = 60 Runs)",
                "seeds": SEEDS,
                "tiers": {
                    "medium_real": {
                        "dataset_id": med_out["dataset_id"],
                        "accounts": med_out["matched_labels"],
                        "contamination": 0.004,
                        "splits": med_out["splits"],
                    },
                    "large_real": {
                        "dataset_id": large_out["dataset_id"],
                        "accounts": large_out["matched_labels"],
                        "contamination": 0.005,
                        "splits": large_out["splits"],
                    },
                },
                "summary_statistics": all_summary_stats,
                "all_evaluations": all_60_runs,
            }

            with open(multiseed_json_path, "w", encoding="utf-8") as f:
                json.dump(robustness_payload, f, indent=2)

            # CSV Summary table
            summary_csv_fields = [
                "scale",
                "dataset_id",
                "experiment_label",
                "feature_groups",
                "feature_count",
                "contamination",
                "num_seeds",
                "roc_auc_mean",
                "roc_auc_std",
                "roc_auc_min",
                "roc_auc_max",
                "pr_auc_mean",
                "pr_auc_std",
                "pr_auc_min",
                "pr_auc_max",
                "f1_mean",
                "f1_std",
                "prec_mean",
                "prec_std",
                "rec_mean",
                "rec_std",
                "test_pos_counts",
            ]

            with open(multiseed_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=summary_csv_fields)
                writer.writeheader()
                for s in all_summary_stats:
                    writer.writerow({
                        "scale": s["scale"],
                        "dataset_id": s["dataset_id"],
                        "experiment_label": s["experiment_label"],
                        "feature_groups": "+".join(s["feature_groups"]),
                        "feature_count": s["feature_count"],
                        "contamination": s["contamination"],
                        "num_seeds": s["num_seeds"],
                        "roc_auc_mean": s["roc_auc"]["mean"],
                        "roc_auc_std": s["roc_auc"]["std"],
                        "roc_auc_min": s["roc_auc"]["min"],
                        "roc_auc_max": s["roc_auc"]["max"],
                        "pr_auc_mean": s["pr_auc"]["mean"],
                        "pr_auc_std": s["pr_auc"]["std"],
                        "pr_auc_min": s["pr_auc"]["min"],
                        "pr_auc_max": s["pr_auc"]["max"],
                        "f1_mean": s["f1_score"]["mean"],
                        "f1_std": s["f1_score"]["std"],
                        "prec_mean": s["precision"]["mean"],
                        "prec_std": s["precision"]["std"],
                        "rec_mean": s["recall"]["mean"],
                        "rec_std": s["recall"]["std"],
                        "test_pos_counts": str([s["test_pos_by_seed"][sd] for sd in SEEDS]),
                    })

            print("\n" + "=" * 110, flush=True)
            print("MULTI-SEED ROBUSTNESS EVALUATION COMPLETE (60 RUNS TOTAL)", flush=True)
            print(f"JSON Export: {multiseed_json_path}", flush=True)
            print(f"CSV Export:  {multiseed_csv_path}", flush=True)
            print("=" * 110, flush=True)

            # -------------------------------------------------------------
            # DISPLAY CONCISE MULTI-SEED SUMMARY TABLE
            # -------------------------------------------------------------
            print("\n### MULTI-SEED PERFORMANCE SUMMARY (Mean +/- Std [Min, Max] across 6 Seeds)")
            print(f"| {'Scale':<20} | {'Experiment':<22} | {'PR-AUC (Mean +/- Std [Min, Max])':<36} | {'ROC-AUC (Mean +/- Std [Min, Max])':<36} | {'Test Positives':<18} |")
            print("|" + "-" * 22 + "|" + "-" * 24 + "|" + "-" * 38 + "|" + "-" * 38 + "|" + "-" * 20 + "|")
            for s in all_summary_stats:
                pr_str = f"{s['pr_auc']['mean']:.4f} +/- {s['pr_auc']['std']:.4f} [{s['pr_auc']['min']:.4f}, {s['pr_auc']['max']:.4f}]"
                roc_str = f"{s['roc_auc']['mean']:.4f} +/- {s['roc_auc']['std']:.4f} [{s['roc_auc']['min']:.4f}, {s['roc_auc']['max']:.4f}]"
                pos_list_str = str([s["test_pos_by_seed"][sd] for sd in SEEDS])
                print(f"| {s['scale'][:20]:<20} | {s['experiment_label']:<22} | {pr_str:<36} | {roc_str:<36} | {pos_list_str:<18} |")
            print("=" * 110, flush=True)

    finally:
        pass


if __name__ == "__main__":
    main()
