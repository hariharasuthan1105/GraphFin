# Phase 7 — Read-only research backend integration

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

## Integration plan recorded before production edits

Reuse the existing FastAPI v1 APIRouter, Pydantic v2 schemas, BaseAppException error envelope and disposable-copy test guard. Add one research catalog service, response schemas and GET-only router; register it in `backend/app/api/router.py`. Do not change main application startup, CORS, existing training/evaluation services, model implementations, data registries or frontend.

Serve a fixed allowlist of completed Phase 5/6A/6B/6C JSON artifacts, pinned to reviewed manifests and SHA256 values. Do not recursively discover filesystem files or accept client paths. Bound artifact bytes, cache size, page size and sort/filter enums. Reject symlink/junction escape, malformed JSON, unsupported schemas, missing manifests and hash mismatches. Never load Joblib/pickle, fit a model, rebuild a graph or generate an intervention.

Separate experiment status (verified/historical/exploratory/incomplete/unavailable) from label provenance (verified/partially_verified/unresolved). IBM baseline reproducibility does not independently verify labels; PaySim retains both conflicting label identities; CREST remains exploratory model response with no superiority or causality claim. Historical and unfinished runs are explicit descriptors, excluded from valid metric comparisons.

Normalize only approved public fields. Rankings and diagnostics use process-local keyed pseudonyms; no raw account IDs, transaction IDs, amounts, full features, source commands or local paths. Comparisons require identical dataset/label/train/test identities and comparable completed scope. Preserve AP ties, E4/E6_BASE distinctions and missing values. Cache by pinned identity and validate bytes before serving cached content.

Tests will use deterministic synthetic fixtures plus read-only actual-artifact smoke checks in disposable copies, including integrity tampering, traversal, pagination, schema/nonfinite behavior, privacy, no model/graph execution and existing-route compatibility. Record measured latency/memory, exact tests and protected-file preservation before acceptance.

## Completed integration and file inventory

Phase 7 adds a read-only projection of saved research, not another detector or application. The existing `backend/app/main.py` registers the existing v1 router and exception handlers. Its startup, CORS and old routes are unchanged. The new flow is HTTP GET -> typed research router -> injected catalog service -> pinned JSON manifests/artifacts -> explicit public Pydantic projection. No research execution dependency is called by these routes.

| File | Phase 7 change |
| --- | --- |
| `backend/app/api/router.py` | Import and register the research router; only existing production module edited in this phase |
| `backend/app/api/routes/research.py` | New 14 GET operations, bounded queries, response/error schemas |
| `backend/app/schemas/research.py` | New public typed contracts, finite JSON values, separate status/provenance |
| `backend/app/services/research_catalog_service.py` | New pinned JSON reader, validation, bounded cache, safe projections |
| `backend/app/services/research_catalog_v1.json` | New reviewed catalog with 27 logical artifact entries, manifest pins and split memberships |
| `backend/tests/test_phase7_research_api.py` | New 56 deterministic fixture tests |
| `backend/scripts/measure_phase7_api.py` | New disposable-copy HTTP measurement tool; execution/deserialization tripwires |
| `backend/scripts/verify_phase7.py` | New read-only preservation/evidence packaging tool; refuses existing output directory |
| `docs/research/07_readonly_api_integration.md` | Initial plan extended with implementation, evidence and frontend contract |
| `data/results/v2/phase7-api-verification-v1/` | New verification, performance, safe response examples, final OpenAPI, JUnit/log/exit and initial snapshot evidence |

The working tree already contained earlier-phase edits and untracked files. Those are not Phase 7 changes. No React, deployment, data processing, E0–E5 or CREST implementation changes were made.

## Artifact catalog and trust boundary

Catalog version is `graphfin-public-catalog-v1`. Seven approved run directories are fixed in code: `phase6c-evidence-v1`, `phase6b-consolidation-v1`, `phase6c-validation-v1`, `phase6a-explanations-v1-pilot-v2`, `phase5-baselines-5k-v1`, `phase5-baselines-50k-v1`, and `phase5-baselines-5k-replay-v1`. Catalog entries name reviewed JSON paths, SHA256, manifest path/SHA256, manifest version/stage/status markers, hash-map field and logical schema. They cover dataset/configuration/limitation tables, protocol, PaySim conflict evidence, baseline metrics, model-seed results/summaries/overlaps, replay evidence, saved explanations, twelve score maps and 5K replay result arrays. Two diagnostic support entries are approved but not currently projected.

The deployed catalog is trusted application configuration. Clients cannot choose it or supply an artifact path. There is no recursive filesystem discovery. Registering new evidence requires an explicit reviewed catalog update. A SHA256 match establishes byte identity to that reviewed catalog, not truth of upstream labels. Dataset hashes are read from pinned evidence; the API does not rehash original CSV datasets on every request. The final preservation verifier does check the original bytes.

Reads enforce JSON suffix, approved root, lexical path rules, resolved containment and rejection of symlinks/junctions including ancestors. Both manifest and artifact bytes are rehashed before cached content is used. Supported collection shapes, size limits, required protocol feature schema and Pydantic public types are checked. Unsupported structures produce controlled errors. Files are limited to 16 MiB each; the LRU retains at most four objects and at most 8 MiB of their serialized source bytes. This is not an 8 MiB process-RAM guarantee: Python objects, request buffers, imports and temporary sorting consume additional memory. The cache uses a lock and immutable identity/hash keys.

Operating-system write access to catalog/source files is outside the untrusted HTTP-client boundary. Deploy artifacts with read-only permissions; concurrent malicious filesystem replacement is not an adversarial race-proof storage design. The link rejection branch was regression-tested through a mocked symlink predicate; no privileged Windows junction creation test was performed. No authentication or rate limiting was added, and no CORS relaxation was made. These are local integration checks, not a penetration-test certification or deployment authorization.

## Scientific classification and supported scope

Every result envelope carries `status` independently from `provenance_status`. Status is `verified`, `historical`, `exploratory`, `incomplete` or `unavailable`; provenance is `verified`, `partially_verified` or `unresolved`. `verified` means the approved artifact was authenticated and projected, not verified financial ground truth. Page status describes the collection; each experiment's status remains authoritative.

The completed baseline table contains 84 method evaluations: seven methods (E0–E5 and E6_BASE), two tiers and six split seeds, at model seed 42. Overview reports 12 distinct dataset/split/model runs and 84 evaluations separately. Each method retains its artifact version and feature list. E6_BASE retains its own stored values and version; calibration ties prohibit substituting E4 values. Split seeds are 42, 123, 7, 2024, 99 and 555. Model-seed analysis is a separate saved 12-row analysis for E1/E4, two tiers, split 42 and model seeds 13/42/101.

IBM metadata reports actual active populations, retained transactions, positive/negative counts and source hashes. Upstream account-label lineage remains partially verified and features remain transductive. PaySim reports both `paysim-research-774` and `paysim-application-2606` label identities, their distinct hashes, 547,686-account population and 1,832 disagreements. Its scalar positives/negatives/prevalence remain null; neither label source is silently selected. Missing transaction count remains null. Simulation hours converted to synthetic timestamps are not presented as observed real-world dates.

`phase5-e6-incomplete` and `legacy-e0-e4` are explicit policy descriptors, not fabricated completed results. They carry incomplete/historical status and null metrics; they are excluded from metric comparisons. CREST diagnostics are saved exploratory model-response records. Detection superiority, explanation superiority and causal evidence of crime are unsupported. The Phase 5H ranking-extension stop decision remains intact. Bounded reproducibility does not establish independent financial generalization or manuscript submission readiness.

## Endpoint and schema reference

All paths below have prefix `/api/v1/research`. All are GET-only. OpenAPI is served at `/api/v1/openapi.json`, with a final snapshot in `phase7-api-verification-v1/openapi-final.json`. The exact generated field types, required/nullability rules, enums and error responses are authoritative there and in `backend/app/schemas/research.py`.

| Path | Response schema | Query / semantics |
| --- | --- | --- |
| `/overview` | `Overview` | Title, datasets, methods, run/evaluation counts, scales, availability, warnings |
| `/datasets` | `Page[Dataset]` | Fixed three-record bounded collection |
| `/datasets/{dataset_id}` | `Dataset` | `ibm-5k`, `ibm-50k`, `paysim` |
| `/experiments` | `Page[Experiment]` | Pagination and exact filters below |
| `/experiments/{experiment_id}` | `Experiment` | Full record including status and metrics when completed |
| `/experiments/{experiment_id}/metrics` | `Experiment` | Same envelope; noncompleted descriptor returns 409 |
| `/experiments/{experiment_id}/rankings` | `Page[Ranking]` | Pagination; `sort=score_desc` or `score_asc` |
| `/experiments/{experiment_id}/provenance` | `Experiment` | Exact identities and warnings; metrics intentionally null |
| `/comparisons` | `Comparison` | Repeated `experiment_id` (2–12 distinct), optional metric |
| `/reproducibility` | `Reproducibility` | Stored replay evidence and detector settings |
| `/model-seeds` | `ModelSeeds` | Optional dataset_id (`ibm-5k`/`ibm-50k`) and method (`E1`/`E4`) |
| `/diagnostics` | `Page[Diagnostic]` | Pagination of saved exploratory records |
| `/diagnostics/{diagnostic_id}` | `Diagnostic` | Saved `crest-NNN` index identity |
| `/limitations` | `Limitations` | Stored topic/assessment/description records |

`Evidence` fields are status, provenance_status, artifact_id, artifact_sha256 and limitations. `Page[T]` adds items, total, page and page_size. Artifact IDs are logical keys, never local paths. `Dataset` adds name/version/type/tier, accounts/transactions/positives/negatives/prevalence, label definition/sets/disagreements, transaction hash and time semantics. `LabelSet` contains identity, sha256, accounts and positives.

`Experiment` adds experiment_id, dataset_id, tier, method, version, feature_names, split_seed/model_seed, population_identity, dataset/label/train/test SHA256 and nullable `Metrics`. Metrics include count, positives, prevalence, average_precision, roc_auc, retrieval rows, nullable confidence_interval and uncertainty_note. Retrieval rows have k, effective_k, positives, precision and recall. No per-run confidence interval is supplied by these endpoints; SD must not be displayed as a CI. Missing/nonfinite metrics become JSON null, never zero.

`Ranking` contains only rank, account_token and anomaly_score. `Comparison` includes metric, shared population identity, experiment/value pairs and descriptive-only interpretation. `Reproducibility` includes replay tier/byte_identical/evidence hash/dataset hash/feature schema/model seed, detector n_estimators/max_samples/contamination and split seeds. The 5K endpoint verifies the pinned primary/replay result-array bytes; the 50K endpoint serves the pinned prior full replay-comparison evidence. Neither starts a new replay or rechecks all feature/score arrays on each HTTP request.

`ModelSeeds` exposes runs (identity, seeds, metrics, saved fit_score_seconds), summaries (mean/sample SD/min/max AP), and pairs (two seeds, ordinal Spearman and top-K overlap/Jaccard). `Diagnostic` exposes diagnostic_id, account_token, saved method/family, available/valid/reason, baseline/intervened score, signed_fidelity and omitted count/fractions. It omits raw accounts, transaction IDs, amounts, feature vectors, commands and local paths. Stored runtime and diagnostic stability support files are not exposed in this initial diagnostic projection.

Tokens use HMAC-SHA256 with a random process-local secret and dataset scope, truncated to 24 hex characters with `acct_` prefix. They are pseudonyms, not a formal anonymity guarantee. Tokens can link records within a process and dataset; they change across process restarts and differ across workers. Phase 8 must not persist them as durable account identities or assume cross-worker joins. Diagnostic index IDs refer only to the pinned diagnostic artifact order.

## Query rules, comparisons and errors

Paginated experiment/ranking/diagnostic routes accept `page_number=1..1000` and `page_size=1..100` (defaults 1 and 25). Beyond the final page returns items=[] with total unchanged. Experiment listing filters: dataset_id (`ibm-5k`, `ibm-50k`, `paysim`, `ibm-historical`), tier (`5k`, `50k`, `historical`), method (`E0`–`E5`, `E6_BASE`, `E6_CREST`, `E0-E4`), version (exact string, maximum 100 characters), split_seed/model_seed (0..2^32-1). No wildcard expressions or arbitrary sort fields are supported. Experiments sort lexically by experiment_id. Rankings sort by score then original lexical ID for deterministic ties; the ID is not returned. Rank is position in the requested ordering, so ascending rank 1 is the smallest finite score. Null scores sort last. Paging occurs after bounded score-map loading/sorting, not a claim of O(page_size) disk work.

First select records with `/experiments?dataset_id=ibm-5k&method=E4&split_seed=42`; then pass their IDs to comparisons. The comparison route itself accepts explicit experiment IDs, not duplicate dataset filters. Example: `/comparisons?experiment_id=baseline-5k-E1-s42-m42&experiment_id=baseline-5k-E4-s42-m42&metric=average_precision`. Metrics are allowlisted: average_precision, roc_auc, precision_at_10, precision_at_25, precision_at_50, precision_at_100.

Comparison compatibility requires identical dataset bytes, labels, training membership and held-out population. The population identity is SHA256 of canonical JSON containing dataset hash, label hash and membership metadata. Distinct split seeds/populations or tiers are rejected even if they share a dataset name. E4 and E6_BASE can be compared as distinct completed versions on the same population; their observed differences are descriptive. No significance test or missing-value imputation occurs.

| Condition | HTTP / behavior |
| --- | --- |
| Unknown valid experiment/dataset ID | 404 EXPERIMENT_NOT_FOUND / DATASET_NOT_FOUND |
| Missing diagnostic ID | 404 DIAGNOSTIC_UNAVAILABLE |
| Invalid ID, enum, metric, query bounds | 422 INVALID_RESEARCH_ID or VALIDATION_ERROR |
| Historical/incomplete metric/ranking request | 409 EXPERIMENT_INCOMPLETE |
| Incompatible or duplicate comparison | 409 INCOMPATIBLE_COMPARISON |
| Missing approved artifact/manifest | 503 RESEARCH_UNAVAILABLE |
| Missing diagnostic collection | 200 empty page, status unavailable |
| Hash or manifest authentication mismatch | 503 ARTIFACT_CHECKSUM_MISMATCH; never verified stale cache |
| Unsupported structure/version | 503 UNSUPPORTED_ARTIFACT_SCHEMA |
| Unsafe path / oversized file / score membership mismatch | 503 UNSAFE_ARTIFACT_PATH / ARTIFACT_TOO_LARGE / POPULATION_MISMATCH |
| PaySim unresolved labels | 200, provenance_status unresolved plus two label sets |
| Empty valid filter | 200, items=[], total=0 |
| POST/PUT/PATCH/DELETE on research paths | 405; no new mutation operations |

Application errors reuse `{error,message,details}`. Framework routing 404/405 responses use FastAPI's routing envelope. ErrorResponse is documented for 404/409/422/503, including the existing custom validation handler. Overview degrades individual missing/corrupt components into an unavailable status with safe component/error-code strings; it does not claim corrupted components are verified. API error messages do not include exception traces or internal paths. Existing request logging is unchanged; clients should not put financial records into query strings.

Real, sanitized response examples for all 14 paths are packaged in `response_examples.json`. For example its overview reports completed_run_count=12 and completed_evaluation_count=84 with provenance_status=unresolved; its PaySim response contains the two saved label identities and null aggregate positive count. These are actual returned values, not illustrative detector metrics.

## Tests and execution evidence

The disposable workflow was `python backend/scripts/verify_phase2.py ../../work/phase7-release-tests -- backend/tests/test_phase7_research_api.py backend/tests/test_paysim_integration.py backend/tests/test_phase2_correctness.py -q`. It copies source/artifacts outside the production repository, marks the copy as a test sandbox and isolates persistence through the existing fixtures. After the final OpenAPI error schema adjustment, the same three files were rerun in that disposable copy with `--junitxml=../final-results.xml`; final source was copied into it without changing research artifacts.

| Execution | Passed | Failed | Skipped | Blocked | Exit | Runner duration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial Phase 7 fixture run | 47 | 1 | 0 | 0 | 1 | 22.52 s |
| Expanded API/existing regression run | 119 | 0 | 0 | 0 | 0 | 31.83 s |
| Release disposable run | 119 | 0 | 0 | 0 | 0 | 35.89 s |
| Final source / OpenAPI contract regression | 119 | 0 | 0 | 0 | 0 | 39.98 s |
| Actual-artifact HTTP probe | 84 requests returned 200 | 0 | 0 | 0 | 0 | Per-route measurements below |

There are **119 distinct final regression tests**, not the sum of repeated executions: 56 Phase 7, 21 existing PaySim integration and 42 Phase 2 correctness tests. The initial failure was a test requesting `/openapi.json` instead of the application's actual `/api/v1/openapi.json`; the test now uses app.openapi_url. Final logs/JUnit/exit are under `work/phase7-release-tests/phase2-l1u43zup/` and copied into the verification package. Full historical backend coverage was not rerun or claimed in this phase. Existing Windows restricted-sandbox socketpair issues were avoided by approved disposable execution; no event-loop or application workaround was introduced.

Coverage includes all endpoints, data/provenance accuracy, metrics, compatible and incompatible comparisons, pagination/filter/sort validation, missing artifacts/IDs, cache tampering, schema errors, traversal/link rejection, privacy, null/nonfinite handling, score-population integrity, GET-only behavior, old evaluation API compatibility and OpenAPI. Tests fingerprint fixture artifacts before/after. Model fit, graph build and intervention generation are replaced by failure tripwires during research-route checks. The real-artifact probe also forbids joblib.load and verifies all fourteen paths six times. Test fixtures in legacy regression tests may train small synthetic models in isolation; no research model was refitted by the new routes or measurement tool.

## Measured performance and limits

Python 3.12.10, Windows 11 build 26300. For each route, one request after clearing the service cache followed by five requests; numbers below are milliseconds. The probe uses in-process TestClient without legacy application lifespan, so these measurements exclude server startup, TCP/TLS and deployment concurrency. Hash verification still occurs on warm requests. Five samples are not enough for a reliable tail-latency estimate. Raw timings are retained in performance.json.

| Route (50K E4 split42 for experiment details) | Cold ms | Warm median ms | Response bytes |
| --- | ---: | ---: | ---: |
| overview | 1548.46 | 1186.55 | 4010 |
| datasets | 126.01 | 107.37 | 3418 |
| datasets/paysim | 98.41 | 104.66 | 1194 |
| experiments (default 25) | 721.69 | 685.69 | 45153 |
| experiment detail | 763.41 | 747.56 | 2046 |
| metrics | 843.92 | 796.40 | 2046 |
| rankings (default 25) | 2202.40 | 715.57 | 2836 |
| provenance | 811.97 | 640.95 | 1415 |
| comparisons (two 5K methods) | 1490.72 | 1091.42 | 758 |
| reproducibility | 150.76 | 167.94 | 1036 |
| model-seeds | 98.84 | 108.62 | 13991 |
| diagnostics | 231.83 | 256.99 | 18154 |
| diagnostic detail | 248.02 | 222.55 | 725 |
| limitations | 63.65 | 40.94 | 1629 |

Process RSS after imports/before requests was 236,277,760 bytes; after requests 247,910,400 bytes; OS peak working set 266,747,904 bytes. The RSS increase was 11,632,640 bytes. These include the existing application and imported dependencies, not just the catalog. No deployment memory SLA is established. The performance probe used identical route execution code; the final exported OpenAPI additionally corrects the documented validation error schema.

The cache is lazy and bounded, but experiment projections repeat catalog reads and ranking requests still load a bounded score map and sort its population (14,998 accounts at the large tier). Measured overview/comparison latency around 1.1–1.2 s and cold rankings around 2.2 s are real constraints. Phase 8 should fetch on demand and avoid frequent polling or parallel requests per table cell. Request batching/index optimization and authenticated rate limiting are possible later engineering work, not implemented or benchmarked here.

## Phase 8 frontend contract (implementation deferred)

| View | Exact data source and rendering rule |
| --- | --- |
| Overview cards | Overview.project_title, completed_run_count, completed_evaluation_count, available_methods, scales; show unavailable_components and limitations |
| Dataset statistics | Dataset accounts/transactions/positives/negatives/prevalence; null means unavailable; show label_sets separately for PaySim |
| E0–E5 charts | Filter experiments to one dataset/tier/split/model; use returned IDs with comparisons; display method and version separately; E6_BASE optional distinct series |
| Six-split table | Fetch experiments for dataset_id, method and model_seed=42; page through total; columns split_seed, metrics.average_precision/roc_auc/retrieval; never mix historical descriptors |
| Model-seed plots | ModelSeeds.runs metrics.average_precision at seeds 13/42/101; summaries.sample_sd_ap is descriptive sample SD, not CI; pairs show saved overlap/Jaccard |
| Replay status | Reproducibility.replays byte_identical, tier, evidence/dataset hashes, feature_schema; clearly label prior saved verification scope |
| Provenance warnings | Always render provenance_status independently of status; unresolved PaySim and partially_verified IBM remain visible even when results are verified |
| CREST availability | Overview availability and diagnostics items.available/valid/reason; exploratory banner, model sensitivity only; missing collection is a legitimate empty state |
| Ranking table | Ranking.rank/account_token/anomaly_score only; page_number/page_size/sort; tokens are process-local; no fraud labels or persistent account links |
| Limitations | Limitations.items topic/assessment/description plus per-response limitations and uncertainty_note |

Generate or hand-map TypeScript types from the final OpenAPI without changing backend semantics. Treat JSON null explicitly, not through `value || 0`. Distinguish loading, empty, unavailable, incomplete and error states. Render 409 as an incompatibility/incomplete explanation, 422 as query correction, and 503 as unavailable integrity-checked evidence; never fall back to illustrative values or historical scores. A missing diagnostic must not trigger a generation request. Validate page bounds client-side as well; use returned total to navigate. Persist experiment IDs and query filters, not process-local account tokens. No React work has started.

## Preservation, limitations and acceptance

The preservation verifier compares 736 pre-edit snapshot files, allowing only the planned v1 router registration and this Phase 7 report to differ: **734 remain byte-identical**. This covers old backend methods, frontend, original data and Phase 1–6C reports/results. All **87 protected originals** match the byte-level policy and supplied ZIP, whose archive SHA256 is also checked. `git diff --check` and new-file trailing-whitespace checks pass. New verification output is append-only; historical result directories are not written. See verification.json for source/evidence hashes and exact test counts.

| Acceptance criterion | Result / evidence |
| --- | --- |
| 1 Secure read-only catalog | PASS: allowlist, manifest/hash/schema/path checks and tamper tests |
| 2 Overview | PASS: real HTTP and fixture tests; 12 runs / 84 evaluations |
| 3 Dataset APIs | PASS: IBM partial lineage, distinct unresolved PaySim identities |
| 4 Experiment/metrics | PASS: stored versioned methods, null uncertainty, incomplete descriptors |
| 5 Compatible comparisons | PASS: population identity checks and 409 regressions |
| 6 Replay/model-seed APIs | PASS: pinned evidence, saved 13/42/101 results |
| 7 Optional diagnostics | PASS: saved projections only, explicit unavailable states |
| 8 Scientific limitations/provenance | PASS: independent classifications and warnings |
| 9 Safe pagination/filtering | PASS: validated limits, enums, deterministic order |
| 10 Missing/incomplete handling | PASS: explicit errors/statuses without fabricated values |
| 11 Historical preservation | PASS: 87 original ZIP matches and 734 unchanged snapshot files |
| 12 No new route fitting/graph recomputation | PASS: tripwire tests and actual-artifact probe |
| 13 OpenAPI | PASS: all 14 GET operations and typed error/public schemas |
| 14 Backend integration tests | PASS: 119 distinct final tests, exit 0; initial test-path failure documented |
| 15 Phase 8 contract | PASS: schemas, queries, ten view mappings and empty/error rules above |

Phase 7 is complete within this bounded backend-integration scope. Ready for Phase 8 read-only frontend integration with the documented latency, token-lifetime and provenance restrictions. This does not certify production security, detector superiority or manuscript readiness. No new experiment, frontend work, deployment or commit was performed.
