# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

A research-driven system that combines graph-mining metrics with behavioral and temporal feature engineering to detect anomalous transactional patterns in financial networks.

---

## Current Status: Milestone 2+ (ML Anomaly Detection & Research Evaluation Complete)

- [x] **FastAPI Backend Pipeline** under `/api/v1`
- [x] **Canonical Transaction Validation** (amounts, timestamps, duplicate IDs, self-transfers)
- [x] **NetworkX Directed Weighted Graph Engine** (in/out degree, weighted degrees, betweenness centrality)
- [x] **Behavioral & Temporal Feature Extraction** (19 statistical and interval features)
- [x] **Interactive REST APIs & OpenAPI Docs** (`/health`, `/transactions`, `/graph`, `/analytics`, `/anomalies`, `/datasets`, `/evaluation`)
- [x] **Multi-Experiment Model Persistence** (coexisting Baseline, E1, E2, E3, E4 models per dataset)
- [x] **Non-ML Statistical Baseline** (rule-based z-score thresholding on graph topology)
- [x] **Isolation Forest ML Anomaly Detection Layer** (dynamic feature group slicing: Graph, Behavioral, Temporal)
- [x] **Relative Presentation Risk Scoring (0-100)** & Explainability Reason Codes
- [x] **Ground-Truth Label Ingestion & Evaluation Layer** (`/datasets/{dataset_id}/labels`)
- [x] **Research Evaluation Layer** (Precision, Recall, F1, Accuracy, ROC-AUC, and headline PR-AUC via `/evaluation/{dataset_id}/compare`)
- [x] **Automated Pytest Test Suite** (100% passing tests: 75/75 tests)
- [x] **Multi-Jurisdiction Tax Analytics Module** (India AY 2026–27, US Federal 2026, UK & Scotland 2026–27, Germany 2026, France 2026)
- [ ] *Milestone 3 (Day 3): Subgraph Pattern Detection & Anomaly Explanation*
- [ ] *Milestone 4 (Day 4): Frontend Dashboard & Visualization*

### Research Experiment Matrix

| Experiment | Features | Method | Description |
|---|---|---|---|
| **Baseline** | Graph | Statistical (z-score, no ML) | Rule-based z-score threshold ($\ge 2.0\sigma$) across graph topology metrics. |
| **E1** | Graph | Isolation Forest | Unsupervised IF trained purely on graph topological metrics (6 features). |
| **E2** | Graph + Behavioral | Isolation Forest | Unsupervised IF combining graph metrics with user transaction statistics (14 features). |
| **E3** | Graph + Temporal | Isolation Forest | Unsupervised IF combining graph metrics with burst and interval metrics (11 features). |
| **E4** | Graph + Behavioral + Temporal | Isolation Forest | Comprehensive feature fusion combining all three groups (19 features, default). |

> [!IMPORTANT]
> The 0–100 score is a relative presentation/ranking score derived from model output.
> It is NOT a calibrated probability of fraud.
> It must not be interpreted as a percentage probability that an account is fraudulent.

> [!IMPORTANT]
> **Research Notice: Pipeline Validation vs. Research Benchmark Results**
> Current experimental runs and metrics produced in this test/development environment serve as **pipeline validation** demonstrating end-to-end architectural, algorithmic, and evaluation correctness. They do NOT represent paper-ready or final research benchmark results. The final IEEE research paper results must be computed using an appropriately sized real or public financial transaction dataset (e.g. Elliptic, PaySim, or real banking networks) with genuine ground-truth labels.

### Evaluation Modes: In-Sample vs. Held-Out

The GraphFin research platform supports two evaluation protocols:

| Mode | Target Entities | Fit Population | Purpose |
|---|---|---|---|
| **`in_sample`** | All labeled entities in dataset | Full dataset feature matrix | Pipeline validation on the full feature population, upper-bound calibration, and sanity-checking model training without partition constraints. |
| **`held_out`** | Test partition entities only | Train partition feature matrix only | Entity-level held-out evaluation where the Isolation Forest/baseline is fit on the training entity rows and evaluated on the test entity rows. |

#### Why Held-Out Evaluation Matters
1. **Preventing Over-Optimistic Performance**: In-sample evaluation evaluates models on the identical distribution and entities used to build the tree structures or baseline statistics. This can dramatically overstate detection capability.
2. **Reviewer Skepticism**: Academic reviewers rightfully question fraud detection papers reporting purely in-sample numbers. Reporting both modes transparently demonstrates why feature engineering choices matter on unseen entities.
3. **Entity-Level Out-of-Sample Evaluation**: In real-world financial systems, anomaly detectors must identify suspicious behavior from accounts not present during model fitting.

#### Entity-Level Splitting & Partitioning Protocol

> [!NOTE]
> - No label leakage and no test-row leakage during model fitting under the entity-level held-out evaluation protocol.
> - Graph features are currently derived from the full transaction network before the entity-level split; therefore this is not a completely isolated inductive graph-learning evaluation.

- **Entity-Level Partitioning**: Financial anomaly detection operates on user/account-level feature vectors. Transactions are grouped at the account level; an entity belongs entirely to either the train set or the test set.
- **Fit-Time Isolation**: In held-out mode, the Isolation Forest ensemble and baseline parameters (mean, standard deviation) are fit **strictly** on the train partition (`X_train`). Test-set user features are evaluated strictly at scoring time.
- **Explainability Isolation**: The empirical percentile reference distribution (`feature_stats`: p10, p50, p90, min, max, mean) for reason codes is computed solely from the train partition, preventing reference distribution leakage into explanations.
- **Stratified Partitioning**: Splits are stratified by ground-truth labels (fraud vs. normal) where classes have $\ge 2$ instances, ensuring the test set preserves realistic class imbalance, falling back gracefully with documented warnings when sample counts are limited.

### Research Evaluation Protocol

1. **Upload Transactions**: `POST /api/v1/transactions/upload`
2. **Upload Genuine Labels**: `POST /api/v1/datasets/{dataset_id}/labels`
3. **(Optional) Create Entity Split**: `POST /api/v1/datasets/{dataset_id}/splits` with `{"split_label": "default", "test_size": 0.3, "stratify_by_label": true}`
4. **Train All Configurations**:
   - In-Sample: `POST /api/v1/anomalies/{dataset_id}/train` with `{"experiment_label": "e4_insample"}`
   - Held-Out: `POST /api/v1/anomalies/{dataset_id}/train` with `{"experiment_label": "e4_heldout", "split_label": "default"}`
5. **Evaluate Each Experiment**: `GET /api/v1/evaluation/{dataset_id}/{experiment_label}` (automatically detects `evaluation_mode`)
6. **Compare PR-AUC**: `GET /api/v1/evaluation/{dataset_id}/compare` (ranked by PR-AUC, cleanly grouped via `by_evaluation_mode`)
7. **Inspect ROC & PR Curves**: `GET /api/v1/evaluation/{dataset_id}/compare?include_curves=true`
8. **Export Research Artifacts**: `POST /api/v1/evaluation/{dataset_id}/export` (exports JSON and CSV to `data/results/`)

---

## Multi-Jurisdiction Tax Analytics Module

GraphFin includes a jurisdiction-aware tax analytics module supporting **India**, **United States**, **United Kingdom & Scotland**, **Germany**, and **France**.

> [!IMPORTANT]
> **Strict Boundary Notice**:
> GraphFin's tax analytics module provides jurisdiction-specific estimates. It does NOT infer taxable income from raw transaction volume. A transaction between two accounts is NOT automatically income.
> The tax module operates strictly from explicitly classified income inputs.

### Supported Jurisdictions & Tax Regimes
1. **India (`IN`)**: Assessment Year 2026–27 New Tax Regime (Slabs: 0%, 5%, 10%, 15%, 20%, 25%, 30%), Section 87A rebate & marginal relief, Surcharge, 4% Cess (`IN-AY2026-27-v1`). Official source: Income Tax Department (`incometax.gov.in`).
2. **United States (`US`)**: Tax Year 2026 IRS Federal Income Tax (`US-2026-v1`) for `single`, `married_joint`, `married_separate`, and `head_of_household`. Includes 2026 standard deductions ($16,100 / $32,200 / $24,150). State tax is federal-only unless explicitly selected. Official source: Internal Revenue Service (`irs.gov`).
3. **United Kingdom (`GB`)**: Tax Year 2026–27 (`GB-2026-27-v1`) for England, Wales, Northern Ireland, and Scotland (Scottish 6-band regime). Includes Personal Allowance (£12,570) and £1-for-£2 tapering above £100,000 adjusted net income. Official source: HMRC (`gov.uk`).
4. **Germany (`DE`)**: Tax Year 2026 (`DE-2026-v1`). Grundfreibetrag (€12,096), progressive Einkommensteuer formula, Solidarity Surcharge (Solidaritätszuschlag), and optional Church Tax (Kirchensteuer 8%/9%). Official source: BMF (`bundesfinanzministerium.de`).
5. **France (`FR`)**: Tax Year 2026 (`FR-2026-v1`). Progressive Barème de l'impôt sur le revenu (0%, 11%, 30%, 41%, 45%) with Quotient Familial parts support. Official source: DGFiP (`impots.gouv.fr`).

### API Endpoints
- `POST /api/v1/tax/calculate` — Calculate estimated income tax liability
- `GET /api/v1/tax/jurisdictions` — List supported tax jurisdictions
- `GET /api/v1/tax/rules/{jurisdiction}/{tax_year}` — Fetch official tax rule metadata and bracket definition

---

## Benchmark Datasets: IBM AMLSim (`bank_mixed` v2.1)

GraphFin includes a dedicated, memory-safe adapter (`AMLSimAdapter`) for ingesting and evaluating the IBM AMLSim multi-bank synthetic transaction benchmark.

> [!CAUTION]
> **Synthetic Data Notice**:
> IBM AMLSim is a **synthetic banking transaction network** generated via agent-based simulation to model anti-money laundering typologies. It **must not be described or cited as real bank transactions or genuine confidential customer data**.

### Dataset Specifications
- **Dataset**: IBM AMLSim `bank_mixed` (v2.1)
- **Data Type**: Synthetic multi-bank transaction network
- **Raw Location**: `data/raw/amlsim_bank_mixed/banks/v2.1/data/bank_mixed/`
- **Total Transactions**: 885,744
- **Account Universe**: 20,000 accounts
- **Time Span**: `2017-01-01T00:00:00Z` to `2018-12-21T00:00:00Z`
- **Typologies**: Bank-to-bank AML typologies (cycles, scatter-gather, gather-scatter)

### Graph Construction
GraphFin constructs its **own** NetworkX directed weighted graph independently from raw transaction relationships (bypassing AMLSim's precomputed graph features):
- **Nodes ($V$)**: Accounts (`acct_id`)
- **Directed Edges ($E$)**: Transactions directed from sender (`orig_acct`) to beneficiary (`bene_acct`)
- **Edge Weight ($W$)**: Cumulative transfer amount (`base_amt`)
- **Edge Metadata**: Transaction count, transaction IDs, timestamp sequence

### Ground-Truth Label Provenance & Construction
Account-level ground-truth labels are decoupled from the unsupervised model training pipeline and managed strictly by GraphFin's `LabelRegistry` for evaluation:
- **Positive SAR Accounts ($y=1$)**: 753 accounts confirmed from `alert_accounts.csv.gz` with `is_sar=True`, corresponding 1-to-1 with `prior_sar_count=True` in `accounts.csv.gz` (3.765% base rate). Accounts appearing across multiple alerts are deterministically aggregated via logical OR (`is_sar.any()`).
- **Negative Accounts ($y=0$)**: 19,247 accounts in `accounts.csv.gz` where `prior_sar_count=False` (generated strictly as normal background traffic by AMLSim).
- **No Label Leakage**: Transaction-level `is_sar` is **never** aggregated into account features, nor included in the 19 GraphFin feature definitions.

### Running the AMLSim Dataset Audit
```bash
python -m backend.app.services.amlsim_adapter
```

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Run Test Suite
```bash
pytest backend/tests -v
```

### 3. Start Backend Server
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation will be available at:
`http://127.0.0.1:8000/docs`

For full API specifications, schemas, and research notes, see [backend/README.md](backend/README.md).

