# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

## Phase 2 — Scientific Correctness and Reproducibility

Completed: 2026-10-20, Asia/Calcutta (implementation and full-suite execution began 2026-10-19). Baseline: `cd4a3fd`, the supplied ZIP plus completed Phase 1 audit. This phase repairs evaluation contracts and creates reproducible execution; it does not establish accuracy improvements, novelty, or publication readiness. E6_CREST, GNNs and dashboard redesign are not implemented.

### 1. Recovery and protected history

The resumed checkout contained eight modified tracked files: `schemas/anomaly.py`, `schemas/transfer.py`, and services `anomaly_service.py`, `baseline_service.py`, `evaluation_service.py`, `label_registry.py`, `split_service.py`, `transfer_service.py` under `backend/app/`. Two untracked files were also present: `services/research_identity.py` and `docs/research/protected_artifacts_v1.json`. Actual recovered diff was 91 insertions/95 deletions under the original Git line-ending setting, rather than the prior session's reported count. Existing changes were retained and reviewed; no destructive Git reset/clean occurred.

The lookup/evaluation checks and bootstrap replacement existed but were untested. Baseline identifiers were only partially connected, label identities had no research enforcement, and deterministic execution/tests/reporting remained unfinished. The pre-edit manifest already recorded 87 protected files, including datasets, all supplied result artifacts, and frontend files. Recovery verification found zero differences.

Authority is the **supplied ZIP's exact bytes**, SHA-256 `02c3b4d4d4c41c259ba1efb668c12551992d174ee2deb2960dcc00fba00a4531`, not a claimed original publication checkout. `protected_artifacts_v1.json` names that authority and baseline commit. `artifact_integrity.py` verifies each listed file, including absence checks. `.gitattributes` prevents automatic line-ending conversion of data and frontend bytes; Git `core.autocrlf` is disabled locally. None of these measures normalizes existing protected files.

Historical E0–E5 JSON/CSV metrics and intervals remain unchanged. New configured runs use `data/results/v2/<run-id>/` or an explicit output root outside the repository. Existing run directories cannot be overwritten. The transfer API writes into a unique `data/results/v2/transfer_api/` directory; generic/final legacy runners use separate v2 namespaces. A generic explicit output cannot target a protected path. The obsolete transfer script fails before doing work because its hardcoded UUID aliases silently select a demo slice; its historical implementation remains available in the Git baseline and the file's retained body.

### 2. Split-specific model lookup and evaluation isolation

Root cause: `_load_artifact` continued from a missing split key/path to the unsplit cache/file, and neither cached nor split-file metadata was checked consistently. Evaluation could then use split B's test IDs with split A's trained model.

`anomaly_service.py` now resolves an explicit `(dataset, experiment, split)` exactly. Missing/corrupt/mismatched artifacts raise `ModelNotTrainedException`; no unsplit recovery is attempted. Top-level and metadata dataset/experiment/split identities must agree. Invalid cached entries are evicted and scored caches invalidated. Unsplit lookup remains available only when no split is requested, including the original default artifact filename and absent legacy default experiment field. The original public missing-model error wording and HTTP 404 contract are preserved.

`split_service.py` verifies cached/disk assignment identity, duplicate IDs and train/test overlap. `evaluation_service.py` checks stored training IDs against the current split and requires complete test-ID coverage. The previous 100,000 prediction cap is removed for evaluation. Training artifact ID lists are copied instead of sharing mutable list objects with split assignments; the first focused test run exposed this additional aliasing issue.

These checks establish dataset/experiment/split and membership consistency. They do not retroactively add dataset-byte hashes to old joblib artifacts. The v2 runner avoids the legacy model cache and reconstructs from checksummed inputs. A full-observation graph is still built before entity splitting: the estimand is **transductive entity holdout**, not prospective temporal or inductive unseen-graph detection.

### 3. Explicit E0 definitions

`research_identity.py` defines versioned contracts. Every contract also records the actual ordered feature list: a version name alone does not identify a feature configuration.

| Implementation ID | Mathematical definition | Distinctions |
|---|---|---|
| `e0-offline-signed-zero-v1` | `s(x)=max_j z_j`; `z_j=(x_j−μ_j)/σ_j` when σ>1e−9, otherwise 0 | Training mean/std, ddof=0, existing float32 features, score rounded to 4 decimals; whole-population percentile is presentation only. Generic runner uses 3 features, graph-group calls use 6. |
| `e0-transfer-signed-unit-v1` | `s(x)=max_j (x_j−μ_j)/d_j`; d=σ when σ≥1e−9, otherwise 1 | Source-training statistics; raw signed z for evaluation. Source-constant features can contribute nonzero target deviations. |
| `e0-replay-absolute-leading-v1` | Maximum absolute z; 0 when σ≤1e−8 | Rounded stored statistics; absent column indices cause leading-column fallback; clipped linear risk. Documented legacy replay behavior, not a valid offline-equivalent research oracle. |
| `e0-source-signed-zero-v2` | Maximum signed z, zero contribution when source-training σ≤1e−9 | Float64 training statistics over existing float32 features; explicit graph-six feature selection; unrounded scores; threshold predeclared in config. |

For a constant source feature 5 and target value 8, v1 offline/v2 contribution is 0 while transfer v1 contributes 3. For μ=5, σ=1, x=2, signed z is −3 and absolute z is +3. These are formula differences, not empirical improvements. Thresholding remains `s≥z_threshold` (default 2); no label-driven threshold search is introduced.

Baseline service model metadata, evaluation responses, generic runner manifests and new final-run JSON records expose implementation identity/contracts; transfer results expose their own contracts. IF source-scaling/percentile API behavior is explicitly distinguished from the new runner's raw-feature, `−decision_function` protocol. Existing E1–E5 feature groups and fitting algorithms are retained. The v2 runner supports E0–E5, but does not pretend its scoring and protocol are byte-equivalent to historical runs.

### 4. Bootstrap AP correction

The point estimate used sklearn AP, while each historical bootstrap draw used per-positive rank precision after a stable sort. That formula only agrees with threshold-grouped AP under appropriate tie-free conditions. For y=[1,0,1,0] and equal scores, grouped AP is 0.5, whereas the old rank formula gives 5/6. Stable sorting does not remove arbitrary tie-order dependence. Resampling itself can create repeated observations/scores.

The corrected statistic is `AP=Σ_k (R_k−R_(k−1)) P_k` across distinct score thresholds, implemented by `sklearn.metrics.average_precision_score` **on every resample**, exactly as for the point estimate. `compute_bootstrap_pr_auc_ci` validates aligned one-dimensional binary labels and finite scores. Sampling uses `numpy.random.RandomState(bootstrap_seed)` with N IID account indices drawn with replacement for each iteration; no prevalence-preserving stratification is claimed.

- Zero-positive draws are undefined under this research policy and skipped/count-reported.
- All-positive draws have AP=1, matching sklearn; ROC-AUC remains undefined for either single-class case.
- Empty/all-negative evaluation inputs have `point_defined=false`; no valid draws give `interval_defined=false` and a reason. Compatibility numeric fields use a zero sentinel, **not a valid AP/CI claim**. New v2 results serialize undefined AP as JSON null.
- `requested_resamples`, `valid_resamples`, `skipped_resamples` and `statistic_version=sklearn-ap-iid-v2` are explicit. Historical records without a version default to `legacy-unspecified` rather than being relabeled corrected.
- Input scores and per-draw statistics are unrounded. The returned point estimate is full precision; CI presentation fields round only after quantiles. Saved account scores use 17 significant digits. New results distinguish full-precision AP from `ap_ci_display`.

Percentile 2.5/97.5 bounds are conditional on nonzero-positive draws when skips occur; rare-positive intervals may be unstable. IID account resampling ignores financial-graph dependence and does not quantify dataset shift, model-refitting variability or split uncertainty. No coverage guarantee or statistical superiority is claimed. Previously stored CIs were not recomputed or edited. Transfer API IF scores retain their versioned percentile mapping; the configuration-driven runner evaluates unrounded raw anomaly scores.

### 5. Dataset and label provenance

Both original PaySim label files still cover exactly 547,686 accounts. Research labels have 774 positives; application labels have 2,606; the 774 are a subset, and 1,832 additional accounts are positive only in the application file. This is **not an entity-population difference**. In the supplied transactions, extra positives are one sender-only and 1,831 receiver-only accounts. Broader-history involvement is plausible but unproven. Transaction-level `isFraud` and an authoritative generator for `account,label,label_meaning` are absent. Neither file is certified correct.

| Path | Effective population and labels |
|---|---|
| `DatasetRegistry.load_paysim`, including UUID alias | First 10,000 canonical transactions, 18,711 active accounts; prefers `paysim_account_labels.csv` (129 matched positives), fallback `paysim_labels.csv` (12). Metadata now explicitly says production/demo prefix and unresolved provenance. |
| Original legacy transfer script | Writes a full processed CSV under the alias, but alias loader still uses the prefix; then explicitly reloads `paysim_labels.csv`. Disabled before execution rather than perpetuating that silent mismatch. |
| `convert_paysim.py` | Seeded raw-row sampling when configured, then endpoint OR aggregation on sampled retained fraud flags; outputs `user_id,label`. Optional account selection is label-dependent. Not a demonstrated generator of the conflicting application file. |
| `paysim_adapter.py` | Aggregates endpoint involvement over supplied raw rows; optional prefix limits change evidence population. No archived raw evidence available for reconstruction. |
| New configured runner | Explicit transaction file/hash, full-file or recorded prefix, label file/hash/ID/definition/status. No implicit UUID alias, auto-selected labels, or performance-based label choice. |

Known hashes map to `paysim-research-774` and `paysim-application-2606`. The original uploaded bytes—not a reserialized matched subset—identify registry labels. Research entry points require the exact selected identity and acknowledgement for unresolved labels. The v2 runner also recognizes PaySim family configuration and requires `provenance_status=unresolved_conflict`. Acknowledgement permits a clearly labeled diagnostic; it does **not** resolve provenance. Ordinary runtime loading remains available, while unresolved labels cannot receive a new paper-reportable flag from the evaluation/transfer services.

Custom and IBM labels are marked declared/unverified rather than automatically proven. Every active entity must have an explicit binary label in the new runner; missing labels are not silently treated as negatives. Training and feature calculations receive no label vector. Source labels may stratify a predeclared split; target labels are evaluated only after source fitting. A regression changes all target labels and verifies unchanged fitted parameters and score arrays.

### 6. Deterministic execution and manifest

Entry point: `python -m backend.app.services.research_protocol CONFIG.json OUTPUT_ROOT RUN_ID`. `ResearchConfig`/`InputSpec` reject unknown keys. Paths resolve relative to the config; saved configs rewrite relative paths for replay from their saved location. Full input SHA-256 checks precede feature extraction. Existing GraphService/FeatureService compute the unchanged canonical graph and 23-column matrix; E0/E1 select six graph columns, E2 fourteen, E3 eleven, E4 nineteen, E5 four egonet columns.

Canonical preprocessing v1 validates transaction schema/IDs, finite amounts and parseable timestamps, then retains positive non-self transfers; it does not introduce label-based sampling. Data bytes remain unchanged. Split seed, IF seed and bootstrap seed are separate explicit fields. Graph sampling remains the existing seed 42, with the effective k, NetworkX version and graph insertion-order hash recorded. IF uses n_jobs=1 in v2; hyperparameters and threshold are explicit, not estimated from held-out prevalence.

Saved files per immutable run directory:

| File | Purpose |
|---|---|
| `config.json` | Expanded execution configuration, replayable from its saved location |
| `split.json` | Exact source train/test IDs; no training label vector is stored here |
| `source_held_out_scores.csv` | Account ID, evaluation label, unrounded anomaly score, prediction for every source test account |
| `target_held_out_scores.csv` (transfer only) | Every target account, never source-fitted; no target-label-based partition/tuning |
| `results.json` | Full-precision AP/ROC-AUC where defined, explicit CI diagnostics and counts |
| `manifest.json` | Protocol/title, input/label identities and checksums, schema/selected features, algorithm contract, fitted parameters, seed roles, population/positive counts, split and feature hashes, library/code identity, artifact paths/hashes, score orientation, metric definitions and timings |

Only account identifiers required for alignment, evaluation labels and scores are persisted; no raw transaction histories, balances or counterparties are copied into prediction artifacts. Treat score files as evaluation-only data. Input reconstruction still requires access to the exact source files. Recorded code and library versions are necessary: deterministic results are not promised across different NetworkX/sklearn versions or hardware arithmetic. `environment_phase2_versions.json` records the tested direct/runtime dependency versions; it is an environment snapshot, not a universal cross-platform lockfile.

Target transfer in v2 evaluates all target accounts under source-fitted preprocessing/model. It therefore differs from historical target 70/30 entity-subset evaluation and is identified accordingly. Legacy generic/API runners remain explicitly labeled compatibility protocols; the configuration-driven runner is the supported path for full raw-score replay. No historical table is used as a target for parameter selection.

### 7. Integrity-test policy

The two old tests expected CRLF hashes, whereas the ZIP contains LF bytes. In-memory LF→CRLF conversion exactly reproduces the old hashes:

| File | Authoritative supplied-LF SHA-256 | Prior CRLF SHA-256 (equivalence diagnostic only) |
|---|---|---|
| `final_e0_e4_comparison.json` | `525b7b696044bd3af0017e8f8b6bba7c4a28e2dfba74837c4b0dcb84b5f1ba9d` | `e16e2d5948b66f0cde493fadf43e1491fee219b582faa6a38eabfe53be786ad2` |
| `final_e0_e4_comparison.csv` | `5beff23b238d9db217d15f410a1599842f157e59fdf209843c3898602a141aa9` | `ba89012faf612cfe96d9e5049a869c40596894d167d37bb26a1581d976efa40a` |

Existing integrity tests now reference the versioned `supplied-zip-bytes-v1` manifest. Focused tests separately retain the old CRLF expectations and check the transformation in memory; normalized equivalence is not an alternative pass condition. Missing files or unexplained byte changes fail exact integrity. This is a documented change of fixture authority, not rewriting results to satisfy a test.

### 8. Safe verification workflow

`backend/scripts/verify_phase2.py SCRATCH_DIRECTORY -- [pytest arguments]` copies the repository into a fresh directory outside the source checkout, excludes Git/node_modules/caches, sets temporary/matplotlib paths, writes a sandbox marker, and saves command, log and JUnit output. `conftest.py` rejects test sessions without the matching marker before destructive cleanup fixtures run. Source production models/splits are not used by tests. Tests require the project's installed dependencies; no application event-loop monkeypatch is introduced.

The separate 15-second `socket.socketpair()` probe hangs in sandboxed Windows `_fallback_socketpair → accept`, but passes when approved outside the sandbox. This local comparison establishes the sandbox boundary as the observed blocker; it does not identify a specific OS firewall/security implementation. Approved unrestricted test execution still uses disposable repositories. This allows API verification that Phase 1 could not complete.

The first targeted run had 38 passes and one failure: mutating the cached artifact's training IDs also mutated the split list. Copying the ID list fixed that defect; the next targeted run passed all 39 tests. An initial broader run exposed two missing-model message compatibility assertions; both passed in the final 42-case focused run after the original wording was restored.

The initial broad run was then deliberately interrupted after discovery of persistent test-state leakage: clearing in-memory labels left `data/processed/paysim_labels.csv` available to later miniature exploration fixtures. Those fixtures repeatedly parsed a prior test's 547,686-row file despite having five unrelated accounts. This was test-order dependence, separate from the socket blocker. `conftest.py` now assigns each test its own temporary processed-data directory and split storage, clears split caches, and retains disk persistence within each individual test. No label parser or dataset bytes were changed to accelerate testing. A fresh full suite uses this isolated fixture and all final code edits. The interrupted run is retained as partial evidence and is not counted as a completed suite.

### 9. Final verification and acceptance

The recovered full run **completed**; it was not restarted. Its log and JUnit both report **266 passed, 1 skipped, 0 failures/errors**, with pytest wall time **639.88 seconds** (JUnit suite time 639.740 seconds). Its terminal session had expired at recovery, and the wrapper had not persisted its process exit code. That exit code is therefore **unavailable**, not represented as an observed 0. The complete pytest summary and valid final JUnit independently establish the test outcomes.

| Execution | Passed | Failed | Skipped | Blocked | Duration / observed exit |
|---|---:|---:|---:|---:|---|
| Full backend, `phase2-433s2y7n` | 266 | 0 | 1 | 0 | 639.88 s; process exit status not retained |
| Final Phase 2 checks including two added isolation cases, `phase2-ghn99x_n` | 42 | 0 | 0 | 0 | 11.35 s; exit 0 |
| Earlier compatibility/focused checks, `phase2-5tdorj3e` | 42 | 0 | 0 | 0 | 13.31 s; exit 0 |

The final follow-up repeats 40 existing Phase 2 cases and adds two parametrized isolation cases. Thus the latest per-test inventory is **268 distinct passed, 0 failed, 1 skipped, 0 blocked**, not the sum of overlapping runs. No production code or fixture changed after the completed full suite; only these two additional regression cases and documentation/evidence were added. The cases intentionally leave stale PaySim disk labels and cached split state, then verify that the next case receives a fresh temporary directory and empty registries. Temporary directories remain available for diagnosis; production directories are never used for their persistence. Model cleanup remains confined to the guarded disposable repository copy.

The one skipped case is `test_locked_datasets_backend_resolvability`: historical processed CSVs `ddbaab44-78b6-41be-a8fb-e83dfec66358.csv` and `03fb9ab0-4f42-4404-9d76-723fd4d8753e.csv` were absent in the supplied checkout. This is an unavailable historical-environment dependency, not an observed application failure. They were not regenerated to force a pass. The Windows sandbox socket blocker was bypassed by approved unrestricted execution of disposable tests; no API cases remain blocked in that execution environment.

Evidence under the enclosing workspace's `outputs/phase2_evidence/` includes each run's `command.txt`, `pytest.log`, and `results.xml`; `test_inventory.json` names every test and its latest outcome. Intermediate failures and the intentionally interrupted earlier suite remain preserved separately. The full report is `phase2-433s2y7n/results.xml`; the final added-regression report is `phase2-ghn99x_n/results.xml`.

Frontend verification used the existing CI installation command, `npm ci`, in `work/phase2-frontend`, outside the source repository. Installation succeeded (146 packages). `npm run lint` exited 0 with existing React/hooks/unused-expression warnings; `npm run build` exited 0 after TypeScript and Vite (653 modules, Vite build 3.16 seconds). No frontend source, lockfile, or dependency definition was edited. The preserved build-output tail is in `../phase2_evidence/frontend_build_tail.txt` relative to the repository root's parent output directory.

The existing IBM medium fixture supplied a measured smoke test: 5,000 accounts, 3,500 train/1,500 held out, 14/6 positive labels, split seed 42, model seed 17, bootstrap seed 123. Both E0 and E4 were run twice; the second run loaded the first run's saved configuration. All six comparisons (scores, split, results for both methods) had identical SHA-256 values. Manifest timings and relocated configuration paths are expected to differ; manifest byte equality is not the reproducibility criterion. E0 total runtimes were 6.066/4.974 seconds and E4 5.910/5.554 seconds. These are single-machine smoke measurements, not comparative performance claims. The 100 bootstrap draws are a runtime smoke setting, not a publication recommendation. No historical ranking is inferred from these new versioned runs.

Configurations are `docs/research/configs/phase2_ibm_medium_e0.json` and `phase2_ibm_medium_e4.json`. New outputs are `data/results/v2/phase2-smoke-{e0,e4}-{a,b}/`. Those generated directories follow the existing Git-ignore policy and must be preserved/exported separately if moving the checkout; they are not silently included in a recommended source commit. `outputs/phase2_evidence/smoke_summary.json` in the enclosing workspace records the equality checks and measured results. Reproduction example, from the repository root:

```powershell
python -m backend.app.services.research_protocol docs/research/configs/phase2_ibm_medium_e4.json data/results/v2 my-new-e4-run
python backend/scripts/verify_phase2.py ../phase2-test-scratch -- -q backend/tests
```

The final integrity diagnostic compares each of 87 protected paths against both its manifest entry and the supplied ZIP member; all 87 match. It also verifies that the Phase 1 audit has no diff from `cd4a3fd` and that `git diff --check` exits 0. Full paths and hashes are preserved in the enclosing workspace's `outputs/phase2_evidence/integrity_verification.json`.

### 10. Changed-file inventory

All nine original Phase 2 criteria are satisfied at the documented scope:

| Acceptance criterion | Disposition and evidence |
|---|---|
| 1. Split-specific lookup fails safely | Satisfied: cache/disk identity, missing/corrupt model and membership/coverage regressions pass |
| 2. Baseline variants identifiable | Satisfied: four explicit E0 contracts and ordered feature lists |
| 3. Bootstrap AP tie-correct | Satisfied: each seeded draw checked against sklearn, including ties and one-class policies |
| 4. PaySim provenance explicit | Satisfied: both byte identities preserved; unresolved conflict and acknowledgement required |
| 5. New runs reproducible | Satisfied: E0–E5 fixture replay tests; saved E0/E4 IBM scores, splits and metrics match |
| 6. Defensible integrity policy | Satisfied: exact supplied-ZIP authority, separate in-memory CRLF diagnostic |
| 7. Available regressions pass | Satisfied: 268 distinct passes, no remaining failures; one unavailable historical-fixture skip |
| 8. Blocks and limitations transparent | Satisfied: skip, historical sandbox blocker, unavailable recovered process exit status, provenance and statistical limits disclosed |
| 9. Protected artifacts unchanged | Satisfied: all 87 exact-byte comparisons against manifest and ZIP pass |

Recommend a reviewed Phase 2 commit: `fix(research): enforce evaluation correctness and reproducible v2 runs`. No commit was created. Preserve the generated evidence and ignored v2 run directories separately when transferring the project.

All paths below are relative to this repository. Sixteen existing files were modified:

| Files | Purpose |
|---|---|
| `backend/app/schemas/anomaly.py`, `evaluation.py`, `transfer.py` | Version/label contracts, bootstrap-definedness diagnostics, explicit transfer identity and model seed |
| `backend/app/services/anomaly_service.py`, `split_service.py`, `evaluation_service.py` | Exact model/split lookup, identity/membership/coverage validation and evaluation metadata |
| `backend/app/services/baseline_service.py` | Explicit legacy E0 contract and copied training membership |
| `backend/app/services/label_registry.py`, `dataset_registry.py` | Byte-identified label sets, unresolved-provenance enforcement and explicit production population |
| `backend/app/services/transfer_service.py` | Tie-correct bootstrap, metadata and versioned export destination |
| `backend/app/services/research_runner.py` | Label/implementation provenance and separate output namespace |
| `backend/scripts/run_final_research_evaluation.py`, `run_transfer_experiment.py` | Versioned final-run metadata/output and fail-fast obsolete transfer entry point |
| `backend/tests/conftest.py` | Disposable-copy safety guard and per-test disk-label/split isolation |
| `backend/tests/test_locked_datasets_regression.py`, `test_reports.py` | Documented exact supplied-byte fixture authority |

Eleven new files complete the implementation:

- `.gitattributes`.
- `backend/app/services/artifact_integrity.py`, `research_identity.py`, `research_protocol.py`.
- `backend/scripts/verify_phase2.py`.
- `backend/tests/test_phase2_correctness.py`.
- `docs/research/protected_artifacts_v1.json`, `environment_phase2_versions.json`, `02_reproducibility_and_correctness.md`.
- `docs/research/configs/phase2_ibm_medium_e0.json`, `phase2_ibm_medium_e4.json`.

The enclosing workspace additionally contains disposable test repositories and `outputs/phase2_evidence/` with command transcripts, JUnit reports, smoke results and integrity evidence. These are verification artifacts, not changes to original application data.

### 11. Residual limitations and Phase 3 boundary

PaySim labels remain unresolved; authoritative raw fraud flags, transformation code and evidence-population documentation are required to resolve them. Historical single-run versus multi-seed rankings retain the Phase 1 interpretation: stored multi-seed trials varied entity splits, with model seed fixed at 42; finite-positive test populations, differing E0 definitions and scoring paths preclude treating a single run as a stable ordering. Historical metrics and intervals were not rerun or replaced in Phase 2.

Existing graph feature computation remains transductive, and its legacy centrality-error fallback remains unchanged. IID account bootstrap is not a graph-dependent or refit uncertainty analysis. Legacy generic/API protocols still have their documented rounding/scoring conventions; only the new configured runner promises the complete raw-score replay contract. Its input/output protocol, independent seeds, label-free fit boundary, versioned feature/model identities and regression fixtures are suitable foundations for a later experimental extension. This is engineering readiness for a separately authorized Phase 3, not paper readiness, demonstrated novelty or predictive superiority. Phase 3 has not started.
