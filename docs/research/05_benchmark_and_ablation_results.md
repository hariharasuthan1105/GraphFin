# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

## Phase 5 benchmark, ablation and statistical review

**Status: partially complete.** The six-seed full-held-out E0–E5 and E6_BASE comparisons ran at both IBM AML tiers. E6 intervention scoring, its ablations and the negative control did not complete. The E6_CREST performance hypothesis therefore remains **inconclusive**. No Phase 6 or frontend work was started.

### Protocol integrity and chronology

The fixed documented protocol is [`05_benchmark_protocol.md`](05_benchmark_protocol.md), machine-readable at `configs/phase5_protocol_v1.json`. Its exact SHA-256 is:

`508a84edfc7eef3cf2a9b99d7b776533c49d742ef5215d18ce59a4e46ec6daff`

The checksum was verified before analyzing the new held-out metrics and is also attached to every reviewed stage. Filesystem timestamps show the protocol and checksum at 14:29 on 2026-10-20, before the feature and baseline manifests at 14:34–14:38. No independent event log establishes what outcomes might have been examined before the protocol file was written. Accordingly, this report calls it a **fixed documented protocol**, not independently verified preregistration. The protocol was not changed after outcomes were inspected.

The cohort was frozen as the 250 IDs in split 42's `cohort_ids`, derived by stratified sampling with seed 31415. Its identity hash is recorded in the review stage. The cohort was not selected using scores or metric outcomes. However, because it was stratified by held-out labels, strict label-independent selection is **not** satisfied; this was explicitly allowed in the fixed protocol, but limits how the cohort should be described. Its observed single positive is reported without replacing IDs.

### Dataset and label definition

The supplied IBM AML files are identified by exact byte hashes in the protocol and manifests. Labels represent the OR of retained-transaction laundering involvement; the upstream raw evidence and independent label verification are unavailable. This is not a prospective future-outcome target.

| Tier | Active accounts | Retained transactions | Label positives | Full-population prevalence | Held-out accounts per seed | Held-out positives per seed | Held-out prevalence |
|---|---:|---:|---:|---:|---:|---:|---:|
| IBM AML 5K | 5,000 | 31,463 | 20 | 0.4000% | 1,500 | 6 | 0.4000% |
| IBM AML ~50K | 49,992 | 353,850 | 249 | 0.4981% | 14,998 | 75 | 0.5001% |

The larger input is the supplied large file; it is not represented as exactly 50,000 active accounts. Both tiers use the documented full-observation graph and stratified 70/30 account split. This is transductive entity holdout. The split seeds are 42, 123, 7, 2024, 99 and 555; each baseline model seed is 42. Seeds are alternate splits on the same source data, not independent datasets.

PaySim was excluded because the 774-positive and 2,606-positive label files still have unresolved provenance. No PaySim labels were used to select or tune methods.

### Execution matrix and verified artifacts

Completed and checksum-verified stages:

| Stage | Scope | Result |
|---|---|---|
| `phase5-features-5k-v1` | 5K full feature matrix and six split memberships | Complete; 3.61 s |
| `phase5-features-50k-v1` | ~50K full feature matrix and six split memberships | Complete; 70.35 s |
| `phase5-baselines-5k-v1` | E0–E5 and E6_BASE, six held-out splits | Complete; 43.07 s |
| `phase5-baselines-5k-replay-v1` | Independent replay of the 5K baseline stage | Complete; scientific result, score, summary and calibration bytes match |
| `phase5-baselines-50k-v1` | E0–E5 and E6_BASE, six held-out splits | Complete; 116.74 s |
| `phase5-pilot-v1` | Label-free intervention feasibility pilot | Complete; no metrics |
| `phase5-interventions-v1` | Exploratory cohort intervention generation | **Incomplete**: 318 rows for 149 cohort accounts, counterparty family only, no completion manifest; not scored or used in metrics |

The 5K and 50K baseline runs each contain exactly the six prespecified split seeds and all seven expected method arrays. For each split, source training and held-out memberships are disjoint and partition the declared active population. All method score maps exactly cover the same held-out IDs. The stored metrics were recomputed from the verified score and label arrays and matched. The ~50K file had 353,860 source rows, 353,850 retained rows and 8 unmatched label rows, as recorded in its verified feature manifest. Score direction for Isolation Forest is the Phase 2 raw convention, negative `decision_function` with larger values more anomalous. E0 is the versioned source-signed-zero v2 contract; E1–E5 use the declared unchanged feature groups and raw Isolation Forest runner. These are new Phase 5 calculations, not locked historical estimates.

E0–E5 use the same split and evaluation entities; their feature groups intentionally differ according to each method definition. E4 raw scores and E6_BASE calibrated scores use the same fitted full-19-feature Isolation Forest. E6_BASE has no intervention information, so its presence in the baseline stage does not constitute evidence for CREST sensitivity or robustness.

### Full-held-out baseline comparisons

Values below are mean average precision over the six prespecified splits, followed by sample standard deviation across those split outcomes. The full per-seed results, exact positives, prevalence, ROC-AUC, score ties and retrieval counts are in `data/results/v2/phase5-results-review-v3/full_heldout_baselines.csv`.

| Method | IBM 5K mean AP (SD) | IBM ~50K mean AP (SD) |
|---|---:|---:|
| E0 | 0.09676 (0.09369) | 0.02183 (0.01390) |
| E1 | 0.03799 (0.03575) | 0.02421 (0.01116) |
| E2 | 0.07948 (0.08502) | 0.02299 (0.01217) |
| E3 | 0.09705 (0.09671) | 0.02247 (0.01322) |
| E4 raw | 0.09591 (0.09680) | 0.02349 (0.01268) |
| E5 | 0.00849 (0.00558) | 0.01786 (0.01050) |
| E6_BASE | 0.08199 (0.08777) | 0.02083 (0.01050) |

These means conceal substantial split variation, particularly with only six positive test accounts in the 5K tier. Do not read the highest mean as an official winner or broad generalization. The table contains the declared means, not an inferential comparison across independent datasets.

E6_BASE applies the source-training empirical percentile map to E4 scores. The map is monotone but can collapse distinct values into ties; deterministic lexical tie-breaking can then change AP. On the six 5K splits, E6_BASE minus E4 AP was negative in all six, with mean −0.013918, median −0.000031, and range −0.083404 to −0.000001. On the six ~50K splits, four differences were negative and two positive; mean −0.002669, median −0.000005, range −0.016003 to +0.000007. The large split-specific drops reflect calibration-induced ties and show why raw E4 must remain a separate comparator. They are calibration effects, not intervention gains.

Paired account bootstrap intervals for each E6_BASE-minus-E4 comparison used 1,000 class-count-conditioned paired draws with seed 2718. The per-seed observed differences, intervals, positive counts and valid/rejected draws are in `data/results/v2/phase5-results-review-v3/paired_e6base_vs_e4.csv`. Each of the twelve comparisons had 1,000 valid and zero rejected draws. These intervals condition on a small observed positive set, ignore graph dependence and do not include split or model refitting uncertainty. They do not support a claim of significance across seeds.

### Matched exploratory cohort

The fixed 250 IDs are a strict subset of the split-42 held-out population, with the same split-42 source training set. The full-held-out E0–E5, raw E4 and E6_BASE arrays were restricted to these IDs and reevaluated; no full-population E4 metrics were substituted. The cohort contains **1 positive and 249 negatives**, prevalence **0.4%**. This is a single-positive descriptive sample, not a reliable estimate of retrieval performance. Per-method scores and matched metrics are in `data/results/v2/phase5-results-review-v3/matched_exploratory_cohort.csv`.

| Method | n | Positives | Prevalence | AP | ROC-AUC | Positive retrieved @10 / @25 / @50 / @100 |
|---|---:|---:|---:|---:|---:|---|
| E0 | 250 | 1 | 0.004 | 1.0000 | 1.0000 | 1 / 1 / 1 / 1 |
| E1 | 250 | 1 | 0.004 | 0.2500 | 0.9880 | 1 / 1 / 1 / 1 |
| E2 | 250 | 1 | 0.004 | 0.2500 | 0.9880 | 1 / 1 / 1 / 1 |
| E3 | 250 | 1 | 0.004 | 0.3333 | 0.9920 | 1 / 1 / 1 / 1 |
| E4 raw | 250 | 1 | 0.004 | 0.5000 | 0.9960 | 1 / 1 / 1 / 1 |
| E5 | 250 | 1 | 0.004 | 0.1667 | 0.9880 | 1 / 1 / 1 / 1 |
| E6_BASE | 250 | 1 | 0.004 | 0.5000 | 0.9960 | 1 / 1 / 1 / 1 |

Because there is just one positive, AP is determined by the rank of one account. The apparently perfect E0 AP and identical positive retrieval at every K are not reliable detector-comparison evidence. E4 versus E6_BASE has observed paired AP difference 0.0000. The prespecified paired bootstrap returned [0.0000, 0.0000] with 1,000 valid draws and zero rejected draws, but every resample retains the same lone positive; the interval omits uncertainty over which positive accounts could have appeared.

E4 versus E6_BASE ordinal rank Spearman correlation was 0.999993; mean absolute displacement was 0.064 positions, maximum 2 positions, and top-10/25/50/100 overlap and Jaccard were each 1. This measures calibration-only ranking stability on this one cohort. It is not intervention stability, model-seed stability, predictive-metric stability, or evidence that E6 improves ranking.

The incomplete intervention stage contains no validated account-level intervention coverage denominator for all 250 accounts. Therefore intervention availability and fallback rates are unavailable, and none of E6_SENSITIVITY, E6_ROBUSTNESS, E6_HYBRID or E6_CONCENTRATION_DIAGNOSTIC was evaluated here.

### Feasibility, runtime and memory

The existing label-free pilot processed the full 5K transaction graph: 31,463 retained transactions, 5,000 accounts and one preselected maximum-incident focal account. It generated 2 accepted interventions. Baseline artifact/feature preparation took 16.56 s; accepted feature recomputations took 19.36 s and 12.53 s. Frozen-model scoring time is null because no model was loaded in the pilot. Total measured runtime was 220.59 s, including candidate enumeration/rejection overhead. Peak traced Python allocation was 39,177,547 bytes; process RSS was 252,452,864 bytes and OS peak working set 337,252,352 bytes. Pilot artifact storage was 599,448 bytes. It is one high-degree account and cannot provide a typical per-account cost.

The partial cohort intervention file is 6,583,501 bytes. Its accepted rows record 466.97 seconds of feature recomputation for 70 accepted counterparty omissions among 149 focal accounts. Because it lacks the remaining family/cohort records and completion manifest, this is partial workload evidence only. No timings from it are treated as a completed benchmark, and it was not scored.

The frozen protocol gates intervention generation at 1,800 seconds. The pilot and partial work show material global feature-recomputation cost; complete E6 coverage for 1,500 5K held-out accounts was estimated in the fixed protocol at 26–40 hours using pilot recomputation times as a scenario, not a measured runtime. The ~50K feature population exceeds Phase 3's 10,000-node intervention guard. Full-coverage intervention experiments were not launched. No additional generation run was started because the existing run is incomplete and the feasibility evidence indicates the unchanged process exceeds the protocol budget. This report does not extrapolate pilot timing as a guaranteed runtime.

The feature stages and baseline comparisons used saved manifests and exact existing score artifacts. Measured stage costs were:

| Stage | Wall seconds | Peak RSS / OS working set | Stage artifact bytes |
|---|---:|---:|---:|
| 5K feature preparation | 3.61 | 224.5 / 231.2 MB | 1,207,446 |
| ~50K feature preparation | 70.35 | 415.6 / 519.2 MB | 12,326,800 |
| 5K six-split baseline evaluation | 43.07 | 208.2 / 208.2 MB | 8,767,888 |
| ~50K six-split baseline evaluation | 116.74 | 284.0 / 291.3 MB | 50,540,633 |

Mean per-split E4 fit/scoring times were 0.376/0.042 seconds at 5K and 0.975/0.365 seconds at ~50K; other E0–E5 fit and scoring averaged 1.499 and 3.485 seconds. Evaluation/bootstrap/reporting averaged 5.017 and 13.750 seconds per split. E6 scoring code batches intervention vectors and reuses the frozen model in principle, but no end-to-end Phase 5 scoring-time or memory result exists. One-time graph feature computation, source fit, baseline scoring, intervention generation/recomputation, intervention scoring and aggregation are not conflated into a fabricated total.

### Ablations, negative controls, explanations and ranking stability

**Not completed:** E6 sensitivity-only, robustness-only, hybrid and concentration rankings; counterparty, temporal and budgeted family ablations; equal-family versus candidate-count-weighted aggregation; structured-versus-placebo score permutation; E6 model-seed ranking stability; and intervention explanation coverage/case study. The partial counterparty file is not used to estimate these outcomes because it does not cover the frozen cohort and lacks complete family support. No family or control is allowed to have a selected favorable subset.

The deterministic stratum score permutation negative control is implemented in the Phase 5 analysis code and unit-tested for budget preservation and order independence, but it was **not evaluated on benchmark data**. The full suite and module tests cannot substitute for experimental evidence.

The only ranking stability outcome reported is E4 versus calibrated E6_BASE on the exact 250 cohort above. Split-seed baseline populations differ, so their full rankings were not correlated. No same-population multi-model-seed E6 ranking study completed.

### Reproducibility, tests and preservation

The separate replay `phase5-baselines-5k-replay-v1` exactly matches the primary 5K run's `results.json`, `summary.json`, split-42 score arrays and calibration reference. Every reviewed feature, baseline, replay and analysis manifest references the frozen protocol checksum and verifies its artifact hashes. Account-score and label IDs were checked against exact evaluation memberships; training and held-out IDs were checked disjoint. The cohort score arrays are restrictions of the verified split-42 results.

The direct in-repository pytest invocation exited before test collection because the repository guard prevents tests that mutate model/split state from running against production data; it produced no test outcomes. An initial disposable combined run was interrupted while investigating a slow integration test and is not counted. The final approved disposable-copy run completed successfully:

| Check | Outcome |
|---|---|
| `backend/tests/test_phase5_benchmark.py` in disposable copy | 16 passed, 0 failed, exit 0 |
| Phase 2–5 selected regression set (correctness, interventions, CREST, benchmark, graph/features/anomaly/evaluation/split/transfer/adapters/runner/transactions/locked-data tests) | **249 passed, 1 skipped, 0 failed**, 122.41 s, exit 0; skip is the unavailable historical processed CSV pair |
| Protected original files | 87/87 verified byte-identical to the supplied ZIP and manifest; all 83 Phase 4 application Python files match the final Phase 4 regression snapshot |
| `git diff --check` | Exit 0 |

The input CSVs and labels, locked E0–E5 results, Phase 2–4 artifacts and frontend were not rewritten. The incomplete intervention directory remains an incomplete append-only artifact and has no completion manifest. Final evaluation products are under `data/results/v2/phase5-results-review-v3`; its manifest hashes review outputs and records the summarizer script hash. `backend/scripts/summarize_phase5.py` re-verifies upstream manifests, dataset and label identities, feature schema, memberships, algorithm score coverage, model configuration and stored metrics before producing its tables. No official winner was selected.

### Evidence-supported interpretation

The full-held-out Phase 5 work establishes that the configured E0–E5 baselines and calibrated E6_BASE can be compared on the same per-seed held-out populations. It also shows that calibration can create tie-driven changes relative to raw E4, sometimes substantial for a particular split. The one-positive cohort is too small for credible model selection or a broad performance statement.

The primary hypothesis about **constrained transaction-evidence sensitivity and robustness** is untested: none of the intervention-derived ranking modes completed a matched evaluation. No ablation, negative-control comparison, or sensitivity/robustness explanation benefit has been observed. There is no evidence in this phase that E6_CREST improves anomaly ranking. Novelty still requires a separate literature review and is not claimed.

### Acceptance review and remaining work

| # | Phase 5 acceptance criterion | Status |
|---|---|---|
| 1 | Preregistered/versioned benchmark protocol | Fixed protocol and checksum verified; independent chronology proof unavailable |
| 2 | Fair baseline comparison where available | Complete for E0–E5 and E6_BASE, six splits per tier |
| 3 | E6 candidate modes | Only E6_BASE; intervention modes incomplete |
| 4 | Evaluation populations and labels validated | Complete for baseline runs and frozen cohort; labels declared, not independently verified |
| 5 | Test-label leakage prevented | Partial: model fitting/calibration and weights use no held-out labels; cohort membership did use held-out labels for prespecified stratification |
| 6 | Feasibility limitations explicit | Complete; full E6 not run |
| 7 | Multi-seed/qualified robustness evaluation | Six split seeds for baselines; no intervention E6 multi-seed evaluation |
| 8 | Paired uncertainty on completed comparisons | Complete for E6_BASE vs E4; sparse-positive caveats apply |
| 9 | Ablations executed | Incomplete |
| 10 | Negative control evaluated | Incomplete; implementation tests only |
| 11 | Ranking stability measured | Calibration-only E4/E6_BASE cohort comparison; E6 intervention/model-seed stability incomplete |
| 12 | Computation costs reported | Baseline and pilot measurements reported; E6 end-to-end cost unavailable |
| 13 | New results reproducible | Baseline rerun and output hashes verified; no E6 intervention replay |
| 14 | Protected artifacts unchanged | Satisfied: 87/87 |
| 15 | Regression tests and evidence documented | Satisfied after final test run evidence is recorded |
| 16 | Scientific report produced | Satisfied: this report |
| 17 | Negative/inconclusive outcomes retained | Satisfied; E6 hypothesis remains inconclusive |
| 18 | Phase 6 readiness and risks assessed | Partial: data identity known, but PaySim provenance unresolved and E6 benchmark incomplete |

Phase 5 is therefore **partially complete**, not accepted as a completed E6 benchmark. The appropriate next scientific step is to secure sufficient bounded compute or redesign intervention generation under a separately versioned, explicitly exploratory protocol that preserves Phase 3 semantics and fixed account selection. Then complete all declared cohort/family records before scoring, report the missing-evidence fallback denominator, compare every mode and placebo on the identical accounts, and retain held-out outcomes without retuning. Phase 6 should wait until PaySim label provenance and the primary E6 evidence gap are addressed.
