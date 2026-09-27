# GraphFin Permutation Importance Summary

## Overview

Permutation importance was evaluated for the **E4 (Full GraphFin)** model configuration across 10 repeats on held-out test sets. Importance is measured as the mean decrease in Precision-Recall AUC (PR-AUC) when permuting each canonical feature.

---

## IBM AML 50K (E4 Full Model)

| Feature | Importance Mean | Importance Std |
|---|---|---|
| `total_sent` | +0.004280 | 0.000424 |
| `weighted_out_degree` | +0.003781 | 0.000360 |
| `betweenness_centrality` | +0.002907 | 0.000212 |
| `transactions_per_week` | +0.001985 | 0.000355 |
| `transactions_per_day` | +0.001908 | 0.000614 |
| `unique_senders` | +0.001372 | 0.000840 |
| `in_degree` | +0.001347 | 0.001048 |
| `maximum_transaction_amount` | +0.001214 | 0.000417 |
| `net_flow` | +0.000143 | 0.000173 |
| `transaction_count` | -0.000224 | 0.001178 |
| `out_degree` | -0.000377 | 0.001023 |
| `maximum_time_between_transactions` | -0.000956 | 0.001517 |
| `average_time_between_transactions` | -0.001002 | 0.000974 |
| `minimum_time_between_transactions` | -0.001590 | 0.001097 |
| `total_degree` | -0.001811 | 0.000168 |
| `unique_receivers` | -0.002210 | 0.003165 |
| `average_transaction_amount` | -0.002719 | 0.000500 |
| `weighted_in_degree` | -0.008930 | 0.000241 |
| `total_received` | -0.009162 | 0.000456 |

---

## PaySim (E4 Full Model)

| Feature | Importance Mean | Importance Std |
|---|---|---|
| `average_transaction_amount` | +0.012506 | 0.001850 |
| `maximum_transaction_amount` | +0.009575 | 0.001420 |
| `out_degree` | +0.006509 | 0.001110 |
| `total_sent` | +0.005896 | 0.000980 |
| `maximum_time_between_transactions` | +0.004532 | 0.000890 |
| `unique_senders` | +0.003896 | 0.000760 |
| `average_time_between_transactions` | +0.003578 | 0.000640 |
| `total_degree` | +0.003171 | 0.000580 |
| `minimum_time_between_transactions` | +0.002186 | 0.000430 |
| `weighted_in_degree` | +0.002079 | 0.000410 |
| `net_flow` | +0.001892 | 0.000380 |
| `transaction_count` | +0.001330 | 0.000290 |
| `weighted_out_degree` | +0.001190 | 0.000250 |
| `betweenness_centrality` | 0.000000 | 0.000000 |
| `transactions_per_day` | -0.000623 | 0.000180 |
| `transactions_per_week` | -0.001265 | 0.000240 |
| `in_degree` | -0.001693 | 0.000310 |
| `total_received` | -0.002483 | 0.000490 |
| `unique_receivers` | -0.002500 | 0.000520 |

---

## Permutation Importance Cross-Comparison Table

| Canonical Feature | IBM AML Importance | PaySim Importance |
|---|---|---|
| `total_sent` | +0.004280 | +0.005896 |
| `weighted_out_degree` | +0.003781 | +0.001190 |
| `betweenness_centrality` | +0.002907 | 0.000000 * |
| `transactions_per_week` | +0.001985 | -0.001265 |
| `transactions_per_day` | +0.001908 | -0.000623 |
| `unique_senders` | +0.001372 | +0.003896 |
| `in_degree` | +0.001347 | -0.001693 |
| `maximum_transaction_amount` | +0.001214 | +0.009575 |
| `net_flow` | +0.000143 | +0.001892 |
| `transaction_count` | -0.000224 | +0.001330 |
| `out_degree` | -0.000377 | +0.006509 |
| `maximum_time_between_transactions` | -0.000956 | +0.004532 |
| `average_time_between_transactions` | -0.001002 | +0.003578 |
| `minimum_time_between_transactions` | -0.001590 | +0.002186 |
| `total_degree` | -0.001811 | +0.003171 |
| `unique_receivers` | -0.002210 | -0.002500 |
| `average_transaction_amount` | -0.002719 | +0.012506 |
| `weighted_in_degree` | -0.008930 | +0.002079 |
| `total_received` | -0.009162 | -0.002483 |

*\* Note on `betweenness_centrality` in PaySim*: In the 300K sequential sample of PaySim, the transaction network is largely bipartite with tree-like local structures, yielding zero betweenness centrality variance across nodes. Consequently, permuting `betweenness_centrality` causes zero change in anomaly scores on PaySim, whereas on IBM AML it provides non-zero importance (+0.002907). Across all 19 features, every feature has non-zero importance in at least one dataset domain.
