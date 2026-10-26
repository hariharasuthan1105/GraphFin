# Phase 9 - Interactive transaction graph explorer

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Finalization date: 25 October 2026 (Asia/Calcutta). Scope: Phase 9 only. No new ML experiments, commits, pushes, deployment or Phase 10 implementation.

## Baseline, recovery and decision

Existing publication checkout: `work/pdf-reports/publish`; starting branch `feature/institutional-dataset-pdf`, commit `2fc9a729efb015029a559c6c2c0f71814ec4e662`. Work remains uncommitted on local `feature/phase9-graph-explorer`. The original separate checkout was not reset or replaced. Existing Phase 9 edits, indexes, logs and failed-run reports were recovered; no topology rebuild was needed on resume.

Final acceptance status is recorded in the gate below. This is a bounded research interface to synthetic transaction evidence. It does not establish detection accuracy, explanation superiority, real-world fraud or anonymity.

## Architecture and execution

`canonical CSV + checksum-pinned research catalog -> offline SQLite index -> bounded read-only GraphExplorerService -> three typed GET endpoints -> validated browser response -> short-lived layout Worker -> static directed SVG and accessible tables`.

The original `/graph` API and ForceGraph remain unchanged. They expose raw identities and can invoke expensive graph work, so the research explorer never calls them. Phase 7 research API and institutional PDF service remain the sources of saved research summaries and reports. No new runtime dependency was introduced; `d3-force` was already installed. Playwright is test tooling installed without package/lockfile changes.

Implementation references:

- `backend/app/services/graph_explorer_index.py`: canonical transaction validation, directed aggregation, immutable topology and fixed scope.
- `backend/scripts/build_graph_explorer.py`: explicit offline creation, exclusive versioned output directory; never called from HTTP.
- `backend/app/services/graph_explorer_service.py`: checksum checks, approved scope, sessions, SQL budgets and compatible saved annotations.
- `backend/app/schemas/graph_explorer.py` and `backend/app/api/routes/graph_explorer.py`: strict public response contracts and read-only routes.
- `frontend/src/research/pages/GraphExplorer.tsx`: route/controller, abortable requests, filters, expiry and accessible alternatives.
- `frontend/src/research/graph/{GraphCanvas.tsx,layout.worker.ts,layout-contract.ts}`: worker lifecycle, runtime message validation, deterministic geometry and interaction.
- `frontend/src/research/graph/Inspector.tsx`: account/relationship detail and saved Phase 7 diagnostics.

## Approved data and exact topology

Only checksum-verified IBM 5K and approximately 50K supplied snapshots are supported. Source files are `data/research/ibm_aml_medium_5k.csv` and `data/research/ibm_aml_large_50k.csv`. IBM labels retain partially verified upstream lineage. PaySim topology is explicitly unavailable; metadata, conflicting label identities and dataset PDF remain available. PaySim provenance is unresolved.

|Dataset|Source rows|Retained rows|Active accounts|Directed pairs|Index bytes|Build seconds|
|---|---:|---:|---:|---:|---:|---:|
|IBM 5K|31,463|31,463|5,000|5,315|5,185,536|0.83217|
|IBM ~50K|353,860|353,850|49,992|65,439|60,940,288|10.62988|

The 50,000 label-account population is distinct from 49,992 active graph accounts. No nodes are fabricated to fill that gap. Each fixed approved browsing lens contains 600 accounts; neither table above is a browser-load size.

SHA256 identities:

|Artifact|SHA256|
|---|---|
|5K source|`622d421b8ba1463ac0acc423f77fbf8a5c5604e5d2b1ea07b80e13dfb5a0a3f2`|
|50K source|`9bed6503841db5cf47f48cad182d39d6a5a6bab142fb267b338050e141f7b45f`|
|5K SQLite|`db1a1e267fa602e2dd0893a78726495050454507098731ef98ea6112299824ef`|
|50K SQLite|`7131b7b3cfa1f45a6a01210ee0f38e83f3a00a5dbc7c01fdb4f021bd212958cd`|

Derived indexes and manifest live under ignored, additive `data/results/v3/phase9-topology-v1/`. The builder refuses an existing destination. It validates source hashes before/after reading, required/nonmissing columns, unique transaction IDs, finite amounts and timestamps; IDs are read as strings, times are interpreted as UTC and represented as epoch seconds. It excludes nonpositive amounts and self-transfers exactly as canonical ingestion does. Timestamps are supplied synthetic times; amounts use canonical dataset units, with currency validity not independently established. No training, feature extraction, score recomputation or centrality calculation occurs.

### Directed aggregation and temporal semantics

For retained event set T and window W=[a,b], define T_uv(W)={t in T: sender(t)=u, receiver(t)=v, a<=time(t)<=b}. A directed edge u->v exists iff this set is nonempty. Its count is |T_uv(W)|, amount is the sum of its original amounts, first/last times are min/max event time. Distinct transaction IDs with the same ordered pair are aggregated; duplicate transaction IDs are rejected. Reverse v->u is a separate relationship. Full-snapshot sums preserve original sequential floating addition order; no extra monetary rounding is introduced at edge aggregation. Display amounts can be rounded, while original stored amounts are preserved. Node sent/received totals use SQL aggregation rounded to two decimal places, explicitly full-snapshot statistics.

Temporal subwindows aggregate retained events inclusively and then apply count/amount thresholds. Full-window requests use preaggregated adjacency. Source/index verification compared every directed pair, count, amount and timestamp in both indexes: maximum amount discrepancy **0.0**, count/time equality exact. See `source-verification.json`. Subwindow regression fixtures separately verify aggregation, cutoff bounds and annotation suppression. Partial neighborhoods are deterministic bounded traversals, not necessarily complete induced subgraphs. Full-snapshot reciprocity may be true even when filters hide the reverse edge.

## API, identities and bounded disclosure

All routes are under `/api/v1/graph-explorer`:

|GET route|Purpose and constraints|
|---|---|
|`/catalog`|Approved datasets, hashes, population/snapshot identities, versions and compatible saved experiments; PaySim unavailable|
|`/session`|Allowlisted dataset/experiment/version; optional descending rank 1-20; returns approved anchors and a session capability|
|`/neighborhood`|Granted focus ref, 1-2 hops, incoming/outgoing/both, count/amount/time filters and node/edge caps; capability required in `X-Graph-Session`|

Topology version: `canonical-directed-amount-v1`; response schema: `graphfin-neighborhood-v1`. OpenAPI-derived frontend schemas are in `frontend/src/research/graph/contract.schema.json` and `contract.ts`. The new client validates against its own schema registry; existing Phase 7 default registry remains unchanged. Unknown/unsupported requests fail explicitly. No path, SQL, arbitrary raw account ID or reverse-token lookup is accepted.

Session IDs are random 24-byte URL-safe capabilities (32 characters), sent in a header rather than query URLs. Node references use `node_` plus the first 32 hexadecimal HMAC-SHA256 characters over the private account identity with a fresh session secret. Edge references similarly bind the ordered endpoints. Display tokens reuse Phase 7's dataset-scoped pseudonymization for compatible ranking navigation, but do not authorize traversal. The service alone holds the raw mapping. References cannot be substituted across sessions, datasets or restarted workers. Snapshot identity binds dataset hash, observation bounds and topology version; index identity is also checked on every query. Expired/evicted references return 410; ungranted references return 403. No localStorage persistence is introduced. The browser clears session-dependent state on TTL expiry/dataset changes and aborts obsolete requests.

Enforced limits:

|Boundary|Limit|
|---|---|
|Fixed disclosure pool|600 approved accounts/dataset, unchanged across sessions|
|Individual response|250 nodes, 500 directed edges, 512 KiB serialized JSON|
|Traversal|1-2 hops; at most 502 fetched adjacency rows/frontier, explicit scan/node/edge/scope truncation|
|Session|600 distinct grants; 20 neighborhood queries; 600-second monotonic TTL|
|Worker process|16 sessions with eviction; 4 concurrently admitted requests; lock serializes session mutation|
|SQLite|Read-only immutable URI, `query_only`, 1.5-second VM execution deadline|
|Files|Allowlisted names only, no symlinks/junctions, manifest <=1 MiB, index <=250 MiB, checksum verification per query|

Responses and handled errors use `Cache-Control: private, no-store` and vary by capability header. Graph request validation removes capability inputs from the public validation envelope and bypasses the global input-logging handler. Neighborhood URLs contain opaque refs only. Tests verify bounds, quota/capacity, private errors, output-byte guard, wrong dataset/session, expiry, source/index/scope tampering, unsafe paths, HTTP mutation rejection and lack of model execution.

**Residual risk:** this is pseudonymization and bounded disclosure, not authentication, formal anonymization or deployment-wide rate limiting. Reopening sessions resets per-session quotas; additional processes multiply throughput. However, reopening/pagination cannot broaden the same approved 600-account pool: there is no arbitrary account lookup or pagination endpoint. Within that pool, repeated legitimate queries can disclose more relationships, time patterns and full-snapshot node aggregates than one screen. Structural reidentification remains possible. Existing legacy raw-ID APIs are unchanged and outside this new boundary; public deployment would require a separate authentication/access review and legacy route policy. A trusted immutable local index directory is assumed; hashes do not protect against an attacker who can replace both index and manifest.

## Ranking and CREST compatibility

Only verified saved split42/model42 experiments for the same dataset are offered. Dataset and label SHA256 must match the pinned protocol; score-map membership hash and count must match the held-out population. Scores are sorted descending with account identity as deterministic tie-break. They are frozen saved anomaly scores, never fraud probabilities. Graph rankings are unavailable for accounts outside that held-out map. The initial 5K focus was checked against the actual saved E4 top-ranked display token in the real browser run.

Rank navigation from Experiments passes explicit dataset/experiment/rank, not pseudonyms to reverse. UI links are limited to descending top20 at supported seeds. The server additionally rejects any account outside the approved fixed lens; top20 in another model can therefore be unavailable. Time subwindows suppress both scores and diagnostics because they differ from the model snapshot. Count/amount/direction filters do not recompute or reinterpret saved scores; displayed scores remain full-snapshot measurements.

**Recovered count correction:** the saved Phase 6A file has **24 diagnostic rows**, of which **13 have available intervention evidence** and 11 explicitly report unavailability. All 24 original baseline scores match E4 within 1e-12; all 13 available rows match E4 and none matches E6_BASE. Thus '24 available diagnostics' would be incorrect. This does not validate every graph node or establish superiority.

The compatibility guard additionally requires the Phase 6A algorithm identity, matching dataset hash and held-out ID hash, 19-feature count, E4 version `isolation-forest-raw-v2`, split/model/graph seeds42, `labels_used=false`, exact UTC source cutoff and the frozen model SHA256 recorded in Phase 6A: `81758da48c8de36f7d3ee08e5a00881ef7d6beaf14877ad758b9e4422f02a298`. No serialized model is loaded. The association relies on checksum-pinned historical evidence; this interface does not independently refit or reconstruct model features. Mismatched provenance leaves diagnostics unavailable while retaining otherwise valid saved rankings. Regression tests mutate each identity separately, including model version.

The panel uses **Experimental model-sensitivity diagnostic**. It reports stored original/intervened scores, signed fidelity, validity, omitted count/fraction and explicit missing fields/reasons. Stability unavailable through the approved API stays unavailable. Removed transaction identities/rows are never exposed or guessed, and no deleted-edge overlay is fabricated. Both available and unavailable saved rows are covered. Original full E6 detector benchmarking remains incomplete; detection/explanation superiority remains unsupported.

## Worker layout and frontend interaction

The `#/graph` page is lazy loaded after the original eight research pages. Layout executes only in a short-lived module Worker created in an effect, never during React render. Posted payloads explicitly project **only** session-scoped node refs, in/out degree and directed endpoint refs; amounts, event rows, timestamps, scores, diagnostics and raw identities are excluded. Typed input/output contracts have runtime checks: <=250 unique nodes, <=500 edges, safe nonnegative degrees, valid ref format, endpoints present, returned IDs in input order, finite coordinates/radii and nonnegative finite timings. Invalid output or worker error leaves an error message and usable inspection tables.

The worker uses deterministic Fibonacci-like initial positions, fixed LCG seed42, stopped d3-force simulation and exactly100 ticks. Radius=min(13,4+2 ln(1+in_degree+out_degree)); relationship width=min(4,0.7+log10(1+count)). These are visual encodings, not new anomaly algorithms. Arrowheads preserve sender-to-receiver direction; incoming-to-focus edges are dashed, reciprocal snapshot pairs curved. Positions/distances do not represent financial similarity. A white selection ring and small dark-red focus accent supplement text and table state.

The Worker terminates on result, error and effect cleanup. An active flag plus response-data identity prevents obsolete layouts from being applied; each query/dataset change replaces work. Selection changes do not relaunch layout. Duplicate termination is harmless, including cleanup after completed work; tests count unique terminated workers. Production browser checks cover deterministic replay, malformed worker inputs/outputs, projected payloads, navigation cleanup, selection reuse and deliberately delayed obsolete replies after a dataset switch. StrictMode-safe cleanup is implemented; no long-duration development-mode worker-leak certification is claimed.

Zoom, pan, Fit, Reset view, pointer node/edge selection, accessible account/relationship buttons, focus exploration and bounded server filters are operational. Pan transforms are scheduled with requestAnimationFrame and use SVG screen-to-view coordinates. Keyboard: arrows pan, +/- zoom, Home fits; native buttons/controls support focus and Enter. SVG labels/tooltips and full pseudonym detail in tables avoid unreadable dense-node text. Selection does not rely on color alone. CSS honors reduced motion and uses monochrome styling with restrained red accents.

Controls and inspector collapse from three columns to two plus inspector, then one mobile column. Browser checks cover widths360,430,768,1280 with no document overflow; wide tables scroll within their own container. This is functional keyboard/responsive verification, not a WCAG audit or screen-reader certification. Dataset selection, loading, schema/network/session errors, empty relationships and unavailable topology have explicit states. Existing PDF download remains on Dataset Explorer; its link carries the selected allowlisted dataset.

## Actual measurements

These are local lab observations, not deployment guarantees or performance-improvement claims. Original direct service profile ran in a fresh Python process with three mixed warm/cold samples per case, no CPU isolation. It includes checksum verification, admission/locking, SQLite retrieval and serialization; pure SQL index-lookup time was not separately instrumented. `query-performance.json` records raw samples and code hashes. Both dense/sparse neighborhoods were bounded; the full 50K graph was never loaded into the browser.

|Dataset|Anchor|Hops|Median service wall ms|Nodes/edges|Serialized bytes|
|---|---|---:|---:|---:|---:|
|ibm-5k|high-degree|1|125.31|250/249|190627|
|ibm-5k|high-degree|2|267.67|250/260|194472|
|ibm-5k|low-degree|1|100.51|2/1|2886|
|ibm-5k|low-degree|2|92.34|2/1|2886|
|ibm-50k|high-degree|1|221.11|250/249|190689|
|ibm-50k|high-degree|2|366.75|250/249|190689|
|ibm-50k|low-degree|1|190.45|2/1|2893|
|ibm-50k|low-degree|2|199.75|2/1|2893|

Direct session-open observations were2.113s (5K) and3.773s (50K), with cache/call overhead; separate real-browser warm session-plus-initial-layout observations were1.416s/1.389s. Query-process RSS before/after:184,815,616/200,847,360bytes; observed OS peak217,677,824bytes. This is process working set, not an incremental index-only allocation or long-duration leak result.

The first successful real browser profile used local production preview + live API, headless Edge, no CPU/network throttling. It is preserved as `browser-real-performance-pre-provenance.json`; final compatibility rerun is separately recorded in `browser-real-performance.json` and its test report. Browser timings include automation polling/render scheduling and are not field INP.

|Dataset/case (2 hops)|Nodes/edges|API-reported query ms|Graph ready ms|Worker compute ms|Worker total ready ms|Node selection ms|Zoom button ms|JS heap bytes|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|ibm-5k high-degree|250/260|150.97|987|350.7|604|84|80|15691690|
|ibm-5k low-degree|2/1|35.01|292|5.6|33.5|24|23|7311864|
|ibm-50k high-degree|250/249|212.21|578|229|243.8|74|60|9727820|
|ibm-50k low-degree|2/1|115.07|255|5.2|29.1|28|20|17203550|

Worker total ready measures construction/postMessage through receipt, including initialization, module load, scheduling, transfer and compute. Subtracting compute gives a combined overhead estimate, not isolated engine initialization:253.3/27.9/14.8/23.9ms for table order. No before/after main-thread baseline was measured, so no quantitative speedup is claimed. Heap samples are Chromium's reported used JS heap, not total browser RSS. No Lighthouse, field INP, controlled load/concurrency benchmark or prolonged leak test was run.

Production build (local `VITE_RESEARCH_API_URL=/`): entry JS246.87KB /75.05KB Vite gzip, graph route30.25KB /9.23KB, graph CSS3.95KB /1.23KB; worker14.88KB uncompressed, deferred. Phase 8's documented entry was246,217bytes /74.80KB gzip; immediate PDF-feature baseline was246.33KB /74.83KB. Differences are small additive routing/schema wiring, not a claimed optimization. Those entry values exclude overview/shared chunks/CSS/fonts. Real browser resource inspection confirms graph/worker chunks are absent before Graph Explorer navigation. Legacy Recharts/evaluation chunk remains deferred. Build/type-check exit0; Vite bundling2.42s (not full install/type-check duration).


Final compatibility rerun (20.2s workflow,22.15s runner) also passed. A disposable backend test was running concurrently, so these are contention-affected observations, not controlled performance comparisons:

|Dataset/case|API query ms|Graph ready ms|Worker compute/total ms|Selection ms|Zoom ms|Heap bytes|
|---|---:|---:|---:|---:|---:|---:|
|ibm-5k high-degree|177.15|832|275.3/312.8|85|90|15698441|
|ibm-5k low-degree|44.40|285|5.2/35.8|26|23|15982252|
|ibm-50k high-degree|258.79|863|267.5/310.3|76|64|21079979|
|ibm-50k low-degree|126.05|305|5.6/28.4|28|28|13160188|

Final session-plus-initial-ready times were1.962s/2.444s. These raw timings are preserved separately from the first run.

## Tests and corrections

Tests use the existing `backend/scripts/verify_phase2.py` disposable-copy runner. It copies to an external scratch directory, uses its own persistence marker, pytest temp and MPL state, and never rewrites source datasets to satisfy tests. Pytest JUnit XML, command and logs remain in each scratch run. Browser fixtures are explicitly synthetic and separate from the one live-data workflow.

Final executed results and run history are listed below; repeated tests must not be summed as independent test cases.

|Validation|Executed result|Exit|Evidence relative to work/phase9|
|---|---|---:|---|
|Recovered backend compatibility + original graph32|108 passed, 0 failed/skipped, 118.04s|0|`backend-first/phase2-y6ylbfxj/{pytest.log,results.xml}`|
|Final graph API/security/provenance46|46 passed, 0 failed/errors/skipped, 56.00s|0|`backend-accepted.log`, `backend-accepted/phase2-kf0ohmpx/results.xml`, `backend-accepted-exit.txt`|
|Recovered dashboard35 + PDF3 + graph18 browser|56 passed, 0 failed/skipped, 66.63s|0|`browser-final.{log,json}`, `browser-final-exit.txt`|
|Final graph interactions/worker lifecycle21|21 passed, 0 failed/skipped, 27.80s|0|`browser-lifecycle-final.{log,json}`, exit file|
|Final actual-data browser/PDF workflow|1 passed, 0 failed/skipped, 22.15s runner /20.2s test|0|`browser-real-accepted.{log,json}`, exit file|
|TypeScript + production Vite build|Passed; 2.42s bundling|0|`build-verified.log`, exit file|
|Lint (oxlint, existing project npm lint command)|0 errors, 42 unchanged legacy warnings; none in new graph code|0|`lint-resume.log`, exit file|
|Source/index numerical verification|Both complete source aggregations passed; zero amount/count/time mismatches|0|`source-verification.json`, `source-exit.txt`|
|Bounded direct query profile|8 cases x3 samples, all cap/byte assertions passed|0|`query-performance.json`, `query-exit.txt`|
|Diagnostic provenance checks|24/24 complete identity matches; 13 available intervention rows|0|`diagnostic-provenance-final.json`, `diagnostic-compatibility.json`|
|Preservation and whitespace|87 originals, 35 pinned assets, 372 unaffected tracked files match; diff check clean|0|`preservation-resume.json`, `final-verification.json`|

Across these selected runs, **122 distinct backend cases** (46 graph +76 existing) and **60 distinct browser cases** (21 graph +35 dashboard +3 PDF +1 live workflow) have executed successfully. These are coverage unions, not one all-suite invocation. Final unresolved failures=0, skipped=0, environment-blocked selected checks=0. Previously corrected failed/setup runs remain listed below.

Security, numerical and deterministic checks are part of the46 graph API cases and21 graph browser cases, not additional independent counts. Existing Phase 7 API cases56, PDF cases11 and legacy report cases9 were exercised in the recovered108-pass run. Targeted graph coverage was expanded afterward; those original compatibility files were not modified. This is selected regression validation, not a claim that the entire repository backend suite was rerun.

Earlier outcomes retained for traceability:

- `browser-first`:16pass/1fail; exact-label `Direction` selector included select option text. The control had a valid combobox accessible name; role-based selection succeeds and the incoming request is asserted. No invalid UI action was masked.
- `browser-final`:56pass; completed worker revision plus dashboard/PDF regressions before resume.
- `browser-real-resume`:1fail, local build inherited production API URL, leaving overview waiting. Rebuilding with documented `VITE_RESEARCH_API_URL=/` selected the local proxy; no application security setting changed.
- `browser-real-local`:1fail, test acted before new query completion and its diagnostic selection was cleared by that response. Corrected explicit query-ready waits.
- `browser-real-ready`:1fail, broad diagnostic label matched anchor option text as well as diagnostic select. Corrected exact combobox accessible-name selector.
- `browser-real-exact`:1pass17.7s; first successful complete real-data workflow.
- `browser-resume`:57pass/1fail; test counted a harmless repeated worker termination as an extra worker. Corrected instrumentation counts unique terminated instances; final worker checks pass.
- `backend-provenance`:45 setup errors21.71s, synthetic Phase 7 fixture exposed only one feature. `backend-provenance-final`:46 setup errors21.52s, fixture incorrectly used the extended23-feature list. Corrected only the new test fixture to explicit `CANONICAL_TRANSFER_FEATURES` (19); no dataset or historical evidence changed. Production19-feature gate was retained.
- An optional formatting command found no local Prettier binary and was canceled while package resolution waited; it is not a passed check. No package/lockfile was changed. Build, lint and browser checks subsequently executed.

The previously reported declined real-browser command had produced no recoverable execution log. Resume requested the ordinary named Playwright workflow transparently; it was approved and executed. No wrapper obfuscation, sandbox bypass or application security weakening was used. No blocked run is reported as passed. Windows CIM process inspection was unavailable under the restricted token; no duplicate test was launched because no prior execution/log existed and approved runs returned concrete exit statuses.

## Visual review and evidence

Evidence directory is `work/phase9` relative to the task workspace, outside the publication repository. Files include source/query/diagnostic verification JSON; preserved initial/final pytest JUnit and logs; Playwright JSON/log/exit files; production build/lint logs; baseline and preservation manifests. Browser screenshots in `visual/` cover real dense/sparse IBM graphs, node/edge inspection, compatible saved CREST, unavailable saved CREST, empty relationships, PaySim topology unavailable and widths360/430/768/1280. Synthetic worker loading/error captures are labeled separately. `visual-pre-provenance/` preserves the first successful real captures.

Rendered PNGs were actually opened for inspection (including final available CREST, worker error/loading, empty and unavailable topology): dense5K, sparse50K, mobile360, selected relationship, saved CREST panel, plus final captures noted in final evidence. Directed arrows, restrained red focus accent, monochrome hierarchy, account/relationship tables, explicit partial notices and mobile containment were visible. Dense networks intentionally avoid overlapping full pseudonym labels; precise identities are available through tooltips/inspectors/tables. Full-page screenshots can place fixed navigation at the scroll position used for capture; this is not evidence of sticky-navigation positioning at every scroll offset.

## Preservation and changed files

`preservation-resume.json` verifies all87 protected originals against `docs/research/protected_artifacts_v1.json` AND supplied ZIP bytes. ZIP SHA256: `02c3b4d4d4c41c259ba1efb668c12551992d174ee2deb2960dcc00fba00a4531`. All35 pinned runtime research/report assets match `dataset_report_runtime_assets.json`. Of377 pre-Phase9 tracked files,372 are byte-identical. Five intentional existing-file changes only:

1. `backend/app/api/router.py` - register additive graph namespace.
2. `frontend/src/ResearchApp.tsx` - lazy graph route/navigation and safe query-route parsing.
3. `frontend/src/research/client.ts` - optional schema registry/const checks and graph API URL helper.
4. `frontend/src/research/pages/Datasets.tsx` - allowlisted selected-dataset report-link context.
5. `frontend/src/research/pages/Experiments.tsx` - compatible numeric-rank graph links.

New files:

- `backend/app/api/routes/graph_explorer.py`
- `backend/app/schemas/graph_explorer.py`
- `backend/app/services/graph_explorer_index.py`
- `backend/app/services/graph_explorer_service.py`
- `backend/scripts/build_graph_explorer.py`
- `backend/scripts/verify_graph_explorer.py`
- `backend/tests/test_phase9_graph_explorer.py`
- `frontend/playwright.graph.config.ts`
- `frontend/src/research/graph/GraphCanvas.tsx`
- `frontend/src/research/graph/Inspector.tsx`
- `frontend/src/research/graph/client.ts`
- `frontend/src/research/graph/contract.schema.json`
- `frontend/src/research/graph/contract.ts`
- `frontend/src/research/graph/graph.css`
- `frontend/src/research/graph/layout-contract.ts`
- `frontend/src/research/graph/layout.worker.ts`
- `frontend/src/research/pages/GraphExplorer.tsx`
- `frontend/tests/graph-explorer.spec.ts`
- `frontend/tests/graph-fixtures.ts`
- `frontend/tests/graph-real.spec.ts`
- `docs/research/09_interactive_graph_explorer.md`

New ignored local artifacts: the two derived SQLite indexes and manifest under v3, frontend dist/dependencies, and validation evidence/scratch copies outside this checkout. No original datasets, protected frontend, E0-E5/CREST algorithms, historical experiments, old docs or PDF service were changed. Phase 7 GET contracts and Phase 8 original eight routes remain compatible in regression tests. PaySim PDF downloading succeeded in the actual new graph-to-dataset flow. `git diff --check` final result recorded below. No commit or push was performed; HEAD remains baseline.

## Reproduction commands

Run from the existing publication repository with the installed project Python/dependencies. Index creation is an explicit one-time operation: `python backend/scripts/build_graph_explorer.py`; an existing destination is refused. Use the prepared index rather than rerunning or deleting it. Verification only:

```text
python backend/scripts/verify_graph_explorer.py --mode source --output NEW_SOURCE_EVIDENCE.json
python backend/scripts/verify_graph_explorer.py --mode queries --output NEW_QUERY_EVIDENCE.json
python backend/scripts/verify_phase2.py OUTSIDE_REPO_SCRATCH -- backend/tests/test_phase9_graph_explorer.py -q
```

Use new evidence paths; verifier outputs are exclusive. No ML experiment commands are required.

From frontend, PowerShell:

```powershell
$env:VITE_RESEARCH_API_URL='/'
npm.cmd run build -- --config vite.research.config.ts
npm.cmd run preview -- --config vite.research.config.ts --host 127.0.0.1 --port 4190
$env:TEST_URL='http://127.0.0.1:4190/GraphFin/'
$env:TEST_REPORT='AN_UNUSED_REPORT.json'
npx.cmd --no-install playwright test --config playwright.graph.config.ts tests/graph-explorer.spec.ts
npx.cmd --no-install playwright test --config playwright.graph.config.ts tests/graph-real.spec.ts
```

The live test additionally requires the local FastAPI application on8000, checksum-pinned Phase 7 assets and the prepared private indexes. Mocked graph/dashboard/PDF tests do not establish live topology correctness on their own. Production uses the deployment's configured research API URL; the localhost override is a test-build environment variable only.

## Acceptance gate

**Overall: COMPLETE for the defined bounded Phase 9 scope. All A-M acceptance criteria PASS.**

|Gate|Status|Evidence / qualification|
|---|---|---|
|A Real topology correctness|PASS|Full-source comparison for both indexes; counts and hashes above|
|B Direction/aggregation|PASS|Ordered pairs, multiplicity, full sums/times exact; direction and temporal fixtures|
|C Privacy/pseudonymization|PASS within new explorer boundary|Cross-session/dataset rejection, no raw IDs/rows, private headers; residual structure/legacy risks disclosed|
|D Bounded safety|PASS|Fixed600 pool, response/query/VM/concurrency limits; quota and tamper tests|
|E Interactive behavior|PASS|21 graph browser cases plus final real workflow; no invented network fallback|
|F Worker lifecycle/layout|PASS|Typed projection, runtime validation, deterministic replay, cleanup, stale reply and failure tests|
|G Ranking compatibility|PASS|Pinned dataset/labels/held-out hashes, supported versions/seeds, real top-rank token comparison|
|H CREST diagnostic integrity|PASS|24 provenance/baseline associations;13 available interventions; mismatch tests and both available/unavailable rendered panels|
|I Responsive/accessibility|PASS for specified functional checks|Keyboard alternatives, reduced motion, four viewport widths; no formal WCAG certification claimed|
|J Build/tests|PASS|Selected122 backend/60 browser cases passed across recorded runs; type/build/lint exit0|
|K Performance evidence|PASS|Actual direct/API/worker/layout/readiness/selection/heap/bundle measurements; no improvement/INP claim|
|L Preservation|PASS|87 originals +35 pinned assets +372 unaffected files unchanged, PDF download/regressions pass, HEAD unchanged|
|M Documentation|PASS|Architecture, contracts, equations, hashes, measurements, failures, limitations and file inventory complete|

`git diff --check`: exit0, no output. New untracked text files were also checked for trailing whitespace. No commit/push/deployment was performed.


Remaining scientific limitations: IBM lineage partially verified, PaySim conflict unresolved, synthetic source times/units, transductive saved features, very limited CREST population, no demonstrated detector/explanation superiority and incomplete original E6 benchmark. Remaining operational limitations: fixed600-account lens, process-local sessions/eviction, trusted index storage, no app-wide authentication/rate policy or formal anonymity, no full-screen-reader audit, no field INP/Lighthouse or prolonged memory test. These do not become research claims through visualization.

Phase 10 readiness: the bounded Phase 9 integration can be reviewed and used locally once the gate passes. Any future expanded disclosure, multiworker sessions, PaySim graph index or public deployment needs explicit scope/provenance/access decisions. Phase 10 was not started. No permission to commit/push/deploy is inferred from older phases.
