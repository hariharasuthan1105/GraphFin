"""Derive versioned manuscript tables from pinned saved evidence; never fit models."""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from sklearn.metrics import average_precision_score
from backend.app.services.research_catalog_service import get_research_catalog


def prepare(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    catalog = get_research_catalog()
    rows = catalog._read("rows")
    protocol = catalog._read("protocol")
    maximum = 0.
    for tier in ("5k", "50k"):
        spec = protocol["datasets"][tier]
        path = ROOT / spec["labels"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec["labels_sha256"]
        with path.open(newline="", encoding="utf-8") as stream:
            labels = {r["user_id"]: int(r["label"]) for r in csv.DictReader(stream)}
        for row in (r for r in rows if r["tier"] == tier):
            experiment = catalog.metric_detail(f"baseline-{tier}-{row['method']}-s{row['split_seed']}-m42")
            scores = catalog._read(f"scores-{tier}-{row['split_seed']}")[row["method"]]
            ids = sorted(scores)
            from backend.app.services.research_catalog_service import canonical_hash
            assert canonical_hash(ids) == experiment.test_sha256
            assert len(ids) == row["count"] and sum(labels[u] for u in ids) == row["positives"]
            value = average_precision_score([labels[u] for u in ids], [scores[u] for u in ids])
            delta = abs(float(value) - row["average_precision"])
            maximum = max(maximum, delta)
            assert delta < 1e-15
    methods = [f"E{i}" for i in range(6)]
    seeds = [42, 123, 7, 2024, 99, 555]
    summary = []
    for tier in ("5k", "50k"):
        for method in methods + ["E6_BASE"]:
            group = [r for r in rows if r["tier"] == tier and r["method"] == method]
            assert len(group) == 6 and {r["split_seed"] for r in group} == set(seeds)
            values = [r["average_precision"] for r in group]
            summary.append({"tier": tier, "method": method, "runs": 6,
                "mean_ap": statistics.mean(values), "sample_sd_ap": statistics.stdev(values),
                "min_ap": min(values), "max_ap": max(values),
                "mean_precision_at_k": {str(k): statistics.mean(r["top_k"][str(k)]["precision"] for r in group) for k in (10,25,50,100)}})
    result = {"derivation": "saved-score AP reconstruction, no fits/interventions", "rows_verified": len(rows),
        "maximum_ap_difference": maximum, "split_seeds": seeds,
        "split_summary": summary, "split_rows": rows,
        "model_seed_summary": catalog._read("seed_summary"), "model_seed_rows": catalog._read("seed_rows"),
        "source_entries": catalog._registry()["entries"] if hasattr(catalog,"_registry") else json.loads(catalog.catalog_file.read_bytes())["entries"]}
    (destination / "evidence_tables.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    for tier in ("5k", "50k"):
        text = "|Method|" + "|".join(str(x) for x in seeds) + "|Mean AP|Sample SD|Mean P@100|\n"
        text += "|---|" + "---:|" * 9 + "\n"
        for method in methods:
            group = {r["split_seed"]: r for r in rows if r["tier"] == tier and r["method"] == method}
            s = next(r for r in summary if r["tier"] == tier and r["method"] == method)
            numbers = [group[seed]["average_precision"] for seed in seeds] + [s["mean_ap"],s["sample_sd_ap"],s["mean_precision_at_k"]["100"]]
            text += "|"+method+"|"+"|".join(f"{v:.6f}" for v in numbers)+"|\n"
        (destination / f"table_{tier}.md").write_text(text, encoding="utf-8")
    print(json.dumps({"verified_saved_rows": len(rows), "maximum_ap_difference": maximum, "destination": str(destination)}))


if __name__ == "__main__":
    if len(sys.argv) != 2: raise SystemExit("Supply a new exclusive output directory.")
    prepare(sys.argv[1])
