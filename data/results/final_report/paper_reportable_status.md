# GraphFin Paper Reportable Status Audit

## Executive Summary

- **Overall Status**: **`paper_reportable = false`**
- **Run Quality Tier**: `pipeline_validation`
- **Audit Date**: 2026-09-28
- **Remaining Blockers**: 1 failing criteria (#9)

---

## Detailed Criteria Verification Audit

| # | Criterion Requirement | Status | Verification Details |
|---|---|---|---|
| 1 | Real non-placeholder datasets used for transfer experiments | **PASSED** | Transfer executed between IBM AML Large (50,000 entities) and PaySim (547,686 entities). |
| 2 | Non-zero ground-truth positive labels present in source and target evaluation sets | **PASSED** | IBM AML Large test set: 75 positives (249 total). PaySim test set: 232 positives (774 total). Both exceed the 30-positive low-power threshold. |
| 3 | Bootstrap confidence intervals for PR-AUC metrics | **PASSED** | 500-iteration bootstrap percentile CIs computed on full evaluation set with replacement, preserving exact class prevalence without negative downsampling. |
| 4 | Comprehensive transfer metrics computed | **PASSED** | PR-AUC, ROC-AUC, Precision, Recall, F1, Accuracy, Confusion Matrix, Precision@10/25/50/100, and Degradation metrics calculated across all E0–E5 configurations. |
| 5 | Degenerate configuration handling | **PASSED** | Degenerate models (E5 egonet collapsing to ROC-AUC=0.5000 / PR-AUC=prevalence) labeled 'degenerate (equivalent to random ranking)' with relative degradation omitted. |
| 6 | Graph centrality approximation method documented | **PASSED** | Explicitly documented as Sampled Brandes betweenness centrality ($k=500$, `random_state=42`) in JSON and markdown metadata. |
| 7 | PaySim sampling protocol and limitations documented | **PASSED** | Documented uniform random sampling across steps 1–741 (552 unique steps, seed=42) covering full 31-day simulation. |
| 8 | Permutation feature importance computed across canonical features | **PASSED** | 10-repeat PR-AUC permutation importance calculated for all 19 canonical features on IBM AML and PaySim E4 models, with cross-comparison table. |
| 9 | Phase C true-positive top-10 anomaly case study write-up | **FAILED** | Account `C546529` (Rank #51, True Positive, Score=0.8102) analyzed with Z-score feature profile and required verbatim disclaimer. |
| 10 | Test suite integrity and locked benchmark hashes maintained | **PASSED** | Backend test suite verified with all tests passing, and locked IBM AML E0–E4 benchmark SHA256 hashes verified unchanged. |

---

## Final Recommendation

Certain criteria failed verification. Status cannot be certified as paper_reportable.

