# IBM AML Research Dataset Fixtures

This directory contains permanent, reproducible real-data fixtures derived from the Kaggle dataset:
**"IBM Transactions for Anti-Money Laundering (AML)"** (HI-Small variant, generated via IBM's AMLSim / AMLworld simulator).

These fixtures are locked in place for the final E0–E4 research benchmark evaluation of GraphFin.

---

## 1. Dataset Generation Commands

Both fixtures were generated deterministically using [`backend/scripts/convert_ibm_aml.py`](file:///backend/scripts/convert_ibm_aml.py) with random seed `42`.

### Medium Real Tier (5,000 Accounts)
```bash
python backend/scripts/convert_ibm_aml.py \
  --input /path/to/HI-Small_Trans.csv \
  --output-tx data/research/ibm_aml_medium_5k.csv \
  --output-labels data/research/ibm_aml_medium_5k_labels.csv \
  --sample-accounts 5000 \
  --seed 42 \
  --chunksize 100000
```
- **Raw Rows Processed**: 5,078,345
- **Transactions Written**: 31,463
- **Unique Accounts**: 5,000
- **Ground-Truth Positive Accounts (Is Laundering = 1)**: 20
- **Ground-Truth Negative Accounts (Is Laundering = 0)**: 4,980
- **Empirical Prevalence**: 0.4000%
- **Contamination Parameter for Isolation Forest**: `0.004` (20 / 5,000)

### Large Real Tier (50,000 Accounts Target / 49,992 Graph Accounts)
```bash
python backend/scripts/convert_ibm_aml.py \
  --input /path/to/HI-Small_Trans.csv \
  --output-tx data/research/ibm_aml_large_50k.csv \
  --output-labels data/research/ibm_aml_large_50k_labels.csv \
  --sample-accounts 50000 \
  --seed 42 \
  --chunksize 100000
```
- **Raw Rows Processed**: 5,078,345
- **Transactions Written**: 353,860
- **Sampled Accounts in File**: 50,000 (249 positive, 49,751 negative)
- **Ingested Graph Accounts**: 49,992 (249 positive, 49,743 negative)
- **Empirical Prevalence**: 0.4981% (~0.498%)
- **Contamination Parameter for Isolation Forest**: `0.005` (249 / 49,992)

#### Explanation of 49,992 Accounts Count
In the raw 50k transaction output, 10 transactions had sub-cent fractional cryptocurrency amounts that rounded to `$0.00`. GraphFin's canonical preprocessing validation strictly enforces positive monetary values (`amount > 0`) and excludes zero-dollar transactions. Exactly 8 accounts participated exclusively in these 10 dropped transactions; all 8 had negative labels (`label = 0`). Consequently, GraphFin ingests exactly 353,850 valid transactions across 49,992 active accounts, preserving all 249 positive laundering accounts.

---

## 2. Methodological Specifications

1. **Composite Account Identifier**:
   Account strings in the IBM AML dataset are bank-local. To prevent false cross-bank entity collisions, composite keys are constructed: `sender_id = f"{From Bank}_{Account}"` and `receiver_id = f"{To Bank}_{Account.1}"`.
2. **Canonical Amount**:
   The `Amount Paid` column in originating currency is used to avoid foreign exchange approximation artifacts.
3. **"Any Involvement" Label Aggregation**:
   Transaction-level `Is Laundering` flags are aggregated to account-level labels: an account is assigned `label = 1` if it participates as either sender or receiver in at least one laundering transaction, and `0` otherwise.
4. **Self-Transfer Filtering**:
   Rows where `sender_id == receiver_id` are invalid cycles that do not represent inter-account edge flows and are excluded.
5. **Stratified Research Split**:
   All benchmark models are trained and evaluated on `research-split`: 70% train / 30% test stratified partition (`random_state = 42`).
