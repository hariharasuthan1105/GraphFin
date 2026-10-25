import argparse
import json
from pathlib import Path
from .schemas import InterventionConfig
from .artifact_writer import write_run


def main():
    parser = argparse.ArgumentParser(description="Historical transaction-evidence omissions; no anomaly scoring.")
    parser.add_argument("transactions", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("run_id")
    args = parser.parse_args()
    raw = json.loads(args.config.read_text())
    focals = raw.pop("focal_accounts")
    cfg = InterventionConfig.model_validate(raw)
    print(json.dumps(write_run(args.transactions.read_bytes(), cfg, focals, args.output_root, args.run_id)["results"]))


if __name__ == "__main__":
    main()
