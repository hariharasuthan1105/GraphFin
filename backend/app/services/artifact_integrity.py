"""Exact supplied-ZIP byte policy v1; normalized text is never integrity proof."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def protected_manifest():
    return json.loads((ROOT / "docs/research/protected_artifacts_v1.json").read_text())


def protected_sha(relative_path):
    return protected_manifest()["files"][relative_path]


def verify_protected(root=ROOT):
    return [path for path, digest in protected_manifest()["files"].items()
            if not (Path(root) / path).is_file() or hashlib.sha256((Path(root) / path).read_bytes()).hexdigest() != digest]


def guard_output(path):
    resolved = Path(path).resolve()
    if resolved.is_relative_to(ROOT) and resolved.relative_to(ROOT).as_posix() in protected_manifest()["files"]:
        raise ValueError(f"Protected historical output cannot be overwritten: {path}")
