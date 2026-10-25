# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

## Phase 5 preregistration — version 1

Frozen before new held-out performance inspection. The authoritative machine-readable protocol is `configs/phase5_protocol_v1.json`; its adjacent `.sha256` records the exact bytes. Changes after final outcomes require a separate explicitly exploratory version.

Hypothesis: constrained evidence sensitivity/robustness improves account anomaly ranking beyond the unchanged full-feature E4. Negative and inconclusive results will be retained.

### Readiness and feasibility

The supplied IBM medium and large canonical CSVs and label files are available. Original raw laundering flags/conversion evidence are absent; labels retain the documented retained-transaction endpoint-OR involvement interpretation and declared/unverified provenance. Medium has historically 5,000 accounts/20 positives; large has 49,992 active accounts/249 positives after removal of nonpositive transactions. Every new split's counts will be independently saved. PaySim is excluded because its label provenance is unresolved.

All baseline methods use the same sorted active IDs, full-observation transductive graph and 70/30 stratified account split. E0 uses explicit graph-six signed training z maxima (`e0-source-signed-zero-v2`). E1–E5 use unchanged feature groups and raw Isolation Forest scoring. E4 raw and E6_BASE are both retained because empirical percentile calibration can change AP through ties. Historical point estimates are not new comparison rows.

Phase 3 globally recomputes graph features per omission. A label-free bounded pilot on the full medium graph measured 31,463 transactions/5,000 accounts, one maximum-incident focal, two accepted omissions: 220.588 s total under tracing, 16.559 s baseline construction, individual recomputation 19.364/12.526 s, 39,177,547 peak traced Python bytes and 337,252,352 OS peak working-set bytes. Candidate enumeration/rejection overhead is included in total time and is large for this deliberately high-degree focal. These measurements are not representative per-account costs or linear scaling guarantees. The pilot has no accuracy metrics.

Full E6 coverage for 1,500 medium held-out accounts could require up to 7,500 accepted recomputations (two counterparty, two temporal, one budgeted), before any baseline work. Using the pilot's recomputation times solely as a scenario gives approximately 26–40 hours; actual untraced work and sparse-account coverage can differ greatly. This exceeds the prespecified 1,800-second intervention budget. The 50K tier additionally exceeds Phase 3's unchanged 10,000-node reference guard. Full-coverage E6 is therefore planned but blocked by this gate; it will not be replaced by a sampled result labeled primary.

Baseline-only full-tier evaluations remain useful and are separately labeled. A prespecified exploratory medium cohort contains 250 accounts from split 42's held-out set, using proportional stratified sampling with seed 31415. This preserves the medium split's 0.4% prevalence when allocation is 1 positive/249 negative, independently checked at execution. Cohort labels are used only for declared stratification; scores and outcomes cannot influence selection. Its single positive makes uncertainty particularly weak. All methods and ablations use exactly this cohort and the same 3,500 source-training accounts. No training-side retuning is performed.

### Frozen configurations

- Baseline split seeds: 42, 123, 7, 2024, 99, 555; model seed 42.
- Exploratory fixed split/cohort, model seeds: 42, 123, 7, 2024, 99, 555. These assess model randomness, not six independent datasets.
- IF: 100 trees, max_samples auto, contamination .005, n_jobs 1, unchanged float32 features.
- Intervention seed 17; inclusive cutoff at maximum retained source timestamp; 24-hour temporal blocks. This is retrospective involvement evaluation, not future-outcome prediction.
- Each family executes the unchanged Phase 3 operator separately with cap two, max count 2, max fraction .5, max monetary fraction .5 and minimum retained count 1. Separate caps prevent one family exhausting all other families' candidate budget. Budgeted generates at most one candidate by its existing definition, so its family-only robustness is unavailable at threshold two.
- E6 alpha=beta=.25, chosen as quarter-scale bounded terms before metrics. BASE ignores both; sensitivity-only/robustness-only use their respective term. Hybrid is the primary candidate, with other modes descriptive.
- Missing required evidence uses unchanged baseline fallback, recorded per mode. Concentration remains diagnostic only.
- Family ablations reuse the same scored interventions. The weighted ablation weights the same eligible family medians by valid candidate counts. It does not redefine E6.
- Negative control: deterministic permutation of intervened calibrated scores within family/exact count/fraction-bin/amount-bin strata (seed 8675309), then recompute deltas from recipient baseline scores. It preserves candidate budgets/counts/population and tests arbitrary score perturbations. It is a score placebo, not a physically generated random omission; donor-change coverage must be reported.

### Metrics, uncertainty and interpretation

Primary metric is sklearn non-interpolated average precision. Report exact prevalence and positive counts, AP/prevalence, ROC-AUC when defined, P/R and positive hits at 10/25/50/100, effective K, ties, coverage and fallback rates. No thresholds or F1 are optimized.

Paired stratified account bootstrap: 1,000 resamples, seed 2718, identical positive/negative draws for both score arrays, percentile .025/.975 interval for AP difference. It conditions on observed class counts, excludes refitting uncertainty and ignores graph dependence. With one positive it cannot measure uncertainty over unseen positive identities. No-positive AP/CI is null with explicit rejected count; all-positive AP is defined and ROC-AUC is null.

Compare each E6/ablation/control to raw E4; additionally compare modes to calibrated BASE and structured hybrid to the placebo. Secondary comparisons are descriptive and are not a label-driven winner-selection exercise. Report mean/median/sample SD/min/max and per-seed paired differences. Across model seeds on identical IDs, measure ordinal-rank Spearman, top-K overlap/Jaccard and displacement. Different split populations are not silently aligned as if identical.

Evidence supporting the primary hypothesis would require consistent full-coverage hybrid improvements across seeds/tiers, compatible paired intervals and top-K results, followed by independent validation. An exploratory cohort alone cannot satisfy that standard. Novelty remains unverified.

### Execution and preservation

Feature/baseline stages have 600-second limits; intervention stage has 1,800 seconds. Incomplete cohort generation is recorded without evaluating a favorable completed subset. Completed feature/intervention artifacts are reused across model seeds. Record fit, baseline scoring, generation/recomputation, intervention scoring, aggregation/evaluation, total wall time, RSS/OS peak, pilot allocation tracing and storage separately.

Outputs are new append-only `data/results/v2/phase5-*` directories, using Phase 2 canonical serialization/hashes and completion manifests. Persist protocol hash, input identities, exact membership, score arrays, calibration/model identities, parameters/seeds, timings, environment/source hashes and output checksums. Existing datasets, E0–E6 implementations, Phase 2–4 results and frontend are preserved.
