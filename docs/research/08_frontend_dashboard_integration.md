# Phase 8 — Research dashboard integration

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

## Plan recorded before implementation

Keep the existing application and lazy operational workspace accessible. Add a default read-only research shell with eight hash routes, shared accessible components and separately lazy research pages. Preserve backend, algorithms, datasets and historic results. Generate TypeScript public types and runtime validation schemas from the actual Phase 7 OpenAPI. Use only GET requests, cancellation, bounded caching and server pagination. No added graph explorer.

Use scoped monochrome tokens, system sans, IBM Plex Mono and licensed Pixelify Sans/Silkscreen with swap/fallbacks. CSS motion is finite and disabled under reduced motion. Charts have tables and descriptive scientific labels. Preserve nulls, unresolved PaySim and partial IBM lineage; no superiority claims.

Validate types, lint, production build, deterministic tests, real read-only API/browser behavior, responsive screenshots and protected bytes. Record actual measurements and any untested limits.

## Final outcome — 2026-10-25

**COMPLETE for Phase 8 frontend integration**, with the bounded verification and limitations below. Eight research pages are connected to the existing Phase 7 API. No algorithm, label, backend, historical result, deployment or Phase 9 implementation was changed. The original project title is retained in project information, footer and research document title.

### Preservation-compatible entry point

The original 87-file policy protects nearly the entire original frontend, including App.tsx, index.html and both package files. The first preservation attempt correctly rejected their interim edits. Those edits were retained under `work/phase8/pre-preservation-adapter/`, then the four originals were restored from the authenticated supplied ZIP. Useful implementation was retained as **additive files**, not discarded.

`vite.research.config.ts` extends the original Vite configuration. It resolves only the original main.tsx import of App.tsx to ResearchApp.tsx and supplies research.html through Vite's HTML transform. The legacy configuration, files and npm commands remain intact. This is one existing frontend project with an opt-in research entry, not a replacement application. The first adapter build produced identical output chunks to the preceding research build. Subsequent small hook cleanup and a seed-page provenance notice were checked separately.

From the existing frontend directory:

```powershell
npm ci
# Development-only test tooling; neither protected package file is changed:
npm install --no-save --package-lock=false @playwright/test@1.64.1
# Same-origin local API proxy; use the Phase 7 backend origin otherwise:
$env:VITE_RESEARCH_API_URL='/'
npm run dev -- --config vite.research.config.ts
npm run build -- --config vite.research.config.ts
npm run preview -- --config vite.research.config.ts --host 127.0.0.1 --port 4173
```

Build and preview are separate commands. Existing `/GraphFin/` base and `/api` proxy are inherited. The research URL defaults to the explicit VITE_RESEARCH_API_URL, then existing VITE_API_URL, then same-origin. A trailing /api/v1 is normalized. The protected `.env.production` still points to its old host; set the research variable explicitly when testing locally. No production host was deployed or assumed to have Phase 7 installed.

### Architecture and reuse

ResearchApp provides hash navigation, toolbar, fixed sidebar, mobile disclosure, skip link and Suspense boundaries. Each research page is a separate lazy module. The original context/provider is not mounted on research routes, so operational requests are not triggered by research-shell startup. `#/workspace` loads LegacyApp, a byte-identical copy of the original App.tsx, which reuses the original context, API client, screens, graph component and UI controls. Existing graph/operational functions remain legacy functionality; no new interactive graph explorer was added.

New shared components are Heading, Panel, Notice, Status, Metric, Chart, Table, Pager, Hash, Tier, Qualifications and State. New `state.ts` separates request state and formatting from presentation. The final hook derives loading from path/schema/retry identity instead of setting state synchronously in an effect, preventing old-query values from flashing while avoiding an extra render. No new production dependency was added. Playwright 1.64.1 is test tooling only. No motion library, icon package or additional chart package is required.

The new charts use simple labeled CSS bars and white/gray/patterned fills, avoiding the existing heavy chart library on research routes. They have linear scales, exact table alternatives and no animated metric values. The existing Recharts code remains deferred in the legacy EvaluationScreen chunk.

## Pages and actual API integration

Every endpoint below is GET under `/api/v1/research`. The exact response schema is preserved from `data/results/v2/phase7-api-verification-v1/openapi-final.json`. Twenty-three public response schemas were extracted into contract.ts and contract.schema.json; the final verifier compares the JSON schemas with the pinned OpenAPI. No protected result payload is embedded in the new application. Synthetic values exist only in tests/fixtures.ts.

| Hash route | Component | Actual endpoint usage |
| --- | --- | --- |
| `#/overview` | Overview.tsx | `/overview` |
| `#/datasets` | Datasets.tsx | `/datasets`, `/datasets/{dataset_id}` |
| `#/experiments` | Experiments.tsx | `/experiments`, `/experiments/{id}`, `/experiments/{id}/metrics`, `/experiments/{id}/provenance`, `/experiments/{id}/rankings` |
| `#/comparison` | Comparison.tsx | `/experiments`, `/comparisons` with repeated compatible IDs |
| `#/seeds` | Seeds.tsx | `/experiments` for six splits; `/model-seeds` for the fixed split |
| `#/reproducibility` | Reproducibility.tsx | `/reproducibility` |
| `#/diagnostics` | Diagnostics.tsx | `/diagnostics`, `/diagnostics/{id}` |
| `#/limitations` | Limitations.tsx | `/limitations` |
| `#/workspace` | LegacyApp.tsx | Original operational APIs, only after explicit navigation |

All fourteen Phase 7 route patterns were exercised in the real workflow: 18 successful research HTTP responses, all GET, no page JavaScript errors. Dataset detail covers IBM and PaySim; experiment metrics/provenance/rankings are explicit on-demand sections. A separate tabular ranking view requests only 25 accounts per page, never the full population. Tests confirm page 2 uses page_number=2 and page_size=25. Token-to-diagnostic linkage is honestly unavailable because the API does not provide a durable cross-worker mapping.

### Client validation, cancellation and caching

`client.ts` validates response objects before use: required fields, references, unions, enums, scalar types, integer/finite numeric values and bounded arrays. Unexpected/missing required fields produce a controlled response-contract error. This lightweight reader validates the subset used by the extracted schemas, not arbitrary JSON Schema documents. API errors retain their safe message; no backend paths or transactions are accepted or fetched by clients.

Queries use URLSearchParams with stable ordering. UI options constrain dataset, method, split and metric choices; the backend remains authoritative for scientific compatibility and bounds. Concurrent callers share a request by schema/path/query identity. Each caller can abort; the underlying request is cancelled when no subscribers remain. A one-task deferred cancellation avoids StrictMode's immediate cleanup/remount creating duplicate requests. The corrected behavior has a browser regression.

Metadata responses have a 60-second in-memory cache capped at 30 entries. Retry clears metadata cache. Ranking and diagnostic responses are not retained in that cache; no research data is persisted in localStorage. Pending concurrent diagnostic requests can share a response within the same request lifetime. Pseudonyms are process-local, may change across backend workers/restarts and are not durable account IDs. No account linking or new ranking formula is introduced.

### Scientific presentation

Null/missing metrics render **Unavailable**, never zero. Counts, versions, positives, source hashes and scores are read from API results. The only derived scientific summary is mean/sample SD/min/max of available stored split AP values. For n values, mean is sum(x)/n and sample SD is sqrt(sum((x-mean)^2)/(n-1)); SD is unavailable for n<2 and is never called a CI. Numerical behavior is tested with six known synthetic AP values. Split runs are not independent datasets. Model seeds 13,42,101 remain separate from six-split evidence and do not establish broad robustness.

Average Precision is labeled as the non-interpolated PR-AUC convention. Compatible comparison IDs come from one dataset/tier/split/model population; server incompatibilities are surfaced rather than bypassed. E6_BASE is explicitly calibration-only and can differ from E4 through ties. Incomplete E6 and historical descriptors never receive fabricated completed metrics. Retrieval tables show effective K, positive hits, precision and recall.

IBM upstream account-label lineage remains partially verified. PaySim shows both 774- and 2,606-positive identities and 1,832 disagreements, with no chosen aggregate prevalence. CREST is labeled experimental model sensitivity; neither detection nor explanation superiority is established. Signed fidelity is shown as saved, not as criminal or causal evidence. Anomaly scores are not fraud probabilities. Replay scope is precise: 5K result-array equality and saved ~50K full replay evidence; no API-triggered replay. Runtime/stability/environment fields absent from the API are labeled unavailable. Transfer limitations and the incomplete original E6 benchmark remain visible.

## Monochrome design, typography and motion

| Token | Value / use |
| --- | --- |
| Void / black | #080809 / #000000; canvas/sidebar |
| Surface / raised / secondary | #101012 / #171719 / #202023 |
| Border | #303034 |
| White / primary / secondary text | #FFFFFF / #F5F5F5 / #A6A6A6 |
| Technical | #77777D; restrained decorative separators, not essential low-contrast labels |
| Pixel / deep / cursor red | #B44A50 / #842D35 / #C04B52 |

Red is confined to large pixel cursor typography, small decorative indicators and the thin active rail; cards are never red. Small dark-red text was changed to gray/white because the requested red does not meet normal-text contrast on black. Status remains understandable from explicit wording and shapes. New research views are scoped under `.research`; legacy styles remain intact.

System sans-serif handles body/navigation. Pixelify Sans handles wordmark and hero identity; Silkscreen is reserved for short terminal labels; IBM Plex Mono handles metrics, hashes and table numerics. Local WOFF2 files are 12,016 / 8,404 / 14,708 bytes respectively. All three SIL Open Font License 1.1 files and source URLs are stored beside the fonts. No proprietary Apple fonts were bundled. `font-display:swap`, system fallbacks and fixed containers allow usable content before fonts load; font-failure behavior is tested. The research HTML removes the old external font stylesheet without modifying the protected original index.html.

The wordmark reveals once in 650 ms using steps(8); the cursor has four 500 ms iterations. Page transitions use 220 ms opacity/5px translation. Cards change border color only. The decorative network/grid is static and is not an interactive graph. Compact opacity-stepped loading squares run only while a genuine request is pending. Reduced motion disables animation/transition, including cursor and loading motion, without hiding content. No animated blur, shadow, large backdrop filter or continuously moving background was introduced. The CSS uses no animation of layout dimensions; measured aggregate CLS is not an isolated proof of zero font/loading shift.

## Responsive and accessible behavior

Verified widths: 360,390,430,768,1280,1440 and1920 CSS pixels. Tests found no page-wide horizontal overflow, including all eight pages at360px. Scientific tables scroll locally. Mobile navigation exposes aria-expanded, closes on selection/backdrop/Escape, and returns focus to the toggle on Escape from its links. The skip link focuses main without corrupting the hash route. Visible focus outlines, labeled native controls, table captions/column headers, aria-current, status/alert regions and non-color status text are implemented. Most controls are at least44px; compact checksum buttons are32px. No full WCAG certification or screen-reader audit is claimed.

Required states are represented: initial/slow loading, network failure/retry, unavailable artifacts, invalid schema/filter, unsupported comparison, incomplete experiment, empty table/ranking, absent diagnostic and unresolved provenance. Null labels/measurements are not replaced by illustrations. The initial mobile screenshot caught the entrance transition; final screenshots explicitly finish finite animations. Pixel completion and reduced-motion behavior were also checked independently, so screenshot stabilization is not used as proof of animation behavior.

### Captured and inspected visual evidence

Paths are relative to the workspace, outside historical research output directories:

- `work/phase8/visual-release/overview-desktop.png`, `comparison-desktop.png`, `overview-390.png`, `overview-768.png`, `overview-1280.png`, `overview-1920.png`: real production application and real local Phase 7 responses.
- `work/phase8/visual-production/final-360.png`, `final-430.png`, `menu-360.png`, `menu-430.png`: missing narrow-screen/menu captures completed in the final check.
- `work/phase8/visual-production/loading-mocked.png`, `error-mocked.png`: actual rendered application with explicitly mocked slow/failing requests; not scientific result screenshots.

Desktop hierarchy, comparison labels/table, mobile overview, tablet/large desktop, mobile menu, pixel fonts, accent restraint, loading and error states were visually inspected. Older screenshots and failed logs remain retained.

## Production bundle and measured performance

Final source build: `npm run build -- --config vite.research.config.ts`, with VITE_RESEARCH_API_URL=/ for the local test proxy. TypeScript and Vite exited0; Vite reported2.31s bundling (not complete install/typecheck time). `work/phase8/build-accepted.log` and bundle-analysis.json are the evidence.

The earlier “approximately250KB” referred to **entry JavaScript only**, not all initial assets. Final entry JS is **246,217 bytes**, Vite gzip report **74.80KB**. Initial overview additionally loads a3,984-byte page chunk and4,465-byte shared UI chunk: **254,666 bytes of JavaScript**. CSS is44,375 bytes; fonts total35,128 bytes. Together these are334,169 bytes, plus1,200-byte HTML, excluding the API payload and untouched legacy public assets. A separate Python gzip estimate is121,998 bytes for that asset set (gzip levels differ from Vite and WOFF2 is already compressed); this is not an observed deployment wire-transfer total.

Research page chunks are approximately1.32–5.07KB each uncompressed. LegacyApp is62.52KB (18.64KB Vite gzip); the existing EvaluationScreen/Recharts-containing chunk is450.73KB (123.54KB gzip). That chunk is not loaded on initial research navigation. It includes legacy screen code as well as chart dependencies, so450.73KB must not be reported as Recharts alone. Existing legacy graph chunk is27.48KB. No new giant research-chart chunk was added.

The final lab run used Edge headless on Windows, 1440x1000, local production preview and local disposable Phase7 backend, with no CPU/network throttle. Three full document navigations were measured in one browser context; static assets are warm after the first. An earlier measurement accidentally reused hash navigations; it was corrected before accepting the data. No Lighthouse run occurred.

| Observation | Navigation1 | Navigation2 | Navigation3 |
| --- | ---: | ---: | ---: |
| LCP (ms) |512|372|376|
| CLS |0.043733|0.043733|0.043733|
| Evidence visible (ms, browser test wall clock) |2156|1628|1461|
| Overview request duration (ms) |1596.2|1116.9|1037.4|
| Route heading ready (ms) |401|372|387|
| JS heap bytes |5035157|5908825|8207105|

Source: `work/phase8/production-performance.json`; the final seed-only qualification changed no initial-view rendering. LCP and CLS meet the stated targets **under these local conditions only**. Route readiness includes lazy loading, scheduling and test polling; it is not input-to-next-paint. **Field INP is unmeasured**, so no200ms INP pass is claimed. API duration includes local proxy/network/server work; evidence readiness also includes HTML/module/font scheduling, React rendering and test polling. Subtracting these overlapping timings would not isolate pure rendering time. Heap rose across these short navigations; GC was not forced, and long-session memory stability/leak freedom is not established. Cache limits are implemented, but this is not a long-duration memory certification.

## Quality results and corrected attempts

| Check | Actual outcome / exit |
| --- | --- |
| Original final deterministic browser suite |35 passed,0 failed,0 skipped;45.2s; exit0 |
| Post-adapter/hook affected checks |9 passed;15.8s; exit0 |
| Post-adapter real API + lab measurement + narrow/mobile menu |3 passed;32.1s; exit0 |
| Final seed qualification/numerical checks |2 passed;3.1s; exit0 |
| Error/loading screenshot checks |2 passed;7.5s; exit0 |
| TypeScript |Final production build includes `tsc -b`; exit0 |
| Production build |Passed; exit0; final bundling2.31s |
| Lint |Exit0,0 errors,42 warnings; reviewed below |
| Original protection/schema check |87 ZIP matches;765 snapshot matches;23 public schemas match; exit0 |
| `git diff --check` |Exit0 |

There are **38 distinct executed browser tests**:35 deterministic fixture tests, one real-API workflow, one measurement test and one final mobile visual check. Repeated targeted executions are not added to that total. None of these final checks is skipped or blocked. The35-test suite was not unnecessarily repeated on resume; only affected checks were rerun after the entry/state changes. The legacy navigation test verifies mounting/navigation with an offline fixture and the original source is byte-identical; it does not revalidate every operational backend workflow.

Retained failures: initial registry/font downloads failed under sandbox DNS (approved retries succeeded); initial type checking exposed optional OpenAPI fields and a missing Evidence alias (fixed); initial browser run was26passed/4failed (Edge launch, two test-selector/mock errors, StrictMode duplicate request); expanded run was34passed/1failed because a fabricated empty legacy payload crashed its original screen (corrected to a valid offline response); an intermediate hook extraction omitted fmt's import (type checker caught it; fixed). Initial protection failed because original frontend files were included in the87-file lock; the additive entry fixes that conflict. No result was manufactured to pass a check.

### Lint review

The42 remaining warnings comprise19 synchronous effect updates,11 unused variables,6 mixed HMR exports,5 dependency warnings and1 short-circuit expression warning. Forty-one are in unchanged protected legacy source; one repeats the original App effect in the identical LegacyApp copy. The short-circuit warning is the existing `onNodeClick && onNodeClick(node.id)` handler, not an omitted required call. Unused bindings are cleanup opportunities; HMR warnings affect development module refresh. Legacy effect/dependency warnings can cause extra renders or stale closures and remain known legacy debt; no observed Phase8 research-route failure was attributed to them. They are not silently suppressed or “fixed” by modifying locked originals. New research code's mixed export/state-reset warnings were removed by extracting state.ts and deriving request loading from identity. No lint suppression was added.

## Preservation and acceptance

`frontend/scripts/verify_research.py` authenticates the supplied archive, checks all87 protected files, compares all765 snapshot members, checks the legacy App copy, compares the23 public JSON schemas and runs git diff --check. Its report is `work/phase8/preservation.json`. **All original files are byte-identical; final Phase8 work is additive only.** Existing working-tree edits from earlier phases remain untouched. No training, graph recomputation, label rewrite, new scientific result or Phase7 backend modification occurred. Frontend-derived descriptive summaries are transient displays of stored results.

| Original acceptance criterion | Final disposition |
| --- | --- |
|1 Existing React functionality retained|PASS: original files intact, lazy legacy workspace navigation verified; broad operational revalidation not claimed|
|2 Real Phase7 integration|PASS: all14 route patterns,18 successful GET responses|
|3 Overview|PASS|
|4 Dataset explorer|PASS: both PaySim identities explicit|
|5 E0–E5 comparison|PASS: compatibility enforced by existing backend|
|6 Split analysis|PASS: six stored splits and tested sample SD|
|7 Model-seed analysis|PASS: separate saved fixed-split evidence|
|8 Experiment details|PASS: metrics, versions, features, hashes and provenance|
|9 Reproducibility|PASS: saved scope shown; unavailable environment fields explicit|
|10 CREST availability|PASS: saved exploratory diagnostics, no generation|
|11 Scientific provenance|PASS: contextual notices and limitations page|
|12 Bounded rankings|PASS:25-row server pages and deterministic sort|
|13 Loading/unavailable/error states|PASS: deterministic and visual evidence|
|14 Responsive/accessibility testing|PASS within documented checks; not full accessibility certification|
|15 Types/lint/tests/build|PASS with42 documented legacy warnings, no final errors|
|16 Original backend/artifacts|PASS:87protected and765snapshot files unchanged|
|17 Documentation/Phase9 notes|PASS|
|18 Consistent monochrome identity|PASS across eight research pages; legacy workspace intentionally retained|
|19 Restrained accessible pixel motion|PASS: finite/reduced-motion/fallback checks|
|20 Actual loading/bundle measurement|PASS: lab data recorded; INP and long-term memory remain unmeasured|

### Remaining limitations and Phase9 readiness

Ready for a separately authorized Phase9 design/integration phase. Phase9 must obtain an approved graph-data contract before exposing transactions or identifiers, preserve the research GET boundary, use bounded/subsampled graph requests, handle worker-local pseudonyms explicitly and retain all scientific caveats. The static hero motif is decorative; the pre-existing legacy graph remains unchanged. No new graph explorer has started.

Outstanding issues: unresolved PaySim provenance, partial IBM label lineage, no CREST superiority, incomplete original E6 benchmark, process-local tokens, unavailable runtime/stability/environment API fields, legacy lint debt, no field INP/Lighthouse/full screen-reader audit/long-session memory study, and no production deployment validation. These limit interpretation and deployment claims, not the completed bounded Phase8 integration. No commit or deployment was performed.

## Complete Phase 8 file inventory

All entries below are new; no pre-phase source file remains modified by Phase8. Generated dist/node_modules and external work evidence are excluded from the source inventory.

- `docs/research/08_frontend_dashboard_integration.md`
- `frontend/.env.research.example`
- `frontend/playwright.config.ts`
- `frontend/research-tooling.json`
- `frontend/research.html`
- `frontend/scripts/verify_research.py`
- `frontend/src/LegacyApp.tsx`
- `frontend/src/ResearchApp.tsx`
- `frontend/src/research/client.ts`
- `frontend/src/research/contract.schema.json`
- `frontend/src/research/contract.ts`
- `frontend/src/research/fonts/ibmplexmono-OFL.txt`
- `frontend/src/research/fonts/pixelify-latin.woff2`
- `frontend/src/research/fonts/pixelifysans-OFL.txt`
- `frontend/src/research/fonts/plex-mono-latin.woff2`
- `frontend/src/research/fonts/silkscreen-OFL.txt`
- `frontend/src/research/fonts/silkscreen-latin.woff2`
- `frontend/src/research/fonts/sources.json`
- `frontend/src/research/pages/Comparison.tsx`
- `frontend/src/research/pages/Datasets.tsx`
- `frontend/src/research/pages/Diagnostics.tsx`
- `frontend/src/research/pages/Experiments.tsx`
- `frontend/src/research/pages/Limitations.tsx`
- `frontend/src/research/pages/Overview.tsx`
- `frontend/src/research/pages/Reproducibility.tsx`
- `frontend/src/research/pages/Seeds.tsx`
- `frontend/src/research/research.css`
- `frontend/src/research/state.ts`
- `frontend/src/research/ui.tsx`
- `frontend/tests/dashboard.spec.ts`
- `frontend/tests/fixtures.ts`
- `frontend/tests/performance.spec.ts`
- `frontend/tests/real-api.spec.ts`
- `frontend/tests/visual-final.spec.ts`
- `frontend/vite.research.config.ts`
