# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

## Phase 5H — Evidence-specificity algorithm revision

This phase implements one opt-in exploratory algorithm, **E6_CREST_V2 — Matched-Control Evidence-Specificity Scoring**. It tests whether structured omissions produce different frozen-detector responses from comparably sized random omissions. It does not fit another detector, establish causality, test fraud accuracy or replace frozen E6. The original title, research idea, datasets and historical outputs remain intact.

### Recovery, scope and provenance

The Phase 1–5G reports and supporting evidence were reviewed. The recovered Git worktree contained 16 tracked files modified by earlier phases plus their untracked research additions. Those changes were preserved. A pre-implementation byte snapshot of **535 existing files** across backend, research documents, data and frontend is retained at workspace `work/phase5h-state/before.json`. Node modules, Python/test caches and virtual environments are excluded.

The frozen Phase 5 protocol hash remains:

`508a84edfc7eef3cf2a9b99d7b776533c49d742ef5215d18ce59a4e46ec6daff`

The reused completed Phase 5G pilot is `data/results/v2/phase5g-feasibility-v1-recovery/`; its manifest SHA-256 is `97db89c06b906a228adabf8cbafd130f30b6bb4e6244d1790b0aaad6279094b3`. Its artifacts, generating code and model identity are authenticated before reuse. Both saved baseline tier manifests and their artifact hashes are verified, without rerunning model fitting or baseline experiments. Original protected bytes are checked before and after execution. Labels may be read as opaque bytes for integrity hashing but are not parsed for this pilot.

Important distinction in the incoming status: the two rank moves for sensitivity-only and robustness-only refer to the **earlier Phase 5R top-five empirical-calibration probe**. The Phase 5G six-account affine pilot had no rank changes *within its six accounts*, while its updated scores moved positions within the 1,500-account population. These populations and score versions must not be conflated. Neither result establishes detector improvement.

New configuration: `docs/research/configs/phase5h_specificity_v2.json`, fixed before v2 outcomes. Completed results: `data/results/v2/phase5h-specificity-v2-pilot-v2/`, abbreviated **H** below; `v2` here is the second execution attempt, not a second scientific formula. A completion manifest is required; absent or failed manifests cannot be treated as a completed experiment. Every output is newly created, and existing run directories are rejected. The incomplete original 250-account Phase 5 experiment and incomplete Phase 5G interruption remain unchanged.

### 1. Existing-pilot diagnosis

The old pilot includes 15 structured omissions and 15 controls on six accounts. `H/phase5g_pair_diagnosis.json` stores **every original pair**, including all original rows: raw E4, intervened scores, signed raw/affine/empirical differences, omitted IDs, counts, count/amount fractions, family, pair identity, baseline/intervened vectors, and the new strict-validity assessment. The scorer replays all 30 original feature vectors in a batch and individually against their saved scores before reuse.

Phase 5G matched omitted counts and budget ceilings, but not realized monetary fractions; it also allowed identical structured/control subsets. Seven of its 15 paired differences were zero, three involving identical subsets, while eight were nonzero. All 30 individual omission responses were nonzero. These facts motivated a stricter contrast, rather than selecting a weight to make ranks change. A nonzero paired difference is a detector-response observation, not a causal contribution of a transaction to fraud. Each recorded delta belongs to the **whole accepted omission set**; no additive per-transaction attribution is inferred for multi-event sets.

### 2. Matching policy fixed before outcomes

Implementation: `backend/app/research/evidence_specificity/matching.py`, version `same-account-decimal-caliper-two-controls-v1`.

Let H_v be the focal account's eligible incident events at cutoff T, N=|H_v| and A their total positive monetary amount. For structured set m and control set r, require:

\[
|m|=|r|=k,\qquad |m|/N=|r|/N,
\]
\[
|A_m-A_r|\le\min(0.01A,\;0.10A_m).
\]

Thus realized monetary fractions differ by at most one percentage point **and** at most 10% of the structured amount fraction. Comparisons use Decimal amounts with multiplicative thresholds, avoiding rounded-ratio boundary decisions. This is a prespecified engineering caliper to limit size confounding, not an estimated optimal tolerance or exact amount equivalence.

Both sets must satisfy the original shared constraints: nonempty, unique eligible transaction IDs; at most two omissions; at most half the incident count and monetary amount; at least one event retained. The context fixes dataset/history hashes, cutoff, time kind, universe, account, budget, matching version and seed. Model and canonical feature identity are checked by the runner. Neither future events nor another account's events can be sampled. The source/evaluation fitting membership remains the existing frozen split.

Enumerate count-k subsets in canonical ID order only when binomial(N,k)≤10,000. Filter identical-to-structured sets and all invalid/caliper-violating sets. Order the remaining sets by SHA-256 of the fixed seed (2902), complete context, structured identity and control IDs; take the first **two distinct** sets. This is deterministic pseudorandom ordering over the feasible pool, independent of scores and labels. The same pool can be reused across structured omissions, and controls can overlap; independence is not claimed. Random controls may incidentally share temporal/counterparty structure, and are not forced to be maximally different.

If fewer than two feasible alternatives exist, record unmatched and retain zero contribution/fallback as appropriate. A two-event account can therefore be valid for omission but lack two distinct controls. A search space above the bound is separately marked `search_space_exceeds_bound`, not interpreted as proof that no match exists. Tolerances, required support and enumeration limit never relax after outcomes. No synthetic transfer is introduced; controls remove existing eligible events only. Artificial event objects in unit tests are fixtures, not experimental transactions.

The match plan (identities, candidates, exact balance quantities, feasible-pool hashes and rejection reasons) is saved **before v2 scoring**. Repeating matching with the same inputs must produce exactly the same plan. A changed cutoff, population or seed changes its identity. Candidate generation does not accept labels or scores as inputs.

### 3. Scoring mathematics and numerical contract

Implementation: `evidence_specificity/scoring.py`, version `raw-e4-family-median-excess-v2`. The original frozen source-trained E4 Isolation Forest supplies

\[
s_0(v)=-\mathrm{IF.decision\_function}(x_v),\quad
\Delta_m=s_0-s_m,\quad\Delta_r=s_0-s_r.
\]

Higher scores remain more anomalous. For each family f, let M_f contain only **fully matched** structured sets and R_f their two controls per set. Define

\[
E_f=\operatorname{median}_{m\in M_f}\Delta_m-
\operatorname{median}_{r\in R_f}\Delta_r,
\qquad
E=\frac{1}{|\mathcal F|}\sum_{f\in\mathcal F}E_f,
\]
\[
S_{v2}=s_0+\lambda E,\qquad\lambda=1.
\]

Only nonempty matched families enter F. Exactly two controls per structured set gives every included set equal control multiplicity; no partially matched set contributes on either side. The family statistic is a **difference of medians**, not a median of paired differences or an effect standardized by variance. Control reuse can still overweight a common subset in the empirical pooled distribution; identities and duplicates remain visible. Equal-family aggregation avoids automatically favoring a family merely because it has more candidates, but families with one match have weaker support than those with two.

The unit coefficient is fixed before outcomes: one raw-score unit of excess response contributes one raw-score unit to the ranking. Both quantities have identical units, so no label-fitted normalization is needed. This is a transparent mechanistic hypothesis, not a theorem that unit weighting is optimal or that excess predicts fraud. There is no percentile/logistic transform, no clipping, and no fitted calibration in v2. Frozen v1 remains separate.

Negative excess reduces the score and is preserved; zero excess leaves it exactly unchanged. With no valid structured sets or no fully matched family, return the raw E4 score and an explicit reason. Zero weight returns the original floating-point score exactly regardless of missing evidence. Ranking uses descending unrounded score followed by ascending account ID. Changed ranks are not forced. Nonzero-weight equality may be a genuine algebraic tie, not calibration quantization.

All scores/deltas/weights must be finite. Median arithmetic avoids overflow from adding two large same-sign values; mean aggregation scales before summation. Nonfinite intermediate differences, overflow, or a nonzero contribution absorbed by float64 addition fail explicitly instead of clipping or silently returning a baseline. A threshold of 1e−12 is used only to describe effects above a conservative numerical diagnostic floor, never to tune, zero out or select scores. Every family input, median, excess, support count, final contribution and fallback is persisted.

### 4. Fixed cohort and fair version comparison

All six Phase 5G accounts are reused, without additions or favorable-outcome selection. Their original selection is replayed from raw E4 and evidence eligibility: two accounts from each of three equal-size held-out score strata in seeded hash order. The new activity categories are declared as 2–4, 5–29 and ≥30 incident events; the fixed cohort contains all three (counts 2,3; 14,16,25; 86). It is not a full score-by-activity factorial design and is not representative of all accounts.

The same six account IDs receive raw E4, original empirical **E6_BASE_V1** and **E6_HYBRID_V1**, the saved **PHASE5G_AFFINE_HYBRID**, and **E6_CREST_V2**. Frozen v1 is applied through its unchanged calibration/statistics/fusion functions to the same structured observations. It has its own scale and baseline ties; cross-version raw numerical scores are not directly commensurate. V2 uses strict matching, so evidence coverage differs and is reported explicitly rather than silently restricting E4/v1 to matched accounts.

Full 1,500-account arrays additionally preserve each method's nonselected baseline fallback. They permit positional diagnostics, not a claim of full intervention coverage. No AP, precision, recall, label counts for this cohort or new confidence interval is computed. No label influences cohort, matching, formula, weight or missingness handling.

### 5. Safe computation and reproducibility

The Phase 5G indexed focal recomputer is reused unchanged: original 19 features, rounding and float32 conversion; original directed graph semantics, node order, global normalization, sampled k=500 centrality at 5K and seed 42. Exact equivalence is to that **sampled reference policy**, not to exact mathematical betweenness. No centrality approximation or component substitution is introduced.

Optimizations in this phase are authenticated reuse and scheduling: bind saved vectors to full history-aware cache identities and model hashes; deduplicate identical `(account, omitted-ID set)` requests; compute each new scenario once; reuse canonical event indexing; batch frozen-model scoring and check it bit-for-bit against singleton scoring. Graphs are not reconstructed for verified reused scenarios. No unverified cross-graph component cache is introduced. A cold run still needs global centrality for every distinct scenario.

The first newly needed control in each represented score stratum is checked against full reference recomputation and an uncached focal replay. All scored vectors, including reused ones, are batch/singleton checked. No `fit` operation exists in the new inference interface; the experiment authenticates the saved source model and rejects selected-account overlap with its training IDs. Tests separately exercise the earlier source-only fitting boundary.

The runner creates a new output directory, saves configuration, then launches an owned worker under a hard 1,800-second parent timeout. Failure or timeout produces an incomplete marker; completion manifest is written last. Code/configuration changes during execution are rejected. Dataset, history, model, calibration, upstream manifests, source files, software versions, seeds, output hashes, runtime and OS memory are recorded. Replays compare scientific values, not timing-dependent artifact bytes.

### 6. Completed pilot observations

The corrected pilot completed in **128.691 seconds**, exit 0. It retained all six accounts and all 15 valid structured omissions. **11 structured omissions have two strict controls each (22 control observations)**, spread over four accounts. Four omissions are unmatched: the two-event account has zero feasible nonidentical alternatives under the calipers, and each of three omissions on the three-event account has only one feasible alternative. They are not converted to single-control comparisons. No enumeration-limit failure occurred on this cohort.

Matched family counts: counterparty **1**, temporal **6**, budgeted **4**. This is sparse, imbalanced family support. Feasible pools for matched omissions range from 20 to 391; the fixed seed selects only two controls from each pool. The largest realized monetary-fraction gap is **0.0002854534** (0.02855 percentage points), well within both prespecified calipers. Some controls overlap or repeat across comparisons; those observations are not independent.

Reassessing the old Phase 5G controls yields four comparable pairs, eight rejected by the monetary caliper and three rejected as identical sets. Of the four comparable old pairs, two have zero excess and two have nonzero excess (0.0017853490 and 0.0914745488 raw-score units). The latter is the largest old pair difference, but that account lacks two distinct feasible controls and therefore has no v2 contribution. This is a support-rule consequence, not evidence that its earlier large response was meaningless. Across all old pairs, eight differences exceed 1e−12; the new checks do not retrospectively redefine their validity under the old protocol.

| Account | E4 score stratum | Activity group/count | Matched / valid structured | Raw E4 | E(v) | V2 score | Fallback |
|---|---|---|---:|---:|---:|---:|---|
| 01467_8008C3BE0 | low | middle / 14 | 3 / 3 | −0.326931640 | +0.000134356 | −0.326797284 | no |
| 011296_800808EB0 | low | low / 2 | 0 / 1 | −0.332324349 | unavailable | −0.332324349 | yes |
| 012381_8015FC7C0 | middle | middle / 25 | 1 / 1 | −0.314495018 | 0 | −0.314495018 | no |
| 001241_800F239A0 | middle | middle / 16 | 3 / 3 | −0.315409551 | +0.000331087 | −0.315078464 | no |
| 01292_8002BAB10 | high | high / 86 | 4 / 4 | −0.112006018 | +0.006183637 | −0.105822381 | no |
| 01588_8008F5240 | high | low / 3 | 0 / 3 | −0.278171344 | unavailable | −0.278171344 | yes |

All **four available budgeted-family excesses are exactly zero**. Many structured and control omissions produce identical model responses even with different event IDs. Temporal-family excesses are +0.0002687113, +0.0006621743 and −0.0044610448 for the first, fourth and fifth accounts respectively. The only counterparty excess is +0.0230119567 for `01292_8002BAB10`. Thus four of eight available account-family statistics are nonzero, including a negative temporal effect. Three of six aggregate account excesses are nonzero; one matched account has zero excess, which is distinct from the two unavailable accounts.

These differences are much larger than the 1e−12 descriptive threshold and the observed zero batch/replay error. They are numerically real changes of this frozen detector under these omissions. They do not isolate causal fraud evidence, establish statistical distinguishability across accounts or generalize to alternate control seeds. Only two controls per set and one model/split were used; there is no uncertainty estimate for control sampling.

### 7. Ranking behavior, kept separate from detection performance

| Method | Changed ranks among the six, versus E4 | Changed positions in full 1,500, versus E4 |
|---|---:|---:|
| Raw E4 | 0 | 0 |
| Frozen empirical E6_BASE_V1 | 0 | 288 |
| Frozen E6_HYBRID_V1 on these six | 0 | 366 |
| Saved Phase 5G affine hybrid | 0 | not regenerated in this phase |
| E6_CREST_V2 | **0** | **10** |

The first six-account ordering stays unchanged in every version. V2 changes three scores, but only two treated accounts move within the full population: `001241_800F239A0` moves 818→812 and `01292_8002BAB10` moves 31→29. Eight other accounts shift by one position because of these moves. The third nonzero excess does not cross a neighboring score. All positions and full arrays are saved in `H/rankings.json`.

Only **4/1,500 (0.267%)** full-population accounts have matched v2 evidence, and **3/1,500 (0.2%)** receive nonzero contributions. Full-population fallback is **1,496/1,500**, including the two unmatched selected accounts; the matched zero-excess account is not an unavailable-evidence fallback. Ten changed positions are not ten newly analyzed accounts. All 15 original structured observations were retained for diagnosis, even where no v2 match exists.

Raw E4 has 1,133 unique full-population scores; v2 has 1,134, while empirical E6_BASE_V1 has 874 and E6_HYBRID_V1 has 876. There is no calibration transform in v2, and zero-weight checks reproduce E4 exactly on all 12 available splits. Counts of unique scores alone do not prove all pairwise arithmetic properties; explicit finite/addition checks and zero-weight identity are the relevant safeguards.

The v1 full-population differences include empirical-calibration ties already present before interventions. They are not directly comparable to v2's raw-score excess as a measure of algorithm quality. The fixed v2 weight was not changed to increase movement. No claim that fewer/more rank moves is better is made.

### 8. Runtime, memory and feasibility

The completed run needed **32 distinct focal omission scenarios** from 15 structured and 22 control observations. It reused **15 authenticated Phase 5G scenarios** and computed **17 fresh scenarios**. Deduplication avoids five repeat requests, including any repeated structured/control sets. Fresh recomputation consumed **82.061 seconds**, mean **4.827 seconds** per scenario. Matching plus its deterministic repeat took **8.072 seconds**; batch scoring plus singleton verification took **0.515 seconds**. These costs are measured separately and must not be mistaken for a new global-centrality speedup.

All three declared low/middle/high fresh-control checks matched full reference features and frozen scores exactly and matched uncached focal replays. The reused source vectors retain Phase 5G's own validation scope; this phase checks their checksums, history-aware identities and raw-score replay. Source hashes, configuration, versions and output hashes are retained in the run manifest.

At summary collection, process RSS was **271,646,720 bytes**, peak working set **281,239,552 bytes**, and peak pagefile/commit **1,313,562,624 bytes**. These are Windows process measures, not Python allocation peaks or estimates for a larger graph. The final manifest also records its later memory snapshot.

The 128.691-second run is an **incremental reused-evidence measurement**; a new cohort would not inherit these saved vectors. Cold-cost scenarios use 32/6 distinct scenarios per account × mean fresh recomputation plus matching/replay time per account, giving **27.090 seconds/account**. They exclude startup, reference checks and the small separate model-scoring cost, and include the matching repeat. They are neither upper bounds nor confidence intervals.

| Scope | Accounts | Projected cold cost using the observed 5K mix | Within 1,800 seconds? |
|---|---:|---:|---|
| Frozen exploratory cohort size | 250 | 6,773 s / 1.88 h | no |
| Larger label-independent cohort size | 500 | 13,545 s / 3.76 h | no |
| Full 5K held-out population | 1,500 | 40,635 s / 11.29 h | no |
| Approximately 50K held-out population | 14,998 | 406,296 s / 112.86 h | no; same-5K-cost counterfactual only |

No larger run was launched. The 250-account row is a scenario for that size, not a measured run or a validated forecast for the original label-stratified IDs. This eligible six-account mix can overstate coverage/work for sparse accounts and understate work for high-degree accounts. Duplicate rate, monetary matching, search bounds and family support can change sharply with population. Running only unmatched fallback accounts quickly would not demonstrate useful intervention coverage.

The 49,992-node graph was not profiled here and still exceeds the 10,000-node reference guard. Multiplying its held-out count by the 5K rate is not a graph-scaling model; its actual centrality and memory costs remain unknown. Saved vector reuse and batch inference improve repeated diagnostics but do not solve the cost of a new full cohort with distinct omissions.

### 9. Final verification and recovered execution record

Finalized 2026-10-22 (Asia/Calcutta). Finalization reused the completed experiments and recovered test reports; **neither experiment nor the completed regression suite was restarted**. Read-only checksum and scientific-value comparisons were executed again and exited 0.

The complete replay is `data/results/v2/phase5h-specificity-v2-replay-v1/`, completed in **119.087 seconds**, exit 0. The independent verifier previously exited 0 and wrote `data/results/v2/phase5h-verification-v1/review.json`. Its results were reconfirmed during finalization:

| Compared evidence | Result |
|---|---|
| Six account identities, cohort and membership hashes | Exact match |
| Structured omission IDs and control identities, including unmatched status | Exact match |
| Matching plans and feasible-pool hashes | Exact match |
| All 32 distinct focal feature vectors and frozen-model scores | Exact match |
| Raw signed deltas, family medians/excess, account excess and contributions | Exact match |
| V1/v2 scores, full and six-account rankings, fallback reasons | Exact match |
| Zero-weight checks on all 12 saved baseline splits | Exact match; scores and ranks preserved |
| Original-pilot pair diagnosis | Exact match |
| Completed run artifact hashes and generating-code hashes | All verified |

**Scientific mismatches: zero.** Comparisons exclude matching/runtime durations, recomputation timing subfields, memory and completion timing; those are performance observations, not deterministic scientific outputs. The verifier independently recomputed all eight available family statistics; four exceed 1e−12 in absolute value. There are 22 control observations but only **21 unique control scenarios**. Repeatability under one fixed seed does not establish robustness across seeds or independent controls.

Completion manifest identities:

- Pilot: `cc17a7ebd2ba50f559c244a14fca38f59d9624b08e4515a50c7a587df5cffe53`.
- Replay: `2f502c84b89a9500bc4267bb741cc9d84111686aa7c8ccd08efa645269907135`.

The initial `phase5h-specificity-v2-pilot-v1/` attempt **failed with exit 1** after recomputation, at the v1 adapter: `KeyError: 'omitted_fraction'`. This was a new adapter defect, not an environmental failure or a failure of the original v1 algorithm. Its `incomplete.json` and partial files are retained; it has no completion manifest and is excluded from conclusions. The adapter was corrected to retain the original omission metadata, and a saved-Phase5G-to-v1 integration regression was added. No formula, caliper, weight, account selection or historical code was altered to recover the run.

Test execution record:

| Run | Passed | Failed / errors | Skipped | Exit | Pytest duration |
|---|---:|---:|---:|---:|---:|
| Initial focused Phase 5H tests | 11 | 0 / 0 | 0 | 0 | 2.15 s |
| Focused tests including adapter regression | 12 | 0 / 0 | 0 | 0 | 2.32 s |
| Final Phase 2–5H relevant regressions | **156** | **0 / 0** | **0** | **0** | **60.29 s** |

The focused runs are subsets, not extra distinct passes to add to 156. No selected test is blocked. The failed experiment above is reported separately from pytest results. The full backend/API suite was not rerun in this phase. No environment-specific failure was observed in the selected tests.

Final command:

```text
python backend/scripts/verify_phase2.py ../../work/phase5h-tests -- backend/tests/test_phase2_correctness.py backend/tests/test_phase3_interventions.py backend/tests/test_phase4_crest.py backend/tests/test_phase5_benchmark.py backend/tests/test_phase5g_feasibility.py backend/tests/test_phase5h_specificity.py -q
```

The wrapper ran in a disposable repository copy, with isolated persistence. Final evidence is at workspace `work/phase5h-tests/phase2-u2wvbip6/pytest.log`, `results.xml`, and `command.txt`. JUnit records 156 tests, zero errors/failures/skips and 60.249 seconds; the console reports 60.29 seconds. The successful process exit code 0 was observed when that run completed. Earlier focused logs are under `phase2-_471ai87` and `phase2-k2kkuv58` in the same scratch directory.

Coverage includes Decimal matching boundaries, exact count/fraction constraints, deterministic selection, context identity, insufficient-control/search-bound handling, signed and family-balanced aggregation, missing evidence, zero contribution/weight, lexical tie-breaking, numerical overflow/nonfinite/absorbed-addition rejection, frozen inference without fitting, feature equivalence, batch/singleton identity, v1 adapter compatibility, append-only output and original-file checks. Existing Phase 2–5G tests retain source-only fitting and prior algorithm regression coverage.

All **87 protected files** remain byte-identical to both the protected manifest and supplied ZIP. All **535 pre-existing snapshotted files** remain unchanged, including prior results, datasets, backend research implementations and frontend. The frozen Phase 5 protocol hash remains unchanged. Final `git diff --check` passed with exit 0. Older uncommitted changes remain intact; no reset or commit was performed.

### 10. Exact account-level rank displacement

These are **all ten** changed positions in the 1,500-account array:

| Account | E4 rank | V2 rank | Explanation |
|---|---:|---:|---|
| 001241_800F239A0 | 818 | 812 | Treated pilot account; excess +0.0003310871 crosses six scores |
| 0037984_80F24F2B0 | 812 | 813 | Unchanged score; displaced by the account above |
| 003144_80E0C6470 | 813 | 814 | Unchanged score; displaced |
| 014099_8019DB1F0 | 814 | 815 | Unchanged score; displaced |
| 013145_8015E6B80 | 815 | 816 | Unchanged score; displaced |
| 011107_8013AC690 | 816 | 817 | Unchanged score; displaced |
| 00220_800FAF410 | 817 | 818 | Unchanged score; displaced |
| 01292_8002BAB10 | 31 | 29 | Treated pilot account; excess +0.0061836373 crosses two scores |
| 010_8001E37F0 | 29 | 30 | Unchanged score; displaced by the account above |
| 01362_800994F60 | 30 | 31 | Unchanged score; displaced |

`01467_8008C3BE0` has a nonzero excess of +0.0001343557 but crosses no score. The other three pilot scores are unchanged: one has exactly zero matched excess and two have missing-evidence fallback. None of the six pilot accounts crosses another pilot account. Accordingly the fixed six-account ordering remains identical, while only two treated accounts cause all ten full-population displacements. There is no evidence here that the displaced accounts were ordered more correctly with respect to fraud.

### 11. Final scientific decision

**STOP RANKING EXTENSION. Preserve CREST as an evidence-sensitivity and model-explanation research component.** This is a decision about the current evidence and budget, not a proof that any future intervention approach must fail.

| Finalization question | Decision | Evidence |
|---|---|---|
| 1. Informative excess beyond matched controls? | **INCONCLUSIVE** | Four account-family effects and three account aggregates are numerically nonzero, but four budgeted-family effects are zero; only four accounts have matched evidence and controls are sparse/dependent. Generalizable information beyond random omission is unestablished. |
| 2. Reproducible results? | **YES** | Exact scientific replay, all 32 feature/score rows, matching, statistics, ranks and fallbacks; zero-weight identity on 12 splits. |
| 3. Rank changes substantial enough to justify continued ranking research now? | **NO on current evidence** | Six-account order unchanged; only two treated accounts move, by six and two places. No label-based benefit or independent validation exists. Movement alone does not justify escalation. |
| 4. Feasible computation at meaningful coverage? | **NO on current evidence** | Four matched accounts demonstrated; cold 250-account scenario about 6,773 s versus 1,800 s. Reuse does not solve cold global-centrality cost. |
| 5. Credible future detector-performance evaluation possible? | **INCONCLUSIVE** | Possible in principle with sufficient verified data and affordable complete coverage, but neither is demonstrated for this mechanism under current constraints. |

For the original Phase 5H A–E gate: **A YES** (zero-contribution E4 identity); **B INCONCLUSIVE** (generalizable structured/control distinction); **C INCONCLUSIVE** (reproducible numerical displacement exists, but useful nontrivial ranking information is unestablished); **D NO on current evidence** (coverage/cost); **E INCONCLUSIVE** (adequately supported future detector comparison). This distinguishes a successful numerical implementation from an accepted detector hypothesis.

The supported use is inspecting how a frozen model responds to bounded evidence omissions, showing matched-control comparisons, uncertainty in evidence availability, and unchanged/negative responses. It must remain labeled as **model sensitivity**, not a causal explanation, fraud probability, validated explanation quality or improved laundering detection. Preserve the v1/v2 code and artifacts for audit; do not introduce another scoring formula or relax matching to manufacture a favorable result.

Before any separately authorized detector benchmark, prerequisites would include verified label provenance, a prespecified meaningful evaluation population and positive/negative counts, sufficient compute or a validated major recomputation improvement, same-account comparisons with explicit fallbacks, control-seed/model-seed robustness, and an analysis plan addressing graph dependence and sparse positives. Existing reports document only six positives in the 5K split-42 holdout and 75 in the approximately 50K split-42 holdout; these are historical population facts, not a power calculation or a new label inspection. An appropriate sample size cannot be invented without a target effect and uncertainty model. PaySim's 774-versus-2,606 label conflict remains unresolved and cannot supply an unqualified validation dataset.

Phase 5R's exact component path was also considered: its small-graph equivalence and mixed/slower sparse-workload timing did not offer a demonstrated solution at 5K, where original sampled-global semantics remain necessary. No safe component cache or centrality approximation was substituted in Phase 5H. Existing transductive features, sampled-pivot/order effects, overlapping omissions, coarse feature rounding, incomplete source history and monetary/currency semantics continue to limit interpretation.

### 12. Acceptance status, file inventory and stopping boundary

| Phase 5H task | Final disposition |
|---|---|
| Preserve original research and version the extension | Satisfied: 87 protected and 535 pre-existing files unchanged; exclusive new namespace |
| Diagnose every old pair | Satisfied: all 15 structured/control pairs, raw responses and strict reassessment retained |
| Prespecify strict matching | Satisfied: exact count/fraction, dual Decimal amount calipers, two-control support, unmatched reasons |
| Implement signed evidence-specificity statistics | Satisfied: family medians, pooled matched controls, intermediate statistics and explicit missingness |
| Separate v2 ranking | Satisfied: raw E4 plus fixed unit-weight excess; v1 retained; no tuning |
| Safe recomputation efficiency | Satisfied at bounded scope: authenticated reuse, deduplication and verified batch inference; no scalable-centrality claim |
| Label-independent bounded pilot | Satisfied: same six accounts, score/activity coverage and recorded matching gaps |
| Separate ranking from detection performance | Satisfied: no detector metrics or improvement claim |
| Compute feasibility gate | Completed with negative result; larger runs not launched |
| Scientific decision | STOP RANKING EXTENSION, with explanation-only research direction |
| Tests, replay, preservation and report | Satisfied: 156 passes, exact replay and explicit failed-attempt history |

Thus **Phase 5H's bounded implementation, investigation and reporting scope is complete**, but its scientific evidence does **not** pass a GO gate for further ranking benchmarks. Original Phase 5 E6 benchmarking remains incomplete and must not be relabeled complete.

New files from Phase 5H:

- `backend/app/research/evidence_specificity/__init__.py`
- `backend/app/research/evidence_specificity/matching.py`
- `backend/app/research/evidence_specificity/scoring.py`
- `backend/scripts/run_phase5h_specificity.py`
- `backend/scripts/verify_phase5h_specificity.py`
- `backend/tests/test_phase5h_specificity.py`
- `docs/research/configs/phase5h_specificity_v2.json`
- `docs/research/05H_evidence_specificity_revision.md`

The only repository file edited during finalization is this Phase 5H report. Failed attempt, corrected pilot, replay and verification directories are retained separately under `data/results/v2/phase5h-*`. Workspace snapshots and disposable test evidence remain under `work/phase5h-state/` and `work/phase5h-tests/`. No original dataset, label, E0–E5/frozen E6 implementation, historical result or frontend was changed. No Phase 6 work or Git commit was performed. Stop at Phase 5H.
