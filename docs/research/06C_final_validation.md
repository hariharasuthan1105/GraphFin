# Phase 6C — Final research validation

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Final review date: 2026-10-24. Phase 6C closes the bounded replay and model-seed evidence gaps. It does **not** establish CREST superiority, resolve raw-label provenance or certify the existing manuscript as submission-ready. No original data, historical result, E0–E5 implementation, frontend or manuscript was changed; no commit or deployment was made.

## Recovery and implementation status

| Component | Final disposition |
|---|---|
| `backend/scripts/validate_phase6c.py` | Complete: exclusive output namespaces, protocol written before fits, dedicated child resource limits, fresh50K reconstruction/refits and fixed split model-seed analysis. Recovered outputs retained; no successful experiment repeated. |
| `backend/scripts/package_phase6c.py` | Complete: label inventory, exact metric alignment, tablesA–G, separate calibration results, claims/bibliography/flowchart/supporting hashes. Package verified after execution. |
| `backend/tests/test_phase6c_validation.py` | Four cases covering exclusive records and child time/memory/success behavior; executed in disposable copies. |
| `backend/scripts/verify_phase6c.py` | Final read-only reconstruction of completed manifests, saved metrics/rank stability, replay byte comparisons, test evidence and protected history. Writes only a new review directory. |
| Four `06C_*.md` reports | Complete evidence interpretation, provenance, replay, release inventory and readiness assessment. Earlier two draft reports preserved and completed. |

Sixteen tracked modifications in `git status` predate this phase and are preserved. No destructive Git command was used. The Phase 6C snapshot includes623 files:622 pre-existing research/application/data/document files plus the newly written validation script. Final comparison covers every snapshot member; the87 protected originals are also compared with the supplied ZIP. The scripts/outputs capture current git HEAD, dirty-diff hash, source hashes, dataset hashes, feature schema, configuration, environment and seeds. Git HEAD alone is not an experiment identity.

## Replay and numerical verification

Fresh ~50K feature reconstruction: **75.912462seconds**, sampled peak RSS **528,474,112bytes**. Fresh six-split baseline fit/scoring/evaluation: **132.305534seconds**, peak **284,782,592bytes**. Each worker limit was600seconds/2GiB; both exited0 without a budget stop. No prior prediction arrays were loaded as the computed result.

`features.npy`, population IDs/labels, six split memberships, all six seven-method score files, results and summaries are **byte-identical**, tolerance0. Exact comparisons and checksums are in `phase6c-validation-v1/replay_comparison.json`; the final verifier also checks the existing six-score-file 5K replay. Timing/memory/run identity are excluded. This is deterministic same-input replay, not external validation.

## Label and comparability findings

IBM label lineage is **PARTIALLY VERIFIED**. Converter code implements retained-transaction endpoint OR; supplied population counts, unique IDs, active filtering, train/test membership and score alignment are verified. Original raw laundering flags are absent from supplied canonical CSVs, preventing independent ground-truth reconstruction. Monetary rounding occurs after converter labeling and can remove zero-rounded events during later ingestion, so code-level OR and current retained-history truth must not be conflated. The50K input loses ten rows/eight negative-only inactive accounts; all249 positive account labels remain. Detailed steps/hashes are in `06C_label_lineage.md` and `ibm_lineage.json`.

PaySim remains **unresolved**: both label files contain547,686 unique accounts,774 versus2,606 positives and1,832 disagreements. Additional positives are1,831 receiver-only and one sender-only account in supplied history. This is evidence of role distribution, not proof of a generation explanation. Raw fraud flags and authenticated generation lineage are absent. API success does not certify label truth or transfer accuracy.

Within each Phase 5 tier/split, E0–E5 compare the same held-out accounts and labels under documented feature groups. E0 is signed-zero source z-scoring; IF uses100trees, max_samples auto, contamination.005, model42, rawfloat32, no scaler and negative decision function. Full-observation features remain transductive. Historical rounded/version-different results stay separate; E6_BASE is calibration-only, separated because score ties can change AP. TablesA–G and per-seed figure-ready files are in `data/results/v2/phase6c-evidence-v1/`.

## Model randomness: new bounded evidence

Twelve completed runs: E1/E4 × IBM 5K/~50K × model seeds13/42/101, with split42 and identical features/memberships. Worker wall21.308303seconds, peak233,308,160bytes, exit0. Every model42 control reproduces saved scores. No seed was selected as the official winner.

| Tier/method | Mean AP | Sample SD | Min AP | Max AP |
|---|---:|---:|---:|---:|
| 5K E1 | .099345 | .072936 | .057130 | .183564 |
| 5K E4 | .190727 | .003307 | .188817 | .194545 |
| ~50K E1 | .017713 | .003935 | .015136 | .022242 |
| ~50K E4 | .015868 | .002633 | .013860 | .018850 |

All per-seed AP/ROC-AUC/P@K/positive-hit/runtime observations are appended in `06C_replay_and_seed_analysis.md` and retained at full precision in JSON/CSV. Pairwise ordinal Spearman ranges .966492–.990139; top10 overlap ranges .5–.9. High overall rank correlation does not imply stable rare-positive AP. These ranges describe the measured twelve pairs only, not general robustness. Six-split variability and three-model-seed variability are separate conditional analyses; E2/E3/E5 model-seed variability remains unmeasured.

## Tests and interrupted attempts

See the final test ledger below for observed counts/durations/exits. No count is inferred from uncompleted sessions.

- The original mixed restricted run was manually interrupted, observed wrapper exit1, with no final result report; do not count its partial progress.
- A separate restricted API diagnostic captured the hang at `socket._fallback_socketpair` during Windows asyncio initialization before application response; interrupted exit1. The approved disposable PaySim integration suite subsequently passed21 tests in3.89seconds, exit0, with unchanged application code. The environmental API blocker is resolved for that permitted test environment.
- The restricted87-test regression attempt terminated in a native Windows access violation while pandas/Arrow constructed rows during label loading. No final JUnit or recovered process exit was available. This is a crashed run, not a pytest assertion failure or proof of an application algorithm defect. Exact native root cause is unestablished; the final approved rerun is the comparative check. Slow loading of547,686 label rows via `iterrows` is a separate observed cost.
- The preliminary four guard tests passed in0.58seconds, exit0; they are repeated in the final regression inventory and must not be double-counted.

The full application suite was not rerun. Relevant source-isolation, labels, bootstrap ties, benchmark, transfer, converter, integration and new guard cases were selected. Safe wrapper copies and per-test persistence kept state outside real project data.

## Final scientific gate

| Question | Decision | Evidence and qualification |
|---|---|---|
| A. IBM 5K reproducible? | **YES**, supplied-file scope | Existing independent replay rechecked across all six score files/results/summary; original data identities preserved. |
| B. IBM ~50K reproducible? | **YES**, same environment/input | Fresh graph/features/refits and six score arrays exactly match. Not external validation. |
| C. IBM ground truth independently verifiable? | **NO** from available inputs | Raw laundering flags and authenticated conversion source absent. Overall lineage **PARTIALLY VERIFIED**. |
| D. PaySim provenance resolved? | **NO** | Common population,1832 conflicting assignments; no authenticated generator for both files. |
| E. Model-seed sensitivity characterized? | **PARTIALLY** | Complete for E1/E4, split42, three seeds/two tiers; insufficient for general robustness or other methods. |
| F. E0–E5 comparisons defensible? | **YES**, within declared transductive tiers/splits | Same IDs/labels, explicit versions/groups/configurations, raw scores and verified metrics. No causal size comparison or legacy pooling. |
| G. CREST detection superiority? | **NO** | Original intervention benchmark incomplete; Phase 5H stopped ranking extension. |
| H. CREST explanation superiority? | **NO** | Phase 6A twelve compatible fidelity pairs tie; limited coverage/stability/cost. |
| I. Strongest defensible contribution? | **YES** to an auditable empirical framework | Versioned evaluation, corrected semantics, measured variability and transparent negative diagnostics; no new superior detector. |
| J. Applied IEEE submission readiness? | **PARTIALLY**, not submission-ready certification | Evidence package is usable for a narrow supplied-data empirical study. Actual manuscript alignment, upstream-label scope/lineage and data-release permissions remain outstanding. |

Minimum additional work: obtain raw-to-label lineage or explicitly limit all claims to supplied unverified labels; verify release permissions; map every actual manuscript sentence/table to this package and closest prior work. Independent traceable dataset/time validation is required **if** generalization is claimed; otherwise remove that claim. Do not restart costly CREST experiments merely to improve novelty framing. No acceptance percentage is implied.

## Acceptance criteria and phase boundary

| Original Phase 6C criterion | Status |
|---|---|
| 1. IBM lineage investigated/documented | Satisfied; missing raw evidence explicitly documented |
| 2. PaySim provenance verified/documented | Satisfied as unresolved, not resolved |
| 3. Fresh50K replay or exact blocker | Satisfied: complete exact replay |
| 4. Bounded model-seed analysis | Satisfied for declared E1/E4 scope |
| 5. E0–E5 comparability reviewed | Satisfied with explicit restrictions |
| 6. Verified final tables | Satisfied: A–G plus separate E6_BASE |
| 7. Updated claims audit | Satisfied: new versioned `claims_audit.csv/json`; Phase 6B matrix unchanged |
| 8. Manuscript evidence package | Satisfied locally; public-release permissions and actual manuscript editing outside this phase |
| 9. Relevant regression tests | Final executed ledger below |
| 10. Protected artifacts preserved | Final checksum verification below |
| 11. Paper-readiness gate | Satisfied; conditional/negative conclusions retained |

Recommended Phase 7 backend scope, only if separately authorized: read-only access to completed run manifests/tables, explicit provenance and fallback/availability status, and evidence links for frozen diagnostics. Keep scientific runs immutable, validate run IDs and score-population identity, avoid target-label tuning, and distinguish anomaly response from proven fraud. No new detector, CREST retraining, frontend/dashboard, deployment or manuscript rewrite has started.

## Complete Phase 6C inventory

New source: `backend/scripts/validate_phase6c.py`, `backend/scripts/package_phase6c.py`, `backend/scripts/verify_phase6c.py`, `backend/tests/test_phase6c_validation.py`.

New reports: `06C_final_validation.md`, `06C_label_lineage.md`, `06C_replay_and_seed_analysis.md`, `06C_manuscript_evidence_manifest.md` under `docs/research/`. The two first-session drafts were completed within Phase 6C; no pre-Phase 6C report was edited.

New data directories under `data/results/v2/`: `phase6c-validation-v1`, `phase6c-features-50k-v1`, `phase6c-baselines-50k-v1`, `phase6c-evidence-v1`, `phase6c-final-review-v1`. Individual contents/hashes are enumerated by their manifests/final review; research output directories remain Git-ignored under existing policy.

Workspace test roots: `work/phase6c-tests`, `phase6c-regression`, `phase6c-guard-tests`, `phase6c-api-diagnostic`, `phase6c-api-unrestricted`, `phase6c-final-tests`. They retain disposable copies and logs; no real data directory was deleted. There are no Phase 6C modifications to pre-existing production code or historical experiments. No commit was made.

## Final execution ledger

The following section is completed from the final runner and checksum records.

| Final execution | Passed | Failed | Skipped | Blocked | Duration | Observed exit |
|---|---:|---:|---:|---:|---:|---:|
| Approved selected regression suite | 87 | 0 | 0 | 0 | 472.78 s | 0 |
| Approved PaySim integration suite | 21 | 0 | 0 | 0 | 3.89 s | 0 |
| Preliminary Phase 6C guard suite (subset of the 87) | 4 | 0 | 0 | 0 | .58 s | 0 |

**108 distinct final passing tests**, not112. The final rerun passed both real-file PaySim loading tests; the native crash did not recur. This comparison does not establish the crash's exact cause. Earlier interrupted runs have no final counts; their total durations and the crashed regression process exit were not persisted and remain unavailable. They are not relabeled as successful runs.

Evidence paths relative to workspace:

- `work/phase6c-final-tests/phase2-u9nqo0ae/{command.txt,pytest.log,results.xml}`; persisted exit `work/phase6c-final-tests/exit.txt`.
- `work/phase6c-api-unrestricted/phase2-qs3wkg_r/{command.txt,pytest.log,results.xml}`.
- `work/phase6c-guard-tests/phase2-kehv4qqw/{command.txt,pytest.log,results.xml}`.
- Interrupted/crashed evidence: `work/phase6c-tests/phase2-itctcm9m`, `work/phase6c-regression/phase2-knamucw5`, `work/phase6c-api-diagnostic/phase2-u4wirwco`.

Final independent verification (`python backend/scripts/verify_phase6c.py`) exits0: all completed package/source artifact hashes verified; all twelve model-seed metric rows and twelve pairwise stability rows independently recomputed from saved arrays; existing5K and fresh50K scientific replay bytes match; **87/87 original files match protected manifest and supplied ZIP**, **623/623 snapshot files unchanged** (622 historical files plus the original Phase 6C validation script). `git diff --check` exits0; new report trailing-whitespace checks pass. Evidence: `data/results/v2/phase6c-final-review-v1/final_review.json`, including exact source/report/test hashes and complete replay file comparisons.

All eleven bounded Phase 6C acceptance criteria are satisfied. Independent IBM ground-truth verification, PaySim provenance resolution, external generalization and full manuscript readiness remain scientifically incomplete as explicitly scoped above; they are not falsely marked resolved by passing implementation tests. Stop after Phase 6C.
