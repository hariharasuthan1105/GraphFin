"""Phase 2 manifest envelope extended with an evidence-intervention stage."""
import json
import platform
import re
import time
from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd
from ...services.research_protocol import PROTOCOL, ROOT, canonical, sha
from ...services.feature_service import CANONICAL_TRANSFER_FEATURES
from .schemas import VERSION
from .historical_evidence import load_history
from .intervention_engine import InterventionEngine


def write_run(content, config, focals, output_root, run_id):
    output_root = Path(output_root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("Invalid run ID.")
    if output_root.is_relative_to(ROOT) and not output_root.is_relative_to(ROOT / "data/results/v2"):
        raise ValueError("Repository outputs must be under data/results/v2.")
    dest = output_root / run_id
    if dest.exists():
        raise FileExistsError("Never overwrite an existing research run.")
    start = time.perf_counter()
    history = load_history(content, config)
    focals = sorted(set(focals))
    if not set(focals) <= set(history.universe):
        raise ValueError("Unknown focal account.")
    engine = InterventionEngine(history, config)
    dest.mkdir(parents=True, exist_ok=False)
    configuration = {**config.model_dump(), "focal_accounts": focals}
    (dest/"config.json").write_bytes(canonical(configuration))
    (dest/"baseline.json").write_bytes(canonical({"account_universe": history.universe,
        "focal_features": {u: engine.baseline[u] for u in focals}, "recomputation": engine.mode}))
    counts = {"accepted": 0, "rejected": 0}
    family_counts = {}
    changes = []
    with (dest/"interventions.jsonl").open("wb") as records:
        for focal in focals:
            for record in engine.generate(focal):
                records.write(canonical(record) + b"\n")
                counts[record["status"]] += 1
                if record["status"] == "accepted":
                    family_counts[record["family"]] = family_counts.get(record["family"], 0) + 1
                    changed = ", ".join(f"{name}: {delta:+.6g}" for name, delta in zip(
                        CANONICAL_TRANSFER_FEATURES, record["feature_difference"]) if delta)
                    changes.append(f"- {focal}, {record['family']} / {record['candidate_key']}: "
                                   f"omit {record['omitted_transaction_ids']}; feature deltas: {changed or 'all zero'}.")
    report = ("# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions\n\n"
              "Phase 3 analytical evidence omissions; no fraud scores or causal claims.\n\n"
              f"Historical transactions: {len(history.events)}; accounts: {len(history.universe)}.\n"
              f"Accepted: {counts['accepted']}; rejected: {counts['rejected']}.\n"
              f"Accepted by family: {family_counts}.\n\n"
              "baseline.json contains the original 19-feature vectors; interventions.jsonl contains "
              "omitted IDs, constraint checks, recomputed vectors and differences. The input CSV is "
              "required to reconstruct the original network. Simulation time uses hourly steps, "
              "not real-world event dates. PaySim label provenance remains unresolved; no labels were read.\n")
    report += "\nObserved changes (intervened minus baseline):\n\n" + "\n".join(changes) + "\n"
    (dest/"report.md").write_text(report, encoding="utf-8")
    artifacts = {"config": "config.json", "baseline": "baseline.json",
                 "interventions": "interventions.jsonl", "report": "report.md"}
    code = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted((ROOT/"backend/app").rglob("*.py"))}
    manifest = {"protocol": PROTOCOL, "stage": "evidence-interventions",
        "project_title": "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions",
        "algorithm": {"implementation_id": VERSION, "families": config.families},
        "configuration": configuration, "configuration_sha256": sha(canonical(configuration)),
        "source": {"dataset_id": config.dataset_id, "source_identity": config.source_identity,
                   "transactions_sha256": history.dataset_sha256, "history_sha256": history.history_sha256,
                   "labels": "not_read", "paysim_label_provenance": "unresolved"},
        "historical_cutoff": {"value": config.cutoff, "boundary": "<=", "time_kind": config.time_kind,
                              "naive_timestamp_policy": "UTC", "simulation_bridge": "1970 epoch for interval arithmetic only"},
        "feature_schema": {"version": "canonical19-plus-egonet4-v1", "selected": CANONICAL_TRANSFER_FEATURES},
        "intervention_seed": config.intervention_seed, "graph_seed": 42,
        "candidate_selection": "family order; lexicographic complete groups; budgeted seeded SHA256 greedy",
        "budget": config.budget.model_dump(), "recomputation": engine.mode,
        "population": {"historical_transactions": len(history.events), "accounts": len(history.universe), "focals": len(focals)},
        "results": {**counts, "accepted_by_family": family_counts},
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "networkx": nx.__version__},
        "code_files": code, "code_sha256": sha(canonical(code)), "artifacts": artifacts,
        "artifact_sha256": {name: sha((dest/name).read_bytes()) for name in artifacts.values()},
        "timing_seconds": {"total": time.perf_counter()-start},
        "protocol_limitations": ["hypothetical evidence omissions, not causal explanations",
            "historical snapshot is not a validated future-only model evaluation",
            "global reference recomputation; existing seeded centrality above 2000 nodes"]}
    # Manifest written last; a failed/partial run has no completion manifest.
    (dest/"manifest.json").write_bytes(canonical(manifest))
    return manifest
