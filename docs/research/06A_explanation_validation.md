# Phase 6A — CREST explanation validation

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Scope: completed explanation diagnostics for frozen E4. Phase 5H's **STOP RANKING EXTENSION** decision remains in force. No new detector, ranking formula, GNN, label tuning, model fitting, frontend changes or deployment. Final Phase 6A decision: **REVISE**.

## 1. Objective and prior evidence

Evaluate whether historical transaction omissions give valid, reproducible, stable and affordable explanations of the existing Isolation Forest's response. Fidelity is a model-response diagnostic, not a causal effect, fraud confirmation, explanation ground truth, or detection-performance metric.

The Phase 1 audit identified feature redundancy, baseline inconsistencies and provenance risks. Phase 2 corrected split isolation and AP bootstrap semantics and introduced manifests. Phase 3 implemented constrained historical evidence removal. Phase 4 implemented CREST scoring, and Phase 5 froze the primary benchmarking protocol. Phase 5R documented computational constraints; Phase 5G tested focal recomputation and score sensitivity; Phase 5H found insufficient support for a ranking extension. These reports and their implementations are preserved. The original frozen Phase 5 E6 benchmark remains incomplete. PaySim's 774 versus 2,606 positives and 1,832 disagreements remain unresolved.

## 2. Definitions and methods

Let H be the ordered historical event table at inclusive cutoff T, H_v the events incident to account v, and O a set of distinct incident transaction identifiers. A valid omission satisfies

\[
O\subseteq H_v,\quad 1\leq |O|\leq2,\quad |O|/|H_v|\leq0.5,\quad |H_v\setminus O|\geq1,
\quad \frac{\sum_{e\in O}a_e}{\sum_{e\in H_v}a_e}\leq0.5.
\]

Amounts are positive finite supplied values; budget comparisons use Decimal arithmetic. Cutoff, population and frozen model remain the same for all original-history methods. No transaction is created for an explanation. Removal changes a hypothetical evidence view, never original files.

For the existing canonical19 feature pipeline phi and frozen E4 model f,

\[
s_0(v)=-f.\mathrm{decision\_function}(\phi(H,v)),\quad
s_m(v)=-f.\mathrm{decision\_function}(\phi(H\setminus O_m,v)),\quad
F(v,m)=s_0(v)-s_m(v).
\]

Negative F is retained. It means the removed evidence suppressed rather than supported the original anomaly score. The model offset cancels in F. Neither absolute value nor a positive-part transformation replaces signed fidelity. Median absolute change is reported as a separate responsiveness statistic.

| Method | Outcome-blind selection rule |
|---|---|
| A: CREST counterparty | First lexicographically eligible **whole** counterparty group |
| B: CREST temporal | First lexicographically eligible **whole** 24-hour historical block |
| C: amount heuristic | Maximum exact omitted amount among all eligible A/B groups |
| D: count heuristic | Maximum omitted count among the same eligible A/B groups |
| E: random | Two distinct feasible count-and-money-matched random omission sets **per available A–D anchor** |

C/D ties use ascending family, string candidate key and sorted IDs. Temporal blocks are right-closed `(T-(b+1)w,T-bw]`; existing lexicographic block order is retained, not interpreted as chronological order. C/D cannot take partial groups or larger budgets. A/B select one predefined eligible group, not the best score-changing group. This tests a bounded deployment policy, not an optimized search over every CREST candidate. The old budgeted family is not substituted when whole groups are unavailable.

E reuses Phase 5H's strict matcher unchanged, with control seed 3902. It enumerates at most 10,000 count-matched subsets, excludes the anchor and requires two distinct sets. Same-account count and history fraction match exactly. With anchor amount a, control amount c and total incident amount V, require `|a-c| <= min(0.01 V, 0.10 a)`. Hash ordering selects two without inspecting scores. Insufficient controls remain unmatched. E_A through E_D are conditional baselines; pooling them as one independent population would be misleading.

Direct A–D paired comparisons require the same account, same omitted count and the symmetric caliper `|a-b| <= min(0.01 V, 0.10 min(a,b))`. Identical evidence is comparable and yields zero difference. Unmatched comparisons retain explicit reasons. Mean random fidelity is first calculated within each account from its two controls; these controls are not independent accounts. Matched excess is F_anchor minus that within-account mean, **not a new anomaly score**.

Sparsity is the vector `(omitted count, count/incident count, omitted amount/incident amount, distinct counterparties, distinct 24h blocks)`. Monetary amounts and denominator counts are also stored. A count of one may remove half a two-event history; low absolute size alone does not establish sparsity. We inspect size–fidelity pairs descriptively without fitting an optimum or claiming monotonicity.

## 3. Cohort, configuration and safeguards

All six fixed Phase 5G accounts are reused, without additions or outcome-based exclusion. The selection ranks all 1,500 held-out E4 scores into three equal score strata and uses seed 1901 hash ordering to choose two eligible accounts per stratum. Eligibility originally required at least two events and at least one frozen feasible candidate, including the budgeted family. Consequently some selected accounts have no eligible A/B whole group; they remain in all coverage denominators.

| Account | Score stratum | Incident events | Original E4 |
|---|---|---:|---:|
| 01467_8008C3BE0 | Low | 14 | -0.3269316397323523 |
| 011296_800808EB0 | Low | 2 | -0.33232434880850925 |
| 012381_8015FC7C0 | Middle | 25 | -0.31449501833947696 |
| 001241_800F239A0 | Middle | 16 | -0.31540955124866077 |
| 01292_8002BAB10 | High | 86 | -0.11200601809729405 |
| 01588_8008F5240 | High | 3 | -0.2781713444681683 |

Activity strata 2–4, 5–29 and >=30 are represented, but coverage is six selected eligible accounts, **not a random sample of all financial accounts**. Original graph features are transductive. No fraud labels enter selection, matching, scoring or evaluation; hashing protected label files for integrity is not label-driven modeling.

Frozen specification: `configs/phase6a_explanations_v1.json`. Data: `data/research/ibm_aml_medium_5k.csv`, 31,463 events, 5,000 accounts; cutoff `2022-09-10 23:57:00 UTC`. Dataset SHA256 `622d421b8ba1463ac0acc423f77fbf8a5c5604e5d2b1ea07b80e13dfb5a0a3f2`. Frozen E4: `data/results/v2/phase5-baselines-5k-v1/split-42-model-42/model.joblib`, SHA256 `81758da48c8de36f7d3ee08e5a00881ef7d6beaf14877ad758b9e4422f02a298`. Model and split seeds 42; graph centrality seed 42; control seed 3902; synthetic selection seed 3903. Manifest stores software versions, exact code/dataset/model/history hashes, held-out ID hash, configuration, provenance and artifact digests. No bootstrap or confidence interval is used in this six-account diagnostic study.

The optimized focal extractor is checked against the existing full-reference extractor, not against an invented exact-centrality implementation. Both retain the existing sampled betweenness policy (k=500 at this graph size), seed and node-order semantics. **Exact equivalence to the reference does not mean exact betweenness.**

## 4. Stability protocol

Fixed-seed selection and matching are replayed. Frozen batch scoring is checked against singleton scoring. Uncached features and full-reference features are compared for the first account in each original score stratum; an account without a selected omission is checked at its original baseline rather than replaced.

The same three representatives undergo two independent shadow-history diagnostics: reverse every historical row while preserving transaction IDs and values; and increase one incident amount selected by SHA256(seed,account,ID) by 1% while preserving positivity, identity, endpoints and time. Synthetic changes are in memory only and are diagnostic perturbations, not generated explanation evidence. Each variant has a new history hash and uses the same frozen model. Fidelity is measured against that variant's own baseline, avoiding conflation of baseline displacement and omission response.

Evidence-set similarity is `J(O,O')=|O intersection O'|/|O union O'|`; empty/empty is defined as 1, but unavailable methods are not scored as successful stability observations. The first two eligible groups' overlap is also reported; disjoint candidates indicate diversity, not replay failure. Random controls are history-hash conditioned, so order-equivalent histories can alter their identities. Genuine perturbation stability and implementation determinism are reported separately.

## 5. Verified literature and novelty boundaries

Primary publication records were checked on 2026-10-22. Years below are the cited publication versions, not search-engine crawl dates or preprint years. Proceedings without a DOI on their publisher record are identified explicitly rather than assigned a guessed DOI.

| Publication | Verified identifier | Relevance and boundary |
|---|---|---|
| Mothilal, Sharma and Tan (2020), **Explaining Machine Learning Classifiers through Diverse Counterfactual Explanations**, FAT* | DOI [10.1145/3351095.3372850](https://doi.org/10.1145/3351095.3372850); [author paper in NSF repository](https://par.nsf.gov/servlets/purl/10179945) | Feasible, diverse counterfactuals and proximity constraints are established concepts. GraphFin measures historical omission response, not decision-flipping actionable recourse. |
| Ying et al. (2019), **GNNExplainer: Generating Explanations for Graph Neural Networks**, NeurIPS 32 | [Publisher record](https://proceedings.neurips.cc/paper_files/paper/2019/hash/d80b7040b773199015de6d3b4293c8ff-Abstract.html); no proceedings DOI listed | Compact graph/feature explanations are established. GraphFin uses fixed handcrafted graph features and Isolation Forest, not a GNN explanation optimizer. |
| Lucic et al. (2022), **CF-GNNExplainer: Counterfactual Explanations for Graph Neural Networks**, AISTATS, PMLR 151:4499–4511 | [Publisher record](https://proceedings.mlr.press/v151/lucic22a.html); no proceedings DOI listed | Edge deletions and minimal prediction-changing perturbations are established. GraphFin removes identified transactions under financial-history budgets; it does not prove minimality or prediction flips. |
| Carletti, Terzi and Susto (2023), **Interpretable Anomaly Detection with DIFFI: Depth-based feature importance of Isolation Forest**, Engineering Applications of Artificial Intelligence 119, 105730 | DOI [10.1016/j.engappai.2022.105730](https://doi.org/10.1016/j.engappai.2022.105730); [publisher metadata](https://www.sciencedirect.com/science/article/abs/pii/S0952197622007205) | Isolation Forest explanation is established, including tree-depth feature importance. GraphFin's evidence-level recomputation is different from attributing importance directly to fixed feature columns; no efficiency advantage over DIFFI is demonstrated. |
| Rao et al. (2022 in the paper's reference format), **xFraud: Explainable Fraud Transaction Detection**, PVLDB 15(3):427–436 | DOI [10.14778/3494124.3494128](https://doi.org/10.14778/3494124.3494128); [publisher PDF, p.1](https://www.vldb.org/pvldb/vol15/p427-rao.pdf) | Transaction-graph interpretation is established. xFraud combines a heterogeneous GNN detector and graph explainer; GraphFin does not reproduce its tasks, scale or results. Some catalogues date the issue 2021; this report follows the PDF's explicit 2022 reference year. |

These comparisons are conceptual, not empirical head-to-head benchmarks. The defensible GraphFin-specific engineering contribution is the auditable connection from constrained historical transaction IDs through recomputed canonical graph features to a frozen anomaly score, with same-account monetary controls, explicit unavailability and provenance. General perturbation explanations, sparsity, signed score sensitivity and matched comparisons are not claimed as new inventions. This is primarily an application and validation of established ideas; a novel general explanation algorithm is not established.

## 6. Actual fidelity and coverage results

Completed artifact directory: `data/results/v2/phase6a-explanations-v1-pilot-v2/`. Manifest SHA256: `b7a88eea435bbcce29881e6c06a01d5cf6579dadd26d051ff88ce2630ca6069e`. Artifact verification: `data/results/v2/phase6a-verification-v1/verification.json`. All numerical tables below are rounded for display; stored arrays and scores retain their original precision.

There are 24 A–D account/method records: **13 available, valid records and 11 unavailable records**, representing only **five distinct account/omission scenarios**. There are 20 matched-random records across ten account/method anchors, with substantial reuse. These records must not be treated as 33 independent accounts. Two accounts, `011296_800808EB0` and `012381_8015FC7C0`, have no eligible whole-group explanation under any A–D method. `01588_8008F5240` has a valid one-event explanation but fewer than two strict matching controls. Unavailable is not zero fidelity and unmatched is not zero excess.

| Method | Available / 6 | Valid / available | Mean signed F | Median signed F | Median absolute F | Positive fraction |
|---|---:|---:|---:|---:|---:|---:|
| A counterparty | 1/6 | 1/1 | 0.026623280 | 0.026623280 | 0.026623280 | 1/1 |
| B temporal | 4/6 | 4/4 | -0.027270846 | -0.003616668 | 0.003616668 | 0/4 |
| C amount | 4/6 | 4/4 | -0.019267763 | -0.001235670 | 0.014233782 | 1/4 |
| D count | 4/6 | 4/4 | -0.019267763 | -0.001235670 | 0.014233782 | 1/4 |
| E_A, mean of two controls/account | 1/6 | 2/2 controls | 0.003611324 | 0.003611324 | 0.003611324 | 1/1 accounts |
| E_B, mean of two controls/account | 3/6 | 6/6 controls | -0.000240596 | -0.001164479 | 0.003168633 | 1/3 accounts |
| E_C, mean of two controls/account | 3/6 | 6/6 controls | -0.000240596 | -0.001164479 | 0.003168633 | 1/3 accounts |
| E_D, mean of two controls/account | 3/6 | 6/6 controls | -0.000240596 | -0.001164479 | 0.003168633 | 1/3 accounts |

The different populations make marginal means unsuitable for declaring a winner. Direct A–D comparison yields **12 compatible pairs, all with exactly zero fidelity difference**, and three incompatible pairs. The latter are A–B, B–C and B–D on `01292_8002BAB10`: counts match but monetary amounts do not satisfy the direct-method caliper. They are excluded rather than used to claim counterparty superiority. A and C/D choose identical evidence on the only A-available account. C/D are identical on all four available accounts. B equals C/D on their other three common accounts.

| Anchor | Strictly matched accounts | Mean paired F minus control mean | Median paired difference | Positive paired difference |
|---|---:|---:|---:|---:|
| A | 1 | 0.023011957 | 0.023011957 | 1/1 |
| B | 3 | -0.002379535 | 0.000537423 | 2/3 |
| C | 3 | 0.008291243 | 0.001324349 | 3/3 |
| D | 3 | 0.008291243 | 0.001324349 | 3/3 |

These are actual paired control differences, not confidence intervals or improvements in detection. A positive difference can occur when both explanations have **negative** fidelity: for example, temporal removal on `01467_8008C3BE0` has F=-0.000627056 versus mean random F=-0.001164479. It raises the anomaly score less than its controls do; it does not reduce that score. The positive A effect on one account is reproduced by the simple heuristics and is not evidence of a general CREST advantage.

## 7. Sparsity and size–response tradeoff

| Account | Methods sharing evidence | Count | Count/history | Amount/history | Signed F |
|---|---|---:|---:|---:|---:|
| 01467_8008C3BE0 | B,C,D | 2 | 14.2857% | 14.2857% | -0.000627056 |
| 001241_800F239A0 | B,C,D | 2 | 12.5% | 2.5423% | -0.001844284 |
| 01292_8002BAB10 | A,C,D | 2 | 2.3256% | 0.2205% | 0.026623280 |
| 01292_8002BAB10 | B | 2 | 2.3256% | 0.0921% | -0.005389051 |
| 01588_8008F5240 | B,C,D | 1 | 33.3333% | 22.7235% | -0.101222992 |

The largest absolute response is a **negative** response to deleting one third of a three-event history. Two-event removals can produce either sign. This does not support a monotonic size–fidelity relation or justify choosing a more destructive budget. The complete outputs contain exact monetary volumes, historical totals, transaction IDs, group keys, counterparties and block counts; monetary units are the supplied normalized dataset amounts, not an independently verified cross-currency valuation.

## 8. Replay and perturbation results

Fixed selection/matching replay was exact for all six accounts. Every original score and every stored intervened score was independently recomputed from its stored feature vector with the frozen model and matched exactly. Three full-reference/uncached comparisons had maximum feature and score error **0**; one was the no-explanation middle account's baseline. This is a partial uncached graph replay, not a second full end-to-end timing run.

| Diagnostic | Evaluated support | Result |
|---|---|---|
| Equivalent reversed rows: baseline | 3 fixed representatives | Features and scores unchanged exactly |
| Equivalent reversed rows: A–D available explanations | 7 account/method observations on 2 representatives | All selection Jaccards=1 and fidelity changes=0 |
| Equivalent reversed rows: random control selection | Same 7 matched anchors | Union Jaccards 0 to 0.4; identities changed |
| One hash-selected amount increased 1% | 3 representatives | Baseline features change; all 3 baseline scores unchanged |
| 1% change: available A–D explanations | 7 observations | Six Jaccards=1 and fidelity changes=0; C on low-score representative has Jaccard=0 and fidelity change=-0.006321156 |
| First two eligible temporal groups | 4 accounts | Jaccard=0 in each; distinct disjoint time blocks, not replay failures |
| First two eligible counterparty groups | 0 accounts | Insufficient multiple candidates; no stability statistic |

For `01467_8008C3BE0`, the small amount change breaks an amount-group tie; C selects another block and F changes from -0.000627056 to -0.006948212. B and D retain their evidence and response. This is a discontinuity in an argmax selector, not a changed model fit. The middle representative remains unavailable under both variants and contributes no successful explanation-stability observation.

The unchanged E4 outputs despite feature changes reflect this frozen forest's piecewise response, not proof that the perturbations are irrelevant in general. Random control selection depends on the history hash, so equivalent row ordering fails control-identity invariance even though structured results were unchanged in this small sample. Variant random controls were rematched and their evidence Jaccards checked; **their new frozen-model fidelities were not recomputed**. Thus stability of matched excess under perturbation remains unestablished. General sampled-centrality order dependence remains a risk even though it did not change these observed focal outputs.

## 9. Runtime, memory and computational feasibility

Feasibility was checked before completing the planned comparisons: focal extraction plus full-reference comparison and uncached replay took **15.386 s**. The conservative allowance was **512.2 s** for the remaining scenario plan, below the budget. The completed worker took **197.009 s**; process wall time including imports/startup was **224.679 s**, exit **0**. The failed first attempt is preserved separately; its file creation-to-failure interval was approximately 115 s. Combined attempts were comfortably below 1,800 s, even allowing for startup. No 250-account run was started.

| Stage | Measured time / resource |
|---|---:|
| History loading and indexing | 2.356 s |
| Selection plus strict matching, all six | 4.809 s |
| Eight fresh focal recomputations | 39.714 s |
| Graph/global centrality within those recomputations | 39.26 s |
| Frame filtering within those recomputations | 0.06 s |
| Focal local features within those recomputations | 0.38 s |
| Batch scoring with singleton verification | 0.174 s |
| Explanation aggregation | 0.083 s |
| Three additional full-reference + uncached checks | 39.421 s |
| Peak resident working set | 304,275,456 bytes (290.18 MiB) |
| Peak pagefile/commit allocation | 1,332,994,048 bytes (not resident memory) |

Stage times are not an exhaustive partition of the process wall time: hashing, imports, history variants, repeated selection, scoring checks and output writes add overhead. Reference and focal costs were timed jointly in the correctness checks, so no isolated reference-versus-focal speedup ratio is claimed. The three comparisons establish numerical equivalence; historical Phase 5G profiling supplies prior performance context.

The 13 unique original-history scenarios reuse five authenticated vectors and compute eight fresh vectors. Reuse is keyed by focal account and omission IDs only after verifying the shared dataset/history/model/cutoff/schema/code context. Batch inference does not eliminate graph recomputation. Average fresh scenario time is **4.964 s**; graph/centrality work dominates. The warm per-account candidate-plus-fresh-feature times below exclude shared startup, indexing, inference, correctness checks and stability experiments; they are not cold service latency.

| Account | Unique scenarios including controls | Measured incremental seconds |
|---|---:|---:|
| 01467_8008C3BE0 | 3 | 9.463 |
| 011296_800808EB0 | 0 | 0.032 |
| 012381_8015FC7C0 | 0 | 0.033 |
| 001241_800F239A0 | 3 | 10.001 |
| 01292_8002BAB10 | 6 | 24.961 |
| 01588_8008F5240 | 1, reused | 0.032 |

Each explanation links to a scenario in `scored_vectors.json`; its measured fresh recomputation metadata is there and in `timings.json`. Reused vectors identify their historical origin rather than reporting a fabricated current recomputation time. Shared scoring is timed as a batch, not assigned fictional individual stopwatch measurements.

| Method runtime comparison | Current feature work |
|---|---|
| A | Its one available vector reused from verified Phase 5H |
| B | Its four available vectors reused from verified Phase 5H |
| C | Its four available vectors reused, overlapping A/B |
| D | Its four available vectors reused, identical to C |
| E | Twenty control observations reduce to eight fresh unique vectors, 39.714 s total |

Thus the measured fresh cost is specifically the new random-control workload. Using its mean as a cold cost for all 13 scenarios is an explicit projection assumption, not measured per-method latency or proof of a speed advantage for structured explanations. Fresh output generation and the reference/stability checks still incur costs despite reuse.

Cold projection `4.9643036625 * 13/6` is **10.756 s/account**; for 250 accounts it is **2,688.998 s**, already above 1,800 s. This scenario assumes the same 5K graph and eligible mix; it excludes fresh baseline construction, startup and reference checks and is not a bound or measured large-cohort runtime. Six-account diagnostic use is feasible; meaningful broad coverage and interactive latency are not established. The 50K guard and global-centrality policy are unchanged.

## 10. Failures, regressions and preservation

The initial focused suite reported **13 passed, 2 failed**, exit 1, in 6.53 s. Both were new test-fixture errors: the expected maximal right-closed block sum was 27, not 29, and simulation-hour loading requires `step`, not `timestamp`. The corrected focused run reported **15 passed**, exit 0, in 4.27 s. After adding explicit label-independence, paired-population and missing-reference coverage, the focused run reported **18 passed**, exit 0, in 2.97 s.

The first pilot (`phase6a-explanations-v1-pilot-v1`) exited 1 with `StopIteration` because the runner assumed every reference account had an eligible omission. This was a **new runner defect**, not an environmental failure or scientific negative. The fix checks the unchanged baseline for that account. A regression explicitly tests it. The failed directory is retained with `incomplete.json` and no completion manifest. Its eight unsaved feature recomputations had to be repeated; the corrected runner now saves each fresh scenario immediately. The cohort and method rules did not change to avoid missing explanations.

The final relevant backend suite reported **174 passed, 0 failed, 0 skipped, 0 blocked**, exit **0**, in **62.99 s**. It includes the 156 existing Phase 2–5H regressions and all 18 Phase 6A cases. Evidence: workspace `work/phase6a-tests/phase2-sf7r0a9b/pytest.log`, `results.xml`, `command.txt`, and `work/phase6a-state/final-tests.exit`. Earlier focused logs are in `phase2-y3ka2zj3` (13 pass/2 fail), `phase2-by6yob7a` (15 pass), and `phase2-ym1uh0eq` (18 pass), under the same test root. These are separate runs; their counts are not added to claim more distinct tests.

Tests cover signed/finite fidelity, whole-group selection, exact Decimal/count budget matching, denominator-aware sparsity, fixed selection/replay, equivalent ordering, cutoff exclusion, unavailable explanations, changed-label independence, no-fit frozen scoring, append-only writes, historical protection, timestamp block semantics and the missing-reference regression. The actual artifact verifier separately checks model preservation and exact rescoring on the real pilot artifacts.

Tests run only through `backend/scripts/verify_phase2.py` in a disposable checkout with per-test temporary persistence, never against production data. This phase does not claim to have rerun the full application/API suite or resolved its previously documented Windows asyncio limitations. Those broader API tests are **not run**, not counted as passed or as blocked in this selected suite. No environmental blocker occurred in the selected regressions.

Independent artifact verification exited 0. It replayed selections and matching, rescored original/intervened/variant vectors with the frozen model, recalculated sparsity and paired differences, checked manifest digests and confirmed **577/577 pre-phase snapshot files unchanged** and **87/87 protected files byte-identical to both the protected manifest and supplied ZIP**. This preserves existing datasets, E0–E5, CREST v1/v2, prior reports/results, Phase 5 protocol and frontend. Historical snapshot SHA256: `4783478662173d00e2fb5820a6cd6ac873ed5ccd0616f2fb1b496ea1d26c5e8d`.

## 11. Final scientific decision and acceptance

**REVISE — retain CREST as an auditable evidence-sensitivity diagnostic, not a validated superior explanation method or ranking extension.** No further formula or experiment is started by this decision.

| Decision gate | Evidence-based answer |
|---|---|
| A. Valid under defined constraints? | **Yes for available outputs**: 13/13 A–D records and 20/20 control records pass; only 4/6 accounts have any whole-group explanation and A covers 1/6. Validity does not imply positive fidelity. |
| B. Greater fidelity than comparable simple methods? | **Not demonstrated**: all 12 budget-compatible direct pairs tie. A's one positive response is duplicated by C/D. Temporal fidelity is negative for all four available accounts. |
| C. Reproducible and reasonably stable? | **Partially**: fixed replay and three reference checks pass exactly; structured row-order results are stable on tested support. Random identities change under equivalent ordering; C changes evidence after a 1% perturbation. General robustness and matched-excess stability remain unproven. |
| D. Practical at meaningful coverage? | **Only for small offline diagnostics so far**: 224.7 s process wall for the six-account validation; projected cold 250-account work is 2,689 s before excluded overhead, with limited coverage. |
| E. Sufficient for an IEEE contribution? | **Insufficient as a superior algorithm/detector claim**. A carefully scoped reproducibility/negative-results or engineering case study is possible, but novelty, reviewer-facing utility and broader validation are not yet demonstrated. Acceptance or publication is not implied. |

Recommended research direction, if separately authorized: preserve the transaction-to-feature-to-score audit trail and negative findings; define a useful explanation target with domain input; investigate versioned control-selection order invariance and computational cost; predefine an adequately supported explanation evaluation. Do not reopen the stopped ranking extension or claim an IEEE-ready result from this pilot.

**Phase acceptance:** the bounded Phase 6A implementation, prescribed comparisons, diagnostics, literature review, regression testing, preservation checks and reporting are complete. The scientific success gates are **not all satisfied**: B, general C, broad D and manuscript-readiness E remain unsupported. Completeness of this phase is not acceptance of the explanation-quality hypothesis. No next phase is started. `git diff --check` passes; final artifact and test hashes are in `phase6a-verification-v1/final_review.json`.

Limitations include six selected accounts on one dataset/split/model, only two representatives with available explanations in the stability subset, repeated identical evidence across methods, one perturbation per representative, no expert utility study or explanation ground truth, no inferential statistics, no feature-attribution baseline implemented for comparison, supplied financial semantics/currency limitations, transductive graph features, sampled centrality and unresolved PaySim provenance. The existing Phase 5 detector-performance benchmark remains incomplete.

## 12. Deliverables and reproduction

New source only:

- `backend/app/research/explanation_validation/__init__.py`
- `backend/app/research/explanation_validation/diagnostics.py`
- `backend/scripts/run_phase6a_explanations.py`
- `backend/scripts/verify_phase6a_explanations.py`
- `backend/tests/test_phase6a_explanations.py`
- `docs/research/configs/phase6a_explanations_v1.json`
- this report.

New output namespaces: the preserved failed `phase6a-explanations-v1-pilot-v1`, completed `phase6a-explanations-v1-pilot-v2`, and `phase6a-verification-v1`, all under `data/results/v2/`. Work logs, snapshot and disposable test reports are under workspace `work/phase6a-state/` and `work/phase6a-tests/`. No pre-existing source file was modified in this phase. The 16 tracked modifications shown by Git predate Phase 6A and are retained. No commit was made.

From repository root, reproduce only when separately authorized and with a **new** run ID:

```text
python backend/scripts/run_phase6a_explanations.py phase6a-explanations-v1-new-replay
python backend/scripts/verify_phase2.py ../../work/phase6a-tests -- backend/tests/test_phase6a_explanations.py -q
python backend/scripts/verify_phase6a_explanations.py data/results/v2/phase6a-explanations-v1-pilot-v2 ../../work/phase6a-state/before.json C:/Users/hariharasuthan/Downloads/GraphFin-main.zip data/results/v2/phase6a-verification-new
```

The runner creates output directories exclusively and saves the completion manifest last. Reusing a run ID fails rather than overwriting. The current run is complete and does not need repeating. The manifest covers experiment artifacts and code as executed; later test/documentation records are recorded separately. Stop after Phase 6A.
