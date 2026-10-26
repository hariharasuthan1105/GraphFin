# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

**Phase 10R controlled demo:** use the isolated loopback-only `backend.app.research_demo:app` entry described in [controlled-demo readiness](docs/research/10R_controlled_demo_readiness.md). Legacy raw/training APIs are deliberately absent from that profile. Earlier Phase 10 reports remain historical evidence, not the current controlled-startup command.

GraphFin is a reproducible research application for retrospective account anomaly ranking on supplied synthetic transaction graphs. It combines established graph features and Isolation Forest with versioned experiments, explicit dataset/label identities, a read-only research dashboard, a bounded graph explorer and institutional PDF exports.

**Scientific status:** CREST detector and explanation superiority are unsupported. Anomaly scores are not calibrated fraud probabilities. Same-input replay establishes reproducibility, not external validity. IBM label lineage is partially verified; PaySim's two label sets remain unresolved. This is a local research demonstration, not a certified financial-crime detection system.

## Current source and publication state

The last verified published feature branch is `feature/institutional-dataset-pdf`, commit `2fc9a729efb015029a559c6c2c0f71814ec4e662`. Phase 9 and Phase 10 are uncommitted local work on `feature/phase9-graph-explorer`. A clone of the published baseline alone does not yet contain the graph-explorer changes described here. No Phase 10 commit, push, merge or deployment was performed.

## Architecture

- Research computation: canonical transactions -> directed NetworkX graph -> ordered features -> source-training-only baseline fitting -> held-out saved scores/metrics -> immutable manifests.
- Saved-evidence serving: FastAPI's `/api/v1/research/*` reads checksum-pinned JSON, with separate dataset PDF and graph namespaces.
- Research frontend: React/TypeScript/Vite with existing Tailwind, D3 and Recharts dependencies. The additive research Vite configuration preserves the original frontend entry.
- Graph serving: offline SQLite index -> bounded GET query -> opaque session references -> deterministic validated Web Worker layout. No model fitting, score recomputation or centrality calculation is triggered by research UI requests.
- Legacy workspace: preserved operational upload, graph, feature, training, simulation, evaluation, report and tax interfaces. It is separate from the validated saved-evidence research path and is not cleared for public exposure.

## Research scope

The canonical E4 vector has19 columns: six structural, eight behavioral and five temporal. Four egonet/circular columns are appended to the23-column exported matrix for E5. Columns include exact/near-exact redundancies; they are not19 independent signals.

|Method|Frozen definition|
|---|---|
|E0|graph-six, signed training z-score maximum, `e0-source-signed-zero-v2`|
|E1|graph-six Isolation Forest|
|E2|graph + behavior,14 features|
|E3|graph + time,11 features|
|E4|all canonical19 features|
|E5|four project-specific egonet/circular heuristics; not a full Graphomaly reproduction|
|E6_BASE|historical empirical-CDF calibration of frozen E4; no intervention evidence|

Six account split seeds42/123/7/2024/99/555 at model42 are distinct from model-seed13/42/101 evidence at split42 for E1/E4. Report non-interpolated **Average Precision**, sample SD and retrieval counts accurately. Graph features use the full observation graph: evaluation is transductive entity holdout. Do not pool historical scoring versions or interpret split SD as a confidence interval. The original full intervention E6 benchmark remains incomplete. Of24 saved diagnostic rows,13 have actual intervention evidence; their coverage does not establish superior explanations.

|Supplied dataset|Active accounts|Retained events|Label status|
|---|---:|---:|---|
|IBM AML5K|5,000|31,463|20 positives; partially verified endpoint-involvement lineage|
|IBM AML~50K|49,992|353,850|249 positives;50,000 label-file rows include8 inactive accounts|
|PaySim|547,686 label-population accounts|Not exposed as a compatible benchmark by the research catalog|774 vs2,606 positives;1,832 disagreements; unresolved|

The graph explorer supports only IBM tiers:5,315/65,439 directed pairs in the full source snapshots, but a fixed600-account approved lens and at most250 nodes/500 edges per response. PaySim graph topology is unavailable. Amount units and synthetic timestamps do not establish real-world currency or financial misconduct. See [label lineage](docs/research/06C_label_lineage.md).

## Installation and bounded local demonstration

Use the current working tree, Python3.12 and a Node version satisfying the locked Vite engine requirement (`^20.19.0 || >=22.12.0`); Phase10 observed Python3.12.10 and Node24.19.0 on Windows. Dependency constraints describe this environment, not universal wheel hashes. For an isolated environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-research.txt
```

The optional research requirements include original backend/report-test requirements, an observed dependency-closure constraint file, and the `psutil` dependency required by research tooling. Original backend requirements remain unchanged. Historical manifests retain their own experiment environments; a new installation is not a guarantee of cross-version bitwise ML replay.

Start the **saved-evidence demonstration** on loopback:

```powershell
python -m uvicorn backend.app.research_demo:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

The restricted entry mounts only saved-evidence, graph, PDF and health routes, with no legacy dataset preloads or operational routers. It rejects nonloopback peers/Host headers, unapproved browser origins and non-GET methods. Docs are disabled by default. Keep the frontend on loopback and use its same-origin API proxy. This is a controlled local boundary, not user authentication or approval for public hosting. The full `backend.app.main:app` remains available for separately trusted operational use and is not the controlled-demo command.

In a second terminal:

```powershell
cd frontend
npm ci
$env:VITE_RESEARCH_API_URL='/'
npm run dev -- --config vite.research.config.ts
```

Open `http://127.0.0.1:5173/GraphFin/`. The explicit API override selects the local `/api` proxy. For a build/preview:

```powershell
$env:VITE_RESEARCH_API_URL='/'
npm run build -- --config vite.research.config.ts
npm run preview -- --config vite.research.config.ts --host 127.0.0.1 --port 4190
```

The existing `/GraphFin/` base path is verified for this local build; no production host is selected. The current GitHub Actions workflow uses the default legacy build command, so it must be reviewed before any future research-dashboard deployment. CORS is not authentication.

Pinned research JSON assets and the supplied local source files are required. Graph indexes are private generated artifacts under `data/results/v3/phase9-topology-v1/`, ignored by Git. A fresh authorized local setup can prepare the index once with `python backend/scripts/build_graph_explorer.py`; it refuses existing output and does not fit models. Do not delete/rebuild existing research evidence merely to get a passing test. Review dataset permissions before transferring these assets.

## Navigation and reports

Research routes: `#/overview`, `#/datasets`, `#/experiments`, `#/comparison`, `#/seeds`, `#/reproducibility`, `#/diagnostics`, `#/limitations`, `#/graph`. `#/workspace` opens the preserved legacy interface.

Dataset Explorer -> select an approved dataset -> **Download Dataset Report (PDF)** exports a formal four-page document. It uses actual supported label counts and saved AP summaries; unsupported PaySim performance stays unavailable. Reports are deterministic, contain evidence hashes/version metadata, and are not tagged PDF/UA documents. Graph references expire and must not be saved as durable account identities.

## Validation

Never run destructive persistence tests in the working repository. Use the existing disposable-copy runner:

```text
python backend/scripts/verify_phase2.py OUTSIDE_REPO_SCRATCH -- backend/tests/test_phase7_research_api.py backend/tests/test_dataset_report_pdf.py backend/tests/test_phase9_graph_explorer.py -q
```

Existing research runners can fit models or perform expensive interventions; they are not needed to demonstrate or validate the saved-evidence UI. Phase10 did not launch them. Browser tooling remains development-only, preserving original package manifests:

```powershell
cd frontend
npm install --no-save --package-lock=false @playwright/test@1.64.1
cd ..
python backend/scripts/prepare_final_browser_tests.py
cd frontend
$env:TEST_URL='http://127.0.0.1:4190/GraphFin/'
npx playwright test --config playwright.final.config.ts
```

The browser preparation creates an exclusive ignored `.phase10-tests` copy and substitutes artifact output paths only, preserving previous validation evidence. Use a new validation workspace for another complete run. Unsaved tooling installation can alter the installed dependency tree; `npm ci` restores the application lockfile tree. See the [reproducibility guide](docs/research/10_reproducibility_guide.md) and [final validation ledger](docs/research/10_final_system_validation.md) for exact scope/counts and observed failures.

## Security, licensing and release status

Keep the full application loopback-only for demonstration. Legacy APIs expose raw identities, mutation/training capabilities and expensive work without application authentication. Pseudonymized graph structure can be reidentified; the fixed lens is not formal anonymity. Source research files can also contain synthetic raw IDs. Do not enter real customer information, upload untrusted model files or expose this complete backend publicly without a separate access/hosting review.

The root MIT license covers project code to the extent owned by the licensor. It does not establish rights to third-party datasets, fonts or dependencies. Font notices are retained under `frontend/src/research/fonts/`. IBM upstream distinguishes code licensing from data licensing; exact permission for these transformed inputs remains unverified. PaySim simulator licensing does not resolve the supplied dataset's license/label provenance. See [security](docs/research/10_security_and_privacy_review.md), [third-party notices](docs/research/10_third_party_notices.md), and [release readiness](docs/research/10_release_readiness.md). No public release/deployment or IEEE acceptance certification is claimed.

## Reviewer materials

- [Final integration and validation](docs/research/10_final_system_validation.md)
- [Security/privacy assessment](docs/research/10_security_and_privacy_review.md)
- [Release decision and proposed commit plan](docs/research/10_release_readiness.md)
- [Reproducibility guide](docs/research/10_reproducibility_guide.md)
- [Versioned IEEE-style review draft](docs/research/manuscript/phase10-v1/manuscript.md)
- [Presenter script and screenshot checklist](docs/research/10_demo_plan.md)
- [Phase9 graph contracts and evidence](docs/research/09_interactive_graph_explorer.md)

Closest prior graph-feature/Isolation-Forest overlap: Dumitrescu et al., IEEE Access2022, DOI10.1109/ACCESS.2022.3170467. GraphFin is presented as an auditable empirical system with transparent negative findings, not the first graph-based financial anomaly detector.
