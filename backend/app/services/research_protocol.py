"""Explicit, append-only v2 research execution. No registry/model-state mutation.

Run with: python -m backend.app.services.research_protocol CONFIG.json OUTPUT_ROOT RUN_ID
Input paths are relative to CONFIG.json. Labels are used for splitting/evaluation only.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import time
from pathlib import Path
from typing import Literal

import networkx as nx
import numpy as np
import pandas as pd
import sklearn
from pydantic import BaseModel, ConfigDict, Field
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from .feature_service import FEATURE_NAMES, FeatureService
from .graph_service import GraphService
from .research_identity import baseline_contract, label_identity
from .transfer_service import compute_bootstrap_pr_auc_ci

PROTOCOL = "graphfin-research-v2"
ROOT = Path(__file__).resolve().parents[3]
GROUPS = {"E0": list(range(6)), "E1": list(range(6)), "E2": list(range(14)),
          "E3": list(range(6)) + list(range(14, 19)), "E4": list(range(19)), "E5": list(range(19, 23))}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str
    family: Literal["ibm", "paysim", "custom"]
    transactions: str
    transactions_sha256: str
    labels: str
    labels_sha256: str
    label_set_id: str
    label_definition: str
    provenance_status: Literal["declared_not_independently_verified", "unresolved_conflict"]
    acknowledge_unresolved: bool = False
    row_limit: int | None = Field(None, ge=1)


class ResearchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: InputSpec
    target: InputSpec | None = None
    experiment: Literal["E0", "E1", "E2", "E3", "E4", "E5"]
    baseline_version: Literal["e0-source-signed-zero-v2"] = "e0-source-signed-zero-v2"
    split_seed: int = 42
    model_seed: int = 42
    bootstrap_seed: int = 42
    test_size: float = Field(0.3, gt=0, lt=1)
    stratify: bool = True
    n_estimators: int = Field(100, ge=1)
    max_samples: int | float | Literal["auto"] = "auto"
    contamination: float = Field(0.005, gt=0, le=0.5)
    n_bootstraps: int = Field(1000, ge=1)
    z_threshold: float = Field(2.0, gt=0)
    preprocessing: Literal["canonical-positive-nonself-float32-v1"] = "canonical-positive-nonself-float32-v1"


def load_input(spec, base):
    tx_path, lbl_path = (base / spec.transactions).resolve(), (base / spec.labels).resolve()
    tx_bytes, label_bytes = tx_path.read_bytes(), lbl_path.read_bytes()
    if sha(tx_bytes) != spec.transactions_sha256 or sha(label_bytes) != spec.labels_sha256:
        raise ValueError("Input checksum mismatch; no automatic replacement of configured identities.")
    identity = label_identity(label_bytes)
    conflict = spec.family == "paysim" or identity["provenance_status"] == "unresolved_conflict"
    if conflict:
        if spec.provenance_status != "unresolved_conflict" or not spec.acknowledge_unresolved:
            raise ValueError("PaySim label provenance unresolved: explicit identity and acknowledgement required.")
        if identity["provenance_status"] == "unresolved_conflict" and spec.label_set_id != identity["label_set_id"]:
            raise ValueError("Configured PaySim label-set identity does not match bytes.")
    df = pd.read_csv(tx_path, nrows=spec.row_limit, dtype={"sender_id": str, "receiver_id": str, "transaction_id": str})
    required = ["transaction_id", "sender_id", "receiver_id", "amount", "timestamp"]
    if not set(required).issubset(df) or df[required].isna().any().any() or df.transaction_id.duplicated().any():
        raise ValueError("Canonical transaction schema/identity validation failed.")
    df.amount = pd.to_numeric(df.amount, errors="raise")
    if not np.isfinite(df.amount).all():
        raise ValueError("Nonfinite amount.")
    pd.to_datetime(df.timestamp, errors="raise")
    original_count = len(df)
    df = df[(df.amount > 0) & (df.sender_id != df.receiver_id)].copy()
    start = time.perf_counter()
    graph = GraphService()
    graph.build_graph(df)
    features = FeatureService(graph)
    features.extract_features(df)
    ids, matrix, names = features.get_feature_matrix()
    if names != FEATURE_NAMES or not np.isfinite(matrix).all():
        raise ValueError("Feature schema/nonfinite feature mismatch.")
    labels = pd.read_csv(lbl_path, dtype=str)
    id_col = "user_id" if "user_id" in labels else "account"
    if id_col not in labels or "label" not in labels or labels[id_col].isna().any() or labels[id_col].duplicated().any():
        raise ValueError("Label identity validation failed.")
    if not labels.label.isin(["0", "1"]).all():
        raise ValueError("Research labels must be explicit binary 0/1.")
    mapping = dict(zip(labels[id_col], labels.label.astype(int)))
    if not set(ids).issubset(mapping):
        raise ValueError("Every active entity requires an explicit evaluation label; missing labels are not negatives.")
    y = np.asarray([mapping[u] for u in ids], dtype=int)
    node_order = list(graph.graph.nodes())
    n = len(node_order)
    k = None if n <= 2000 else (100 if n > 50000 else 500)
    metadata = {**spec.model_dump(), "population": "prefix" if spec.row_limit else "full_supplied_file",
                "rows_read": original_count, "rows_retained": len(df), "active_entities": len(ids),
                "positive_labels": int(y.sum()), "unmatched_label_rows": len(mapping) - len(ids),
                "feature_seconds": time.perf_counter() - start,
                "feature_matrix_sha256": sha(matrix.tobytes()), "ordered_ids_sha256": sha(canonical(ids)),
                "graph_node_order_sha256": sha(canonical(node_order)),
                "centrality": {"normalized": True, "weighted": False, "seed": 42, "k": k},
                "observed_label_identity": identity}
    return ids, matrix, y, metadata


def fit_and_score(x_train, evaluation_matrices, config):
    """Label-free fit boundary. Evaluation inputs never determine fitted statistics."""
    if config.experiment == "E0":
        train = np.asarray(x_train, dtype=np.float64)
        mean, std = train.mean(axis=0), train.std(axis=0)
        active = std > 1e-9
        scores = [np.max(np.divide(np.asarray(x, dtype=np.float64) - mean, std,
                                   out=np.zeros_like(x, dtype=np.float64), where=active), axis=1)
                  for x in evaluation_matrices]
        return scores, [(s >= config.z_threshold).astype(int) for s in scores], {"mean": mean.tolist(), "std": std.tolist()}
    model = IsolationForest(n_estimators=config.n_estimators, max_samples=config.max_samples,
                            contamination=config.contamination, random_state=config.model_seed, n_jobs=1)
    model.fit(x_train)
    return ([-model.decision_function(x) for x in evaluation_matrices],
            [(model.predict(x) == -1).astype(int) for x in evaluation_matrices], model.get_params())


def run(config, base, output_root, run_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("run_id must contain only letters, digits, underscore or hyphen.")
    output_root = Path(output_root).resolve()
    if output_root.is_relative_to(ROOT) and not output_root.is_relative_to(ROOT / "data/results/v2"):
        raise ValueError("Repository research outputs must be under data/results/v2.")
    dest = output_root / run_id
    if dest.exists():
        raise FileExistsError("Run already exists; use a new run ID, never overwrite results.")
    start = time.perf_counter()
    source = load_input(config.source, Path(base))
    ids, matrix, y, source_meta = source
    train, test = train_test_split(np.arange(len(ids)), test_size=config.test_size,
                                  random_state=config.split_seed, stratify=y if config.stratify else None)
    # Stable saved evaluation order, independent of randomized split return order.
    train, test = np.sort(train), np.sort(test)
    target = load_input(config.target, Path(base)) if config.target else None
    cols = GROUPS[config.experiment]
    names = [FEATURE_NAMES[j] for j in cols]
    matrices = [matrix[test][:, cols]] + ([target[1][:, cols]] if target else [])
    fit_start = time.perf_counter()
    scores, predictions, fitted = fit_and_score(matrix[train][:, cols], matrices, config)
    fit_seconds = time.perf_counter() - fit_start
    # Nothing is written until inputs, splits, fit and scoring succeed.
    dest.mkdir(parents=True, exist_ok=False)
    cfg = config.model_dump()
    for item in (cfg["source"], cfg["target"]):
        if item:
            for key in ("transactions", "labels"):
                item[key] = os.path.relpath((Path(base) / item[key]).resolve(), dest)
    (dest / "config.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    split = {"train_ids": [ids[i] for i in train], "test_ids": [ids[i] for i in test]}
    (dest / "split.json").write_bytes(canonical(split))
    results, artifacts = {}, {"config": "config.json", "split": "split.json", "results": "results.json"}
    pools = [("source", [ids[i] for i in test], y[test])]
    if target:
        pools.append(("target", target[0], target[2]))  # All target accounts; no target-label-driven split/tuning.
    for (domain, users, truth), raw, predicted in zip(pools, scores, predictions):
        if len(raw) != len(users) or not np.isfinite(raw).all():
            raise ValueError("Evaluation score coverage/nonfinite error.")
        _, ci = compute_bootstrap_pr_auc_ci(truth.tolist(), raw.tolist(), config.n_bootstraps, config.bootstrap_seed)
        results[domain] = {"average_precision": float(average_precision_score(truth, raw)) if truth.sum() else None,
                           "roc_auc": float(roc_auc_score(truth, raw)) if len(np.unique(truth)) == 2 else None,
                           "ap_ci_display": ci.model_dump(), "count": len(users), "positive_count": int(truth.sum())}
        filename = domain + "_held_out_scores.csv"
        pd.DataFrame({"account_id": users, "evaluation_label": truth, "raw_anomaly_score": raw,
                      "predicted_anomaly": predicted}).to_csv(dest / filename, index=False, float_format="%.17g")
        artifacts[domain + "_scores"] = filename
    (dest / "results.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    code_hashes = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted((ROOT / "backend/app").rglob("*.py"))}
    manifest = {"protocol": PROTOCOL, "project_title": "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions",
                "configuration": cfg, "configuration_sha256": sha(canonical(cfg)),
                "source": source_meta, "target": target[3] if target else None,
                "feature_schema": {"version": "canonical19-plus-egonet4-v1", "all_names": FEATURE_NAMES, "selected": names},
                "algorithm": baseline_contract(config.baseline_version, names) if config.experiment == "E0" else
                    {"implementation_id": "isolation-forest-raw-v2", "formula": "-decision_function", "feature_names": names},
                "fitted_parameters": fitted, "split_seed": config.split_seed, "model_seed": config.model_seed,
                "bootstrap_seed": config.bootstrap_seed, "graph_seed": 42, "n_jobs": 1,
                "population": {"train": len(train), "test": len(test), "train_positives": int(y[train].sum()),
                               "test_positives": int(y[test].sum()), "target": len(target[0]) if target else 0},
                "split_sha256": sha(canonical(split)), "score_orientation": "higher_is_more_anomalous",
                "metrics": {"AP": "sklearn.average_precision_score; grouped thresholds; no-positive undefined",
                            "ROC_AUC": "sklearn.roc_auc_score; one-class undefined", "bootstrap": "IID accounts; zero-positive draws skipped; graph dependence not modeled"},
                "protocol_limitations": ["transductive full-observation graph before entity split", "no historical equivalence or publication readiness certified"],
                "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                             "networkx": nx.__version__, "sklearn": sklearn.__version__},
                "code_sha256": sha(canonical(code_hashes)), "code_files": code_hashes,
                "artifacts": artifacts, "artifact_sha256": {name: sha((dest / name).read_bytes()) for name in artifacts.values()},
                "timing_seconds": {"fit_and_score": fit_seconds, "total": time.perf_counter() - start}}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("run_id")
    args = parser.parse_args()
    config = ResearchConfig.model_validate_json(args.config.read_text())
    result = run(config, args.config.resolve().parent, args.output_root, args.run_id)
    print(json.dumps({"protocol": result["protocol"], "artifacts": result["artifacts"]}, indent=2))


if __name__ == "__main__":
    main()
