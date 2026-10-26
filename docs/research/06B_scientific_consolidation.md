# Phase 6B — Scientific consolidation and readiness

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Date: 2026-10-23. Decision: **neither applied-conference submission-ready nor methodology-conference ready at present**. An applied empirical/system paper is a plausible next objective after the bounded validation and provenance work below. Phase 6B consolidation is complete; completion does not establish the rejected scientific hypotheses. No new model fit, graph experiment, scoring variant, frontend edit or commit was performed.

## 1. Audit scope and evidence hierarchy

The research record comprises `01_baseline_audit.md`, `02_reproducibility_and_correctness.md`, `03_evidence_intervention_engine.md`, `04_crest_scoring_algorithm.md`, `05_benchmark_protocol.md`, `05_benchmark_and_ablation_results.md`, `05R_scalability_recovery.md`, `05G_algorithm_feasibility_gate.md`, `05H_evidence_specificity_revision.md`, and `06A_explanation_validation.md`. Earlier prospective recommendations are historical decisions, not authorization to restart those experiments. Phase 5H's **STOP RANKING EXTENSION** and Phase 6A's **REVISE** remain in force.

Authority order: versioned configuration and implementation; complete artifact manifests and raw score/membership arrays; executed verification/test reports; narrative summaries. Incomplete directories without a completion manifest cannot support completed-performance claims. Filesystem chronology supports a fixed documented Phase 5 protocol, not independently authenticated preregistration.

Current new evidence: `data/results/v2/phase6b-consolidation-v1/` contains recomputed per-seed metrics, summary, tables, input-verification report and an exclusive output manifest. Workspace script `../../work/phase6b-state/consolidate.py` is recorded by SHA256 in that manifest. It verifies existing artifacts and calculates metrics from saved scores; it does not refit models or repeat interventions. Release this script and the workspace logs with the research package.

### Corrections to historical prose (historical files preserved)

1. Phase 5's sentence attributing AP changes to lexical tie-breaking is inaccurate for its sklearn metric implementation. **Coarsening distinct scores into ties changes threshold-grouped AP; lexical order does not.** Lexical tie-breaking affects top-K membership and ordinal ranks. See section 3.
2. Phase 5G already corrects Phase 5R's broad “unchanged rankings” interpretation: hybrid order was unchanged in the bounded probe, but sensitivity and robustness each displaced two accounts. This is not evidence of better detection.
3. The original Phase 5 exploratory cohort contains **one positive among 250**, not the six positives in the full 1,500-account held-out population. Phase 6A's six accounts are a separate score-stratified, eligible diagnostic cohort.
4. The protocol's intended full E6 comparisons, ablations and controls remain incomplete. E6_BASE is calibration of E4 without interventions, not a completed CREST detector evaluation.

## 2. Architecture, algorithms and experiment identities

Production flow remains Python/FastAPI ingestion → transaction normalization → NetworkX directed graph → canonical account features → sklearn Isolation Forest or E0 → saved model/split/evaluation → existing React/TypeScript/Vite/Tailwind/D3/Recharts views. Research entry points are separate: `backend/app/research/benchmark/runner.py`, `backend/app/services/research_protocol.py`, and versioned scripts/configurations. Phase 6B changes none of those components.

Canonical nineteen columns are graph-six (in/out/total degree, weighted in/out degree, betweenness); behavior-eight (count, total sent/received, net flow, average/maximum amount, unique receivers/senders); temporal-five (transactions/day, transactions/week, average/minimum/maximum inter-event gap). `backend/app/services/feature_service.py` and Phase 1 give exact definitions. The frozen Phase 5 matrix contains these nineteen plus four E5 columns: egonet node count, edge count, density and circular-flow indicator. Feature order and matrix/ordered-ID hashes are preserved in both feature manifests and the new verification report.

| Method | Frozen Phase 5 definition/version | Scope |
|---|---|---|
| E0 | `e0-source-signed-zero-v2` | Maximum signed training-standardized graph-six feature; population SD (`ddof=0`), zero contribution if SD ≤ 1e-9; source statistics float64 |
| E1 | `isolation-forest-raw-v2` | Graph-six |
| E2 | Same IF version | Graph + behavior, fourteen |
| E3 | Same IF version | Graph + temporal, eleven |
| E4 | Same IF version | All nineteen |
| E5 | Same IF version | GraphFin's four-feature egonet/circular heuristic; not the complete published Graphomaly method |
| E6_BASE | Frozen E4 plus source empirical mid-CDF (`empirical-mid-cdf-frozen-e4-v1` descriptive identity in consolidation) | No intervention information; historical Phase 5 calibration retained |

The E6_BASE descriptive identity in the new table is not a renamed historical algorithm. The authoritative implementation/configuration remain the original Phase 5 manifest, calibration artifact and source hashes. Later affine calibration from Phase 5G must not be silently substituted into this table.

Every baseline split uses model seed 42, 100 trees, `max_samples=auto`, contamination .005, `n_jobs=1`, raw float32 features and no standard scaler. Larger IF scores mean more anomalous: `-decision_function`. Model offset cancels for within-model score differences. Separate split seeds are **42, 123, 7, 2024, 99, 555**; centrality seed is 42; paired-bootstrap seed is 2718. Changing split seed is not changing model seed or independently sampling another dataset.

`backend/app/services/research_identity.py` records distinct E0 historical contracts; `baseline_service.py` and `research_runner.py` retain compatibility paths. Historical absolute/scaled or epsilon-based baselines and rounded risk-score evaluations must not be pooled with the signed-zero raw Phase 5 version. Phase 2's explicit split lookup fails closed, evaluation checks training membership and held-out coverage, and manifests name labels/configuration. These protections do not convert full-observation graph features into prospective features.

Training and calibration use source-training features only. Labels are used for declared stratified splitting and evaluation, not unsupervised fitting or target-label tuning. Features were computed on the entire supplied graph, including held-out accounts and edges: **transductive entity holdout**, not unseen-network or future-transaction prediction. The original 250-account cohort additionally used labels for stratification; later six-account pilots used frozen score/eligibility/hash selection.

## 3. Metric definitions and uncertainty

Reported “PR-AUC” is sklearn **non-interpolated average precision**, not trapezoidal integration:

\[
AP=\sum_j (R_j-R_{j-1})P_j,
\qquad \bar A=\frac1{6}\sum_{i=1}^6 A_i,
\qquad SD=\sqrt{\frac{\sum_i(A_i-\bar A)^2}{5}}.
\]

Each j is a distinct score threshold, including all tied observations together. For labels [1,0], scores [1,0] yield AP=1; scores [.5,.5] yield AP=.5 regardless of account ordering. A strictly increasing map preserves threshold groups; the empirical source percentile is only nondecreasing and can merge groups. Thus E6_BASE can change AP without adding evidence. The Phase 6B verifier executed the equal-score order-invariance check and recomputed all stored metrics using `backend/app/research/benchmark/metrics.py`.

P@K is positive hits divided by effective K after score-descending/account-ID tie ordering. The per-seed JSON retains hits, precision, recall and effective K. All these populations exceed K=100. Sample SD measures **observed split dispersion**, not a confidence interval, independent-replication error bar or model-seed robustness estimate.

Existing `phase5-results-review-v3/paired_e6base_vs_e4.csv` contains 1,000 class-stratified paired bootstrap draws per split (seed 2718; twelve comparisons, each 1,000 valid/zero rejected). These intervals condition on the observed positive accounts, fixed fitted models and class counts. Graph accounts are dependent; splits overlap; the bootstrap does not refit or measure unseen-positive uncertainty. No new interval or significance claim is manufactured. Phase 2's ordinary bootstrap also explicitly counts undefined resamples; all-positive AP is defined, no-positive AP is unavailable, and one-class ROC-AUC is unavailable.

## 4. Populations, provenance and primary result interpretation

| Population | Active accounts | Retained events | Full positives | Train/test | Test positives | Test prevalence |
|---|---:|---:|---:|---|---:|---:|
| Supplied IBM 5K | 5,000 | 31,463 | 20 | 3,500 / 1,500 | 6 | .004000 |
| Supplied IBM ~50K | 49,992 | 353,850 | 249 | 34,994 / 14,998 | 75 | .005000667 |

The 50K input has 353,860 rows; nonpositive filtering leaves 353,850 and eight label-only inactive accounts. Full prevalence is .004 and approximately .004980797, respectively. Declared labels are endpoint OR involvement in retained laundering transactions, **not independently verified account culpability**. Source raw flags/conversion evidence are absent; supplied IBM label identities remain declared/unverified despite stable hashes. Source files, exact byte hashes and label identities are in `configs/phase5_protocol_v1.json` and `phase6b-consolidation-v1/verification.json`.

The original IBM dataset publication describes a simulator, not real bank ground truth ([IBM primary record](https://research.ibm.com/publications/realistic-synthetic-financial-transactions-for-anti-money-laundering-models)). It cannot authenticate GraphFin's particular conversion. PaySim remains excluded: **774 versus 2,606 positives, 1,832 disagreements on the same 547,686-account label population**; the smaller positive set is a subset of the larger. The 10K-row transaction prefix has 18,711 accounts and 12 versus 129 positives under those label files. These are neither interchangeable labels nor a conflict solved by prefix size. Authoritative generation evidence is still absent. No file was preferred, relabeled or rewritten.

The complete numerical tables appended below come from 84 verified saved-score evaluations (2 tiers × 6 splits × 7 methods), not new experiments. E3 has the largest displayed mean AP on 5K and E1 on 50K, but the small differences and split dispersion do not establish winners. Enrichment is nonmonotone. E5 has lower mean AP yet higher mean P@100 on 50K than E4, showing metric-dependent tradeoffs rather than a generally inferior/superior model. Network size, composition, history and prevalence vary together: no causal size effect is isolated.

### Historical single runs — separate archival comparison

Source: `data/results/final_e0_e4_comparison.csv`. Values as archived, not recomputed in Phase 6B:

| Tier | E0 | E1 | E2 | E3 | E4 |
|---|---:|---:|---:|---:|---:|
| 5K | .1891 | .0597 | .1854 | .1955 | .1969 |
| 50K | .0122 | .0159 | .0170 | .0116 | .0136 |

Historical `final_multiseed_robustness.json`/CSV and cross-dataset JSON remain separate too. Split selection, baseline/scoring versions, rounding and historical contamination/configuration differ. With six positive held-out accounts, changing which positives appear can radically change AP; Phase 5 5K E4 spans .006104–.194545. Therefore the paper's single-run E4 lead is neither contradicted nor generalized by a different multi-seed mean. Missing historical processed inputs prevent exact reconstruction of every legacy result. Historical `is_paper_reportable` flags do not override these audit findings.

## 5. CREST disposition

Retain an **optional offline evidence-sensitivity implementation**, with a concise negative-results subsection if space permits. It is not the primary methodological contribution. Available whole counterparty and temporal groups remove at most two incident events, at most half the incident count and amount, retaining at least one event. Amount/count heuristics use the same eligible groups; random controls match count and monetary calipers. No artificial transaction is introduced as explanation evidence.

For frozen model f and historical feature map phi, signed fidelity is

\[
F(v,O)=-f.decision\_function(\phi(H,v))
       +f.decision\_function(\phi(H\setminus O,v)).
\]

Positive F means omission lowers anomaly score; negative F means it raises it. This is model response, not causal financial relevance. Missing valid evidence is explicitly unavailable; unchanged-base ranking fallback in historical CREST is not a zero-fidelity explanation. Insufficient matching controls is missing excess, not zero excess.

Phase 6A has thirteen valid A–D records but only five distinct account/omission scenarios; four of six selected accounts have any explanation. Counterparty covers one, temporal/amount/count each four. All twelve budget-compatible direct comparisons tie; three incompatible comparisons are excluded. Counterparty's one positive F=.026623280 is reproduced by simple heuristics. Temporal F is negative on all four accounts (mean −.027270846). These observations do not establish fidelity superiority.

Fixed selection/matching and saved-vector score replay are exact. Three full-reference comparisons have zero error. Structured row reversal is invariant for seven available observations on two representatives; random-control identities change (Jaccard 0–.4). A 1% amount perturbation changes one amount-selector evidence set (Jaccard 0, F change −.006321156). Perturbed-control fidelity was not rescored, so matched-excess stability is unestablished. Small tested support cannot support broad robustness.

Phase 6A measured 197.009 s worker / 224.679 s process wall; eight fresh unique random-control vectors took 39.714 s, with 39.260 s in betweenness. Structured vectors were reused. The cold projection for 250 accounts is 2,688.998 s before excluded startup/reference overhead, exceeding 1,800 s; it is not a measured full run. Phase 5H's pilot/replay took 128.7/119.1 s and displaced ten positions in the 1,500-account array without changing six-pilot relative ordering. Rank movement is not detection improvement. Original intervention E6 remains incomplete and absent from the detection tables.

## 6. Limitations and contribution classes

**A — Established:** graph summaries, IF, egonets, temporal aggregates, removal-based response and matched comparisons. Literature overlap is substantial; see L1–L10 in the related-work report.

**B — Engineering:** explicit model/split identities, source-only fit checks, versioned E0 and label contracts, append-only manifests/scores, isolated tests, constrained transaction-to-feature-to-score traceability and explicit missing evidence. Useful integration, not proof of algorithmic novelty.

**C — Empirical:** split-sensitive AP and nonmonotone enrichment on supplied IBM subsets; empirical-CDF ties can alter AP; limited explanation availability and tied direct fidelity; global-centrality cost dominates bounded diagnostic work. These are the strongest supported findings.

**D — Speculative:** superior CREST rankings/explanations, general robustness, causal financial explanations, cross-domain accuracy and scalable broad coverage. None is established.

Feature columns are not nineteen independent signals: in/out degree duplicate unique senders/receivers; weighted in/out duplicate received/sent; total degree is in+out; net flow is received−sent; weekly rate is seven times daily; average amount derives from volume/count. Float32 arithmetic can make identities near-exact. Repeated signals can change IF feature-selection frequency; no new deduplication ablation was run.

Sampled betweenness retains the reference's node-order/seed semantics (exact for ≤2,000 nodes, k=500 through 50,000, k=100 above). Unweighted Brandes is O(VE) exact and approximately O(kE) sampled, aside from traversal overhead; repeated global computation across m omissions gives approximately O(mkE), plus graph construction, candidate selection and feature work. This is an algorithmic cost description, not a measured scaling law. Focal/reference equivalence does not mean exact betweenness or isolation from sampling artifacts. Synthetic data, endpoint labels, unknown currency normalization, tiny positive counts, graph dependence, overlapping splits and missing historical inputs further limit interpretation.

## 7. Reproducibility and tests executed in Phase 6B

- Input dataset/label bytes, frozen protocol, feature/baseline manifests and referenced source hashes checked. Saved memberships partition each population, train/test are disjoint, calibration uses intended train IDs, and all seven arrays cover each held-out population.
- **84/84** saved metric rows reconstructed exactly; aggregate means/sample SD match the earlier review to 1e-15. No original metric file rewritten.
- Existing independent 5K replay: all six score arrays plus results/summary are byte-identical. No new model replay launched. A separate complete 50K baseline replay is not available; metric/artifact reconstruction is not equivalent to refitting replay.
- **77 passed, 0 failed, 0 skipped, 0 errors, 0 blocked**, pytest **17.94 s**, exit **0**. Selected suites: `test_phase2_correctness.py`, `test_phase5_benchmark.py`, `test_phase6a_explanations.py`. Disposable wrapper: `python backend/scripts/verify_phase2.py ../../work/phase6b-tests -- backend/tests/test_phase2_correctness.py backend/tests/test_phase5_benchmark.py backend/tests/test_phase6a_explanations.py -q`.
- Logs: `../../work/phase6b-tests/phase2-9n5s3295/pytest.log`, `results.xml`, `command.txt`; exit record `../../work/phase6b-state/tests.exit`. Previous Phase 6A 174-test results are historical evidence, not added to this count. Full application/API suite was not rerun; its historical Windows asyncio limitation is not a blocked test in this selected run.
- Preservation: **87/87** protected files match manifest and supplied ZIP; **612/612** pre-phase files under backend/data/docs/frontend match the pre-phase snapshot. `git diff --check` exit **0**. Final verification and document/test digests are recorded separately in `data/results/v2/phase6b-verification-v1/final_review.json`.

Git still contains sixteen tracked modifications inherited from Phase 2 and previous untracked research work. Phase 6B adds four reports and derived consolidation/verification artifacts, plus workspace verification scripts/logs. No pre-existing source, dataset, research artifact, report or frontend file is modified. Derived result directories are Git-ignored by existing policy; do not assume a source commit automatically publishes the research package.

## 8. Readiness gate and acceptance

| Gate | Answer and evidence |
|---|---|
| A. Reproducible? | **Scoped yes.** Saved results reconstruct; 5K independent replay exact; source/config/seed identities explicit. Not complete historical reconstruction, independent 50K replay or full CREST benchmarking. |
| B. Comparable detection experiments? | **Yes within each Phase 5 tier/split for E0–E5/E6_BASE.** Same held-out IDs and labels, declared feature/version differences. Cross-tier causal, legacy-version pooling and incomplete E6 comparisons are not valid. |
| C. Sufficient provenance? | **For byte-defined supplied-file reproducibility, yes; for independent label truth or deployment claims, no.** IBM conversion lineage missing; PaySim unresolved and excluded. |
| D. CREST superiority? | **No.** Full ranking benchmark incomplete; Phase 5H stopped ranking; Phase 6A twelve comparable fidelity ties. |
| E. Strongest contribution? | Auditable empirical comparison and transparent negative findings in an integrated transaction-graph system; not a new superior detector. |
| F. Minimum validation? | Recover/document raw-to-subset/label lineage or explicitly constrain the paper to supplied unverified labels; independent 50K replay; bounded model-seed sensitivity on cached features; one frozen independently derived dataset/time cohort for any generalization claim. Detailed conditional priorities in the manuscript plan. |
| G. IEEE/methodology readiness? | **Neither submission-ready now.** Applied/empirical or system-demo direction is plausible after validation and reviewer-facing utility/novelty framing. Methodology-oriented superiority is unsupported. No acceptance probability implied. |

| Phase 6B requirement | Completion |
|---|---|
| Preserve/audit research record, identities and restrictions | Complete; scoped limitations explicit |
| Claims matrix | Complete: `06B_claims_matrix.md` |
| Authentic literature and novelty assessment | Complete: `06B_related_work_comparison.md`; DOI/access limitations explicit |
| Consolidate six-seed results, uncertainty and historical separation | Complete; tables below and machine-readable artifacts |
| CREST disposition and limitations | Complete; diagnostic only, no superiority |
| Ten-section manuscript/contribution plan | Complete: `06B_manuscript_revision_plan.md` |
| Tests, integrity and whitespace verification | Complete with execution records above |
| Readiness A–G and phase boundary | Complete; readiness is negative/conditional |

Recommended Phase 6C: separately authorized bounded provenance/replay/validation and release packaging. Recommended Phase 7: manuscript and system presentation only after that gate; preserve negative conclusions. Neither phase was started. No commit made.

## 9. Verified per-seed AP and mean retrieval tables

Generated from the append-only consolidation; displayed decimals rounded to six places. JSON retains full precision. SD is sample SD across split outcomes, and all P@K entries are means over the same six splits.
### 5k per-seed AP

| Method | 42 | 123 | 7 | 2024 | 99 | 555 | Mean | Sample SD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E0 | 0.190758 | 0.179754 | 0.175903 | 0.014686 | 0.006658 | 0.012789 | 0.096758 | 0.093694 |
| E1 | 0.057130 | 0.054309 | 0.092981 | 0.008032 | 0.005574 | 0.009934 | 0.037993 | 0.035755 |
| E2 | 0.184212 | 0.176109 | 0.094470 | 0.007523 | 0.005467 | 0.009083 | 0.079477 | 0.085020 |
| E3 | 0.194830 | 0.181048 | 0.179710 | 0.007888 | 0.008408 | 0.010429 | 0.097052 | 0.096705 |
| E4 | 0.194545 | 0.177102 | 0.180686 | 0.006784 | 0.006104 | 0.010239 | 0.095910 | 0.096805 |
| E5 | 0.017521 | 0.009286 | 0.012105 | 0.004000 | 0.004000 | 0.004000 | 0.008485 | 0.005581 |
| E6_BASE | 0.194544 | 0.177075 | 0.097282 | 0.006779 | 0.006070 | 0.010201 | 0.081992 | 0.087770 |

| Method | Mean P@10 | Mean P@25 | Mean P@50 | Mean P@100 |
|---|---:|---:|---:|---:|
| E0 | 0.050000 | 0.026667 | 0.020000 | 0.013333 |
| E1 | 0.050000 | 0.020000 | 0.013333 | 0.011667 |
| E2 | 0.050000 | 0.020000 | 0.013333 | 0.006667 |
| E3 | 0.050000 | 0.026667 | 0.016667 | 0.013333 |
| E4 | 0.050000 | 0.026667 | 0.013333 | 0.011667 |
| E5 | 0.016667 | 0.013333 | 0.013333 | 0.010000 |
| E6_BASE | 0.050000 | 0.026667 | 0.013333 | 0.011667 |

### 50k per-seed AP

| Method | 42 | 123 | 7 | 2024 | 99 | 555 | Mean | Sample SD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E0 | 0.011613 | 0.009969 | 0.038768 | 0.019384 | 0.011472 | 0.039761 | 0.021828 | 0.013905 |
| E1 | 0.022242 | 0.013135 | 0.027132 | 0.031863 | 0.010852 | 0.040036 | 0.024210 | 0.011158 |
| E2 | 0.017253 | 0.010568 | 0.035245 | 0.028313 | 0.009605 | 0.036962 | 0.022991 | 0.012166 |
| E3 | 0.012099 | 0.011624 | 0.036700 | 0.028948 | 0.008499 | 0.036929 | 0.022466 | 0.013220 |
| E4 | 0.014894 | 0.012826 | 0.035697 | 0.030384 | 0.009100 | 0.038065 | 0.023494 | 0.012678 |
| E5 | 0.009942 | 0.027769 | 0.027027 | 0.007777 | 0.027428 | 0.007230 | 0.017862 | 0.010499 |
| E6_BASE | 0.014888 | 0.012822 | 0.035705 | 0.030371 | 0.009104 | 0.022062 | 0.020825 | 0.010495 |

| Method | Mean P@10 | Mean P@25 | Mean P@50 | Mean P@100 |
|---|---:|---:|---:|---:|
| E0 | 0.083333 | 0.040000 | 0.043333 | 0.025000 |
| E1 | 0.100000 | 0.060000 | 0.043333 | 0.031667 |
| E2 | 0.100000 | 0.040000 | 0.030000 | 0.015000 |
| E3 | 0.083333 | 0.040000 | 0.026667 | 0.025000 |
| E4 | 0.116667 | 0.060000 | 0.030000 | 0.016667 |
| E5 | 0.116667 | 0.080000 | 0.073333 | 0.051667 |
| E6_BASE | 0.116667 | 0.060000 | 0.030000 | 0.016667 |

