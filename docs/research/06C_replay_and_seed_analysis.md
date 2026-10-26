# Phase 6C — Replay and model-seed analysis

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

## Frozen design and execution

`backend/scripts/validate_phase6c.py` writes an exclusive protocol before fitting. Outputs: `data/results/v2/phase6c-validation-v1/`, `phase6c-features-50k-v1/`, `phase6c-baselines-50k-v1/`. Existing IDs are rejected. No intervention benchmark was restarted.

Before execution the resource record checked available RAM against2GiB and existing inputs. Earlier measured 50K feature/baseline work was70.35/116.74seconds and peak working set about520MB. Each dedicated worker was limited to600seconds and2GiB sampled RSS; only the owned child is terminated if exceeded. No nested worker processes are used (`n_jobs=1`). These checks are not a guarantee against transient RSS peaks between quarter-second samples.

| Fresh stage | Process wall seconds | Sampled peak RSS bytes | Exit | Budget stop |
|---|---:|---:|---:|---|
| 50K feature reconstruction | 75.912462 | 528,474,112 | 0 | None |
| Six-split 50K E0–E5/E6_BASE refit/scoring/evaluation | 132.305534 | 284,782,592 | 0 | None |
| Twelve fixed-split E1/E4 model-seed fits/scores | 21.308303 | 233,308,160 | 0 | None |

The replay reads original canonical transactions/labels, rebuilds the directed graph and23-column matrix, regenerates six memberships, fits fresh models with seed42, and computes new predictions. Previous scores are read only afterward for comparison. Sampled betweenness uses k500, seed42; it is not exact centrality. Original source code and hyperparameters are unchanged.

## Exact replay outcome

`phase6c-validation-v1/replay_comparison.json` records **all compared files byte-identical**, tolerance0:

- `features.npy`, `population.json`, `splits.json`;
- all six `split-<seed>-model-42/scores.json` files, containing seven methods each;
- `results.json`, `summary.json`.

Account IDs, feature values, score values and metrics therefore match exactly, with zero numeric difference in compared arrays. Runtime/memory, output identity and feature-manifest identity are excluded; model serialization bytes are not claimed identical. Each old/new stage manifest is checked separately. This is a fresh same-input, same-environment replay, **not independent external validation** or a cross-platform result. Existing 5K replay remains unchanged and was verified in Phase 6B; it was not redundantly refitted here.

## Separate model randomness

Fixed before results: model seeds **13,42,101**, split seed42, E1/E4, both tiers. The frozen full-graph feature arrays and identical train/test IDs are reused. Only `random_state` changes; no scaler,100trees,`max_samples=auto`,contamination.005,`n_jobs=1`,rawfloat32. Labels enter metrics only. Source seed42 scores exactly equal saved E1/E4 scores on both tiers.

| Tier/method | Mean AP | Sample SD | Minimum | Maximum |
|---|---:|---:|---:|---:|
| 5K E1 | .099345 | .072936 | .057130 | .183564 |
| 5K E4 | .190727 | .003307 | .188817 | .194545 |
| ~50K E1 | .017713 | .003935 | .015136 | .022242 |
| ~50K E4 | .015868 | .002633 | .013860 | .018850 |

Complete per-seed AP/ROC-AUC, positive hits/precision/recall at10/25/50/100, threshold anomaly count and fit/scoring seconds: `phase6c-evidence-v1/model_seed_per_run.csv` and JSON. All twelve pairwise method/tier/seed comparisons include ordinal Spearman, top-K overlap/Jaccard, and mean/max rank displacement in `model_seed_pairwise_stability.csv`/JSON. Spearman uses deterministic descending score/account-ID ordinal ties, not average tied ranks. Model-seed score files are retained and hashed, not just summaries.

Table F separates six-split variation at model seed42 from three-model-seed variation at split42. These are conditional slices of different randomness sources, not an additive variance decomposition. E4 appears less model-sensitive than E1 on this 5K split, but one split/three model seeds cannot establish general robustness; E2/E3/E5 model-seed variation was not measured. No best seed is selected. Six or75 positives, overlapping split populations and common synthetic histories limit inference. Sample SD is not a confidence interval; no new significance claim is made.

## Comparability

E0–E5 share exact held-out accounts, labels, full graph, split and metric implementation within each tier/split. E0 uses `e0-source-signed-zero-v2`; E1–E5 use `isolation-forest-raw-v2`. Their feature groups intentionally differ. E0's z-threshold is irrelevant to AP and not an IF contamination parameter. Table C records exact group names and score directions. Historical baseline versions, rounded risk scores and different contamination values remain separate.

E6_BASE is calibration-only and stored outside E0–E5 manuscript tables. Nondecreasing empirical calibration can merge scores into ties; sklearn AP groups tied thresholds. Lexical ordering affects retrieval/ranks, not threshold-grouped AP. No new score formula was introduced.

Reproduction requires a new run ID or separately versioned script configuration, never deleting existing output. The current scripts deliberately refuse reusing their Phase 6C destinations. Runtime measurements are local observations, not scaling guarantees or independent dataset validation.

## Full per-model-seed results

| Tier | Method | Split | Model | AP | ROC-AUC | P@10 | P@25 | P@50 | P@100 | Positive hits @10/25/50/100 | Fit+score seconds |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 5k | E1 | 42 | 13 | 0.057340 | 0.756861 | 0.100000 | 0.040000 | 0.040000 | 0.020000 | 1/1/2/2 | 0.547281 |
| 5k | E1 | 42 | 42 | 0.057130 | 0.732207 | 0.100000 | 0.040000 | 0.040000 | 0.020000 | 1/1/2/2 | 0.429157 |
| 5k | E1 | 42 | 101 | 0.183564 | 0.730868 | 0.100000 | 0.040000 | 0.040000 | 0.020000 | 1/1/2/2 | 0.422613 |
| 5k | E4 | 42 | 13 | 0.188817 | 0.760263 | 0.100000 | 0.080000 | 0.040000 | 0.020000 | 1/2/2/2 | 0.444215 |
| 5k | E4 | 42 | 42 | 0.194545 | 0.749442 | 0.100000 | 0.080000 | 0.040000 | 0.030000 | 1/2/2/3 | 0.430599 |
| 5k | E4 | 42 | 101 | 0.188818 | 0.770750 | 0.100000 | 0.040000 | 0.040000 | 0.030000 | 1/1/2/3 | 0.447174 |
| 50k | E1 | 42 | 13 | 0.015761 | 0.700973 | 0.000000 | 0.080000 | 0.060000 | 0.030000 | 0/2/3/3 | 1.054561 |
| 50k | E1 | 42 | 42 | 0.022242 | 0.710066 | 0.100000 | 0.040000 | 0.060000 | 0.040000 | 1/1/3/4 | 1.025062 |
| 50k | E1 | 42 | 101 | 0.015136 | 0.716028 | 0.000000 | 0.040000 | 0.020000 | 0.030000 | 0/1/1/3 | 1.033853 |
| 50k | E4 | 42 | 13 | 0.018850 | 0.703062 | 0.100000 | 0.040000 | 0.020000 | 0.010000 | 1/1/1/1 | 1.055284 |
| 50k | E4 | 42 | 42 | 0.014894 | 0.706434 | 0.100000 | 0.040000 | 0.020000 | 0.010000 | 1/1/1/1 | 0.996991 |
| 50k | E4 | 42 | 101 | 0.013860 | 0.712516 | 0.100000 | 0.040000 | 0.020000 | 0.010000 | 1/1/1/1 | 1.016098 |

## All paired model-seed ranking comparisons

| Tier | Method | Seeds | Ordinal Spearman | Top10 overlap | Top25 overlap | Top50 overlap | Top100 overlap |
|---|---|---|---:|---:|---:|---:|---:|
| 5k | E1 | 13/42 | 0.977420 | 0.800000 | 0.880000 | 0.940000 | 0.930000 |
| 5k | E1 | 13/101 | 0.979929 | 0.800000 | 0.880000 | 0.960000 | 0.960000 |
| 5k | E1 | 42/101 | 0.990139 | 0.900000 | 0.880000 | 0.980000 | 0.920000 |
| 5k | E4 | 13/42 | 0.974295 | 0.900000 | 0.920000 | 0.880000 | 0.890000 |
| 5k | E4 | 13/101 | 0.975946 | 0.800000 | 0.920000 | 0.860000 | 0.890000 |
| 5k | E4 | 42/101 | 0.979630 | 0.800000 | 0.880000 | 0.780000 | 0.860000 |
| 50k | E1 | 13/42 | 0.968855 | 0.500000 | 0.800000 | 0.780000 | 0.720000 |
| 50k | E1 | 13/101 | 0.970614 | 0.600000 | 0.800000 | 0.800000 | 0.820000 |
| 50k | E1 | 42/101 | 0.966492 | 0.600000 | 0.880000 | 0.840000 | 0.710000 |
| 50k | E4 | 13/42 | 0.978430 | 0.800000 | 0.720000 | 0.840000 | 0.920000 |
| 50k | E4 | 13/101 | 0.970818 | 0.600000 | 0.680000 | 0.800000 | 0.860000 |
| 50k | E4 | 42/101 | 0.971724 | 0.700000 | 0.720000 | 0.800000 | 0.930000 |
