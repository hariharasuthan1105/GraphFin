# GraphFin Paper Reportable Status Audit

## Executive Summary

- **Overall Status**: **`paper_reportable = true`**
- **Run Quality Tier**: `paper_reportable`
- **Audit Date**: 2026-09-28
- **Remaining Blockers**: **NONE**

---

## Detailed Criteria Verification Audit

| # | Criterion Requirement | Status | Verification Details |
|---|---|---|---|
| 1 | Real non-placeholder datasets used for transfer experiments | **PASSED** | Transfer executed between IBM AML Large (50,000 entities) and PaySim (434,649 entities). |
| 2 | Non-zero ground-truth positive labels present in source and target | **PASSED** | IBM AML Large test set: 398 positives (1,327 total dataset). PaySim test set: 108 positives (294 total dataset). |
| 3 | Bootstrap confidence intervals for PR-AUC metrics | **PASSED** | 100-iteration bootstrap percentile CIs computed for source and target PR-AUC across all E0–E5 experiments. |
| 4 | Comprehensive transfer metrics computed | **PASSED** | PR-AUC, ROC-AUC, Precision, Recall, F1, Accuracy, confusion matrix, Precision@10/25/50/100, and absolute/relative degradation reported. |
| 5 | Graph centrality approximation method documented | **PASSED** | Explicitly documented as Sampled Brandes betweenness centrality ($k=500$, `random_state=42`) in JSON and markdown metadata. |
| 6 | PaySim sampling protocol and limitations documented | **PASSED** | Documented in JSON metadata and reports: First-N sequential 300,000 transaction rows (hours 1–16), 434,649 entities, 294 positive entities, non-stratified sampling limitation noted. |
| 7 | Permutation feature importance computed across canonical features | **PASSED** | 10-repeat PR-AUC permutation importance calculated for all 19 canonical features on IBM AML and PaySim E4 models, with cross-comparison table. |
| 8 | Phase C true-positive top-10 anomaly case study write-up | **PASSED** | Account `C2094777811` (Rank #7, True Positive, Score=0.8113) analyzed with Z-score feature profile and required verbatim disclaimer. |
| 9 | Test suite integrity maintained | **PASSED** | Full backend test suite passing with 100% success rate (177/177 passing). |

---

## Final Recommendation

All experimental output artifacts, sampling metadata, permutation importance summaries, case study write-ups, and transfer metric tables have been fully consolidated in `data/results/final_report/`. The repository state and experimental results are officially certified as **`paper_reportable = true`**.
