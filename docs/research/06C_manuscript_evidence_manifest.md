# Phase 6C — Manuscript evidence manifest

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Finalized 2026-10-24. Repository-relative paths below are actual local artifacts. This is a local evidence package, not a public release or a manuscript rewrite. Dataset redistribution permissions remain unverified. The six-page manuscript itself was not located among repository PDF/TeX/DOCX sources; no manuscript source or performance figure was modified, and its current prose cannot be certified from these artifacts alone.

## Package inventory

Root: `data/results/v2/phase6c-evidence-v1/`. Every listed data table exists as both CSV and JSON; nested quantities in CSV are JSON-encoded to preserve exact keys. JSON retains full numeric precision. The package `manifest.json` hashes its files; `supporting_artifacts.json` hashes the referenced source evidence. Final source/document/test digests are separately recorded in `data/results/v2/phase6c-final-review-v1/final_review.json` so the original completion manifests need not be changed.

| Table / artifact | File stem | Purpose |
|---|---|---|
| A | `table_A_datasets` | Source hashes, retained population, positives/negatives and prevalence |
| B | `table_B_features` | Ordered canonical19 + egonet4 definitions, grouping, rounding and source code |
| C | `table_C_configurations` | E0–E5 feature groups, versions, detector settings, score direction and seeds |
| D | `table_D_six_split_5k`, `table_D_summary_5k` | Per-split metrics and six-split mean/sample SD for E0–E5 |
| E | `table_E_six_split_50k`, `table_E_summary_50k` | Same for 49,992 active accounts |
| F | `table_F_variability` | Six split seeds at model42 versus three model seeds at split42; conditional, not variance decomposition |
| G | `table_G_limitations` | Provenance and scientific limitations |
| Separate calibration | `calibration_only_E6_BASE` | Calibration-only results; not a completed intervention detector |
| Model-seed detail | `model_seed_per_run` | Twelve actual runs: AP, ROC-AUC, P/R/hits@K, configuration and runtime |
| Ranking stability | `model_seed_pairwise_stability` | Twelve paired seed comparisons: Spearman ordinal ranks, top-K overlap/Jaccard, displacement |
| Claims | `claims_audit` | SUPPORTED/PARTIALLY SUPPORTED/UNSUPPORTED with evidence pointers and narrow scope |
| Provenance | `ibm_lineage.json`, `paysim_provenance.json` | Verified populations and explicit missing raw-label evidence |
| Protocols | `baseline_protocol.json`, `validation_protocol.json` | Exact baseline and Phase 6C configuration, Python/dependencies, git/code identity, seeds and budgets |
| Bibliography | `verified_bibliography.md` | Byte-copy of Phase 6B primary-source-verified comparison; no new references invented or new search claimed |
| Flowchart | `flowchart.mmd` | Existing transductive graph → source fit → held-out metrics → manifest workflow; diagnostic branch separate |

The per-seed CSVs are figure-ready. Show all observed split/model points; distinguish sample SD from confidence intervals. Do not combine split and model rows as independent datasets. No completed CREST improvement, PaySim transfer accuracy or future-time generalization table is supplied.

## Source and replay chain

1. `docs/research/configs/phase5_protocol_v1.json` identifies IBM transaction/label byte hashes, feature schema `canonical19-plus-egonet4-v1`, E0 `e0-source-signed-zero-v2`, IF `isolation-forest-raw-v2`, split seeds42/123/7/2024/99/555 and model seed42.
2. `phase5-features-{5k,50k}-v1` preserves ordered features, labels, membership and manifests; `phase5-baselines-{5k,50k}-v1` preserves held-out scores, calibration/model settings and metrics. Paths here are under `data/results/v2/`.
3. `phase5-baselines-5k-replay-v1` is the existing fresh-fit 5K replay; Phase 6C rechecks all six score files plus result/summary bytes without repeating training.
4. `phase6c-features-50k-v1` and `phase6c-baselines-50k-v1` are the fresh Phase 6C input-to-feature-to-fit replay. `phase6c-validation-v1/replay_comparison.json` contains old/new hashes and tolerance0 comparisons; corresponding `*-process.json` files record observed exits, timings and sampled memory.
5. `phase6c-validation-v1/*-model-*-scores.json` and model-seed summaries hold all twelve fits. The seed42 controls reproduce the saved E1/E4 arrays exactly.
6. `phase6c-evidence-v1` derives tables without changing any preceding output. `phase6c-final-review-v1` separately validates hashes, metrics, seed stability, tests and protected history.

The calibration-only E6_BASE table uses the original empirical CDF. Later affine variants are not substituted. Exact replay refers to compared scientific files; execution time, memory, destination-dependent metadata and model serialization bytes are not asserted equal.

## Environment and commands

Python executable used: `C:/Users/hariharasuthan/AppData/Local/Programs/Python/Python312/python.exe` (3.12.10). Exact pip freeze and git/diff identities are in `phase6c-validation-v1/protocol.json`; manifest source hashes identify the uncommitted checkout, so git HEAD alone is insufficient. Historical manifests also record numpy/sklearn/pandas versions and centrality configuration.

Already executed, **do not repeat to regenerate this package in place**:

```text
python backend/scripts/validate_phase6c.py
python backend/scripts/package_phase6c.py
python backend/scripts/verify_phase6c.py
```

These commands refuse existing exclusive destinations. For a separately authorized fresh replay, use new run IDs with the unchanged runner and retain the same 600-second/2GiB child-process guards from `validate_phase6c.py`:

```text
python -m backend.app.research.benchmark.runner prepare docs/research/configs/phase5_protocol_v1.json phase6c-features-50k-new --tier 50k
python -m backend.app.research.benchmark.runner evaluate docs/research/configs/phase5_protocol_v1.json phase6c-baselines-50k-new --features data/results/v2/phase6c-features-50k-new
```

The module commands alone do not enforce the parent memory/time watchdog; wrap them with `bounded` as the executed orchestrator did. For model seeds, create a new empty output directory and run `python backend/scripts/validate_phase6c.py seeds <new-directory>` under the same watchdog. This reuses verified feature arrays with fixed memberships and seeds; it does not rebuild features. No target-label tuning is permitted.

Regression commands and environment are preserved in each disposable test directory's `command.txt`, `pytest.log`, `results.xml`; the final report identifies failed/interrupted attempts separately. The approved API run used the ordinary application, without event-loop substitutions or application patches.

## Statistical and publication boundaries

AP is sklearn threshold-grouped non-interpolated average precision. P@K uses deterministic account-ID tie ordering. Three model seeds and six overlapping splits are not independent dataset replications. IBM ground truth is supplied but not independently reconstructed; PaySim conflict remains unresolved. Full-graph features are transductive. Rare positives, graph dependence, redundant features and sampled-centrality sensitivity limit interpretation. Bootstrap intervals retained from Phase 5 condition on observed class counts and fitted models; they do not validate generalization. CREST remains an optional evidence-sensitivity diagnostic; superiority was not demonstrated.

Only the narrowly audited claims in `claims_audit.json` are suitable for future manuscript drafting. The current manuscript must still be checked against them before submission. Phase 7 backend integration may expose read-only validated run identities, evidence availability and provenance with truthful status; it must not introduce a new detector, tune on target labels, relabel unresolved data, or display diagnostic response as confirmed fraud. No Phase 7 work is included here.

## Completed-stage manifest checksums

The following table is generated from the actual files, not manually transcribed.

| Manifest path (under data/results/v2) | SHA256 |
|---|---|
| phase5-baselines-5k-v1/manifest.json | `da0a166a1ec21efbdb97359908c27decc6a25547d4570f804ab35f87e7316da6` |
| phase5-baselines-5k-replay-v1/manifest.json | `7ac5f56aa074b78b89ac6caa01ca3b3f7ef1d4b9bb1989527ebb6eed82c71d3e` |
| phase5-baselines-50k-v1/manifest.json | `95d4b6e9e580131205e43ddba0d00dbe49fcd9fb9d273a757f6e4f1438d933f1` |
| phase6c-validation-v1/manifest.json | `f73a6174d8a370c0eeaa3952c2b684909522a229e7c12627bc688485d872ce7f` |
| phase6c-features-50k-v1/manifest.json | `61a8ccb1811df79142de6c105fdd4a46a8146d9be7f5260bdd69fb932d36ce4c` |
| phase6c-baselines-50k-v1/manifest.json | `b772e039b9af9c5779dc5a4405370e2eaf84c67f7d9c1a0302f3408e765431ea` |
| phase6c-evidence-v1/manifest.json | `5075915a9c43c9e1559c77cb0e5d735448606cbeaded6361352261902357c90b` |
