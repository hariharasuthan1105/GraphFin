"""Read-only local release audit; redacted evidence, no model/graph execution.

python backend/scripts/audit_release.py --output UNUSED.json
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import subprocess
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = {
    "github_token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "aws_access_key": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "api_key": re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
}


def secret_findings(raw):
    # Only identifiers and counts are retained, never matching secret values.
    return {name: len(pattern.findall(raw)) for name, pattern in PATTERNS.items() if pattern.search(raw)}


def write_exclusive(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def dependency_inventory():
    requirements = []
    for name in ("backend/requirements.txt", "backend/tests/requirements-reports.txt"):
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                requirements.append(Requirement(line).name)
    pending = requirements + ["psutil"]
    found = {}
    while pending:
        name = pending.pop()
        distribution = metadata.distribution(name)
        key = distribution.metadata["Name"].lower().replace("_", "-")
        if key in found:
            continue
        found[key] = {"version": distribution.version,
            "license_expression": distribution.metadata.get("License-Expression"),
            "license": distribution.metadata.get("License"),
            "license_classifiers": [v for v in distribution.metadata.get_all("Classifier", []) if v.startswith("License")],
            "declared_requirements": distribution.requires or []}
        for raw in distribution.requires or []:
            req = Requirement(raw)
            if req.marker is None or req.marker.evaluate({"extra": ""}):
                pending.append(req.name)
    return found


def audit():
    git = lambda *args: subprocess.check_output(["git", "-c", "safe.directory=*", *args], cwd=ROOT, text=True).strip()
    tracked = git("ls-files").splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    findings = []
    sizes = []
    for name in tracked + untracked:
        path = ROOT / name
        if path.is_file():
            raw = path.read_bytes()
            hits = secret_findings(raw)
            if hits: findings.append({"path": name, "rules": hits})
            sizes.append({"path": name, "bytes": len(raw)})
    history_hits = []
    revisions = git("rev-list", "HEAD").splitlines()
    scanned = set()
    for revision in revisions:
        entries = git("ls-tree", "-r", revision).splitlines()
        for entry in entries:
            spec, name = entry.split("\t", 1)
            mode, kind, identity = spec.split()
            if kind != "blob" or identity in scanned: continue
            scanned.add(identity)
            raw = subprocess.check_output(["git", "-c", "safe.directory=*", "cat-file", "blob", identity], cwd=ROOT)
            hits = secret_findings(raw)
            if hits: history_hits.append({"path": name, "blob": identity, "rules": hits})
    protected = json.loads((ROOT / "docs/research/protected_artifacts_v1.json").read_bytes())["files"]
    runtime = json.loads((ROOT / "docs/research/dataset_report_runtime_assets.json").read_bytes())
    mismatches = lambda entries: [n for n, h in entries.items() if hashlib.sha256((ROOT / n).read_bytes()).hexdigest() != h]
    return {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
        "tracked_files": len(tracked), "untracked_files": untracked,
        "working_tree_secret_patterns": findings, "reachable_head_history_secret_patterns": history_hits,
        "local_head_revisions_scanned": len(revisions), "unique_blobs_scanned": len(scanned),
        "largest_files": sorted(sizes, key=lambda x: -x["bytes"])[:20],
        "protected_files": len(protected), "protected_mismatches": mismatches(protected),
        "pinned_assets": len(runtime), "pinned_asset_mismatches": mismatches(runtime),
        "python_dependencies": dependency_inventory(),
        "limitations": ["Pattern scan is not entropy/semantic secret detection or a complete remote-branch audit.",
            "Installed dependency metadata is not a legal clearance or vulnerability audit.",
            "Exact versions describe this Windows Python environment, not wheel hashes or all platforms."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit()
    write_exclusive(args.output, result)
    print(json.dumps({k: result[k] for k in ("head", "tracked_files", "local_head_revisions_scanned", "unique_blobs_scanned", "working_tree_secret_patterns", "reachable_head_history_secret_patterns", "protected_mismatches", "pinned_asset_mismatches")}, indent=2))
