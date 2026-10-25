"""Measured, bounded workloads; writes only new v2 directories.

python -m backend.scripts.benchmark_phase3 data/results/v2 phase3-check
tracemalloc measures traced Python allocations, not total process/native RSS.
"""
import argparse
import io
import json
import time
import tracemalloc
from pathlib import Path
import pandas as pd
from backend.app.services.research_protocol import ROOT, sha, canonical
from backend.app.research.interventions.schemas import InterventionConfig, Budget
from backend.app.research.interventions.artifact_writer import write_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("prefix")
    args = parser.parse_args()
    output = args.output_root.resolve()
    # Writer validates destination policy; evidence directory follows same rule.
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT/"data/results/v2"):
        raise ValueError("Use a versioned output root.")
    if not args.prefix.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid prefix.")
    evidence = output/(args.prefix+"-evidence")
    evidence.mkdir(parents=True, exist_ok=False)
    config = json.loads((ROOT/"docs/research/configs/phase3_demo.json").read_text())
    focal = config.pop("focal_accounts")
    config = InterventionConfig(**config)
    data = (ROOT/"docs/research/fixtures/phase3_transactions.csv").read_bytes()
    measurements = []
    for suffix in ["demo-a", "demo-b"]:
        tracemalloc.start()
        start = time.perf_counter()
        manifest = write_run(data,config,focal,output,args.prefix+"-"+suffix)
        duration, peak = time.perf_counter()-start, tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        measurements.append({"workload": suffix, "wall_seconds":duration,"peak_traced_python_bytes":peak,
                             "population":manifest["population"],"results":manifest["results"]})
    source = ROOT/"data/research/ibm_aml_medium_5k.csv"
    original = source.read_bytes()
    for count in [500,1500]:
        # Prefix selection fixed in advance, no label access.
        frame = pd.read_csv(io.BytesIO(original), nrows=count, dtype=str)
        content = frame.to_csv(index=False,lineterminator="\n").encode()
        filename = f"ibm-prefix-{count}.csv"
        (evidence/filename).write_bytes(content)
        accounts = pd.concat([frame.sender_id,frame.receiver_id]).value_counts()
        focal = sorted(accounts[accounts == accounts.max()].index)[0]
        cfg = InterventionConfig(dataset_id=f"ibm-medium-prefix-{count}",
            source_identity=f"supplied-ibm-medium-prefix-{count}",time_kind="timestamp_utc",
            cutoff=str(pd.to_datetime(frame.timestamp).max()), window_size=24,window_unit="hours",
            budget=Budget(max_count=2,max_fraction=.5,min_retained=1,max_interventions=3))
        tracemalloc.start()
        start = time.perf_counter()
        m = write_run(content,cfg,[focal],output,args.prefix+f"-ibm-{count}")
        elapsed, peak = time.perf_counter()-start, tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        measurements.append({"workload":filename,"source_file_sha256":sha(original),"subset_sha256":sha(content),
            "selection":"first N source rows; focal maximum incident count, lexical tie break; no labels",
            "wall_seconds":elapsed,"peak_traced_python_bytes":peak,"population":m["population"],
            "results":m["results"],"centrality":m["recomputation"]["centrality"]})
    def stable(path):
        rows = [json.loads(x) for x in path.read_text().splitlines()]
        return [{k:v for k,v in row.items() if k != "runtime_seconds"} for row in rows]
    a,b = [output/(args.prefix+"-"+s) for s in ["demo-a","demo-b"]]
    equal = stable(a/"interventions.jsonl") == stable(b/"interventions.jsonl")
    assert equal and (a/"baseline.json").read_bytes() == (b/"baseline.json").read_bytes()
    result = {"memory_measure":"tracemalloc peak Python allocations; excludes untraced native memory/RSS",
              "timing_measure":"single runs under tracemalloc, includes feature extraction and output; no scalability extrapolation",
              "demo_replay_equal_excluding_runtime":equal,"measurements":measurements}
    (evidence/"benchmark.json").write_bytes(canonical(result))
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
