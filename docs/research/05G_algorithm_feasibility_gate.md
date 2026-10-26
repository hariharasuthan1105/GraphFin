# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

## Phase 5G — Algorithm feasibility and scientific decision gate

This is a bounded scoring-behavior investigation, not a completed intervention-based fraud benchmark. It retains the original E0–E5 methods, frozen E6 definitions, datasets, frontend and previous reports. The implementation and pilot are separately versioned. No model was refitted and no completed baseline experiment was rerun.

### Scope and evidence

The Phase 1–5R reports, frozen protocol, saved baselines, intervention records, calibration, graph, feature and scoring implementations informed this phase. Source and artifact paths below are relative to the repository. All new experimental outputs are under `data/results/v2/phase5g-feasibility-v1-recovery/`, abbreviated **G** below. `manifest.json` is the completion and checksum authority; absence of that manifest means an incomplete run.

The initial `phase5g-feasibility-v1/` execution was interrupted before completion. Its session was unavailable on recovery and its partial directory had no completion manifest. It is preserved and excluded from completed-pilot conclusions. A fresh directory was used for the identical fixed protocol; no partial records were relabeled as completed results.

Frozen Phase 5 protocol SHA-256:

`508a84edfc7eef3cf2a9b99d7b776533c49d742ef5215d18ce59a4e46ec6daff`

The original 250-account experiment remains incomplete: 318 records for 149 accounts, 70 accepted and 248 rejected, counterparty-only, with no completion manifest. Its log SHA-256 remains `1dfa2b7928fd0321efee011b68276f76b1cc50001e141a6e0e87adc1568948d0`. It was not scored or extended in this phase. Its label-stratified cohort cannot become a label-independent cohort retrospectively.

### 1. Correction and numerical diagnosis of the selective probe

The earlier Phase 5R statement that every mode had identical rankings to E6_BASE is too broad. Replaying the saved scores shows **hybrid unchanged**, but sensitivity-only and robustness-only each move **two accounts**. Phase 5R remains intact as historical evidence; this report records the correction. Its later reference to one positive should not be read as the full selective evaluation population: that population has six positives; the older 250-account cohort has one.

`G/selective_account_diagnosis.json` contains a row for every one of the 1,500 evaluated accounts: raw E4, E6_BASE, accepted count, every signed raw/calibrated change, family statistics, sensitivity, robustness, final E6 scores, pairwise score differences, ranks, fallback reasons and pre-clipping scores. All stored E6 scores replay exactly through the unchanged `crest/statistics.py::candidate_score`.

| Selected account | Raw E4 | E6_BASE | Accepted | D | R | Hybrid minus base |
|---|---:|---:|---:|---:|---:|---:|
| 070_100428660 | 0.1125046843 | 1 | 3 | 0 | 1 | 0 |
| 00513_800597410 | 0.0732828023 | 0.9997142857 | 3 | 0.0005714286 | 0.9994285714 | +0.0000000408 |
| 001412_800CD5E00 | 0.0608658568 | 0.9991428571 | 0 | unavailable | unavailable | 0, fallback |
| 013327_801565A50 | 0.0585150414 | 0.9991428571 | 4 | 0.0006190476 | 0.9992857143 | −0.0000236565 |
| 012_8006455A0 | 0.0320401159 | 0.998 | 4 | 0.0007619048 | 0.9985714286 | −0.0001659524 |

Eleven of 14 accepted omissions have nonzero raw score changes, ranging from −0.01669592 to +0.02627956; all eleven also have nonzero empirical-calibrated changes. The three exact zeros belong to the first account. Thus empirical quantization did not erase those eleven changes, although it compressed their magnitudes to a finite grid (calibrated changes −0.00057143 to +0.002). Quantization also creates baseline ties: E4 and E6_BASE differ in ordering independently of interventions.

Sensitivity and robustness terms nearly cancel for `00513_800597410`: +0.0001428571 versus −0.0001428163. Equal weights 0.25, bounded percentile-scale changes, cancellation, and gaps between neighboring scores explain why changed hybrid scores need not change ranks. No clipping occurred in any E6 mode. There are three changed scores in each sensitivity/robustness/hybrid mode, but 1,496/1,500 accounts fall back because required intervention statistics are absent. The concentration diagnostic leaves base scores unchanged by definition. Only four accounts have accepted interventions, and family support is sparse. These are numerical explanations, not evidence that larger weights would improve detection.

### 2. Separately versioned affine formulation

`feasibility_gate/raw_scoring.py::TrainingAffine`, version `source-binary-iqr-affine-v1`, uses only saved source-training E4 scores. Let m be their median and w their interquartile range. If w is nonpositive, use the source range; for a constant source use 1. Define

\[
a=2^{\lfloor\log_2 w\rfloor}>0,\qquad z(s)=(s-m)/a.
\]

The positive binary scale avoids additional division rounding in ordinary representable ranges. It discretizes the training scale, not individual scores. There is no percentile map, sigmoid, clipping, test fit or label-based parameter choice. A positive affine map preserves order mathematically; floating-point subtraction can still collapse distinct values. The implementation explicitly rejects nonfinite outputs or any non-strict order among sorted distinct inputs. Existing ties remain ties. Callers must check the joint population, not separate singleton calls: the runner checks training plus held-out scores, and the union of pilot baseline/intervened scores. An adversarial adjacent-float regression exercises explicit rejection.

`G/affine_checks.json` and `affine_scores.npz` retain all raw and transformed scores, account IDs, source parameters and calibration hashes. The 12 available baseline splits are six seeds (42,123,7,2024,99,555) at each of 5K and approximately 50K, with model seed 42. They are alternate splits, not independent datasets. This check does not refit their models or recompute detection metrics.

Raw-affine sensitivity is dimensionless but no longer bounded by 1. Reusing the percentile robustness formula `1 − median(abs(delta))` could produce negative robustness. The separate `raw-affine-crest-feasibility-v1` therefore defines, for omission j in family f,

\[
\delta_{fj}=z(s_0)-z(s_{fj}),\quad D_f=\operatorname{median}_j\delta_{fj},\quad A_f=\operatorname{median}_j|\delta_{fj}|,
\]
\[
D=\operatorname{mean}_{f:n_f\ge1}D_f,\qquad
R=\operatorname{mean}_{f:n_f\ge2}\frac{1}{1+A_f}.
\]

Equal-family means prevent a family with more candidates automatically dominating. The reciprocal maps nonnegative absolute changes to (0,1], with R=1 at zero change. It is a chosen sensitivity-stability summary, not calibrated uncertainty. Two candidates is only a support threshold, not a statistical guarantee. The candidate modes are

\[
S=z_0+\alpha D,\quad Q=z_0-\beta\max(z_0,0)(1-R),\quad H=z_0+\alpha D-\beta\max(z_0,0)(1-R).
\]

Weights are fixed at 0.25 before the pilot. The nonnegative anomaly-level penalty prevents negative z from receiving an upward reward due to instability; below-median accounts receive no robustness penalty. Scores are unbounded, not probabilities. Required missing statistics cause explicit baseline fallback; zero weights require no statistics. This fusion is a substantive exploratory definition, not the frozen CREST formula and not a silent E6 replacement. Its scale and asymmetric penalty require future scientific validation. Positive/negative deltas describe detector response to omission, not causal fraud evidence.

### 3. Focal-feature path and equivalence scope

`feasibility_gate/focal_features.py`, version `indexed-focal-features-global-centrality-v1`, indexes event positions once and computes only the focal account's canonical 19-vector. Behavioral and temporal calculations use its retained incident events with the original pandas aggregation, rounding and float32 conversion. Directed degree and weighted degree come from the original graph. Full nonfocal behavioral/temporal vectors and unused egonet vectors are avoided.

The global graph and betweenness calculation remain unchanged: same retained transaction order, DiGraph repeated-edge aggregation, directed unweighted shortest paths, global normalization, original node order, seed 42 and source sample size. Missing known nodes are appended in sorted order and centrality is recomputed just as in the reference. At up to 2,000 nodes centrality is exact; at 5K it uses the reference's sampled k=500 policy. Thus this is **exact equivalence to the existing reference**, not exact mathematical betweenness at 5K. No new approximation is implemented. The 10,000-node workload guard remains in place.

The cache identity includes history/dataset hashes, cutoff/time kind, account universe, focal account, omission IDs, feature/graph versions and seed. Returned vectors are copied. Only one graph scenario is retained; vector entries accumulate for this bounded pilot, so this cache is not a demonstrated large-scale memory policy. A cache hit's total time is newly measured; its stored substage timings describe the originating computation and must not be added as fresh work.

The earlier Phase 5R component optimization remains untouched and is not used here. Focal recomputation still invokes global centrality; it does not claim a dynamic shortest-path update or compute only focal betweenness. The principal cost remains global rather than local.

### 4. Fixed label-independent pilot and controls

`configs/phase5g_feasibility_v1.json` fixes selection and scoring before execution. Sort the 1,500 split-42 held-out accounts by ascending raw E4 and lexical ID, divide into three 500-account rank strata, then choose two eligible accounts per stratum in SHA-256(seed,stratum,ID) order. Eligibility requires at least two incident events and one feasible frozen candidate. This uses scores and evidence only. It is a balanced eligible sample, not a random sample of all accounts or a prevalence estimate.

Seeds: selection 1901, controls 1902, synthetic profiles 1903, intervention 17, model/split 42. The original 5K transaction bytes, historical cutoff, saved E4 model and source-training calibration are reused. No labels are used for selection, controls, fitting, fusion or pilot analysis; integrity verification hashes protected bytes without interpreting labels. No fraud-accuracy metric is computed.

All three families are attempted. Budgets retain at most two omitted transactions, 50% count, 50% amount, at least one retained event, and two accepted candidates per family. The original budgeted generator produces at most one. The temporal window is 24 hours. Rejected candidates and reasons are saved per account. Missing families are reported, not silently dropped from coverage claims.

One random control is paired to each accepted structured omission on the same account, cutoff, model and feature schema. It uniformly samples subsets with the same omitted count, rejecting any subset that violates the identical budget ceilings, for at most 128 attempts. Amount ceilings match; realized omitted amounts need not match. Identical subsets are permitted by chance and recorded. Controls are grouped by the paired structured family for aggregation; they are not claimed to satisfy that family's grouping semantics. Overlapping omissions and repeated controls are dependent observations, not independent replicates.

The pilot includes one full reference baseline, a full reference check for the first accepted omission per account, and an uncached replay for one omission per score stratum. These are feature/score diagnostics, not rerun baseline experiments. The hard worker ceiling is 1,800 seconds; no larger benchmark is launched.

### 5. Completed measurements

The recovery run completed with exit 0 in **192.439 seconds** of worker time, including diagnosis, affine checks, profiles, reference comparisons and replays. Its completion manifest SHA-256 is `97db89c06b906a228adabf8cbafd130f30b6bb4e6244d1790b0aaad6279094b3`. Source-training parameters for split 42 are m=−0.311723527322485, IQR=0.05675218332218923 and a=0.03125 (3,500 training accounts). All 12 saved splits preserved strict distinct-score ordering, original ties and zero-weight hybrid ranking. The final verifier additionally checked the union of all held-out and pilot-intervened raw scores.

| Account | Score stratum | Incident events | Structured / control accepted | Structured D | Structured R | Control D |
|---|---|---:|---:|---:|---:|---:|
| 01467_8008C3BE0 | low | 14 | 3 / 3 | −0.032964 | 0.972134 | −0.173156 |
| 011296_800808EB0 | low | 2 | 1 / 1 | +0.187346 | unavailable | +0.187346 |
| 012381_8015FC7C0 | middle | 25 | 1 / 1 | +0.164552 | unavailable | +0.107421 |
| 001241_800F239A0 | middle | 16 | 3 / 3 | −0.090801 | 0.925749 | −0.101396 |
| 01292_8002BAB10 | high | 86 | 4 / 4 | +0.313439 | 0.873165 | +0.115562 |
| 01588_8008F5240 | high | 3 | 3 / 3 | −2.507339 | 0.360290 | −3.239136 |

Cutoff: `2022-09-10 23:57:00`, interpreted by the configured UTC timestamp policy. There are **15 accepted structured omissions**, **38 rejected candidates**, and **15 accepted matched controls**, with no unmatched control. Accepted family counts are counterparty 1, temporal 8 and budgeted 6. Every family was attempted, but this is highly uneven support, not broad family validation. Candidate files retain every rejection reason and exact omitted IDs.

All 15 structured and 15 control deltas are nonzero and exceed the prespecified absolute threshold 1e−12. Structured affine deltas have minimum −3.239136, median −0.037263, maximum +0.851945 and mean −0.392107. Controls have minimum −3.239136, median −0.037263, maximum +0.187346 and mean −0.643210. All six accounts have nonzero family-aggregated sensitivity in both conditions. Negative changes are retained: omission can increase anomaly score.

| Mode | Structured changed scores / 6 | Structured changed ranks within 6 | Structured changed ranks in 1,500 | Control changed ranks in 1,500 | Pilot fallbacks |
|---|---:|---:|---:|---:|---:|
| RAW_BASE | 0 | 0 | 0 | 0 | 0 |
| RAW_SENSITIVITY | 6 | 0 | 216 | 294 | 0 |
| RAW_ROBUSTNESS | 2 | 0 | 43 | 50 | 2 |
| RAW_HYBRID | 4 | 0 | 258 | 342 | 2 |

Every mode in both conditions preserves the six selected accounts' relative ordering. Updating six scores within the fixed 1,500-account array moves many other accounts' positions; **258 moved ranks is not 258 intervention-covered accounts**. Actual intervention coverage is 6/1,500=0.4%. Sensitivity baseline coverage outside the pilot is 1,494 accounts, and robustness/hybrid fallback totals are 1,496 including two selected accounts with insufficient family support. Some available robustness scores remain unchanged because z is negative and the penalty uses max(z,0). Per-account scores, family statistics and both conditions' ranks are in `G/pilot_accounts.json` and `pilot_summary.json`.

Eight of 15 paired deltas differ; seven are identical, including three identical omission sets. The signed structured-minus-control difference ranges from −0.288012 to +2.927186, with median 0 and mean +0.251104. Distinct omission sets can also yield the same frozen detector score. These differences establish neither structured superiority nor useful fraud information. Realized amounts differ within common ceilings, family support is imbalanced, and correlated pairs from six eligible accounts are too sparse for a defensible significance claim. No p-value, confidence interval or detection improvement is asserted.

#### Feature equivalence, runtime and memory

| Workload | Reference seconds | Focal seconds | Reference / focal | Reference / focal peak traced bytes |
|---|---:|---:|---:|---:|
| 500 synthetic transactions, 248 accounts | 0.9996 | 0.7508 | 1.331× | 1,094,890 / 479,346 |
| 1,500 synthetic transactions, 739 accounts | 5.6269 | 5.3134 | 1.059× | 2,630,534 / 1,493,342 |

All 19 features and frozen scores matched exactly in both profiles. Tracemalloc measures per-call Python allocation peaks, excludes prior cache setup, and is not total process memory. These workloads exercise repeated timestamps, parallel transfers and extreme amounts; their ratios are observations, not scaling laws.

On the actual 5K history (31,463 transactions), all six baseline focal vectors matched the full reference and their saved E4 scores. The first accepted omission for each of the six accounts also matched all 19 reference features and frozen scores with maximum absolute error **0.0**. Focal times for those six scenarios were 4.012, 4.580, 4.218, 4.067, 8.253 and 4.423 seconds, against reference times 4.784, 4.602, 4.744, 4.628, 11.096 and 4.837 seconds. These are six selected checks, not independent recomputation of every accepted omission.

Three uncached low/middle/high replays reproduced features and scores exactly (4.583, 4.418 and 8.395 seconds). The final verifier rescored all 30 saved feature vectors through the frozen model, reproduced their affine deltas, and regenerated all 12 structured/control account summaries exactly. This verifies score replay for all records and graph replay for the declared subset; a second full end-to-end pilot was not run.

Of 30 intervention/control vector calls, 24 were uncached. Their average recomputation plus model scoring cost was 4.5146 seconds. Graph building plus global centrality accounted for **98.978%** of uncached recomputation time. The remaining local-feature work is already small, so eliminating nonfocal output vectors has not removed the bottleneck. Windows process RSS at pilot completion was 280,141,824 bytes, peak working set 284,794,880 bytes; peak pagefile/commit was 1,314,013,184 bytes. These OS figures differ from tracemalloc and are not full-benchmark memory forecasts. Software versions are recorded in the manifest.

### 6. Runtime feasibility, measured versus projected

The only real 5K intervention run completed here covers six accounts. Structured processing plus candidate generation ranged from 4.232 to 21.353 seconds per account (mean 10.201); controls added 47.251 seconds in total. Full diagnostic reference/replay overhead is included in the 192.439-second worker measurement, not silently treated as per-account production cost. Setup used by the scenario projections is 8.058 seconds.

`G/runtime_projections.json` uses setup + account count × observed average structured cost. A separate cache-free sensitivity scenario in `data/results/v2/phase5g-review-v1/review.json` uses the mean 2.5 accepted omissions/account × average uncached recomputation/scoring cost plus generation. Neither is a confidence bound.

| Scope | Accounts | Observed-cache scenario | Cache-free average-cost scenario | Measured complete run? |
|---|---:|---:|---:|---|
| Original frozen cohort size | 250 | 2,558 s (42.6 min) | 2,830 s (47.2 min) | No |
| Larger label-independent cohort size | 500 | 5,109 s (85.1 min) | 5,652 s (94.2 min) | No |
| Full 5K held-out population | 1,500 | 15,310 s (4.25 h) | 16,940 s (4.71 h) | No |
| Approximately 50K tier held-out count | 14,998 | 153,006 s (42.5 h) | 169,307 s (47.0 h) | No; same-5K-cost counterfactual only |

All scenarios exceed 1,800 seconds, so no larger run was started. The 250-account row is a size-based scenario, not a measured forecast for the original label-stratified cohort: eligibility, degree and family mix may differ. Cache hits can include duplicate structured/control omissions; the second scenario removes that optimistic assumption but is not an upper bound. Controls, broader verification and high-degree candidate enumeration can add further cost. An eligible sample can also overestimate costs for a population containing ineligible accounts. The six-account sample cannot determine those opposing effects.

The approximately 50K graph has 49,992 accounts and was **not** profiled by this path. Its 14,998 held-out count is multiplied by the 5K rate only to illustrate even a favorable same-cost scenario. Graph structure, centrality work and memory do not scale linearly with account count. The retained 10,000-node guard independently prevents that run. No validated 50K duration or memory estimate is claimed.

### 7. Regression tests, artifact integrity and execution evidence

Initial focused tests: **6 passed in 11.88 seconds**, exit 0, before the two final edge-case tests were added. Logs: `work/phase5g-tests/phase2-k46xe8n2/pytest.log` and `results.xml`, relative to the enclosing task workspace.

Final relevant regression command, executed in a fresh disposable repository copy:

```text
python backend/scripts/verify_phase2.py ../../work/phase5g-tests -- backend/tests/test_phase2_correctness.py backend/tests/test_phase3_interventions.py backend/tests/test_phase4_crest.py backend/tests/test_phase5_benchmark.py backend/tests/test_phase5g_feasibility.py -q
```

Result: **144 passed, 0 failed, 0 skipped, 0 errors, exit 0**, pytest duration **62.90 seconds**. No selected regression test was blocked. These include eight Phase 5G cases; the earlier six passes are a subset and are not added to the final count. This is the relevant Phase 2–5G regression set, not a claim that the full application/API suite was rerun.

Final logs and JUnit: `work/phase5g-tests/phase2-fvr74cv7/pytest.log`, `results.xml`; exact command also retained as `command.txt`. The safe wrapper creates a marker-guarded disposable copy with isolated persistence, outside the real repository. Tests cover exact and sampled reference centrality, feature order, disconnected/isolated nodes, repeated edges/timestamps, extreme amounts, cache defensive copies, invalid omissions, affine ties/collision failure, zero weights, fusion sign/fallback behavior, deterministic label-independent selection, constrained deterministic controls and exclusive artifact creation.

Independent final verifier command:

```text
python backend/scripts/verify_phase5g_gate.py data/results/v2/phase5g-feasibility-v1-recovery ../../work/phase5g-state/before.json C:/Users/hariharasuthan/Downloads/GraphFin-main.zip data/results/v2/phase5g-review-v1
```

It exited 0 and verified **87/87 protected files against both current bytes and the supplied ZIP**, **480/480 pre-existing snapshotted files unchanged**, every completed-pilot artifact/code hash, 30 saved-vector score replays and 12 account-mode replays. The unchanged snapshot includes prior source, Phase 1–5R reports/results and frontend. The frozen protocol hash above is unchanged. The review JSON records the verifier's own code hash and input manifest hash. `git diff --check` is included in final repository verification.

The interrupted initial pilot is an incomplete execution, not a passed or failed scientific equivalence test. Full 250/500/1,500-account runs were deliberately not launched because projections exceeded budget; the 50K path is also workload-guarded. These are explicit experiment limitations, not skipped pytest cases. No environment workaround, dataset rewrite or historical-output overwrite was used to obtain passing tests.

### 8. Decision gate

**Recommendation: REVISE. The scientific usefulness gate remains inconclusive; do not launch the original full benchmark on the strength of this pilot.**

| Requirement | Decision | Evidence and qualification |
|---|---|---|
| A. Preserve E4 ranking at zero intervention weights | **YES** | All 12 available splits preserve order/ties; zero-weight identity and explicit float-collision rejection tested; joint held-out/intervention check passes. |
| B. Produce useful nonzero sensitivity reproducibly | **INCONCLUSIVE** | Nonzero sensitivity is reproducible mechanically: 15/15 structured changes, 6/6 account D values, three uncached graph replays and all saved-vector score replays. Usefulness beyond random omission or for fraud detection is unestablished; 8/15 pairs differ, six-account ordering does not. |
| C. Meaningful intervention coverage within 1,800 seconds | **NO on current evidence** | Only 0.4% held-out coverage demonstrated. Even 250-account cost scenarios exceed budget; global graph/centrality remains ~99% of uncached cost. This is not a hardware-independent impossibility proof. |
| D. Defensible same-account, label-independent evaluation plan | **YES, plan only** | Freeze a separate budget-aware protocol using source-only fitting and score/eligibility/hash selection before labels; compare E4, affine base, every mode and matched controls on identical declared held-out IDs, retaining all fallbacks. |

The next step should be a **separately authorized budget-aware method and evaluation protocol**, not silent changes to the frozen Phase 5 experiment. Specify an affordable cohort/family policy using label-free timing and eligibility evidence, or develop a substantially faster centrality update with numerical equivalence. If approximation becomes necessary, name it separately and quantify feature/score/rank errors before detection claims. Selection, seed set, budgets, fallback handling, primary metric and analysis must be fixed before viewing outcomes. Do not optimize weights on this pilot's labels or retrospectively choose successful cases.

For evaluation, retain raw E4 and affine baseline comparisons; score the same held-out accounts for structured and random-control conditions. Report both scoring-population size and actual intervention/family coverage. Use a prespecified complete cohort or full population with explicit fallback and an intention-to-evaluate denominator; do not exclude missing-evidence accounts after seeing outcomes. Preserve existing split identities and distinguish a score-selected policy from full intervention inference. Source-only fitting does not make the existing transductive graph features inductive. Any future paired bootstrap must disclose sparse positives, overlapping splits, dependent graph accounts and fixed-model conditioning; it cannot substitute for independent validation. Cross-dataset work must keep target labels out of tuning.

### 9. Limitations, file inventory and phase boundary

PaySim provenance remains **unresolved**: 774 versus 2,606 positive accounts and 1,832 disagreements. No label file was changed or preferred. Other retained limitations include source-history completeness, monetary aggregation/currency semantics, transductive graph construction, float32 feature rounding and sensitivity to the reference's sampled-centrality policy. Rebuilding node order after omissions can alter sampled sources under the same seed; preserving reference semantics does not separate sampling effects from transaction effects. The detector response and controls both inherit this limitation. Small selected accounts, one model/split for interventions, unequal family support, heuristic fusion, and only three uncached replays prevent a broad scientific claim.

New source/config/test/document files in this phase:

- `backend/app/research/feasibility_gate/__init__.py`
- `backend/app/research/feasibility_gate/raw_scoring.py`
- `backend/app/research/feasibility_gate/focal_features.py`
- `backend/app/research/feasibility_gate/pilot_design.py`
- `backend/scripts/run_phase5g_gate.py`
- `backend/scripts/verify_phase5g_gate.py`
- `backend/tests/test_phase5g_feasibility.py`
- `docs/research/configs/phase5g_feasibility_v1.json`
- `docs/research/05G_algorithm_feasibility_gate.md`

New data directories: incomplete `phase5g-feasibility-v1`, complete `phase5g-feasibility-v1-recovery`, and independent verification `phase5g-review-v1`, all under `data/results/v2/`. Run IDs are exclusive: existing output directories are rejected and completion is recorded only after success. The interrupted directory is not repaired in place. Workspace-only evidence includes the before-state hash snapshot and disposable test reports. No pre-existing file was modified in Phase 5G; older Git changes belong to prior phases and remain intact.

Phase 5G's nine investigation/documentation tasks are complete with the above negative/inconclusive findings. Passing an investigation's execution checks is not passing all four scientific gates. **Phase 5 remains incomplete**, intervention-based E6 effectiveness is unvalidated, and the project is not ready to advance to Phase 6 on these results. No frontend redesign, commit, novelty claim or fraud-accuracy improvement was made.
