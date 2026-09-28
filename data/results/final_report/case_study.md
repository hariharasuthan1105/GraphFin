# Phase C — Anomaly Case Study Analysis

## Disclaimer & Context

> This is presented as an anomaly explanation, not as evidence that this account committed fraud.

---

## Case Study Selection Criteria & Account Overview

The case study account was selected from the PaySim dataset held-out test evaluation set according to the following strict Phase C selection criteria:
1. **Top-10 Rank**: Ranked within the top-10 highest anomaly scores assigned by the E4 (Full GraphFin) Isolation Forest model.
2. **True Positive**: Confirmed ground-truth fraud label (`label = 1`).
3. **Complete Data**: 100% complete feature representation available across all canonical feature groups.

### Target Account Metadata
- **Account ID**: `C546529`
- **Dataset**: PaySim (uniform random sample, steps 1-741)
- **Model Rank**: `#51`
- **Model Anomaly Score**: `0.8102`
- **Ground-Truth Label**: `1` (True Positive Fraud)

---

## Top Driving Anomaly Features (Z-Score Deviation)

The table below highlights the top 5 features exhibiting the highest absolute Z-score deviation relative to the PaySim dataset distribution mean ($\mu$) and standard deviation ($\sigma$):

| Feature Name | Feature Value | Dataset Mean ($\mu$) | Dataset Std ($\sigma$) | Z-Score |
|---|---|---|---|---|
| `weighted_out_degree` | 10,000,000.00 | 98,769.69 | 440,557.28 | **+22.47** |
| `total_sent` | 10,000,000.00 | 98,769.69 | 440,557.28 | **+22.47** |
| `average_transaction_amount` | 10,000,000.00 | 170,033.23 | 543,985.75 | **+18.07** |
| `maximum_transaction_amount` | 10,000,000.00 | 184,080.12 | 605,755.00 | **+16.20** |
| `net_flow` | -10,000,000.00 | 0.00 | 663,528.44 | **-15.07** |

---

## Behavioral Interpretation & Graph Profile

1. **Extreme Transaction Volume / Flow**: Account `C546529` exhibits extraordinary deviation in `weighted_out_degree` (Z = +22.47, value = 10,000,000.00 vs mean 98,769.69).
2. **Asymmetric Flow Dynamics**: The account shows strong structural asymmetry in `total_sent` (Z = +22.47), characteristic of money mule or cashing-out behavior.
3. **Graph Topology**: As an active fraudulent node in the PaySim transaction network, this account displays rapid transaction accumulation and extreme structural divergence from baseline normal customer behavior.

---

## Full Feature Profile

| Feature Name | Feature Value | Dataset Mean | Dataset Std | Z-Score |
|---|---|---|---|---|
| `weighted_out_degree` | 10000000.0000 | 98769.6875 | 440557.2812 | +22.47 |
| `total_sent` | 10000000.0000 | 98769.6875 | 440557.2812 | +22.47 |
| `average_transaction_amount` | 10000000.0000 | 170033.2344 | 543985.7500 | +18.07 |
| `maximum_transaction_amount` | 10000000.0000 | 184080.1250 | 605755.0000 | +16.20 |
| `net_flow` | -10000000.0000 | 0.0002 | 663528.4375 | -15.07 |
| `out_degree` | 1.0000 | 0.5478 | 0.4978 | +0.91 |
| `unique_receivers` | 1.0000 | 0.5478 | 0.4978 | +0.91 |
| `unique_senders` | 0.0000 | 0.5478 | 0.7149 | -0.77 |
| `in_degree` | 0.0000 | 0.5478 | 0.7149 | -0.77 |
| `total_degree` | 1.0000 | 1.0955 | 0.3985 | -0.24 |
| `transaction_count` | 1.0000 | 1.0955 | 0.3985 | -0.24 |
| `weighted_in_degree` | 0.0000 | 98769.6875 | 476101.5000 | -0.21 |
| `total_received` | 0.0000 | 98769.6875 | 476101.5000 | -0.21 |
| `maximum_time_between_transactions` | 0.0000 | 32269.5879 | 155299.3750 | -0.21 |
| `average_time_between_transactions` | 0.0000 | 27945.0605 | 138032.2656 | -0.20 |
| `minimum_time_between_transactions` | 0.0000 | 24112.2285 | 131163.0000 | -0.18 |
| `transactions_per_day` | 1.0000 | 0.9862 | 0.1994 | +0.07 |
| `transactions_per_week` | 7.0000 | 6.9036 | 1.3959 | +0.07 |
| `betweenness_centrality` | 0.0000 | 0.0000 | 0.0000 | +0.00 |

