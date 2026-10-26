"""Copy existing browser regressions with new evidence paths, preserving old runs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    source = ROOT / "frontend/tests"
    target = ROOT / "frontend/.phase10r-tests"
    target.mkdir(exist_ok=False)
    replacements = {
        "../../../phase9": "../../../phase10r",
        "../../../phase10": "../../../phase10r",
        "../../../work/phase8": "../../../phase10r/phase8-compat",
        "../../../work/pdf-reports": "../../../phase10r/pdf-compat",
    }
    records = []
    for path in source.glob("*.ts"):
        original = path.read_bytes()
        text = original.decode("utf-8")
        # Longest old path first; don't replace the newly created phase10r prefix twice.
        for old in sorted(replacements, key=len, reverse=True):
            text = text.replace(old, replacements[old].replace("phase10r", "PHASE_R_OUTPUT"))
        text = text.replace("PHASE_R_OUTPUT", "phase10r")
        output = target / path.name
        output.write_text(text, encoding="utf-8", newline="\n")
        records.append({"file": path.name, "source_sha256": hashlib.sha256(original).hexdigest(),
                        "execution_sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    (target / "manifest.json").write_text(json.dumps({"output_path_changes_only": replacements,
        "files": records}, indent=2), encoding="utf-8", newline="\n")
    print("Prepared", len(records), "browser files with isolated Phase10R evidence paths.")
