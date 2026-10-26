# Phase 10T — Private source-only distribution review

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

25 October 2026. **Phase 10T preparation/review: COMPLETE within the bounded scope below. Public publication: NO-GO pending owner and distribution clearance.** Successful installation/tests do not certify ownership, anonymity, full scientific reproducibility or public hosting.

## Purpose, recovery and package location

Continued from Phase 10S and Phase 10R security/licensing findings. The existing repository remains the authoritative research workspace; the private package is a reduced read-only research interface. Its scope deliberately excludes legacy operations and full ML training/replay, rather than silently requiring omitted artifacts.

Final clean candidate, outside the original repository:

`C:\Users\hariharasuthan\Documents\Codex\2026-10-19\you-are-my-senior-machine-learning\work\phase10t\source-only-distribution-v1`

Original checkout:

`C:\Users\hariharasuthan\Documents\Codex\2026-10-19\you-are-my-senior-machine-learning\work\pdf-reports\publish`

The candidate is a local, unshared review directory, not a created Git repository, remote, deployment or secure-storage certification. No `.git` directory/history was copied or initialized. No claim is made that inherited filesystem ACLs were hardened for multiuser access.

The separate `work/phase10t/private-source-candidate-v1` is the **validation working copy**, retaining `node_modules` and generated frontend `dist` from testing. It is NOT the release payload. The final `source-only-distribution-v1` copies only the explicit allowlist; no dependency/build/test-output directory is in it. Validation virtual environment, logs, JUnit and HTTP process records are siblings under `work/phase10t`, not payload files. Existing successful checks were recovered, not restarted on resume. The last outstanding build completed successfully.

## Exact inventory and the 67/68 discrepancy

The final package has **68 files, 401,895 bytes**. The first disclosure scan covered 67 source/configuration/document/test payload files. The additional file is generated **`SOURCE_MANIFEST.json`**, added to inventory those 67 hashes. It is legitimate metadata, not a hidden dataset or dependency. The final disclosure scan explicitly inspected all **68**, including the manifest. No package content changed after that final scan.

The JSON manifest excludes its own hash to avoid self-reference. Its external SHA-256 is:

`8fbad845c5afc75c03b7242645749a25abdfad24a73a9a5d97cef0a48ffebee1`

`10T_candidate_file_manifest.md` independently lists all 68 relative paths, classifications/purposes, origins, justifications, licensing status, hashes and disclosure results. Fifty-five original-source origins comprise **43 exact copies and 12 candidate-only adaptations**; 12 independently authored files and the JSON inventory complete the 68. It also lists all 377 excluded original files and dependency-reference inventories. No file has an implicit include decision.

Proposed layout:

```text
source-only-distribution-v1/
  LICENSE, README.md, SOURCE_MANIFEST.json
  .gitignore, .env.example, pytest.ini
  backend/
    requirements.txt, constraints-research-v1.txt
    app/research_demo.py
    app/core/                  # minimal package paths/logging/exceptions
    app/api/routes/            # research, graph, PDF read-only interfaces
    app/schemas/               # research/graph contracts
    app/services/              # existing serving/index/PDF implementations
  frontend/
    package.json, package-lock.json, tsconfig*.json
    index.html, vite.config.ts, .env.example
    src/main.tsx, src/ResearchApp.tsx, src/research/
  tests/test_source_package.py
  docs/                       # acquisition, fixture origins, changes, prior exposure
```

## Inclusion, exclusion and candidate-only adaptations

Included: reviewed project application source/contracts, inert package initializers, exact lock/version references, loopback templates, newly authored safe tests and factual setup/acquisition/limitations documentation. The root MIT notice is retained.

Excluded: every raw/processed transaction or label file; account maps, memberships, saved scores/results and catalogs; graph indexes/private manifests; model/serialized artifacts; PDFs/DOCX/previews; historical manuscript/result reports; unknown-origin images/icons; all font binaries/notices; deployment automation and remote `.env.production`; old fixtures/tests and operational/training/replay code outside the reviewed serving closure. No copied dependency source/binary or native wheel is in the final package.

Candidate-only changes are explicit in `docs/PACKAGING_CHANGES.md` and the manifest: direct research UI entry; no legacy workspace lazy import/link or legacy global CSS; no font-face declarations; minimal HTML with the exact title and no imported icon; loopback Vite dev/preview/proxy; inert Python initializers; minimal core path/logging settings without parent `.env` search or directory creation; reduced serving/test/index requirements and independent tests. The original application files, ML algorithms and results were not modified. These adaptations do not claim original-dashboard pixel equivalence or full feature parity.

## Complete disclosure and fixture review

Final `disclosure_scan.json`: **68 files**, zero canonical identifier matches, zero credential/absolute-user-path pattern findings, zero Python parse errors, zero forbidden payload types, zero Git/link/junction findings. File hashes match the complete allowlist/manifest, including the externally pinned JSON inventory. All files are UTF-8 text; no unreviewed binary is bundled.

The local non-disclosing comparison read identifier columns in canonical IBM/PaySim/sample CSVs and compared **1,251,632 unique account/transaction identifiers** against candidate tokens and exact Python string constants. Original identifier values and raw records were not output or copied. This is a bounded exact-token check, not proof against every possible transformed/encoded record or unknown source. Source schemas/constants were additionally classified by role: field names, algorithm versions, opaque provenance hashes and source-authored decorative SVG coordinates are not embedded transaction samples or topology dumps.

`tests/test_source_package.py` is independently authored. Its only transaction fixture constructs three fictional edges using the `PH10T_SYNTHETIC_` namespace, amounts 3/5/7 and timestamps on 1 January 2000. Expected aggregation is derived directly from those constants. No historical test, sampled row, model score or private graph is imported. Temporary CSV/SQLite files are created only beneath pytest's external temporary directory. Origins and documentation-network values are explained in `docs/FIXTURE_ORIGINS.md`. No fake experimental results were generated.

The dependency trees/build output are outside final scan/payload by design. They are validation tooling, not a claim that all installed third-party bytes have been legally cleared for redistribution. Final candidate inspection verifies there are no symlinks escaping to them or to the original workspace.

## Licensing, attribution and remaining clearance

|Component|Evidence / decision|Obligations and unresolved points|
|---|---|---|
|Selected project code and source-authored vector markup|Existing root MIT notice, copyright 2026 Hariharasuthan; no separately vendored third-party source identified in this allowlist|Preserve MIT notice. Owner must confirm contribution/employer/institution rights before publication; a declaration is not proof of every author's authority.|
|Independent package files/tests|Authored for this review, no copied data or third-party template|Retain project notice; obtain owner's distribution approval.|
|Fonts|Original IBM Plex Mono, Pixelify Sans, Silkscreen carry OFL 1.1 notices, but exact binary provenance was not reauthenticated|All omitted, including font-face declarations. No assertion that OFL prohibits bundling; reintroduction needs byte-source/notice review.|
|Legacy icons/images/previews|Origin/redistribution evidence remains UNCLEARED|Omitted. No preview PDF, image/logo file or external icon pack copied.|
|PDF source/resources|Existing generator uses ReportLab primitives and standard Times/Helvetica names; no bundled font/preview/template binary|Generator remains MIT-declared project code; ReportLab and runtime font/native resources retain their own conditions. No generated report included.|
|Python packages|Fresh isolated install resolved 30 distributions; `installed-python-licenses.json` records versions, declared licenses and notice paths|Only requirements/constraints references included. Actual wheels/native-library redistribution and a complete SBOM/license certification remain UNCLEARED; installed dependencies are not bundled.|
|Frontend packages|Exact original lock: 189 non-root entries, including optional platforms; Windows install added 146|Only manifests included. Per-entry license declarations are listed in the file review; preserve applicable notices on actual build redistribution. MPL/attribution/native obligations are not waived by registry availability.|
|Datasets and derived artifacts|Exact local provenance/grants and PaySim labels unresolved|All omitted; acquisition/limitations documented. Do not infer redistribution clearance from synthetic origin or public availability.|

Primary sources reconfirmed: [IBM AML-Data](https://github.com/IBM/AML-Data) separates Apache-2.0 source and CDLA-Sharing-1.0 data; [PaySim simulator](https://github.com/EdgarLopezPhD/PaySim) identifies GPL-3.0 code and a separate dataset link; [official OFL text](https://openfontlicense.org/open-font-license-official-text/) gives font-bundling conditions. None authenticates all supplied transformed research bytes. Where an actual payload grant could not be established, the relevant asset was excluded rather than assumed approved. Public release remains withheld while ownership and actual distribution obligations are unresolved.

## Installation, static checks and actual test evidence

|Check|Executed outcome|Evidence under `work/phase10t`|
|---|---|---|
|Fresh Python venv bootstrap|Initial sandbox temp-path permission failure; completed using a writable task-local TEMP/TMP|Bootstrap tool outputs; no original environment modified|
|Python dependency installation|Initial sandbox resolver/index attempt failed; authorized network retry installed all 30 constrained distributions, exit 0. Constraints were not relaxed.|`python-install-initial.log`, `pip-index.log`, `python-install-network.log`, exit files, `python-freeze.txt`|
|Python dependency consistency|`pip check`: exit 0, no broken requirements|`pip-check.log`, `pip-check-exit.txt`|
|Frontend install|Final ordinary `npm ci --offline`, scripts enabled: 146 packages, exit 0, 39.71 s wall time. Earlier successful scripts-disabled install retained separately.|`npm-install-final.log/json`, initial log/exit|
|TypeScript and production build|`npm run build` executes `tsc -b && vite build`: exit 0, 8.62 s wall time; Vite portion 376 ms|`frontend-build-final.log/json`; previous successful build retained|
|Frontend lint|`npm run lint` / oxlint: exit 0|`frontend-lint-final.log`, exit file|
|Python static parsing / disclosure|All candidate Python parses passed; complete payload text/identifier scan passed within documented limits|`disclosure_scan.json`, `scan.py`|
|First completed synthetic suite|34 passed, 1 failed: newly authored test incorrectly required 503 for missing diagnostics. Existing service deliberately returns empty/unavailable HTTP 200.|`tests-elevated.log/xml/json`|
|Corrected validation-copy suite|36 passed, 0 failed/errors/skipped; exit 0; pytest 4.98 s|`tests-final.log/xml/json`|
|Final clean-package suite|**36 passed, 0 failed, 0 errors, 0 skipped; exit 0; pytest 4.79 s**, wrapper 7.81 s|`tests-clean.log/xml/json`|
|Actual HTTP/proxy smoke|**8/8 expected outcomes**, script exit 0, 4.05 s; both task-owned processes stopped|`http-smoke.json`, backend/frontend logs|

These are 36 distinct synthetic cases, not 72 independent tests obtained by adding repeated runs. No original full data-dependent suite or ML benchmark was rerun. The suite covers health/title, explicit missing evidence, diagnostics/graph unavailability, method/peer/Host/Origin guards, legacy-route absence, no eager legacy imports/data directory, path traversal, fictional graph aggregation/no-overwrite/checksum behavior, nonfinite metrics and missing-value formatting. One Starlette TestClient deprecation warning recommends `httpx2`; the existing environment was retained and the warning is not a failed test or an unnoticed dependency upgrade.

The source package has no cached bundle or installed dependencies. Frontend install/build occurred in the separate validation copy from the same hash-matched frontend source/lock; the clean backend tests ran directly from the final clean directory using only the new external virtual environment. No original private data path, symlink, catalog or `.env` was supplied.

## Actual HTTP outcomes and scope

The bounded smoke used only child processes created by its helper: clean backend on loopback 8000, matching validation frontend preview on loopback 5362, then terminated both. Preflight refused occupied ports rather than contacting/stopping another service. The existing user preview on 4190 was not touched. Intentional process termination exits are not test failures.

|Proxied request|Observed|
|---|---|
|`/GraphFin/`|200; built HTML served|
|`/api/v1/health`|200; restricted profile|
|`/api/v1/research/overview`|200; unavailable evidence, no datasets, zero completed runs|
|`/api/v1/research/datasets`|503; missing evidence|
|`/api/v1/research/diagnostics`|200; empty list explicitly unavailable|
|`/api/v1/graph-explorer/catalog`|200; unavailable graph entries, no disclosed topology|
|`/api/v1/research-reports/datasets/ibm-5k/report.pdf`|503; no fabricated PDF|
|`/api/v1/datasets`|404; operational route absent|

This is actual HTTP/proxy validation, not a new browser visual/accessibility audit. No result-bearing PDF or live graph is claimed functional without its separately authorized evidence. The existing read-only app rejects mutations and remote peers; it is not authentication or permission to tunnel publicly.

## Windows environment distinction

An initial sandboxed API test run stalled and was interrupted; no successful test result is claimed for it. A minimal application-free `asyncio.run(asyncio.sleep(0))` probe also timed out after 15.02 s inside the sandbox, while the identical external probe passed in 0.36 s. The bounded outside-sandbox suites then completed. This isolates an environmental asyncio limitation from the separate test-expectation failure. The probe does not justify ignoring future application timeouts. No task-owned Python process remained after the interrupted run check.

## Evidence-absent functionality and unsupported work

Supported: source installation/build/static checks, restricted loopback startup, health, research UI shell, explicit empty/unavailable states, safe independent tests and fictional index aggregation. No hidden raw dataset, prior frontend bundle, original account map or Git history is needed for that limited mode.

Unsupported in this package: original operational workspace/upload/training, original E0–E5 experiment execution, CREST detector evaluation, cross-dataset transfers, scientific replay, genuine saved-score charts, data-bearing graph/PDF exports, and complete original-environment/native-binary reproduction. Existing algorithm/result source in the original is preserved, not substituted. Font appearance differs because bundled fonts are omitted.

`docs/DATA_ACQUISITION.md` identifies authoritative acquisition sources, applicable terms/receipt checks, original checksum-manifest location, owner-provisioned conversion/protocol material and separate artifact authorization. It preserves the unresolved PaySim 774/2,606-positive conflict and 1,832 disagreements, transductive feature scope and incomplete E6 evaluation. Downloading another upstream dataset is not promised to reproduce the supplied hashes. No automated downloader, label selection or checksum bypass was added.

## Original repository preservation and prior exposure

The pre-phase snapshot covers **432 pre-existing files** (source/docs plus the three ignored topology artifacts). Final read-only verification accounts for those exact hashes and separately allows only the two requested new Phase 10T Markdown reports in the original checkout. All **87 protected originals** and **35 pinned reporting assets** are checked against their existing hash manifests; historical results and Phase 9/10 changes in that snapshot remain preserved. Git HEAD remains `2fc9a729efb015029a559c6c2c0f71814ec4e662`; refs and actual staging entries remain unchanged. Existing alternate-index file bytes are compared as well. `final_preservation.json` records exact results and ordinary `git diff --check` exit status after document creation.

No commit, push, repository creation, remote settings change, history rewrite or deployment command was run. No re-fetch or rescan of remote histories was needed: Phase 10S's recorded branch-tip/history evidence is cited as that audit's observation, not a freshly certified remote state. Its feature branch already exposes tracked transactions/labels/identity-bearing artifacts, including historical-only transfer files. Main/pages remote-only contents, forks and caches remain incompletely assessed.

`docs/REMOTE_HISTORY.md` documents this separately. A clean package does not retract prior copies. Owner-led remediation should authenticate source grants, classify prior exposure, review visibility/access and any confirmed credential response; an explicitly approved coordinated rewrite needs private archives, affected-ref/collaborator planning and identity mapping. A rewrite cannot erase forks/caches. No such change is performed here.

## Decisions and required owner approvals

|Decision|Status|Conditions / limits|
|---|---|---|
|A. Private candidate preparation|**GO**|68-file independently reviewable local package complete; no history or evidence payloads included|
|B. Local synthetic test/demo use|**GO**|Restricted loopback and evidence-absent scope only; 36 tests and 8 HTTP outcomes verified|
|C. Creating a new source-only repository|**CONDITIONAL GO**|Owner must approve this reduced exact allowlist, source/contribution ownership, notices and intended private repository/access policy. No repository is created automatically.|
|D. Public source publication|**NO-GO**|No approval to publish; ownership, actual dependency/bundle distribution obligations and any future asset provisioning require explicit clearance. Tests are insufficient.|
|E. Previously exposed remote history remediation|**NO-GO for execution without separate authorization**|Owner must choose and authorize a remediation plan; existing history remains uncleared, and this package does not repair it.|

Unrestricted deployment and IEEE submission remain NO-GO. Required decisions include accepting the reduced operating scope; attesting rights for selected project/contribution code; approving exact source-only repository preparation/access; clearing any later binary/font/icon/data additions; and separately authorizing any old-remote remediation. No request for automatic publication, commit or rewrite is inferred.

The private distribution review is complete; outstanding permission/publication/remediation gates remain explicit. No further development phase is started.
