# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

A research-driven platform combining graph-mining metrics with behavioral and temporal feature engineering to detect anomalous transactional patterns in financial networks.

---

## Project Overview & Current Status

GraphFin provides a controlled empirical framework for evaluating structural, behavioral, and temporal transaction representations. The repository currently includes:

- [x] **FastAPI Backend Pipeline** under `/api/v1` for datasets, graph analytics, feature engineering, model training, and evaluation.
- [x] **NetworkX Directed Weighted Graph Engine** computing in/out degrees, weighted amounts, and Brandes betweenness centrality.
- [x] **19-Dimensional Canonical GraphFin Representation** integrating 6 graph, 8 behavioral, and 5 temporal features.
- [x] **E0–E5 Anomaly Detection Suite** featuring rule-based statistical baselines, Isolation Forests across feature groups, and egonet/circular-flow metrics.
- [x] **IBM AML Benchmark Dataset Integration** (`HI-Small` subsamples: 5,000 and 49,992 accounts).
- [x] **PaySim Secondary Research Dataset Integration** (299,999 transactions, 547,686 unique accounts).
- [x] **Bidirectional Cross-Dataset Transfer Generalization (IBM AML $\leftrightarrow$ PaySim)** under a strict source-only fitting protocol.
- [x] **Rigorous Research Metrics**: 1,000-resample 95% Bootstrap Confidence Intervals, Precision@K ($P@10, P@25, P@50, P@100$), and standardized feature distribution shift ($\Delta \mu$).
- [x] **React Research Interface**: Interactive dashboard for dataset selection, graph exploration, feature analysis, anomaly scoring, and cross-dataset evaluation.
- [x] **Automated PaySim Integration Test Suite** (21 / 21 passing tests in `backend/tests/test_paysim_integration.py`).
- [x] **Multi-Jurisdiction Tax Analytics Module** (India AY 2026–27, US Federal 2026, UK & Scotland 2026–27, Germany 2026, France 2026).

---

## Research Architecture & Feature Representation

GraphFin transforms raw transaction streams into entity-level graph representations for anomaly scoring:

```
Transactions  ──>  Directed Weighted Graph  ──>  19-Dimensional Feature Schema  ──>  E0–E5 Anomaly Pipeline  ──>  Evaluation & Research Artifacts
```

### Canonical 19-Feature Schema

GraphFin enforces a strict 19-dimensional canonical feature schema across all datasets to ensure feature-level compatibility during cross-dataset evaluation:

1. **Graph Topological Features (6)**:
   - `in_degree`: Count of incoming transaction edges
   - `out_degree`: Count of outgoing transaction edges
   - `total_degree`: Total incident edge count (`in_degree + out_degree`)
   - `weighted_in_degree`: Total incoming transaction volume
   - `weighted_out_degree`: Total outgoing transaction volume
   - `betweenness_centrality`: Network flow centrality metric

2. **Behavioral Features (8)**:
   - `transaction_count`: Total number of transactions associated with account
   - `total_sent`: Cumulative value sent
   - `total_received`: Cumulative value received
   - `net_flow`: Net transfer balance (`total_received - total_sent`)
   - `average_transaction_amount`: Mean transfer size
   - `maximum_transaction_amount`: Peak transfer size
   - `unique_receivers`: Number of distinct counterparty destination accounts
   - `unique_senders`: Number of distinct counterparty source accounts

3. **Temporal Features (5)**:
   - `transactions_per_day`: Average daily transaction frequency
   - `transactions_per_week`: Average weekly transaction frequency
   - `average_time_between_transactions`: Mean inter-transaction interval (seconds)
   - `minimum_time_between_transactions`: Shortest inter-transaction interval (seconds)
   - `maximum_time_between_transactions`: Longest inter-transaction interval (seconds)

---

## Research Experiment Matrix

| Experiment | Features | Method | Description |
|---|---|---|---|
| **E0** | Graph Baseline (6) | Statistical (z-score) | Non-ML baseline using rule-based z-score thresholding ($\ge 2.0\sigma$) on source-fitted graph topology metrics. |
| **E1** | Graph Only (6) | Isolation Forest | Unsupervised Isolation Forest trained exclusively on 6 graph topological features. |
| **E2** | Graph + Behavioral (14) | Isolation Forest | Unsupervised Isolation Forest combining graph topology with 8 user behavioral statistics. |
| **E3** | Graph + Temporal (11) | Isolation Forest | Unsupervised Isolation Forest combining graph topology with 5 temporal interval metrics. |
| **E4** | Full GraphFin (19) | Isolation Forest | Comprehensive feature fusion combining all 19 canonical graph, behavioral, and temporal features (default model). |
| **E5** | Reduced Egonet + Circular Flow | Isolation Forest | Topology-focused model using 1-hop egonet structure (`egonet_node_count`, `egonet_edge_count`, `egonet_density`) and 2/3-step circular flow indicators. |

---

## Research Dataset: PaySim

PaySim is integrated as a secondary research benchmark to evaluate model transferability and domain generalizability.

### Dataset Specifications
- **Dataset**: PaySim (Secondary Research Benchmark)
- **Raw Data Location**: `data/research/paysim_transactions.csv`
- **Transactions Loaded**: 299,999
- **Unique Account Universe**: 547,686 accounts (unique senders and receivers)
- **Fraud-Labelled Transactions**: 181 (`isFraud == 1` in loaded transactions)
- **Positive Accounts**: 480 accounts (derived via the ground-truth Any-Involvement rule)
- **Label Provenance File**: `data/research/paysim_labels.csv`

### Feature Ingestion & Leakage Prevention Protocol
GraphFin ingests the following raw fields from PaySim:
- `step`: Simulated time index (converted deterministically to UTC timestamp)
- `nameOrig`: Sender account ID
- `nameDest`: Receiver account ID
- `amount`: Transaction value
- `isFraud`: Ground-truth label (used **strictly** for evaluation, never as an input feature)

> [!IMPORTANT]
> **Data Leakage Prevention**:
> The raw PaySim fields `oldbalanceOrg`, `newbalanceOrig`, `oldbalanceDest`, `newbalanceDest`, and `isFlaggedFraud` are **strictly excluded** from GraphFin feature engineering. No balance data is incorporated into anomaly scoring vectors.

### Time Conversion Mapping
PaySim's `step` column represents 1-hour time steps. GraphFin converts `step` using a deterministic base timestamp:
$$\text{timestamp} = \text{2023-01-01 00:00:00 UTC} + \text{step hours}$$

- `step = 0` $\rightarrow$ `2023-01-01 00:00:00 UTC`
- `step = 1` $\rightarrow$ `2023-01-01 01:00:00 UTC`

*Note: PaySim step values reflect simulated time steps and are not wall-clock timestamps.*

---

## Betweenness Centrality Strategy

Betweenness centrality measures an account's role in intermediary financial flows using NetworkX Brandes algorithm:
- **Small Networks ($\le 2,000$ nodes)**: Exact Brandes betweenness centrality (`normalized=True`).
- **Large Networks ($> 2,000$ nodes)**: Sampled Brandes approximation ($k=500$ sample size, $k=100$ if $> 50,000$ nodes, `seed=42`, `normalized=True`) to maintain computational safety.

---

## Cross-Dataset Transfer Generalization Protocol

GraphFin evaluates cross-dataset transfer generalization across distinct transaction domain distributions (IBM AML $\leftrightarrow$ PaySim) under a strict protocol:

1. **Source-Only Model & Preprocessing Fitting**:
   - Isolation Forest models and `StandardScaler` parameters ($\mu, \sigma$) are fit **strictly** on the source dataset.
   - Target dataset feature vectors are normalized using source mean and standard deviation.
   - Target ground-truth labels are used **only** for final test evaluation; no target tuning or threshold adaptation occurs.

2. **Any-Involvement Account Labeling Rule**:
   - An account is designated positive ($y=1$) if involved as sender or receiver in at least one transaction where `isFraud == 1`.

3. **Evaluation Metrics & Bootstrap Confidence Intervals**:
   - **Metrics**: PR-AUC, ROC-AUC, Precision, Recall, F1, Precision@K ($P@10, P@25, P@50, P@100$).
   - **Relative Degradation Formula**:
     $$\text{Relative Degradation} = \frac{\text{PR-AUC}_{\text{source}} - \text{PR-AUC}_{\text{target}}}{\text{PR-AUC}_{\text{source}}}$$
   - **Bootstrap CIs**: 1,000-resample 95% percentile confidence intervals (`random_state=42`).

---

## Empirical Cross-Dataset Transfer Results

Results from the empirical transfer experiments stored in `data/results/cross_dataset/`:

### Direction A: IBM AML $\rightarrow$ PaySim
*Source: IBM AML (50,000 accounts) $\mid$ Target: PaySim (547,686 accounts)*

| Exp | Method | Source PR-AUC (95% CI) | Target PR-AUC (95% CI) | Target ROC-AUC | Rel. Degradation | P@10 | P@25 | P@50 | P@100 |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **E0** | Statistical Baseline | 0.0116 (0.0081–0.0214) | 0.0018 (0.0017–0.0027) | 0.5787 | +84.48% | 0.00 | 0.00 | 0.00 | 0.00 |
| **E1** | Graph (Isolation Forest) | 0.0222 (0.0101–0.0555) | 0.0081 (0.0059–0.0114) | 0.7697 | +63.51% | 0.00 | 0.00 | 0.00 | 0.00 |
| **E2** | Graph + Behavioral | 0.0173 (0.0094–0.0449) | 0.0091 (0.0066–0.0133) | 0.7730 | +47.40% | 0.00 | 0.00 | 0.00 | 0.00 |
| **E3** | Graph + Temporal | 0.0121 (0.0079–0.0196) | 0.0043 (0.0032–0.0098) | 0.7464 | +64.46% | 0.10 | 0.04 | 0.02 | 0.02 |
| **E4** | Full GraphFin (19-feat) | 0.0149 (0.0088–0.0313) | 0.0053 (0.0037–0.0107) | 0.7564 | +64.43% | 0.10 | 0.04 | 0.04 | 0.03 |
| **E5** | Egonet + Circular Flow | 0.0099 (0.0065–0.0251) | 0.0014 (0.0012–0.0019) | 0.5000 | N/A* | 0.00 | 0.00 | 0.00 | 0.00 |

*\*E5 baseline on PaySim is degenerate (target ROC-AUC = 0.5000).*

### Direction B: PaySim $\rightarrow$ IBM AML
*Source: PaySim (547,686 accounts) $\mid$ Target: IBM AML (50,000 accounts)*

| Exp | Method | Source PR-AUC (95% CI) | Target PR-AUC (95% CI) | Target ROC-AUC | Rel. Degradation | P@10 | P@25 | P@50 | P@100 |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **E0** | Statistical Baseline | 0.0065 (0.0047–0.0110) | 0.0128 (0.0088–0.0237) | 0.7187 | −96.92% | 0.10 | 0.04 | 0.02 | 0.01 |
| **E1** | Graph (Isolation Forest) | 0.0077 (0.0056–0.0106) | 0.0136 (0.0092–0.0317) | 0.7453 | −76.62% | 0.10 | 0.08 | 0.04 | 0.02 |
| **E2** | Graph + Behavioral | 0.0091 (0.0066–0.0132) | 0.0119 (0.0082–0.0186) | 0.7377 | −30.77% | 0.00 | 0.00 | 0.02 | 0.03 |
| **E3** | Graph + Temporal | 0.0054 (0.0041–0.0077) | 0.0155 (0.0105–0.0277) | 0.7281 | −187.04% | 0.00 | 0.00 | 0.00 | 0.02 |
| **E4** | Full GraphFin (19-feat) | 0.0093 (0.0065–0.0145) | 0.0133 (0.0093–0.0289) | 0.7448 | −43.01% | 0.00 | 0.04 | 0.04 | 0.03 |
| **E5** | Egonet + Circular Flow | 0.0014 (0.0012–0.0019) | 0.0050 (0.0040–0.0086) | 0.7300 | −257.14% | 0.00 | 0.00 | 0.00 | 0.00 |

---

## Research Artifacts

The empirical cross-dataset evaluation artifacts are saved in structured JSON formats separate from locked benchmark results:
- `data/results/cross_dataset/ibm_to_paysim_transfer.json`
- `data/results/cross_dataset/paysim_to_ibm_transfer.json`

Each artifact details the full reproducibility manifest, random seeds, bootstrap CI distributions, confusion matrices, and feature shift statistics.

---

## Automated Test Suite

PaySim integration correctness is verified via an automated test suite:
- **PaySim Integration Tests**: **21 / 21 Passing** (`pytest backend/tests/test_paysim_integration.py -v`)
- **Key Test Coverage**:
  - Dataset registration and alias mapping
  - Required column validation and time conversion
  - Account label derivation under the any-involvement rule
  - Exact 19-feature schema ordering and balance field exclusion
  - Deterministic feature generation & Brandes betweenness approximation
  - Source-only model fitting & target label isolation
  - Precision@K calculation & 95% bootstrap reproducibility
  - Correct relative degradation sign calculation
  - Immutability of locked IBM research benchmark results

---

## Methodological Disclosures & Research Notice

> [!IMPORTANT]
> **Research Notice**:
> GraphFin includes completed empirical within-dataset IBM AML evaluation and bidirectional IBM AML $\leftrightarrow$ PaySim cross-dataset transfer experiments. Results are stored as reproducible research artifacts under `data/results/`. These experiments use synthetic benchmark datasets and should not be interpreted as evidence of production fraud detection or legal fraud determination.

1. **Relative Presentation Risk Score (0–100)**: The risk score is a relative ranking score derived from normalized anomaly outputs. It is **not** a calibrated probability of fraud.
2. **Synthetic Data Characteristics**: Both IBM AMLSim and PaySim are synthetic agent-based financial simulation benchmarks.
3. **Transductive Graph Feature Construction**: Graph features are derived from the full transaction network prior to entity-level train/test splitting; this protocol evaluates entity-level held-out generalization rather than fully isolated inductive graph learning.
4. **Cross-Dataset Generalization Scope**: Transfer experiments quantify cross-distribution performance degradation between synthetic benchmark datasets and do not guarantee performance on unseen real-world banking systems.

---

## Multi-Jurisdiction Tax Analytics Module

GraphFin includes a jurisdiction-aware tax analytics engine supporting **India**, **United States**, **United Kingdom & Scotland**, **Germany**, and **France**.

> [!IMPORTANT]
> **Strict Boundary Notice**:
> The tax analytics module operates strictly from explicitly classified income inputs. A transaction between accounts is not automatically treated as taxable income.

### Supported Jurisdictions & Tax Regimes
1. **India (`IN`)**: Assessment Year 2026–27 New Tax Regime (Slabs: 0%, 5%, 10%, 15%, 20%, 25%, 30%), Section 87A rebate & marginal relief, Surcharge, 4% Cess. Official source: Income Tax Department (`incometax.gov.in`).
2. **United States (`US`)**: Tax Year 2026 IRS Federal Income Tax for `single`, `married_joint`, `married_separate`, and `head_of_household`. Official source: Internal Revenue Service (`irs.gov`).
3. **United Kingdom (`GB`)**: Tax Year 2026–27 for England, Wales, Northern Ireland, and Scotland (6-band regime). Personal Allowance tapering above £100,000. Official source: HMRC (`gov.uk`).
4. **Germany (`DE`)**: Tax Year 2026 progressive formula, Grundfreibetrag (€12,096), Solidaritätszuschlag, and Church Tax options. Official source: BMF (`bundesfinanzministerium.de`).
5. **France (`FR`)**: Tax Year 2026 Barème de l'impôt (0%–45%) with Quotient Familial. Official source: DGFiP (`impots.gouv.fr`).

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Run Test Suite
```bash
# Run PaySim integration tests
pytest backend/tests/test_paysim_integration.py -v

# Run complete backend test suite
pytest backend/tests -v
```

### 3. Start Backend Server
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive OpenAPI documentation: `http://127.0.0.1:8000/docs`

### 4. Start Frontend Interface
```bash
cd frontend
npm install
npm run dev
```
Interactive dashboard: `http://localhost:5173`
