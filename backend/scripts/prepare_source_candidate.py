"""Audit explicit source-only additions in alternate Git indexes; never commit/push.

python backend/scripts/prepare_source_candidate.py NEW_REVIEW_DIRECTORY
The real index/worktree are not staged, reset, cleaned or normalized.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

try:
    from audit_release import secret_findings
except ModuleNotFoundError:
    from backend.scripts.audit_release import secret_findings

ROOT = Path(__file__).resolve().parents[2]
GROUPS = {
    "phase9-source": [
        "backend/app/api/router.py", "frontend/src/ResearchApp.tsx",
        "frontend/src/research/client.ts", "frontend/src/research/pages/Datasets.tsx",
        "frontend/src/research/pages/Experiments.tsx",
        "backend/app/api/routes/graph_explorer.py", "backend/app/schemas/graph_explorer.py",
        "backend/app/services/graph_explorer_index.py", "backend/app/services/graph_explorer_service.py",
        "backend/scripts/build_graph_explorer.py", "backend/scripts/verify_graph_explorer.py",
        "backend/tests/test_phase9_graph_explorer.py", "frontend/playwright.graph.config.ts",
        "frontend/src/research/graph/GraphCanvas.tsx", "frontend/src/research/graph/Inspector.tsx",
        "frontend/src/research/graph/client.ts", "frontend/src/research/graph/contract.schema.json",
        "frontend/src/research/graph/contract.ts", "frontend/src/research/graph/graph.css",
        "frontend/src/research/graph/layout-contract.ts", "frontend/src/research/graph/layout.worker.ts",
        "frontend/src/research/pages/GraphExplorer.tsx", "frontend/tests/graph-explorer.spec.ts",
        "frontend/tests/graph-fixtures.ts", "frontend/tests/graph-real.spec.ts",
    ],
    "phase10-source": [
        "backend/constraints-research-v1.txt", "backend/requirements-research.txt",
        "backend/scripts/audit_release.py", "backend/scripts/prepare_final_browser_tests.py",
        "backend/scripts/prepare_manuscript_evidence.py", "backend/scripts/verify_final_api.py",
        "backend/tests/test_phase10_release_validation.py", "frontend/playwright.final.config.ts",
        "frontend/tests/final-system.spec.ts",
    ],
    "phase10r-safety": [
        ".gitignore", "backend/app/research_demo.py",
        "backend/scripts/prepare_controlled_demo_tests.py", "backend/scripts/prepare_source_candidate.py",
        "backend/tests/test_phase10r_controlled_demo.py", "frontend/playwright.controlled.config.ts",
        "frontend/tests/controlled-demo.spec.ts", "docs/research/10R_controlled_demo_readiness.md",
        "docs/research/10R_safe_commit_plan.md", "docs/research/10R_remaining_submission_gaps.md",
    ],
}
LOCAL_PATH = re.compile(rb"(?:[A-Za-z]:[\\/]+(?:Users|Documents|Temp)[\\/]|/"
                        rb"home/[^/\s]+/)", re.I)
RAW_ACCOUNT = re.compile(rb"\b\d{4,}_[A-Fa-f0-9]{5,}\b")


def prepare(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ)

    def git(*args, candidate=False, check=True):
        return subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=ROOT,
                              env=environment if candidate else None,
                              capture_output=True, check=check)

    before = git("diff", "--cached", "--raw").stdout
    head = git("rev-parse", "HEAD").stdout.decode().strip()
    environment["GIT_INDEX_FILE"] = str(destination / "candidate.index")
    git("read-tree", "HEAD", candidate=True)
    records = []
    findings = []
    paths = []
    patches = {}
    for group, names in GROUPS.items():
        for name in names:
            if name in paths:
                raise ValueError("Duplicate candidate path")
            paths.append(name)
            path = ROOT / name
            if not path.is_file() or path.is_symlink():
                raise ValueError("Missing or linked candidate source")
            if name.startswith("data/") or path.suffix not in (".py", ".ts", ".tsx", ".json", ".css", ".md", ".txt") and name != ".gitignore":
                raise ValueError("Candidate is not an approved source file")
            raw = path.read_bytes()
            raw.decode("utf-8")
            if b"\0" in raw or len(raw) > 1024 * 1024:
                raise ValueError("Binary/oversized candidate")
            problems = secret_findings(raw)
            if LOCAL_PATH.search(raw): problems["absolute_local_path"] = True
            if RAW_ACCOUNT.search(raw): problems["raw_account_identifier"] = True
            # Schema JSON is code; arbitrary exported JSON maps/rows are not allowed.
            if path.suffix == ".json" and not name.endswith("/contract.schema.json"):
                problems["unapproved_json_artifact"] = True
            if problems: findings.append({"path": name, "rules": problems})
            records.append({"group": group, "path": name, "bytes": len(raw),
                            "working_sha256": hashlib.sha256(raw).hexdigest()})
        if findings:
            (destination / "preflight-findings.json").write_text(
                json.dumps(findings, indent=2), encoding="utf-8", newline="\n")
            raise ValueError("Candidate preflight found unsafe content; no further staging")
        git("add", "--", *names, candidate=True)
        patch = git("diff", "--cached", "HEAD", "--full-index", "--", *names, candidate=True).stdout
        (destination / (group + ".diff")).write_bytes(patch)
        patches[group] = {"files": len(names), "sha256": hashlib.sha256(patch).hexdigest(), "bytes": len(patch)}

    for record in records:
        raw = git("show", ":" + record["path"], candidate=True).stdout
        record["staged_sha256"] = hashlib.sha256(raw).hexdigest()
        record["git_normalizes_eol_only"] = record["working_sha256"] != record["staged_sha256"]
        if record["git_normalizes_eol_only"]:
            assert (ROOT / record["path"]).read_bytes().replace(b"\r\n", b"\n") == raw
        assert not secret_findings(raw) and not LOCAL_PATH.search(raw) and not RAW_ACCOUNT.search(raw)

    names = git("diff", "--cached", "HEAD", "--name-only", candidate=True).stdout.decode().splitlines()
    assert set(names) == set(paths)
    full = git("diff", "--cached", "HEAD", "--full-index", candidate=True).stdout
    (destination / "complete-staged.diff").write_bytes(full)
    plain = git("diff", "--cached", "--check", candidate=True, check=False)
    windows = git("-c", "core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol",
                  "diff", "--cached", "--check", candidate=True, check=False)
    (destination / "plain-diff-check.txt").write_bytes(plain.stdout + plain.stderr)
    (destination / "eol-policy-diff-check.txt").write_bytes(windows.stdout + windows.stderr)
    assert windows.returncode == 0, "Real whitespace violations in candidate"
    after = git("diff", "--cached", "--raw").stdout
    assert before == after, "Actual staging area changed unexpectedly"
    baseline_data = git("ls-tree", "-r", "--name-only", "HEAD", "--", "data/").stdout.decode().splitlines()
    baseline_assets = git("ls-tree", "-r", "--name-only", "HEAD", "--", "frontend/src/research/fonts/", "frontend/src/assets/").stdout.decode().splitlines()
    result = {"head": head, "groups": patches, "candidate_files": records,
              "complete_patch_sha256": hashlib.sha256(full).hexdigest(),
              "new_data_or_binary_paths": [], "content_findings": findings,
              "plain_staged_diff_check_exit": plain.returncode,
              "eol_policy_staged_diff_check_exit": windows.returncode,
              "actual_index_unchanged": before == after,
              "already_tracked_data_paths": baseline_data,
              "already_tracked_font_image_paths": baseline_assets,
              "public_commit_gate": "NO-GO for current parent tree/history pending rights/release-base review",
              "scope": "Explicit new source delta only; no actual index staging, commit, branch rewrite or publication."}
    (destination / "audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"candidate_files": len(records), "groups": patches,
        "actual_index_unchanged": before == after, "content_findings": findings,
        "plain_check": plain.returncode, "eol_policy_check": windows.returncode,
        "already_tracked_data_paths": len(baseline_data), "public_commit_gate": result["public_commit_gate"]}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Provide a new exclusive review directory outside source artifacts.")
    prepare(sys.argv[1])
