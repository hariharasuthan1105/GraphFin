# Phase 6B — Manuscript revision and validation plan

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Keep this title verbatim. Proposed paper type: a bounded applied empirical/system study, with an optional short negative-results diagnostic subsection. The present evidence is not submission-ready and does not justify a methodology-superiority paper. This is a plan, not authorization to execute Phase 6C/7 or redesign the frontend.

## 1. Abstract — evidence-bounded draft

Financial transaction graphs provide account-level structural, behavioral and temporal summaries for anomaly detection, but reliable comparison requires explicit data identities, evaluation populations and score semantics. We consolidate GraphFin into a versioned research system for unsupervised account scoring with Isolation Forest and an explicit statistical baseline. On two supplied synthetic IBM AML subsets, we compare six baseline configurations and a calibration-only variant across six stratified account splits. Full-feature Isolation Forest achieves mean average precision of 0.095910 (split SD 0.096805) on 1,500 held-out accounts and 0.023494 (SD 0.012678) on 14,998 held-out accounts; each split contains six and seventy-five positives, respectively. Feature enrichment does not produce a consistent advantage, and empirical-percentile calibration can alter average precision through tied scores. A separate six-account evidence-omission diagnostic produces thirteen valid method records across four accounts, but all twelve budget-compatible comparisons with simple heuristics tie. We document replay evidence, provenance limitations, graph dependence and substantial recomputation cost. The results support transparent empirical evaluation and bounded model-response diagnostics, not CREST detector or explanation superiority.

Before submission, revise this draft only from completed versioned evidence. Do not imply that the thirteen records are thirteen independent accounts, that split SD is a confidence interval, or that the supplied labels are independently verified.

## 2. Introduction

Motivate account-level investigation of transaction histories and the need for reproducible comparison. State that the evaluation target is retrospective simulated transaction involvement aggregated to accounts. Avoid unsupported fraud-loss estimates, deployment claims or assertions that graph features plus IF are new. Establish the practical research question: what is reproducibly learned from baseline feature groups and bounded evidence-removal diagnostics under sparse labels and compute constraints?

## 3. Research gap and contributions

Do not claim a literature-wide absence of reproducibility. Describe the specific gaps found in this project's original workflow: model/split fallback, inconsistent E0 semantics, tied-score AP, data identities and incomplete coverage. The comparison with Graphomaly and removal-based explanation literature is mandatory.

**Contribution paragraph:** This work contributes an auditable implementation and empirical examination of account anomaly detection on supplied synthetic financial transaction graphs. It records dataset and label identities, separates fitting and evaluation membership, versions baseline definitions, and preserves raw held-out scores for reproducible metric calculation. A controlled six-split comparison documents substantial split sensitivity and nonmonotone feature-enrichment outcomes. An additional constrained historical-evidence diagnostic links omitted transaction identifiers to recomputed graph features and frozen-model responses, while reporting missing explanations, tied heuristic comparisons and computational limitations. These contributions concern implementation rigor and measured behavior; a superior general anomaly detector or explanation algorithm is not established.

## 4. Related work

Use the verified references and exact distinctions in `06B_related_work_comparison.md`. Lead with Dumitrescu et al. (IEEE Access 2022), then graph anomaly/flow and temporal methods, removal/counterfactual explanations, and evaluation methodology. Explain that GraphFin E5 is a four-feature local heuristic rather than a faithful complete reimplementation of the closest paper. Do not copy published performance numbers into a shared GraphFin leaderboard. Cross-domain benchmarking and source-to-target transfer are distinct evaluation problems.

## 5. GraphFin methodology

Describe directed amount-aggregated graphs, canonical feature groups and redundancies; IF configuration and score direction; E0 source-signed-zero definition; versioned memberships/artifacts; full-observation transductive semantics. Labels enter stratification/evaluation only. Report sampled-centrality policy and monetary assumptions.

Algorithm 1 should be the **existing reproducible account-evaluation workflow**, referencing `backend/app/research/benchmark/runner.py`, `metrics.py`, `services/research_protocol.py` and frozen Phase 5 JSON: validate identities → build/reuse full-graph features → declare split → fit source-only model → score identical held-out IDs → save arrays/metrics/manifests. Name the transductive graph explicitly rather than placing feature computation inside an implied training-only graph.

Optional Algorithm 2 should describe **existing bounded omission diagnostics**, referencing `explanation_validation/diagnostics.py` and `interventions/intervention_engine.py`: validate historical IDs and budgets → select whole groups without score optimization → recompute features → frozen score → signed response → matched comparisons with unavailable reasons. No new fusion or ranking rule. State that removal is not actionable causal recourse.

## 6. Experimental design

Give dataset/label hashes and lineage status; active-account filtering; positive counts; six split seeds versus one model seed; versions and environment; matching populations; AP definition/ties; P@K tie ordering; sample SD; conditional bootstrap limitations; exact replay scope. Declare historical results archival and incomplete E6 excluded. Explain the diagnostic cohort selection and repeated-evidence dependence. Specify future validation before inspecting its outcomes; existing experiments are fixed documented protocols, not retrospectively certified preregistration.

## 7. Results and supported visuals

Repository-relative artifact plan; no new figure or performance result has been fabricated:

| Item | Content | Authoritative source | Interpretation restriction |
|---|---|---|---|
| Table 1 | Populations, positives, label provenance, seeds and versions | `docs/research/configs/phase5_protocol_v1.json`; `data/results/v2/phase5-features-{5k,50k}-v1/manifest.json` | Synthetic supplied subsets; not two independently validated domains |
| Table 2 | Seven methods: AP mean/sample SD; per-seed supplement; P@K | `data/results/v2/phase6b-consolidation-v1/{summary.json,per_seed_metrics.json,tables.md}` | No best-method significance marks |
| Figure 1 | Account-processing and artifact workflow | Existing backend service/research modules named in section 5 | Architecture schematic, not measured performance |
| Figure 2 | All six AP observations per method/tier, plus mean | `per_seed_metrics.json` | Show individual splits; avoid SEM/error bars suggesting independence |
| Table 3 / small Figure 3 | E4 versus empirical-calibrated E6_BASE; score tie effects | `data/results/v2/phase5-results-review-v3/paired_e6base_vs_e4.csv`; exact score arrays | Calibration comparison only; conditional intervals if shown |
| Table 4 (optional) | Explanation availability, signed F, compatible pair ties, stability failures | `data/results/v2/phase6a-explanations-v1-pilot-v2/`; `06A_explanation_validation.md` sections 6–8 | Six selected accounts, thirteen method records, five distinct structured scenarios |
| Table 5 (optional/supplement) | Measured baseline/pilot timing and separate projections | Feature/baseline manifests; Phase 6A runtime artifacts/report section 9 | Distinguish fresh/reused work, worker/wall and projected/measured cost |
| Supplement | Provenance, exact memberships, hashes, commands, failures and acceptance gates | Phase 1–6B reports; protected manifest; completion/verification manifests | Preserve negative and incomplete experiments |

The historical single-run table may appear only as an explicitly archival audit example, not mixed with new means. No unfinished E6 ablation, cross-domain accuracy, 250-account explanation runtime measurement or expert-utility figure exists.

## 8. Discussion

Discuss instability under rare positives, nonmonotone feature enrichment, AP/top-K tradeoffs, CDF ties, and the difference between valid interventions and useful explanations. Explain how changing ten ordinal positions can leave six pilot accounts' relative ordering unchanged. Neither fact establishes predictive benefit. Make CREST a short diagnostic subsection or implementation supplement; do not structure the paper around a claimed superior CREST method.

## 9. Limitations and minimum validation

Explicitly include synthetic data, unverified transformed-label lineage, endpoint involvement versus culpability, missing historical processed inputs, PaySim conflict, transductive features, six/75 held-out positives, overlapping splits, graph-dependent bootstrap, feature redundancy, sampled betweenness/order effects, limited explanation support, reused evidence, lack of domain-expert utility evidence and global recomputation cost.

### Required before an applied empirical submission

1. **Provenance/package audit:** obtain the authoritative raw-to-subset conversion and label-generation procedure, or explicitly publish the task as a supplied-file case study with unverified upstream labels and no external validity claim. Verify licensing/sharing permissions and package the exact reproducible environment, manifests, retained verifier scripts and raw scores. This is documentation/data evidence work, not an excuse to alter existing labels. PaySim remains excluded unless authoritative provenance resolves the conflict.
2. **One independent ~50K baseline replay:** fresh output namespace/environment from the frozen feature/fit specification; compare score/split/metric artifacts with runtime metadata excluded. Existing saved-score reconstruction is insufficient to claim this already happened. Baseline stages previously took about two minutes, so this is far more feasible than full intervention replay; do not promise identical runtime.
3. **Bounded model-seed sensitivity on cached features:** freeze a small prespecified model-seed list and identical held-out memberships for E1–E5 before evaluation; report all outcomes. This addresses the distinction between split randomness and model randomness without repeating graph extraction. No label-driven seed or hyperparameter selection. If omitted, restrict claims explicitly to fixed model seed 42 rather than general robustness.
4. **Independent validation if the paper claims generalization:** one separately derived, traceable synthetic dataset or frozen later-time cohort with sufficient positive support, under a prespecified protocol. For prospective claims, restrict graph/history to the cutoff and define future labels; for source-to-target claims, fit/tune only on source and reveal target labels only for final evaluation. Do not repurpose unresolved PaySim labels. A two-subset descriptive case study can instead omit generalization claims, but will have a weaker conference contribution.

### Conditional, not a mandatory new research program

- If claiming feature-enrichment mechanisms, a versioned deduplicated-feature ablation is needed; otherwise retain only the observed group comparison and acknowledge redundancy. Use cached columns and fixed seeds; never silently replace E0–E5.
- If claiming explanation utility beyond a diagnostic, define a domain-grounded task and expert/ground-truth assessment before collecting evidence. The current pilot does not supply it. A broad expensive CREST benchmark is **not recommended** merely to rescue a novelty claim.
- Do not repeat already completed pilots, invent a new formula, optimize explanation selection on observed outcomes, or automatically repair control-order semantics during consolidation. Such changes would be separately authorized and versioned.

## 10. Conclusion and next-phase gate

Conclude that GraphFin supports reproducible, explicitly scoped comparison and transparent diagnostic limitations. State that consistent feature-enrichment benefits, CREST superiority, broad explanation stability and affordable full coverage were not established. Preserve the original project idea and title while narrowing claims to evidence.

**Phase 6C recommendation:** bounded validation, provenance resolution or explicit scope restriction, and a reproducible artifact release. Reassess the A–G gate in `06B_scientific_consolidation.md` afterward. **Phase 7 recommendation:** write the applied empirical/system manuscript and presentation using only validated claims; frontend/demo work, if wanted, requires separate authorization and must not label diagnostics as proven fraud explanations.

A methodology-oriented ML submission is not supported by present novelty or results. An applied IEEE computing venue, empirical anomaly-detection study or system demonstration is a plausible qualitative fit after those gates; venue fit is not a forecast of acceptance. No Phase 6C/7 work or commit is performed in Phase 6B.
