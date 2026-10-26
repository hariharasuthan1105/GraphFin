# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

## Phase 4 — CREST anomaly-scoring algorithm

Completed 2026-10-20. E6_CREST (Constrained Robustness and Evidence-Stability Testing) is a **proposed experimental research method**. Its novelty and anomaly-detection improvements have not been established. Sensitivity and robustness are not proof of money laundering.

### Scope and recovered work

The interrupted implementation was preserved and inspected against the Phase 1 audit, Phase 2 protocol and Phase 3 intervention interfaces. The recovered first run actually completed: 35 passed in 4.54 seconds, exit 0 (`work/phase4-tests/phase2-3dsznlub/pytest.log`, relative to the workspace). Two subsequent tests had not yet run. Final verification includes those tests and six additional malformed-artifact cases, for 43 Phase 4 test cases.

This continuation strengthened manifest metadata with explicit cutoff and feature-input hashes; checked dataset-hash formats, cutoff/source/family consistency and recorded population/result counts; and corrected account-level no-history rejection accounting. A no-history sentinel is now a separate unavailability reason, not a candidate rejection attributed to every family.

Established functionality remains GraphFin's graph representation, canonical 19 features, Isolation Forest, E0–E5 and Phase 3 omissions. New engineering is the frozen scorer, calibration, statistics, artifact validation and replay. The proposed research contribution is investigating whether constrained evidence sensitivity adds useful ranking information. Executed tests establish implementation properties, not predictive benefit.

### Hypothesis and architecture

Hypothesis: changes in a fixed detector's scores under permitted historical omissions may provide information beyond its static score. The sign and usefulness of this information require future experiments.

Execution:

1. Validate pinned Phase 3 manifests, their file hashes, canonical feature order, cutoff, membership, budgets and semantic intervention identities.
2. Select explicitly declared source-training rows in sorted account-ID order.
3. Fit one E4 Isolation Forest and one source-training empirical calibration reference.
4. Batch-score held-out baseline vectors and accepted intervention vectors with that same detector and mapping.
5. Calculate intervention profiles, family summaries and budget-stratified concentration.
6. Produce all requested candidate rankings and explanations.
7. Write a new versioned directory, with the manifest written last.

No graph construction, intervention generation, label lookup or metric-based tuning occurs in the E6 runner. The demo prepares a bounded Phase 3 fixture only when matching input artifacts do not already exist.

### Frozen reference detector and isolation

Let \(F(v)\in\mathbb R^{19}\) be the canonical ordered feature vector and \(F_m(v)\) its Phase 3 recomputation after omission \(m\). Both are cast to float32:

\[
s_0(v)=-\operatorname{IF.decision\_function}(F(v)),\qquad
s_m(v)=-\operatorname{IF.decision\_function}(F_m(v)).
\]

Higher raw scores mean more anomalous. Preprocessing is `identity-float32-v1`: there are no fitted scaling statistics. This exactly matches **Phase 2 raw-feature E4** in `backend/app/services/research_protocol.py::fit_and_score` for matching training order, parameters and seed. It does not claim numerical equivalence to legacy rounded risk-score/API representations or overwrite historical E4 scores.

The configuration records tree count, sample policy, contamination and model seed; fitting uses `n_jobs=1`. Only designated source-training rows enter fitting. Calibration uses only that fitted model's source-training scores. The model identity binds source dataset, split, sorted training IDs, pinned source manifest, training matrix and parameters. A mismatched scoring identity raises an error; there is no alternate-model lookup or fallback.

Same-dataset train/evaluation overlap is rejected, including aliases with identical transaction hashes. Different datasets may legitimately reuse account strings. Source features remain transductive graph representations, as documented in Phase 2: account-level held-out fitting does not establish inductive graph isolation. The model is frozen by execution contract, not by making a Python estimator impossible for outside code to mutate.

### Calibration

For source-training scores \(t_1,\ldots,t_N\):

\[
C(s)=\frac{\#\{i:t_i<s\}+\tfrac12\#\{i:t_i=s\}}{N},
\qquad q_0=C(s_0),\quad q_m=C(s_m).
\]

This deterministic empirical mid-CDF is nondecreasing and bounded in [0,1]. Tied references receive their midpoint percentile. Values below the minimum map to 0; above the maximum to 1. A constant reference maps its exact value to 0.5. The sorted reference is read-only and reused for every vector. Identical vectors yield identical raw and calibrated scores. These percentiles are **not calibrated fraud probabilities**.

Calibration may collapse different raw scores into ties and saturates outside the source range. Therefore E6_BASE reproduces the *calibrated* baseline ordering, not necessarily every strict ordering of the raw detector.

### Sensitivity, family balancing and robustness

\[
\Delta_m=q_0-q_m,\quad a_m=|\Delta_m|,\quad
p_m=\max(\Delta_m,0),\quad n_m=\max(-\Delta_m,0).
\]

Positive change means omission reduced the score; negative change means omission increased it. Neither sign establishes fraud or innocence. Zero calibrated change may conceal a raw change.

For eligible interventions \(M_f\) in family \(f\):

\[
D_f=\operatorname{median}_{m\in M_f}\Delta_m,\qquad
D=\frac1{|\mathcal F_D|}\sum_{f\in\mathcal F_D}D_f.
\]

Only nonempty families enter \(\mathcal F_D\). Equal family weights prevent a family dominating merely by generating more candidates; the median limits the effect of extreme individual changes. Signed cancellation remains possible.

\[
R_f=1-\operatorname{median}_{m\in M_f}|\Delta_m|,\qquad
R=\frac1{|\mathcal F_R|}\sum_{f\in\mathcal F_R}R_f.
\]

Since \(|\Delta_m|\le1\), \(R_f,R\in[0,1]\). A family needs at least two valid interventions by default for robustness; this threshold is explicit and configurable upward. It is an engineering support threshold, not a statistical confidence guarantee. D and R may use different family sets; both support counts are saved. No valid omissions yields null robustness, never automatic robustness 1.

Family summaries preserve valid, rejected, excluded-by-stratum and candidate counts, signed/absolute medians, maximum positive/negative influence and reasons for unavailable statistics. Rejected account-level no-history records are reported separately.

### Budget strata and concentration

A stratum combines exact omitted transaction count with bins for omitted count fraction and amount fraction. Default edges are (0, .25, .5, .75, 1); bins are [0,.25], (.25,.5], (.5,.75], (.75,1]. Actual fraction ranges are saved.

Within one family and stratum with at least two valid interventions and \(\sum p_m>0\):

\[
C_{f,b}=\sum_{m\in M_{f,b}}
\left(\frac{p_m}{\sum_{j\in M_{f,b}}p_j}\right)^2.
\]

Fewer than the configured minimum returns null with `insufficient_interventions`; zero total positive influence returns null with `zero_positive_influence`. Two valid candidates with only one positive contribution can legitimately produce 1. There is no cross-family or cross-budget pooled concentration scalar and no concentration ranking penalty.

By default D/R aggregate within each bounded family across its budgets. `ranking_stratum` can restrict these aggregates to one declared stratum; diagnostics still retain all strata. Different omission sizes are not causally equivalent. Bins are coarse, candidates may overlap, and HHI depends on candidate count. These limitations prevent interpreting concentration as a universal comparable evidence-strength measure.

### Candidate scores and fallback

All weights are explicit nonnegative configuration values. They are hypotheses, not established optimal parameters.

| Versioned mode | Score before clipping to [0,1] |
|---|---|
| E6_BASE | \(q_0\) |
| E6_SENSITIVITY | \(q_0+\alpha D\) |
| E6_ROBUSTNESS | \(q_0-\beta q_0(1-R)\) |
| E6_HYBRID | \(q_0+\alpha D-\beta q_0(1-R)\) |
| E6_CONCENTRATION_DIAGNOSTIC | \(q_0\), with concentration diagnostics |

The sensitivity term tests whether score-reducing omissions support the baseline ranking. The robustness term tests a penalty for instability, scaled by baseline anomaly level. Either choice could hurt detection: meaningful anomalies may depend on one relationship, and negative sensitivity may reflect complex graph effects. Clipping introduces further ties.

If a component required by a nonzero weight is unavailable, that mode returns the entire baseline score with explicit fallback reasons. A zero weight does not require that component. Consequently alpha=beta=0 exactly recovers baseline scores and ranking even with missing evidence.

Ranking uses descending final score, then ascending account ID by Unicode code-point lexical order. IDs are sorted before feature collection; label values never enter sorting. Each ranked record includes dataset/model/split identity, raw and calibrated baseline, all statistics, mode, final score, score difference, rank and evidence status.

### Explanations and pseudocode

`intervention_scores.jsonl` retains before/after features and raw/calibrated scores, omitted transaction IDs, budget information and signed/absolute/positive/negative change. `accounts.json` retains family summaries, warnings and the most influential omission by absolute calibrated change, breaking ties by intervention ID. Mode-specific score differences and fallback reasons reside in `rankings.json`. Synthetic demonstration identifiers carry no personal information.

```text
verify source and evaluation Phase 3 bundles against pinned manifests
train = source baselines for sorted predeclared training IDs
fit E4 once on train; fit empirical mid-CDF on its training scores
score sorted held-out baselines and accepted intervention vectors in batches
for each account:
    compute signed intervention changes
    summarize within family and within budget strata
    compute eligible equal-family D and R; retain undefined values
    calculate diagnostic concentration only within comparable strata
    apply each requested mode, recording baseline fallback when necessary
sort each mode by (-score, account_id)
write new artifacts; hash them; write completion manifest last
```

These explanations describe model sensitivity, not causal explanations of money laundering.

### Reproducibility and artifact contract

Uses the existing Phase 2 `graphfin-research-v2` protocol, canonical serialization and hashing, under `data/results/v2/<new-run-id>`. Existing destinations are rejected. Repository destinations outside this versioned tree are rejected; external disposable output roots are supported. No historical output is overwritten. A failed partial directory without a manifest is incomplete and is not silently reused.

Implementation identifier: `e6-crest-frozen-e4-v1`. The manifest stores dataset/history hashes, Phase 3 manifest identities, cutoff metadata, baseline/intervention file hashes, actual evaluation/training matrix hashes, exact canonical features, preprocessing identity, model parameters/seed/hash, explicit membership, graph/intervention seeds, equations, dependency versions, application source hashes, runtime and artifact paths/hashes. Source calibration reference and training scores/features are saved separately. No split or bootstrap RNG is used in this stage: memberships are explicit and no confidence interval is calculated.

Dataset provenance is checked transitively through the pinned Phase 3 manifest and its hashed artifacts. E6 does not reopen the original transaction file or regenerate features; the protected-artifact audit independently checks original bytes. Hash integrity does not prove a maliciously regenerated manifest is scientifically truthful. Input manifests must come from the trusted Phase 3 generation procedure.

Saved outputs: `config.json`, `model.joblib`, `calibration.json`, `intervention_scores.jsonl`, `accounts.json`, `rankings.json`, `report.md`, `manifest.json`. Scientific artifacts exclude inherited runtime values; manifests intentionally contain variable timing. Serialized models should only be loaded from trusted sources; the runner writes them and does not load arbitrary supplied pickle files.

From repository root:

```powershell
python -m backend.scripts.demonstrate_phase4 data/results/v2 NEW_DEMO_PREFIX
python -m backend.app.research.crest data/results/v2/phase4-verified-a/config.json data/results/v2 NEW_REPLAY_ID
```

Use fresh output IDs. The demo reuses verified `phase4-demo-inputs-v1` when present. Its initial bounded generation was needed because the earlier Phase 3 A-only fixture did not cover the declared training/evaluation population and demo budget. Existing Phase 3 outputs remain untouched.

### Complexity and resource scope

Let N be source-training accounts, V evaluated accounts, M accepted interventions, T trees, and psi samples per tree. Typical Isolation Forest fitting is O(T psi log psi), scoring O((N+V+M) T log psi), and calibration-reference sorting O(N log N), with O((V+M) log N) percentile lookup. These are typical tree-depth bounds, not a full-dataset runtime guarantee.

The current Python runner repeatedly filters profiles by account, costing O(VM), and stratum grouping can cost O(sum of squared family candidate counts); bounded Phase 3 candidate caps limit this smoke workload. Account ranking costs O(K V log V) for K modes. Memory includes all loaded artifacts/vectors O((N+V+M)*19), tree storage and duplicated explanation structures in K rankings. Scoring batches limit estimator call size but do not stream all artifacts. No graph-recomputation cost is incurred inside the runner. There is no new model-score cache.

### Executed verification

Final disposable run: `work/phase4-tests/phase2-38uiewpg`.

| Outcome | Actual result |
|---|---|
| Passed | 233, including all 43 Phase 4 cases |
| Failed / errors | 0 / 0 |
| Skipped | 1 |
| Blocked in selected regression run | 0 |
| Pytest duration / process exit | 112.60 seconds / 0 |

This is the selected relevant regression suite, not a claim that every repository test ran. It covers Phase 2/3 correctness plus graph, features, anomaly, demo workflow, evaluation, splits, transfer, adapters, research runner, transactions and locked-artifact tests. Exact command, JUnit and log are copied to workspace `outputs/phase4_evidence/`. The historical processed-dataset test skipped because `ddbaab44-78b6-41be-a8fb-e83dfec66358.csv` and `03fb9ab0-4f42-4404-9d76-723fd4d8753e.csv` are unavailable. Original data was not regenerated to satisfy it.

Execution used an approved disposable environment. The previously diagnosed Windows sandbox socket-pair/asyncio restriction was environmental; no event-loop monkeypatch was introduced.

Tests verify E4 raw numerical equivalence, orientation, exact feature order, source-only fitting/calibration, one fit per experiment, wrong-identity rejection, batching equality, monotonic/tied/constant/out-of-range calibration, both sensitivity signs, family imbalance, strata, bounded/undefined statistics, all modes, zero-weight identity, deterministic ties, missing evidence, append-only output and replay. Target-vector changes leave source calibration and model identity/hash unchanged. Label lookup and graph reconstruction are patched to fail in integration tests, demonstrating their absence from scoring. Corrupt/rehashed but inconsistent artifacts are rejected.

### Measured synthetic demonstration

Input: unchanged `docs/research/fixtures/phase3_transactions.csv`, cutoff simulation step 9, temporal window 1, max omission count 1, max fraction .5, min retained 1, max interventions 12, explicit isolated account. Training A/B/C/F/X/Y; held-out D/E/ISOLATED. Model seed 42, 100 trees, max_samples auto, contamination .005, alpha=beta=.25. No labels or weight selection.

Input manifest SHA-256:
`432ade1c75640cb2bdd5bda872825c19000ac4ec879ff69f0eb50f5ec0fe651f`.

| Account | Raw baseline | q0 | D | R | Valid interventions |
|---|---:|---:|---:|---:|---:|
| D | -0.22032088723098886 | .16666666666666666 | -.5277777777777778 | .45833333333333326 | 5 |
| E | -0.19023716925399942 | .5 | -.2777777777777778 | .75 | 5 |
| ISOLATED | -0.07832882871969826 | .8333333333333334 | null | null | 0 |

D and E have distinct observed profiles; their negative D means omission tends to increase calibrated anomaly scores. The isolated account illustrates missing evidence and baseline fallback, not confirmed suspiciousness. Concentration retains undefined/insufficient statuses when support or positive influence is absent; edge-case defined values are tested separately.

| Measurement | Run A | Run B |
|---|---:|---:|
| Wall seconds | 3.3536884 | 3.1158870 |
| Fit seconds | 2.6109365 | 2.4960780 |
| Batched score seconds | .0634012 | .0530581 |
| Peak traced Python bytes | 1,274,153 | 1,196,004 |

Initial Phase 3 fixture preparation took 4.0829174 seconds separately. Memory is tracemalloc Python allocation peak, not total RSS/native memory. These tiny-fixture timings do not establish scalability.

Runs `phase4-verified-a`, `phase4-verified-b` and independent saved-config CLI `phase4-cli-replay` produced byte-identical `accounts.json`, `intervention_scores.jsonl`, `rankings.json`, `calibration.json` and `model.joblib`. All three manifests' output hashes validate. CLI exited 0; its untraced recorded total was 2.3111726 seconds. Timing-bearing manifests are not asserted byte-identical.

### Integrity, files and evidence

`outputs/phase4_evidence/verification.json` (workspace-relative) records:

- 87/87 protected files match the protected manifest and original supplied ZIP byte-for-byte.
- 127 prior files match preserved snapshots: Phase 2/3 application sources, earlier versioned results and reports 01–03.
- All three demo runs' artifact hashes validate and scientific replay bytes match.
- `git diff --check` exits 0.

Phase 4 creates these ten repository files:

1. `backend/app/research/crest/__init__.py`
2. `backend/app/research/crest/schemas.py`
3. `backend/app/research/crest/frozen_scorer.py`
4. `backend/app/research/crest/artifacts.py`
5. `backend/app/research/crest/statistics.py`
6. `backend/app/research/crest/runner.py`
7. `backend/app/research/crest/__main__.py`
8. `backend/scripts/demonstrate_phase4.py`
9. `backend/tests/test_phase4_crest.py`
10. `docs/research/04_crest_scoring_algorithm.md`

Continuation edits were confined to existing Phase 4 files (`artifacts.py`, `statistics.py`, `runner.py`, tests), plus this new report and workspace-only `work/collect_phase4_evidence.py`. New research outputs are the demo-input bundle, two verified runs, CLI replay and demonstration evidence under `data/results/v2`; these ignored artifacts require explicit preservation outside Git.

The working tree still includes prior Phase 2/3 uncommitted work. The 16 tracked modifications against `cd4a3fd` predate Phase 4; they are listed in `outputs/phase4_evidence/git-status.txt`. Do not mistake that cumulative diff for new Phase 4 modifications. No original algorithm, frontend, protected data or historical result was changed in this phase. No commit was made.

### Acceptance review

| # | Original Phase 4 criterion | Result and evidence |
|---|---|---|
| 1 | Frozen E4 scoring | Satisfied: source-only single fit, raw Phase 2 equivalence tests |
| 2 | Source-only calibration | Satisfied: monotonicity, ties, boundaries and target-independence tests |
| 3 | Signed sensitivity | Satisfied: signed/absolute/positive/negative profiles and tests |
| 4 | Family-balanced aggregation | Satisfied: equal-family medians, unequal-count regression |
| 5 | Evidence robustness | Satisfied: bounded values, support thresholds and missingness |
| 6 | Concentration edge cases | Satisfied: stratified diagnostic; null/zero/one-supported-positive cases |
| 7 | Candidate scores | Satisfied: all five modes, formula and fallback tests |
| 8 | Zero-weight identity | Satisfied: exact calibrated baseline scores/order |
| 9 | Deterministic rankings | Satisfied: ID tie rule and three matching replays |
| 10 | Explanation records | Satisfied: account/profile/ranking outputs with warnings |
| 11 | Versioned manifests | Satisfied: pinned inputs, model/config/seeds/hashes and append-only tests |
| 12 | Historical preservation | Satisfied: 87 protected files and 127 prior snapshot files match |
| 13 | Tests pass or failures documented | Satisfied: 233 passed, 0 failed, 1 documented environmental-data skip |
| 14 | Reproducible demo | Satisfied: distinct D/E profiles, three identical scientific replays |
| 15 | Scientific report | Satisfied: this report, equations, limitations and measured evidence |

### Limitations and Phase 5 readiness

PaySim provenance remains explicitly unresolved: the 774-positive and 2,606-positive account label sets have 1,832 disagreements. Neither is silently preferred or altered.

No final benchmark, PR-AUC improvement, confidence interval, novelty determination or label-based parameter selection was performed. Source-only fitting is not sufficient to claim inductive evaluation because graph features are transductive. Source percentiles can saturate under transfer; overlapping omissions are correlated; support thresholds and binning are heuristic; signed medians can cancel; family support can differ between D and R; robustness penalties may suppress real localized anomalies. Small synthetic evidence does not validate financial effectiveness.

Phase 4 engineering acceptance criteria are satisfied with the documented missing historical-file test. Ready for a separately authorized Phase 5 prespecified evaluation: freeze candidate configurations and budgets before held-out evaluation, declare dataset/label identities, retain E4 comparison, separate development from final-test selection, and assess paired seeded outcomes and resource costs. Resolving or explicitly partitioning PaySim label provenance remains necessary for defensible benchmark interpretation. Phase 5, dashboard APIs and frontend redesign have not been implemented.
