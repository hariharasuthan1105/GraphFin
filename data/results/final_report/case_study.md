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
- **Account ID**: `C2094777811`
- **Dataset**: PaySim (300K transaction slice)
- **Model Rank**: `#7` out of 130,395 test evaluation accounts
- **Model Anomaly Score**: `0.8113`
- **Ground-Truth Label**: `1` (True Positive Fraud)

---

## Top Driving Anomaly Features (Z-Score Deviation)

The table below highlights the top 5 features exhibiting the highest absolute Z-score deviation relative to the PaySim dataset distribution mean ($\mu$) and standard deviation ($\sigma$):

| Feature Name | Feature Value | Dataset Mean ($\mu$) | Dataset Std ($\sigma$) | Z-Score |
|---|---|---|---|---|
| `weighted_in_degree` | \$17,246,114.00 | \$121,595.23 | \$759,506.56 | **+22.55** |
| `total_received` | \$17,246,114.00 | \$121,595.23 | \$759,506.56 | **+22.55** |
| `net_flow` | \$17,246,114.00 | \$0.0001 | \$822,102.13 | **+20.98** |
| `transactions_per_week` | 273.00 | 9.66 | 15.31 | **+17.21** |
| `transactions_per_day` | 39.00 | 1.38 | 2.19 | **+17.21** |

---

## Behavioral Interpretation & Graph Profile

1. **Extreme Inflow Volume**: Account `C2094777811` received a total of \$17,246,114.00 across 39 inbound transactions ($Z = +22.55$), placing it in the top 0.001% of all accounts by received volume.
2. **Asymmetric Flow (Mule / Money Laundering Destination)**: The account has `out_degree = 0` and `total_sent = $0.00`, resulting in a massive net flow imbalance ($Z = +20.98$).
3. **High Burst Frequency**: The account completed 39 transactions within a short temporal window (translating to 273 transactions/week equivalent rate, $Z = +17.21$), significantly higher than the average account activity of ~1.38 transactions.

---

## Full Feature Profile

| Feature Name | Feature Value | Dataset Mean | Dataset Std | Z-Score |
|---|---|---|---|---|
| `weighted_in_degree` | 17246114.0000 | 121595.2266 | 759506.5625 | +22.55 |
| `total_received` | 17246114.0000 | 121595.2266 | 759506.5625 | +22.55 |
| `net_flow` | 17246114.0000 | 0.0001 | 822102.1250 | +20.98 |
| `transactions_per_week` | 273.0000 | 9.6630 | 15.3056 | +17.21 |
| `transactions_per_day` | 39.0000 | 1.3804 | 2.1865 | +17.21 |
| `total_degree` | 39.0000 | 1.3804 | 2.1865 | +17.21 |
| `transaction_count` | 39.0000 | 1.3804 | 2.1865 | +17.21 |
| `unique_senders` | 39.0000 | 0.6902 | 2.3494 | +16.31 |
| `in_degree` | 39.0000 | 0.6902 | 2.3494 | +16.31 |
| `maximum_transaction_amount` | 3310206.7500 | 163928.7344 | 324678.3750 | +9.69 |
| `maximum_time_between_transactions` | 7200.0000 | 358.0544 | 1762.8599 | +3.88 |
| `out_degree` | 0.0000 | 0.6902 | 0.4625 | -1.49 |
| `unique_receivers` | 0.0000 | 0.6902 | 0.4625 | -1.49 |
| `average_time_between_transactions` | 1326.3199 | 164.8994 | 909.8058 | +1.28 |
| `average_transaction_amount` | 442208.0625 | 140548.8594 | 264398.1875 | +1.14 |
| `weighted_out_degree` | 0.0000 | 121595.2266 | 263497.5938 | -0.46 |
| `total_sent` | 0.0000 | 121595.2266 | 263497.5938 | -0.46 |
| `minimum_time_between_transactions` | 0.0000 | 57.8204 | 677.5627 | -0.09 |
| `betweenness_centrality` | 0.0000 | 0.0000 | 0.0000 | 0.00 |
