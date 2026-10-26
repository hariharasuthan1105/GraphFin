# Phase 10 - Final system validation

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Date: 25 October 2026. Scope: final integration, review, verification and documentation. No new detector, ML fitting/replay, calibration, CREST experiment, label change, commit, push, merge or deployment was performed. Normal startup did execute its existing legacy feature preload in a disposable copy; this is documented below and excluded from the bounded demonstration command.

## Recovery, architecture and integration inventory

Verified source: `work/pdf-reports/publish`, local branch `feature/phase9-graph-explorer`, HEAD `2fc9a729efb015029a559c6c2c0f71814ec4e662`. Read-only remote heads confirm the published PDF feature still points to that commit. The default branch was not reset or merged. All inherited Phase 9 work remains uncommitted and is preserved.

Phase 10 snapshot contains 401 existing files: tracked/untracked application/document sources plus all available data/research/v2/v3 files, excluding dependency/build caches. It includes the Phase 9 implementation and all available historical results/indexes. Final comparison distinguishes intentional README/ignore edits from preserved Phase 9/scientific files. The exact source/generated inventory is in `10_integration_inventory.json`; test/download/performance records are under task `work/phase10/`, not historical experiment directories.

|Component|Verified functionality|Boundary|
|---|---|---|
|Research computation|Versioned E0-E5, saved scores, separate splits/model seeds, immutable manifests|Existing evidence; no Phase 10 fits or algorithm changes|
|Research API|Fourteen GET projections, compatible population/version checks, missing/tampered evidence handling|Saved JSON only; not upstream-label authentication|
|Dashboard|Original eight research pages, explicit availability/provenance, legacy entry|Additive research Vite config required|
|Graph explorer|Three GET endpoints, real indexed directed topology, opaque refs, bounded deterministic worker/interaction|Fixed 600-account lens, 250 nodes/500 edges, process-local sessions|
|PDF|Three datasets, deterministic institutional four-page exports|Supported catalog aggregates only; no invented histogram/PaySim results|
|Legacy workspace|Entry remains available; operational backend retained|Unauthenticated mutable/expensive surface; not publicly cleared|

Graph totals remain 5,000 accounts/5,315 directed pairs and 49,992/65,439. Source rows/retention, directed sums/counts/timestamps and all index hashes were verified in Phase 9 and preserved here. Temporal subwindows suppress full-snapshot score/diagnostic annotations. Repeated sessions cannot enlarge the approved pool, but can disclose more within it; pseudonyms do not guarantee anonymity.

New Phase 10 functionality is verification/tooling/documentation, not a replacement application: redacted local release audit; localhost-only read probe; exclusive saved-score table derivation; isolated browser-output preparation; optional research dependency constraints; meaningful tooling regressions and a complete workflow test. No production application source was changed in Phase 10.

## End-to-end workflow A-R

The actual API used a disposable copy, with normal startup on loopback. The working research development command started successfully on 5190. Production previews used 4190, then the fresh lockfile build on 4191. Explicit local API override retained the `/api` proxy and `/GraphFin/` base. No production host was selected.

|Required step|Evidence|
|---|---|
|A Startup|Normal disposable API startup completed; additive Vite dev started; clean lock install/build/preview executed. Bounded `--lifespan off` startup verified separately.|
|B-D Overview/dataset|Actual 84-evaluation overview, IBM 5K metadata and partially verified lineage visible.|
|E Model comparison|Actual same-split E0-E5 and separately identified E6_BASE, all supported methods visible.|
|F Seed axes|Six-split view and separate E1/E4 model-seed/ranking-overlap view.|
|G-H Experiment/replay|E4 details, metrics/provenance/held-out rankings and replay view.|
|I CREST|Available `crest-001` plus graph available/unavailable records, without superiority claims.|
|J-M Graph|Actual E4 ranked link, approved session, bounded source neighborhood, node and directed-edge inspection, compatible saved diagnostics.|
|N-O Dataset/PDF|Graph report link retains selected dataset; genuine downloads for all three approved datasets.|
|P Open/inspect PDFs|All 12 pages rendered with native Poppler, text/metadata/numerics parsed and rendered contact sheets visually inspected.|
|Q Limitations|Research Limitations remains accessible and qualified.|
|R Legacy|Preserved workspace entry opens; no training/upload action performed.|

The complete live workflow records no page errors and no mutating API requests. Controlled tests separately cover empty/missing/error/expired states, wrong population/session, unavailable topology/diagnostics and reduced motion/mobile alternatives. Synthetic fixtures are not presented as production records.

Normal startup logs span 19:02:58-19:07:08 with legacy PaySim feature/label preloading, including global feature work. This host-contended interval is not a benchmark or scientific replay. It explains the documented research startup `--lifespan off`, which bypasses preloads only. No expensive centrality or fit endpoint is invoked by saved-evidence UI requests; graph regression spies additionally forbid those calls. Legacy operational actions retain their original capabilities and are not certified by this restriction.

## Scientific integrity

All 84 existing saved AP rows reconstructed exactly, maximum difference 0.0, from pinned score arrays/labels and verified held-out membership. Tables are derived into a new versioned manuscript directory; nothing under historical v2 is rewritten. Means/sample SD and retrieval data retain explicit split/model axes. Historical E0 variants/single-run results are not pooled with `e0-source-signed-zero-v2`; E6_BASE remains a tie-coarsening empirical-CDF calibration, not an intervention detector.

Features use the complete observation graph: transductive entity holdout. Fitting is source-training-only; labels are not used to fit the unsupervised model or tune target transfer. AP is non-interpolated, SD is not a confidence interval, and overlapping splits/graph accounts are not independent samples. Exact historical same-input 5K/50K replay is supported by pinned summaries and existing reports; 25 of the33 Phase6C evidence-package members are not included in the publication subset. The original local archive remains available:33 package members and173 supporting references were hash-verified with no missing/mismatched files. This is read-only archive integrity, not a new refit or independent dataset validation.

IBM lineage stays partially verified; raw flags/authoritative conversion inputs are absent. The legacy loader/log terminology still selects a preferred label file and calls it ground truth; that path is outside the scientifically qualified research projection and remains a release defect, not a resolved provenance decision. PaySim retains 774/2,606 positives and 1,832 disagreements on the same label population, with no preferred definition or compatible detector metrics. Existing label bytes are unchanged.

All 24 saved diagnostic baseline rows match E4 under the Phase 9 identity gate, but only 13 have intervention evidence, representing five distinct account/omission scenarios. Twelve compatible direct comparisons tie. CREST detector and explanation superiority remain unsupported; the original full E6 intervention evaluation is incomplete. Scores are not fraud probabilities and omission responses are not causal evidence of crime. Same-input replay is not external validation.

## Executed test/build ledger

|Executed check|Passed|Failed/errors|Skipped|Blocked final|Duration|Exit/evidence|
|---|---:|---:|---:|---:|---|---|
|Health/startup/research/PDF/graph backend|115|0|0|0|95.79 s|0; `backend/phase2-czwp4ptc/{pytest.log,results.xml}`, `backend-exit.txt`|
|New release tooling backend|5|0|0|0|0.57 s|0; `tool-tests/phase2-vyk_w0yx/{pytest.log,results.xml}`, exit file|
|Fresh-build complete browser selection|62|0|0|0|120.25 s|0; `browser-final.json/log`, `browser-final-exit.txt`|
|Python tool compilation|No syntax errors|0|n/a|0|Not separately timed|0; `python-compile-exit.txt`|
|TypeScript + fresh production Vite build|Passed|0|n/a|0|23.81 s bundling, not full install/type-check|0; `demo/build.log`, exit file|
|oxlint|0 errors,42 legacy warnings|0 errors|n/a|0|Not separately timed|0; `lint.log`, exit file|
|Fresh npm lock install|146 packages installed|0|n/a|0|21 s|0; `demo/npm-ci.log`, exit file|
|Python constrained resolver dry-run|Compatible installed closure|0|n/a|0|Not separately timed|0; `pip-dry-run.log`, exit file; clean-venv install not executed|
|Local API/security/performance probe|34 GET checks +6 concurrent reads; CORS expectations met|0|n/a|0|Per-request samples in JSON|0; `api-probe.json`, approved exit file|
|Saved AP reconstruction|84 rows, max difference0.0|0|n/a|0|Not separately timed|0; `manuscript-evidence.log`, versioned evidence tables|
|Fresh bounded graph profile|8 cases x3 samples; caps verified|0|n/a|0|Raw timings in JSON|0; `query-memory.json`, exit file|
|PDF QA|3 documents/12 pages; saved statistics and byte identities checked|0 observed clipping/raw-ID pattern|n/a|0|Not separately timed|`pdf-qa.json`, `pdf-numerical-qa.json`, native render logs and inspected contact sheets|
|Original experiment archive hashes|33 package members +173 supporting references|0 missing/mismatched|n/a|0|Read-only check|0; `original-archive-verification.json`|

**Phase10 selected test totals:120 distinct backend cases across two runs and62 browser cases in one final selection.** No unresolved failures, skipped tests or environment-blocked selected checks remain. Prior debug/repeat runs are preserved below and are not added to those totals. Nonexecuted formal audits/clean Python installation remain explicit limitations, not passed tests.

Repeated debug runs are not additional independent cases. This is selected application validation, not a claim that every backend test was run. Tests that fit models/run research jobs were deliberately outside Phase 10. No separate React component runner or ESLint configuration exists: Playwright covers rendered interactions and the actual npm lint command runs oxlint.

### Failed, corrected, restricted and unexecuted checks

- Initial three live tests: two passed; the new workflow expected API-internal `partially_verified` rather than existing displayed `partially verified`. Only the new test assertion changed.
- Next workflow timed out at the default 5-second comparison expectation. Measured comparison responses take around 3 seconds warm, and route/render work added overhead. The explicit 30-second bounded expectation passed the unchanged UI; no loading/error condition was hidden.
- Initial 59-case browser regression: 58 passed/one 409-error case timed out; total 976.528 s, with 884.543 s attributed to that case despite its 60-second timer. This indicates an abnormal scheduling/timing stall, but its exact cause is not proven. The unchanged isolated case passed three times (about 1 s each), exit 0, 11.6 s total. Final full selection is recorded independently; the original failure remains retained.
- The first localhost Python probe failed with Windows WinError 10013 under the restricted token. The transparently approved same named probe then passed; this is an execution-environment restriction, not an application correction.
- Bundled Poppler `.cmd` launcher could not locate its target. The documented native Poppler executable rendered all 12 pages successfully. Symbol/ArialUnicode fallback warnings occurred; no missing glyph/clipping was observed in these reports.
- An initial HTTP-shell check wrongly expected the full scientific title inside the minimal HTML shell; that assertion failed after successful HTTP responses. Correcting it to the actual React root/script shell contract passed; title rendering was already checked by the live UI. No application title changed.
- Initial final-diff checking flagged CRLF introduced in the two intentionally rewritten root text files. Only README/.gitignore were restored to LF; no historical/Phase9 bytes were normalized. Standard `git diff --check` then passed.
- Python resolver dry-run exited 0 but emitted sandbox temporary-cleanup warnings. No real project data was deleted. Full fresh Python/cross-platform wheel installation, online CVE review, formal accessibility/penetration tests and public-host load tests were not executed; they are limitations, not fictitious passed or skipped test cases.

No approval restriction was bypassed. Earlier Phase 8/9 evidence was preserved through a disposable browser suite that changes output paths only. Initial/final source/execution digests identify the new workflow's assertion changes.

## Actual performance and installation observations

Conditions: local Windows, Python 3.12.10, Node 24.19.0, Edge headless, no controlled CPU/network isolation. Normal-startup API contained legacy preload state. These are lab samples, not field INP, hosting SLAs or measured improvements.

|API path/case|Samples|Median ms|
|---|---:|---:|
|Overview|3|891.15|
|Datasets|3|83.68|
|Model seeds|3|67.62|
|Reproducibility|3|107.86|
|Six-method comparison|2|3,016.04|
|Graph session, two tiers combined|2|1,660.37|
|Bounded graph queries, two tiers combined|6|157.12|
|IBM 5K PDF|2|726.75|
|IBM ~50K PDF|2|712.47|
|PaySim PDF|2|118.97|

The probe also completed one six-read burst using three workers, all 200, and rejected unknown/traversal-shaped/mismatched/cross-session requests as expected. This is not a sustained load test. PDF browser download observations were 1,132/944/341 ms initially; file sizes 10,747/10,736/9,199 bytes. Download includes browser/transport overhead and is distinct from server generation timing. Missing-artifact behavior is covered by isolated tests, without removing production evidence.

Final fresh-lock production browser observations (same bounds, headless Edge; automation polling included):

|Dataset/case|Nodes/edges|API-reported query ms|Ready ms|Worker compute/total-ready ms|Selection/zoom ms|JS heap bytes|
|---|---:|---:|---:|---:|---:|---:|
|ibm-5k high-degree|250/260|169.06|964|334.2/520.4|84/70|16414556|
|ibm-5k low-degree|2/1|43.52|231|5.5/38.7|39/27|13167426|
|ibm-50k high-degree|250/249|277.29|791|287/316.6|79/75|18865470|
|ibm-50k low-degree|2/1|144.51|366|5.9/38.2|41/24|11273817|

Fresh direct-query Python process RSS before/after: 184,102,912/200,081,408 bytes; observed peak 216,911,872 bytes. This profile loads no model/centrality work and measures full process memory, not index-only allocation. Startup sampling separately observed normal API RSS139,354,112 bytes and bounded API242,192,384 bytes; OS working-set trimming and different process histories make these unsuitable for a causal memory comparison. No claimed memory saving follows.

The final overview checkpoint observed LCP-entry436 ms, CLS0.043733 and used JS heap4,929,966 bytes. They are partial lab observations; field INP, finalized session-wide CWV and long-duration memory behavior remain unmeasured. Fresh session-plus-initial-ready times were2.015/2.414 s. Backend query timings include index hashing/SQL/serialization; pure index engine latency and pure worker initialization were not separately instrumented. Worker total-ready includes startup/module/scheduling/transfer and compute.


The earlier overview observation recorded LCP-entry 476 ms, CLS observed 0.043690 and heap metadata at the workflow checkpoint. This is partial lab observation, not a finalized field Core Web Vitals assessment; INP was not measured. Final fresh-build observations are retained separately. Heap samples are not browser RSS or long-duration leak measurements. No before/after speedup is claimed.

Fresh npm install succeeded offline (146 packages, 21 s). Fresh build/type checking exited 0; Vite 8.3.0 bundling was 23.81 s under concurrent activity. Entry JS 246.65 kB /74.94 kB gzip; deferred graph JS 30.25 kB /9.23 kB; graph CSS 3.95 kB /1.23 kB; worker 14.89 kB uncompressed. Earlier working installation used Vite 8.3.5 and had entry 246.87 kB. Phase 8 documented entry was 246,217 bytes /74.80 kB gzip; immediate PDF baseline 246.33 kB /74.83 kB. These are entry sizes, not all initial assets. Dependency/build-condition differences preclude an improvement claim. Graph/worker code remains deferred until navigation.

## Institutional PDF review

Three actual UI downloads, four A4 pages each, were parsed and rendered. All source titles/counts/label identities, seven IBM AP means/sample SDs and PaySim missing metrics match saved data. PDF text words remained within page bounds; no raw account-ID pattern/local user path was found. Visual inspection covered the complete 12-page contact sheets: formal serif headings/sans-serif body, labeled figures/captions/tables, consistent margins, four page breaks, headers/footers and wrapped hashes remained legible with no observed clipping. No pixel-font body styling or generator rewrite was introduced.

Metadata identifies the exact project title, GraphFin Research author label, report version/dataset subject and evidence hashes. The invariant creation/modification date 2000-01-01 is a determinism sentinel, not the actual run/download date. Missing current generation time is disclosed rather than invented. PDFs are untagged, not PDF/UA certified; dashboard tables provide an alternative but do not automatically make a PDF accessible. Font notices remain retained; no new font binaries were added.

## Manuscript, demo and missing material

The original six-page manuscript source was not found. A new versioned IEEE-style Markdown draft is provided in `manuscript/phase10-v1/manuscript.md`, with derived tables/full precision in the same directory. It covers abstract through conclusion, feature mathematics, frozen baselines, six splits, model seeds, provenance, replay and negative CREST findings. Primary references were rechecked, including the 2022 Graphomaly overlap; no superiority/first-of-kind claim is added. Author affiliation, target venue, required declarations and compiled-template compliance remain unresolved. This is critical-review material, not submission certification.

`10_demo_plan.md` provides a timed presenter script and screenshot checklist using actual supported routes and artifacts. It is a rehearsal plan rather than a fabricated delivered presentation. The documentation distinguishes engineering quality from scientific contribution.

## Preservation and final inventory

Final preservation: **87/87 protected originals match both the manifest and supplied ZIP;35/35 pinned runtime assets match;399/401 pre-phase files remain byte-identical**. The only two intentional pre-phase edits are README and root ignore policy. All26 inherited Phase9 changes (five edits plus21 additions), original algorithms, available historical results, dataset bytes, labels, score maps and topology indexes remain unchanged. Phase10 adds21 files, including the complete integration inventory. `git diff --check` exits0, and new text has no trailing-space violations. The inventory and external final-verification JSON record hashes, exclusions and source identities.

New Phase 10 material: README/ignore revisions, optional requirements/constraints, four verification/audit/browser-preparation tools, five tool tests, final browser config/two live workflow tests, the required reports, demo/notices/dependency inventory and versioned manuscript/evidence tables. Existing Phase 9 source/schema/tests/report and all historical data/results remain byte-identical to the Phase 10 snapshot. Complete paths/hashes are in the inventory rather than relying on git HEAD alone.

No dataset relabeling, score recalculation, algorithm change, graph scope expansion or historical output rewrite occurred. Saved AP reconstruction computes verification metrics only; it does not generate new model scores. Generated build/test/index assets remain excluded from staging.

## Phase completion and decisions

The Phase 10 review/documentation deliverables are complete with exact remaining limitations recorded. Functional local readiness and release/submission clearance are separate:

|Gate|Decision|
|---|---|
|Controlled final-year demonstration|**CONDITIONAL GO**: complete local assets, loopback-only bounded startup, verified environment and explicit limitations|
|Public GitHub data release/unrestricted deployment|**NO-GO**: rights, disclosure, legacy access/ingress/security and hosting prerequisites remain|
|IEEE submission|**NO-GO for submission; critical-review draft available**: author/venue/source alignment and scientific/provenance issues remain|

See the security and release reports for severity and proposed actions. No commit, push or deployment is authorized by this review, and none was performed. Work stops at Phase 10 review/documentation.
