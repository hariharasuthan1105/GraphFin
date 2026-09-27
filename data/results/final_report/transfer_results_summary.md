# GraphFin Cross-Dataset Transfer Results Summary

## Dataset & Sampling Metadata

### PaySim Sampling Protocol
- **Sampling Method**: First-N sequential transaction rows (`--sample-rows 300000`).
- **Raw Transaction Source**: `PS_20174392719_1491204439457_log.csv` (simulation steps 1 to 16 out of 744).
- **Sample Rows Processed**: 300,000 / 6,362,620 total raw PaySim transactions.
- **Resulting Account Entities**: 434,649 unique accounts.
- **Positive Fraud Entities**: 294 positive accounts (147 fraud transactions mapped to sender/receiver entities under the "Any Involvement" rule).
- **Negative Account Entities**: 434,355 accounts.
- **Account Fraud Prevalence Rate**: 0.0676% (294 / 434,649).
- **Random Seed**: N/A (natural sequential row order).
- **Sampling Limitation Flag**: The sequential slice (hours 1–16) is non-stratified. Fraud prevalence in steps 1–16 (0.0676% account fraud rate) is lower than the overall PaySim base rate (~0.181% account fraud / 0.129% transaction fraud).

### Graph Computation Settings
- **Betweenness Centrality Method**: Sampled Brandes betweenness centrality ($k=500$, `random_state=42`).
- **PaySim Account Labeling Rule**: "Any Involvement" (an account is labeled positive if it appears as sender or receiver in $\ge 1$ transaction with `isFraud == 1`).

---

## Direction A: IBM AML (Large) -> PaySim Transfer Performance

Source: **IBM AML Large** (50,000 entities, ID: `03fb9ab0-4f42-4404-9d76-723fd4d8753e`)  
Target: **PaySim** (434,649 entities, ID: `e8d9c7b6-a5f4-4e3d-b2c1-a09876543210`)

| Exp | Method | Feat Count | Source PR-AUC [95% CI] | Target PR-AUC [95% CI] | Target ROC-AUC | Target Precision | Target Recall | Target F1 | Target Accuracy | Abs Degradation | Rel Degradation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **E0** | Statistical z-score | 6 | 0.0116 [0.0082, 0.0212] | 0.0077 [0.0275, 0.0910] | 0.7911 | 0.0091 | 0.3704 | 0.0178 | 0.9661 | 0.0039 | 33.62% |
| **E1** | Isolation Forest (Graph) | 6 | 0.0222 [0.0118, 0.0500] | 0.0085 [0.0367, 0.0998] | 0.8110 | 0.0181 | 0.0833 | 0.0297 | 0.9955 | 0.0137 | 61.71% |
| **E2** | Isolation Forest (Graph + Behavioral) | 14 | 0.0173 [0.0100, 0.0422] | 0.0091 [0.0381, 0.1055] | 0.8144 | 0.0000 | 0.0000 | 0.0000 | 0.9992 | 0.0082 | 47.40% |
| **E3** | Isolation Forest (Graph + Temporal) | 11 | 0.0121 [0.0081, 0.0193] | 0.0079 [0.0352, 0.0862] | 0.7978 | 0.0113 | 0.2870 | 0.0217 | 0.9786 | 0.0042 | 34.71% |
| **E4** | Isolation Forest (Full GraphFin) | 19 | 0.0149 [0.0090, 0.0321] | 0.0087 [0.0381, 0.1002] | 0.8087 | 0.0556 | 0.0093 | 0.0159 | 0.9990 | 0.0062 | 41.61% |
| **E5** | Isolation Forest (Egonet + Circular) | 4 | 0.0099 [0.0057, 0.0241] | 0.0008 [0.0043, 0.0065] | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.9992 | 0.0091 | 91.92% |

### Direction A Target Precision@K Metrics

| Exp | P@10 | P@25 | P@50 | P@100 |
|---|---|---|---|---|
| **E0** | 0.0000 | 0.0400 | 0.0400 | 0.0200 |
| **E1** | 0.0000 | 0.0400 | 0.0200 | 0.0200 |
| **E2** | 0.0000 | 0.0400 | 0.0400 | 0.0200 |
| **E3** | 0.0000 | 0.0000 | 0.0200 | 0.0100 |
| **E4** | 0.0000 | 0.0400 | 0.0200 | 0.0100 |
| **E5** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

---

## Direction B: PaySim -> IBM AML (Large) Transfer Performance

Source: **PaySim** (434,649 entities, ID: `e8d9c7b6-a5f4-4e3d-b2c1-a09876543210`)  
Target: **IBM AML Large** (50,000 entities, ID: `03fb9ab0-4f42-4404-9d76-723fd4d8753e`)

| Exp | Method | Feat Count | Source PR-AUC [95% CI] | Target PR-AUC [95% CI] | Target ROC-AUC | Target Precision | Target Recall | Target F1 | Target Accuracy | Abs Degradation | Rel Degradation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **E0** | Statistical z-score | 6 | 0.0134 [0.0484, 0.1403] | 0.0120 [0.0073, 0.0304] | 0.5186 | 0.0289 | 0.0955 | 0.0444 | 0.9419 | 0.0014 | 10.45% |
| **E1** | Isolation Forest (Graph) | 6 | 0.0105 [0.0445, 0.1170] | 0.0133 [0.0087, 0.0225] | 0.5750 | 0.0520 | 0.0327 | 0.0401 | 0.9702 | -0.0028 | -26.67% |
| **E2** | Isolation Forest (Graph + Behavioral) | 14 | 0.0114 [0.0471, 0.1269] | 0.0117 [0.0082, 0.0174] | 0.5513 | 0.0000 | 0.0000 | 0.0000 | 0.9735 | -0.0003 | -2.63% |
| **E3** | Isolation Forest (Graph + Temporal) | 11 | 0.0103 [0.0410, 0.1095] | 0.0133 [0.0088, 0.0225] | 0.5756 | 0.0518 | 0.0327 | 0.0401 | 0.9702 | -0.0030 | -29.13% |
| **E4** | Isolation Forest (Full GraphFin) | 19 | 0.0129 [0.0517, 0.1425] | 0.0124 [0.0084, 0.0196] | 0.5620 | 0.0242 | 0.0075 | 0.0115 | 0.9721 | 0.0005 | 3.88% |
| **E5** | Isolation Forest (Egonet + Circular) | 4 | 0.0008 [0.0043, 0.0065] | 0.0050 [0.0040, 0.0062] | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.9735 | -0.0042 | -525.00% |

### Direction B Target Precision@K Metrics

| Exp | P@10 | P@25 | P@50 | P@100 |
|---|---|---|---|---|
| **E0** | 0.1000 | 0.0400 | 0.0200 | 0.0100 |
| **E1** | 0.0000 | 0.0000 | 0.0000 | 0.0300 |
| **E2** | 0.0000 | 0.0000 | 0.0200 | 0.0100 |
| **E3** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **E4** | 0.0000 | 0.0000 | 0.0200 | 0.0200 |
| **E5** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
