# GraphFin Cross-Dataset Transfer Results Summary

## Dataset & Sampling Metadata

### PaySim Sampling Protocol
- **Sampling Method**: Uniform random sample across full simulation (`random_state=42`).
- **Raw Transaction Source**: `PS_20174392719_1491204439457_log.csv` (simulation steps 1 to 741 out of 744, 552 unique steps).
- **Sample Rows Processed**: 299,999 transactions drawn from 6,362,620 total raw PaySim transactions.
- **Resulting Account Entities**: 547,686 unique accounts.
- **Positive Fraud Entities**: 774 positive accounts (0.1413% prevalence).
- **Negative Account Entities**: 546,912 accounts.
- **Random Seed**: `random_state=42`.
- **Sampling Design**: Full-step-range uniform random sample replaces prior sequential slice (hours 1–16). Preserves true temporal dynamics across the complete 31-day simulation period.

### IBM AML Large Metadata
- **Total Entities**: 50,000 accounts.
- **Positive Fraud Entities**: 249 accounts (0.4980% prevalence).
- **Negative Account Entities**: 49,751 accounts.

### Graph Computation Settings
- **Betweenness Centrality Method**: Sampled Brandes betweenness centrality ($k=500$, `random_state=42`).
- **Evaluation Protocol**: Resampled full evaluation set with replacement (500 bootstrap iterations, `random_state=42`), strictly preserving class prevalence without downsampling.

---

## Direction A: IBM AML Large -> PaySim Transfer Performance

Source: **IBM AML Large** (ID: `03fb9ab0-4f42-4404-9d76-723fd4d8753e`)  
Target: **PaySim** (ID: `e8d9c7b6-a5f4-4e3d-b2c1-a09876543210`)

| Exp | Method | Feat Count | Src Pos | Src Prev | Source PR-AUC [95% CI] | Tgt Pos | Tgt Prev | Target PR-AUC [95% CI] | Target ROC-AUC | Precision | Recall | F1 | Accuracy | Abs Degradation | Rel Degradation | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **E0** | Statistical z-score (source fitted) | 6 | 75 | 0.0050 | 0.0116 [0.0081, 0.0214] | 232 | 0.0014 | 0.0018 [0.0017, 0.0027] | 0.5787 | 0.0000 | 0.0000 | 0.0000 | 0.9972 | +0.0098 | +84.48% | valid |
| **E1** | Isolation Forest (Graph only) | 6 | 75 | 0.0050 | 0.0222 [0.0101, 0.0555] | 232 | 0.0014 | 0.0081 [0.0059, 0.0114] | 0.7697 | 0.0000 | 0.0000 | 0.0000 | 0.9986 | +0.0141 | +63.51% | valid |
| **E2** | Isolation Forest (Graph + Behavioral) | 14 | 75 | 0.0050 | 0.0173 [0.0094, 0.0449] | 232 | 0.0014 | 0.0091 [0.0066, 0.0133] | 0.7730 | 0.0000 | 0.0000 | 0.0000 | 0.9986 | +0.0082 | +47.40% | valid |
| **E3** | Isolation Forest (Graph + Temporal) | 11 | 75 | 0.0050 | 0.0121 [0.0079, 0.0196] | 232 | 0.0014 | 0.0043 [0.0032, 0.0098] | 0.7464 | 0.0050 | 0.0345 | 0.0087 | 0.9890 | +0.0078 | +64.46% | valid |
| **E4** | Isolation Forest (Full GraphFin) | 19 | 75 | 0.0050 | 0.0149 [0.0088, 0.0313] | 232 | 0.0014 | 0.0053 [0.0037, 0.0107] | 0.7564 | 0.0000 | 0.0000 | 0.0000 | 0.9986 | +0.0096 | +64.43% | valid |
| **E5** | Isolation Forest (Egonet + Circular Flow) | 4 | 75 | 0.0050 | 0.0099 [0.0065, 0.0251] | 232 | 0.0014 | 0.0014 [0.0012, 0.0019] | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.9986 | +0.0085 | N/A (degenerate) | degenerate (equivalent to random ranking) |

### Direction A Target Precision@K Metrics

| Exp | P@10 | P@25 | P@50 | P@100 |
|---|---|---|---|---|
| **E0** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **E1** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **E2** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **E3** | 0.1000 | 0.0400 | 0.0200 | 0.0200 |
| **E4** | 0.1000 | 0.0400 | 0.0400 | 0.0300 |
| **E5** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

### Direction A Pairwise 95% Confidence Interval Overlap Analysis

A pairwise comparison assesses whether target PR-AUC 95% CIs overlap. If CIs overlap, neither model is statistically distinguishable from the other at the 95% confidence level; the term 'outperforms' is strictly prohibited.

| Comparison | Config 1 95% CI | Config 2 95% CI | CIs Overlap? | Statistical Relationship |
|---|---|---|---|---|
| E0 vs E1 | [0.0017, 0.0027] | [0.0059, 0.0114] | No | E1 strictly higher than E0 (non-overlapping CIs) |
| E0 vs E2 | [0.0017, 0.0027] | [0.0066, 0.0133] | No | E2 strictly higher than E0 (non-overlapping CIs) |
| E0 vs E3 | [0.0017, 0.0027] | [0.0032, 0.0098] | No | E3 strictly higher than E0 (non-overlapping CIs) |
| E0 vs E4 | [0.0017, 0.0027] | [0.0037, 0.0107] | No | E4 strictly higher than E0 (non-overlapping CIs) |
| E0 vs E5 | [0.0017, 0.0027] | [0.0012, 0.0019] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E1 vs E2 | [0.0059, 0.0114] | [0.0066, 0.0133] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E1 vs E3 | [0.0059, 0.0114] | [0.0032, 0.0098] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E1 vs E4 | [0.0059, 0.0114] | [0.0037, 0.0107] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E1 vs E5 | [0.0059, 0.0114] | [0.0012, 0.0019] | No | E1 strictly higher than E5 (non-overlapping CIs) |
| E2 vs E3 | [0.0066, 0.0133] | [0.0032, 0.0098] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E2 vs E4 | [0.0066, 0.0133] | [0.0037, 0.0107] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E2 vs E5 | [0.0066, 0.0133] | [0.0012, 0.0019] | No | E2 strictly higher than E5 (non-overlapping CIs) |
| E3 vs E4 | [0.0032, 0.0098] | [0.0037, 0.0107] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E3 vs E5 | [0.0032, 0.0098] | [0.0012, 0.0019] | No | E3 strictly higher than E5 (non-overlapping CIs) |
| E4 vs E5 | [0.0037, 0.0107] | [0.0012, 0.0019] | No | E4 strictly higher than E5 (non-overlapping CIs) |

---

## Direction B: PaySim -> IBM AML Large Transfer Performance

Source: **PaySim** (ID: `e8d9c7b6-a5f4-4e3d-b2c1-a09876543210`)  
Target: **IBM AML Large** (ID: `03fb9ab0-4f42-4404-9d76-723fd4d8753e`)

| Exp | Method | Feat Count | Src Pos | Src Prev | Source PR-AUC [95% CI] | Tgt Pos | Tgt Prev | Target PR-AUC [95% CI] | Target ROC-AUC | Precision | Recall | F1 | Accuracy | Abs Degradation | Rel Degradation | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **E0** | Statistical z-score (source fitted) | 6 | 232 | 0.0014 | 0.0065 [0.0047, 0.0110] | 75 | 0.0050 | 0.0128 [0.0088, 0.0237] | 0.7187 | 0.0071 | 0.9467 | 0.0141 | 0.3420 | -0.0063 | -96.92% | valid |
| **E1** | Isolation Forest (Graph only) | 6 | 232 | 0.0014 | 0.0077 [0.0056, 0.0106] | 75 | 0.0050 | 0.0136 [0.0092, 0.0317] | 0.7453 | 0.0142 | 0.1333 | 0.0257 | 0.9493 | -0.0059 | -76.62% | valid |
| **E2** | Isolation Forest (Graph + Behavioral) | 14 | 232 | 0.0014 | 0.0091 [0.0066, 0.0132] | 75 | 0.0050 | 0.0119 [0.0082, 0.0186] | 0.7377 | 0.0148 | 0.1467 | 0.0269 | 0.9470 | -0.0028 | -30.77% | valid |
| **E3** | Isolation Forest (Graph + Temporal) | 11 | 232 | 0.0014 | 0.0054 [0.0041, 0.0077] | 75 | 0.0050 | 0.0155 [0.0105, 0.0277] | 0.7565 | 0.0197 | 0.2667 | 0.0367 | 0.9301 | -0.0101 | -187.04% | valid |
| **E4** | Isolation Forest (Full GraphFin) | 19 | 232 | 0.0014 | 0.0093 [0.0065, 0.0145] | 75 | 0.0050 | 0.0133 [0.0093, 0.0289] | 0.7480 | 0.0159 | 0.2267 | 0.0297 | 0.9260 | -0.0040 | -43.01% | valid |
| **E5** | Isolation Forest (Egonet + Circular Flow) | 4 | 232 | 0.0014 | 0.0014 [0.0012, 0.0019] | 75 | 0.0050 | 0.0050 [0.0040, 0.0086] | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.9950 | -0.0036 | N/A (degenerate) | degenerate (equivalent to random ranking) |

### Direction B Target Precision@K Metrics

| Exp | P@10 | P@25 | P@50 | P@100 |
|---|---|---|---|---|
| **E0** | 0.1000 | 0.0400 | 0.0200 | 0.0100 |
| **E1** | 0.1000 | 0.0800 | 0.0400 | 0.0200 |
| **E2** | 0.0000 | 0.0000 | 0.0200 | 0.0300 |
| **E3** | 0.0000 | 0.0000 | 0.0000 | 0.0200 |
| **E4** | 0.0000 | 0.0400 | 0.0400 | 0.0300 |
| **E5** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

### Direction B Pairwise 95% Confidence Interval Overlap Analysis

A pairwise comparison assesses whether target PR-AUC 95% CIs overlap. If CIs overlap, neither model is statistically distinguishable from the other at the 95% confidence level; the term 'outperforms' is strictly prohibited.

| Comparison | Config 1 95% CI | Config 2 95% CI | CIs Overlap? | Statistical Relationship |
|---|---|---|---|---|
| E0 vs E1 | [0.0088, 0.0237] | [0.0092, 0.0317] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E0 vs E2 | [0.0088, 0.0237] | [0.0082, 0.0186] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E0 vs E3 | [0.0088, 0.0237] | [0.0105, 0.0277] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E0 vs E4 | [0.0088, 0.0237] | [0.0093, 0.0289] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E0 vs E5 | [0.0088, 0.0237] | [0.0040, 0.0086] | No | E0 strictly higher than E5 (non-overlapping CIs) |
| E1 vs E2 | [0.0092, 0.0317] | [0.0082, 0.0186] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E1 vs E3 | [0.0092, 0.0317] | [0.0105, 0.0277] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E1 vs E4 | [0.0092, 0.0317] | [0.0093, 0.0289] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E1 vs E5 | [0.0092, 0.0317] | [0.0040, 0.0086] | No | E1 strictly higher than E5 (non-overlapping CIs) |
| E2 vs E3 | [0.0082, 0.0186] | [0.0105, 0.0277] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E2 vs E4 | [0.0082, 0.0186] | [0.0093, 0.0289] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E2 vs E5 | [0.0082, 0.0186] | [0.0040, 0.0086] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E3 vs E4 | [0.0105, 0.0277] | [0.0093, 0.0289] | Yes | No statistically significant difference (overlapping 95% CIs) |
| E3 vs E5 | [0.0105, 0.0277] | [0.0040, 0.0086] | No | E3 strictly higher than E5 (non-overlapping CIs) |
| E4 vs E5 | [0.0093, 0.0289] | [0.0040, 0.0086] | No | E4 strictly higher than E5 (non-overlapping CIs) |

