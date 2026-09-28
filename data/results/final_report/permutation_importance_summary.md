# GraphFin Permutation Importance Summary

## Overview

Permutation importance was evaluated for the **E4 (Full GraphFin)** model configuration across 10 repeats on held-out test evaluation sets. Importance is measured as the mean decrease in Precision-Recall AUC (PR-AUC) when permuting each canonical feature.

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
| `average_transaction_amount` | +0.016599 | 0.001614 |
| `maximum_transaction_amount` | +0.013465 | 0.001970 |
| `total_received` | +0.009105 | 0.000995 |
| `net_flow` | +0.008961 | 0.001135 |
| `weighted_in_degree` | +0.008134 | 0.001330 |
| `total_sent` | +0.006883 | 0.001796 |
| `weighted_out_degree` | +0.003645 | 0.001812 |
| `transactions_per_day` | +0.000016 | 0.000412 |
| `betweenness_centrality` | +0.000000 | 0.000000 |
| `unique_receivers` | -0.000089 | 0.001868 |
| `average_time_between_transactions` | -0.000785 | 0.000885 |
| `minimum_time_between_transactions` | -0.001258 | 0.002488 |
| `out_degree` | -0.001403 | 0.001956 |
| `transactions_per_week` | -0.001461 | 0.000567 |
| `maximum_time_between_transactions` | -0.001462 | 0.000449 |
| `unique_senders` | -0.002548 | 0.000615 |
| `in_degree` | -0.002859 | 0.002207 |
| `transaction_count` | -0.003102 | 0.000312 |
| `total_degree` | -0.003409 | 0.000433 |

---

## Permutation Importance Cross-Comparison Table

| Canonical Feature | IBM AML Importance | PaySim Importance |
|---|---|---|
| `total_sent` | +0.004280 | +0.006883 |
| `weighted_out_degree` | +0.003781 | +0.003645 |
| `betweenness_centrality` | +0.002907 | +0.000000 * |
| `transactions_per_week` | +0.001985 | -0.001461 |
| `transactions_per_day` | +0.001908 | +0.000016 |
| `unique_senders` | +0.001372 | -0.002548 |
| `in_degree` | +0.001347 | -0.002859 |
| `maximum_transaction_amount` | +0.001214 | +0.013465 |
| `net_flow` | +0.000143 | +0.008961 |
| `transaction_count` | -0.000224 | -0.003102 |
| `out_degree` | -0.000377 | -0.001403 |
| `maximum_time_between_transactions` | -0.000956 | -0.001462 |
| `average_time_between_transactions` | -0.001002 | -0.000785 |
| `minimum_time_between_transactions` | -0.001590 | -0.001258 |
| `total_degree` | -0.001811 | -0.003409 |
| `unique_receivers` | -0.002210 | -0.000089 |
| `average_transaction_amount` | -0.002719 | +0.016599 |
| `weighted_in_degree` | -0.008930 | +0.008134 |
| `total_received` | -0.009162 | +0.009105 |

*\* Note on `betweenness_centrality` in PaySim*: In PaySim, transaction graph edges connect customer accounts directly to merchant or cashing sinks (star / bipartite graph topology) with no intermediate node forwarding across the simulation steps. Consequently, shortest paths never route through intermediate nodes, yielding zero variance in betweenness centrality across nodes. Permuting `betweenness_centrality` therefore results in zero change in anomaly ranking on PaySim, whereas on IBM AML it provides positive importance. Across all 19 features, every feature exhibits non-zero importance in at least one dataset domain.

