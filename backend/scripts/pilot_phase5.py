"""Label-free full-5K feasibility pilot; no performance outcomes."""
import argparse
import json
import time
import tracemalloc
from pathlib import Path
import psutil
import pandas as pd
from backend.app.services.research_protocol import ROOT, PROTOCOL, canonical, sha
from backend.app.research.interventions.schemas import InterventionConfig, Budget
from backend.app.research.interventions.historical_evidence import load_history
from backend.app.research.interventions.intervention_engine import InterventionEngine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    if not args.run_id.replace("-", "").isalnum():
        raise ValueError("Invalid run ID")
    out = ROOT/"data/results/v2"/args.run_id
    out.mkdir(exist_ok=False)
    source = ROOT/"data/research/ibm_aml_medium_5k.csv"
    content = source.read_bytes()
    df = pd.read_csv(source, dtype=str)
    cutoff = str(pd.to_datetime(df.timestamp).max())
    cfg = InterventionConfig(dataset_id="ibm-medium-supplied-file-v1",
        source_identity="supplied-ibm-medium-v1", time_kind="timestamp_utc", cutoff=cutoff,
        window_size=24, window_unit="hours",
        budget=Budget(max_count=2, max_fraction=.5, min_retained=1, max_interventions=2))
    tracemalloc.start()
    start = time.perf_counter()
    history = load_history(content, cfg)
    engine = InterventionEngine(history, cfg)
    baseline_seconds = time.perf_counter()-start
    # Max-incident account exercises accepted candidates without any label access.
    focal = min(engine.incident, key=lambda u:(-len(engine.incident[u]),u))
    rows = list(engine.generate(focal))
    elapsed = time.perf_counter()-start
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    (out/"records.json").write_bytes(canonical(rows))
    accepted = [r for r in rows if r["status"]=="accepted"]
    result = {"protocol":PROTOCOL,"stage":"phase5-label-free-feasibility",
        "source_sha256":sha(content),"configuration":cfg.model_dump(),
        "selection":"maximum incident count, lexical tie; labels never loaded",
        "transactions":len(history.events),"accounts":len(history.universe),
        "focals":1,"accepted":len(accepted),"mean_interventions_per_focal":len(accepted),
        "max_interventions_per_focal":len(accepted),"baseline_seconds":baseline_seconds,
        "recompute_seconds":[r["runtime_seconds"] for r in accepted],
        "total_seconds":elapsed,"peak_traced_python_bytes":peak,
        "process_memory":psutil.Process().memory_info()._asdict(),
        "available_memory":psutil.virtual_memory()._asdict(),"logical_cpus":psutil.cpu_count(),
        "storage_bytes":(out/"records.json").stat().st_size,
        "scoring_seconds":None,"performance_metrics":"not computed"}
    (out/"pilot.json").write_bytes(canonical(result))
    print(json.dumps(result,indent=2),flush=True)


if __name__ == "__main__":
    main()
