# Phase 10 - Reproducibility and local demonstration guide

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Saved-evidence demonstration, verification and scientific replay are distinct activities. Phase 10 verifies existing results without new fits/interventions. Never overwrite historical output or change labels/checksums to satisfy tests.

## Source and environment

Current source is local `feature/phase9-graph-explorer`, HEAD `2fc9a729efb015029a559c6c2c0f71814ec4e662`, plus preserved Phase 9/current Phase 10 changes. HEAD alone is insufficient: the final inventory records file hashes. The published baseline does not contain unpublished Phase 9/10 work. No commit/push occurred.

Observed environment: Windows, Python 3.12.10, Node 24.19.0. Optional `backend/requirements-research.txt` includes original backend/report-test requirements, psutil 7.2.2 and `constraints-research-v1.txt` with 56 observed dependency versions. This is a Windows closure, not hashed wheels or a universal lock. Installed-environment resolver dry-run passed; a full clean Python/cross-platform wheel installation was not executed. Historical manifests retain their own environments for bitwise scientific replay.

Fresh disposable `npm ci --offline` installed 146 packages in 21 s, exit 0, preserving manifest/lock bytes. Its Vite is locked to 8.3.0; prior unsaved tooling installed 8.3.5 in the working test installation. Bundle sizes differ slightly despite unchanged application source. Use the fresh lockfile build as installation evidence; do not call the difference an improvement. Development-only Playwright 1.64.1 is installed separately without changing protected package files.

## Required inputs

- Supplied canonical IBM transactions/labels retain exact protected bytes. Active and label-file populations are distinguished.
- PaySim retains both 774/2,606-positive identities and 1,832 disagreements; a legacy loader preference does not resolve provenance.
- The catalog pins 34 saved payloads/manifests; `dataset_report_runtime_assets.json` lists 35 files including the catalog. Ignored directories alone do not constitute a release package.
- Private graph indexes/manifest are under `data/results/v3/phase9-topology-v1/`. Their source hashes, aggregation and fixed 600-account scope are in the Phase 9 report. Do not enlarge the scope or rebuild successful outputs during verification.
- The publication checkout intentionally omits25 of33 Phase6C evidence-package members, including table_B_features.json and supporting_artifacts.json. The earlier `outputs/GraphFin-main` archive remains available: all33 package members and173 supporting references were hash-verified read-only with no mismatches. These assets were not copied into Git. The original manuscript source remains missing; archive integrity is not a new replay.

## Bounded startup and production-style local preview

From repository root, in an isolated environment:

```powershell
python -m pip install -r backend/requirements-research.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --lifespan off
```

This skips legacy startup preloads only. Catalog/PDF/index paths still validate their own evidence. Legacy runtime datasets may be empty until explicitly loaded. Normal lifespan was also exercised in a disposable copy and performed a costly PaySim feature/label preload; it does not train Isolation Forest, but is unnecessary for a saved-evidence presentation.

In another terminal:

```powershell
cd frontend
npm ci
$env:VITE_RESEARCH_API_URL='/'
npm run dev -- --config vite.research.config.ts
```

Default URL: `http://127.0.0.1:5173/GraphFin/`. Phase 10 used development port 5190 to avoid existing tabs. The explicit API override selects the local `/api` proxy.

```powershell
$env:VITE_RESEARCH_API_URL='/'
npm run build -- --config vite.research.config.ts
npm run preview -- --config vite.research.config.ts --host 127.0.0.1 --port 4190
```

The fresh lockfile build was served separately on 4191. `/GraphFin/` is verified as the current subpath, not an assumption that a production host has been selected. Other hosts/origins require configuration and access review. Existing Actions uses the default legacy build, and `.env.production` has a remote API fallback; do not dispatch it or accidentally use it as the local research setup.

A separately authorized first-time local setup may run `python backend/scripts/build_graph_explorer.py` once if the versioned output does not exist. It refuses existing output, preserves the fixed scope and does not fit models. Phase 10 reused existing indexes. Verify dataset permissions before transferring source/index assets.

## Safe tests and evidence outputs

Tests reset persistence and must use disposable copies:

```text
python backend/scripts/verify_phase2.py OUTSIDE_REPO_SCRATCH -- backend/tests/test_health.py backend/tests/test_startup_resilience.py backend/tests/test_phase7_research_api.py backend/tests/test_dataset_report_pdf.py backend/tests/test_phase9_graph_explorer.py -q
python backend/scripts/verify_phase2.py ANOTHER_SCRATCH -- backend/tests/test_phase10_release_validation.py -q
python backend/scripts/audit_release.py --output UNUSED_AUDIT.json
python backend/scripts/verify_final_api.py --base http://127.0.0.1:8000 --output UNUSED_API_EVIDENCE.json
```

The API probe accepts only HTTP localhost URLs without credentials, uses bounded GET/preflight checks, and writes exclusively. The audit redacts credential-pattern matches, records local-object/preservation/license evidence and does no model work. Neither is a full penetration, vulnerability or remote-branch audit.

```powershell
cd frontend
npm install --no-save --package-lock=false @playwright/test@1.64.1
cd ..
python backend/scripts/prepare_final_browser_tests.py
cd frontend
$env:TEST_URL='http://127.0.0.1:4191/GraphFin/'
$env:TEST_REPORT='AN_UNUSED_BROWSER_REPORT.json'
npx playwright test --config playwright.final.config.ts dashboard.spec.ts dataset-report.spec.ts graph-explorer.spec.ts graph-real.spec.ts final-system.spec.ts
npm run lint
```

Preparation creates an exclusive ignored `.phase10-tests` copy, redirecting historical output paths only. It does not substitute application behavior or live data. This preserves old Phase 8/9 evidence. Initial/final execution hashes record source changes made to the new workflow test during debugging. Use a new validation workspace for another complete run. The selection has 62 distinct browser cases; repeat/debug runs are not additional independent cases.

The npm lint command is **oxlint**, not ESLint; no ESLint run is claimed. Component/interactions are exercised through Playwright; no separate React component runner is configured. Unsaved tooling can change the installed tree; use `npm ci` in a clean application directory for the authoritative lockfile build.

## Read-only scientific reconstruction

```text
python backend/scripts/prepare_manuscript_evidence.py NEW_EXCLUSIVE_DIRECTORY
```

This checks pinned labels, held-out membership/counts and sklearn AP for 84 existing saved-score rows, then derives tables. It does not fit, recalibrate, tune a seed or modify original evidence. Phase 10 output is `docs/research/manuscript/phase10-v1/`, with full precision and source hashes. Six-split SD uses n-1; three-model-seed summaries remain separate.

Existing Phase 6C reports record exact 5K/50K scientific replay. Phase 10 does not repeat those jobs. Do not launch benchmark preparation/fits or CREST workers to refresh the dashboard. A separately authorized future replay needs a new namespace and dataset/label/configuration/code/environment/seed identities. Same-input reproducibility is not external validation.

## Expected states and limits

The overview has 84 stored method evaluations. E0-E5 are versioned; E6_BASE remains calibration-only. Six split seeds differ from three model seeds. Unsupported CIs, PaySim metrics and missing diagnostics stay unavailable. The graph supports only approved IBM snapshots, caps disclosure/work and clears expired state. Temporal subwindows suppress full-snapshot score/diagnostic annotations.

PDFs are deterministic four-page projections with hashes/version metadata. Their PDF date `2000-01-01` is an invariant determinism sentinel, not the research/download date; execution timing is in the validation record. They are not tagged PDF/UA documents.

No screenshot, test pass or professional report resolves label lineage, establishes CREST superiority, grants redistribution, certifies anonymity or makes the manuscript submission-ready. The separate readiness report retains those decisions.
