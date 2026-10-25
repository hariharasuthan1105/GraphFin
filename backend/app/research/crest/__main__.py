import argparse
import json
from pathlib import Path
from .schemas import CrestConfig
from .runner import run


def main():
    parser = argparse.ArgumentParser(description="Frozen E4/CREST candidate scores; no benchmark evaluation.")
    parser.add_argument("config",type=Path)
    parser.add_argument("output_root",type=Path)
    parser.add_argument("run_id")
    args = parser.parse_args()
    saved = json.loads(args.config.read_text())
    cfg = CrestConfig(**saved["configuration"])
    base = args.config.resolve().parent
    manifest = run(cfg,base/saved["source_directory"],base/saved["evaluation_directory"],args.output_root,args.run_id)
    print(json.dumps({"model_id":manifest["model_id"],"timing_seconds":manifest["timing_seconds"]}))


if __name__ == "__main__":
    main()
