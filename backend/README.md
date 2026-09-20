# Financial Anomaly Detection - Backend Foundation

This repository implements the backend foundation for the research project:
> **"Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions"**

The backend establishes a modular, research-grade pipeline in **FastAPI** that ingests financial transactions, enforces schema validation, constructs a directed weighted **NetworkX** transaction graph, calculates structural graph metrics alongside behavioral and temporal features, and exposes them via dataset-scoped REST APIs managed by an in-memory **`DatasetRegistry`**.

---

## 1. System Pipeline

```text
CSV Transaction Data
        ↓
POST /api/v1/transactions/upload
        ↓
Pydantic Schema & Data Quality Validation (Hard rejections + Soft duplicate warnings)
        ↓
DatasetRegistry creates StateStore with UUID4 `dataset_id`
        ↓
NetworkX Directed Weighted Graph (Nodes=Users, Edges=Transactions, Weights=Amount)
        ↓
Feature Extraction (Structural + Behavioral + Temporal)
        ↓
Raw Engineered Feature Matrix (Ready for Unsupervised ML / Isolation Forest)
        ↓
Dataset-Scoped REST APIs (/transactions/{dataset_id}/..., /graph/{dataset_id}/..., /analytics/{dataset_id}/...)
```

---

## 2. Directory Layout

```text
financial-anomaly-detection/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entrypoint & lifespan
│   │   ├── api/
│   │   │   ├── router.py              # Aggregated v1 router
│   │   │   └── routes/
│   │   │       ├── health.py          # GET /api/v1/health
│   │   │       ├── transactions.py    # POST /upload, GET /{dataset_id}/status, GET /{dataset_id}/summary
│   │   │       ├── graph.py           # GET /{dataset_id}/summary, GET /{dataset_id}/nodes/{user_id}
│   │   │       └── analytics.py       # GET /{dataset_id}/users, GET /schema
│   │   ├── core/
│   │   │   ├── config.py              # Environment configuration & paths
│   │   │   ├── logging.py             # Formatted logging system
│   │   │   └── exceptions.py          # Domain exceptions & error handlers (NotFoundException)
│   │   ├── schemas/
│   │   │   ├── transaction.py         # Transaction validation, upload & status models
│   │   │   ├── graph.py               # Graph topological models
│   │   │   └── analytics.py           # Behavioral, temporal & ML feature models
│   │   ├── services/
│   │   │   ├── preprocessing.py       # Data cleaning, validation & soft duplicate warnings
│   │   │   ├── graph_service.py       # NetworkX construction & centrality
│   │   │   ├── feature_service.py     # Behavioral & temporal feature extraction
│   │   │   ├── state_store.py         # StateStore instance (per-dataset state)
│   │   │   └── dataset_registry.py    # DatasetRegistry (dataset-scoped state manager)
│   │   └── utils/
│   │       └── validators.py          # Column & timestamp parsing utilities
│   ├── tests/
│   │   ├── conftest.py                # Pytest fixtures & sample payloads
│   │   ├── test_health.py             # Health check test
│   │   ├── test_transactions.py       # Upload, status, isolation & duplicate tests
│   │   ├── test_graph.py              # NetworkX structural metrics tests
│   │   └── test_features.py           # Feature engineering & ML vector tests
│   ├── requirements.txt
│   └── README.md
├── data/
│   ├── raw/
│   │   └── sample_transactions.csv    # Pre-packaged synthetic dataset
│   └── processed/
├── verify_live_api.py                 # Live API validation script
└── README.md
```

---

## 3. Canonical Transaction Schema

The backend ingests transactions according to this canonical schema:

| Column | Type | Requirement | Description |
| :--- | :--- | :--- | :--- |
| `transaction_id` | String | **Mandatory** | Unique transaction identifier |
| `sender_id` | String | **Mandatory** | Sending entity/user ID |
| `receiver_id` | String | **Mandatory** | Receiving entity/user ID (`sender_id != receiver_id`) |
| `amount` | Float | **Mandatory** | Numerical transaction value (`amount > 0`) |
| `timestamp` | Datetime | **Mandatory** | Transaction timestamp (ISO 8601 or `YYYY-MM-DD HH:MM:SS`) |
| `transaction_type` | String | Optional | e.g., `transfer`, `payment`, `purchase` |
| `merchant` | String | Optional | Merchant name or terminal ID |
| `location` | String | Optional | Location / city / IP origin |
| `device` | String | Optional | Device identifier |

### Data Quality & Validation Rules
- **Non-empty IDs**: Missing or whitespace-only IDs are flagged and rejected.
- **Positive Amounts**: Amounts $\le 0$ or non-numeric values are rejected.
- **Timestamp Integrity**: Unparseable or empty dates are caught.
- **Self-Transfer Guard**: Transactions where `sender_id == receiver_id` are rejected.
- **Duplicate Detection (Hard)**: Duplicate `transaction_id` entries are flagged and rejected.
- **Soft Duplicate Warnings**: Rows that share the exact `(sender_id, receiver_id, amount, timestamp)` tuple of an earlier row are **kept** as valid transfers, but logged with an explicit warning in `duplicate_warnings`.
- **Non-Silent Handling**: Invalid rows are isolated in a rejection log with precise row numbers and reasons.

---

## 4. Dataset-Scoped Architecture (`DatasetRegistry`)

Instead of a single global runtime singleton that gets overwritten on every upload, state is managed by `DatasetRegistry`:
- Each upload allocates a UUID4 `dataset_id`.
- The registry creates and manages isolated `StateStore` instances per dataset.
- Concurrent datasets can be loaded, explored, and compared independently without interference.

---

## 5. Extracted Feature Hierarchy

The system computes 19 numerical features per entity, fusing structural graph metrics with behavioral patterns and temporal activity intervals:

### A. Structural (Graph) Features
1. `in_degree`: Count of incoming counterparties.
2. `out_degree`: Count of outgoing counterparties.
3. `total_degree`: Total distinct counterparties ($in + out$).
4. `weighted_in_degree`: Total cumulative monetary volume received.
5. `weighted_out_degree`: Total cumulative monetary volume sent.
6. `betweenness_centrality`: Node network centrality measuring intermediary flow.

### B. Behavioral Features
7. `transaction_count`: Total transactions involving the user.
8. `total_sent`: Cumulative sent volume.
9. `total_received`: Cumulative received volume.
10. `net_flow`: Net balance change ($\text{total\_received} - \text{total\_sent}$).
11. `average_transaction_amount`: Mean amount per transaction.
12. `maximum_transaction_amount`: Maximum amount in a single transaction.
13. `unique_receivers`: Distinct recipient count.
14. `unique_senders`: Distinct sender count.

### C. Temporal Features
15. `transactions_per_day`: Average transaction frequency per active day.
16. `transactions_per_week`: Estimated weekly transaction frequency.
17. `average_time_between_transactions`: Mean duration (seconds) between successive transactions.
18. `minimum_time_between_transactions`: Minimum duration (seconds) between transactions (detects rapid bursts).
19. `maximum_time_between_transactions`: Maximum duration (seconds) between transactions (detects dormancy gaps).

---

## 6. Quick Start & Execution

### Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### Installation
From the `financial-anomaly-detection` root directory:
```bash
pip install -r backend/requirements.txt
```

### Running the API Server
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be live at `http://127.0.0.1:8000`.
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc UI: `http://127.0.0.1:8000/redoc`

### Running the Test Suite
> **Note:** Pytest must be run from the project root directory (`financial-anomaly-detection/`), rather than from inside the `backend/` folder, so that `backend` resolves correctly as a Python package via `pytest.ini`.

```bash
cd financial-anomaly-detection
pytest backend/tests -v
```

---

## 7. API Endpoints & Example Requests

### 1. Health Check
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/health"
```
**Response:**
```json
{
  "status": "healthy",
  "service": "financial-anomaly-detection-api"
}
```

### 2. Upload Transactions CSV (Extracts `dataset_id`)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/transactions/upload" \
  -F "file=@data/raw/sample_transactions.csv"
```
**Response:**
```json
{
  "message": "Transactions processed and graph updated successfully.",
  "dataset_id": "380bd6d7-136f-4023-983a-23f1ee957bfc",
  "status": "complete",
  "total_rows_parsed": 25,
  "valid_transactions": 25,
  "invalid_rows_count": 0,
  "validation_errors": [],
  "duplicate_warnings": [],
  "summary": {
    "transactions": 25,
    "users": 11,
    "total_amount": 48943.1,
    "average_amount": 1957.72,
    "min_amount": 44.0,
    "max_amount": 25000.0,
    "time_range": {
      "start": "2026-03-01T09:15:00",
      "end": "2026-03-05T17:00:00"
    }
  }
}
```

### 3. Check Dataset Status
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/transactions/380bd6d7-136f-4023-983a-23f1ee957bfc/status"
```
**Response:**
```json
{
  "dataset_id": "380bd6d7-136f-4023-983a-23f1ee957bfc",
  "status": "complete"
}
```

### 4. Transaction Summary (Dataset-Scoped)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/transactions/380bd6d7-136f-4023-983a-23f1ee957bfc/summary"
```

### 5. Graph Topological Summary (Dataset-Scoped)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/graph/380bd6d7-136f-4023-983a-23f1ee957bfc/summary"
```
**Response:**
```json
{
  "nodes": 11,
  "edges": 22,
  "density": 0.2,
  "is_directed": true,
  "weakly_connected_components": 1,
  "strongly_connected_components": 6,
  "top_in_degree_nodes": [
    {
      "user_id": "USR_MERCHANT_99",
      "in_degree": 6,
      "out_degree": 0,
      "total_degree": 6,
      "weighted_in_degree": 25351.6,
      "weighted_out_degree": 0.0,
      "betweenness_centrality": 0.0
    }
  ],
  "top_out_degree_nodes": [
    {
      "user_id": "USR_BURST_01",
      "in_degree": 0,
      "out_degree": 5,
      "total_degree": 5,
      "weighted_in_degree": 0.0,
      "weighted_out_degree": 350.0,
      "betweenness_centrality": 0.0
    }
  ]
}
```

### 6. Node Structural Metrics (Dataset-Scoped)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/graph/380bd6d7-136f-4023-983a-23f1ee957bfc/nodes/USR_ALICE"
```

### 7. User Features Analytics (Dataset-Scoped)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/analytics/380bd6d7-136f-4023-983a-23f1ee957bfc/users?limit=5"
```
**Single User Inspection:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/analytics/380bd6d7-136f-4023-983a-23f1ee957bfc/users/USR_ALICE"
```

### 8. Global Feature Schema (Model Contract)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/analytics/features/schema"
```

---

## 8. Machine Learning Anomaly Detection Layer (Isolation Forest)

The machine learning layer applies unsupervised **Isolation Forest** (via `scikit-learn`) directly on top of the engineered user-level feature matrix. The model isolates anomalies based on the principle that anomalous instances require fewer recursive partitions in decision trees compared to normal, tightly clustered points.

> [!NOTE]
> **Research Terminology Notice**: This system performs **unsupervised anomaly detection** based on statistical and topological deviation in financial transaction graphs. It identifies **anomalous users/entities** exhibiting **potentially suspicious behavior**. It does NOT make deterministic claims of "confirmed fraud" or "fraud detected with certainty".

### 1. Research Experiment Structure (5-Row Benchmark Matrix)
The backend enables side-by-side training and comparison across 5 designated research configurations:

| Experiment | Features | Method | Description |
|---|---|---|---|
| **Baseline** | Graph | Statistical (z-score, no ML) | Rule-based z-score threshold ($\ge 2.0\sigma$) across graph centrality and volume metrics. |
| **E1** | Graph | Isolation Forest | Unsupervised IF trained purely on graph topological metrics (6 features). |
| **E2** | Graph + Behavioral | Isolation Forest | Unsupervised IF combining graph metrics with user transaction statistics (14 features). |
| **E3** | Graph + Temporal | Isolation Forest | Unsupervised IF combining graph metrics with burst and interval metrics (11 features). |
| **E4** | Graph + Behavioral + Temporal | Isolation Forest | Comprehensive feature fusion combining all three groups (19 features, default). |

### 2. Model Scoring & Relative Presentation Risk Score
- **Raw Continuous Score (`raw_score`)**:
  - For **Isolation Forest**: Output directly from `decision_function`. Higher/positive = more normal, lower/negative = more anomalous.
  - For **Statistical Baseline**: Output is the maximum z-score across checked features ($\ge 2.0$ indicates extreme statistical deviation).
- **Relative Presentation Risk Score (`risk_score`)**:
  Calculated as the inverted percentile rank within the training population, mapped strictly to $[0.0, 100.0]$:
  $$\text{risk\_score} = 100 \times (1 - \text{percentile\_rank}(\text{raw\_score}))$$
  where:
  $$\text{percentile\_rank}(s) = \frac{\text{count}(S_{\text{train}} < s) + 0.5 \times \text{count}(S_{\text{train}} == s)}{N_{\text{train}}}$$
  > [!IMPORTANT]
  > The 0–100 score is a relative presentation/ranking score derived from model output.
  > It is NOT a calibrated probability of fraud.
  > It must not be interpreted as a percentage probability that an account is fraudulent.
  > A risk score of 95.0 means the user is in the top 5% most anomalous entities relative to this dataset's population distribution.
- **Categorical Classification (`status`)**:
  - `"suspicious"` if model `prediction == -1`.
  - `"normal"` if model `prediction == 1`.

### 3. Transparent Explainability Layer
Isolation Forest trees do not provide native feature importances. GraphFin provides a transparent heuristic explanation layer based on training-population percentile thresholds ($p90$ for volumes, degrees, and centrality; $p10$ for inter-transaction intervals).

**Reason codes** include:
- `"unusually high transaction count"`
- `"unusually high outgoing volume"`
- `"unusually high incoming volume"`
- `"unusually high transaction amount"`
- `"unusually high receiver diversity"`
- `"unusually high sender diversity"`
- `"unusually short transaction intervals"`
- `"unusually high network centrality"`
- `"unusually high counterparty connections"`
- `"unusually high graph outgoing weight"`
- `"unusually high graph incoming weight"`

Reason codes are strictly scoped to the features included in that experiment's trained model.

### 4. Multi-Experiment Model Persistence
- Models are persisted via `joblib` keyed by `(dataset_id, experiment_label)` into `data/models/{dataset_id}__{experiment_label}.joblib`.
- Multiple experiments (e.g. `Baseline`, `E1`, `E2`, `E3`, `E4`) coexist side by side without overwriting each other.
- Retraining the same `(dataset_id, experiment_label)` overwrites that specific experiment.

---

## 9. Ground-Truth Labeling & Research Evaluation Layer

### 1. Label Leakage Protection
Ground-truth user-level fraud labels are stored in the dedicated `LabelRegistry` service exclusively for offline post-hoc evaluation. Labels are **never** injected into the feature matrix or visible to the Isolation Forest during training.

### 2. Supported Label Variants
Labels CSV uploads (`POST /api/v1/datasets/{dataset_id}/labels`) accept case-insensitive boolean variants:
- **Positive / Fraud (`True`)**: `1`, `"1"`, `"true"`, `"t"`, `"yes"`, `"y"`, `"fraud"`, `"fraudulent"`, `"suspicious"`, `"anomaly"`, `"anomalous"`
- **Negative / Normal (`False`)**: `0`, `"0"`, `"false"`, `"f"`, `"no"`, `"n"`, `"normal"`, `"legitimate"`, `"legit"`, `"non-fraud"`

### 3. Headline Metric: PR-AUC (Average Precision)
In financial transaction networks, fraud is severely imbalanced ($<5\%$). Accuracy can be deceptively high (e.g., $98\%$ accuracy by classifying all entities normal). Therefore:
- **PR-AUC (Precision-Recall Area Under Curve / Average Precision)** is the designated **headline metric** for ranking models.
- Continuous ranking scores (`risk_score` for IF, `raw_score` for baseline) drive the precision-recall curves.

### 4. Research Evaluation Protocol

For empirical studies and paper evaluation (ICITIIT):
1. **Upload Transactions**: `POST /api/v1/transactions/upload` validates transactions and builds the directed weighted NetworkX graph.
2. **Generate User-Level Features**: 19 structural, behavioral, and temporal features are extracted into the numerical feature matrix.
3. **Upload Genuine User-Level Labels**: `POST /api/v1/datasets/{dataset_id}/labels` registers entity ground truth in `LabelRegistry`.
4. **Train All 5 Configurations**:
   - `Baseline` (`POST /api/v1/anomalies/{dataset_id}/baseline`): Graph statistical z-score threshold ($\ge 2.0\sigma$).
   - `E1` (`POST /api/v1/anomalies/{dataset_id}/train?experiment_label=E1`): Graph topology (6 features).
   - `E2` (`POST /api/v1/anomalies/{dataset_id}/train?experiment_label=E2`): Graph + Behavioral (14 features).
   - `E3` (`POST /api/v1/anomalies/{dataset_id}/train?experiment_label=E3`): Graph + Temporal (11 features).
   - `E4` (`POST /api/v1/anomalies/{dataset_id}/train?experiment_label=E4`): Graph + Behavioral + Temporal (19 features).
5. **Evaluate Each Experiment**: `GET /api/v1/evaluation/{dataset_id}/{experiment_label}` computes confusion matrix, Precision, Recall, F1, Accuracy, ROC-AUC, and PR-AUC.
6. **Compare PR-AUC**: `GET /api/v1/evaluation/{dataset_id}/compare` produces the comparative ranking table.
7. **Inspect ROC & PR Curves**: Pass `?include_curves=true` to retrieve coordinate arrays for generating publication figures.
8. **Export Research Run**: `POST /api/v1/evaluation/{dataset_id}/export` serializes reproducible JSON and CSV tables into `data/results/`.
9. **Repeat with the Final Research Dataset**: Benchmark against large-scale public datasets (e.g., Elliptic Bitcoin or IBM AML).

> [!IMPORTANT]
> **Methodological Principles**:
> - **Feature vs. Label Separation**: Labels are stored solely in `LabelRegistry` for evaluation and never enter feature extraction or model training.
> - **PR-AUC Importance**: Given the extreme class imbalance of fraud (<5%), PR-AUC (Average Precision) is the primary comparison metric.
> - **Pipeline Validation vs. Research Benchmark**: Current experimental runs on development datasets serve as pipeline validation demonstrating end-to-end functionality. The final IEEE research paper results must be computed using an appropriately sized real or public financial transaction dataset with genuine ground-truth labels.

---

## 10. API Endpoints Reference

### A. Dataset Ground-Truth Labels
- **`POST /api/v1/datasets/{dataset_id}/labels`**: Upload CSV with columns `user_id` and `label` (column names configurable via query parameters `user_id_col` and `label_col`).
- **`GET /api/v1/datasets/{dataset_id}/labels/summary`**: Retrieve label summary counts and prevalence rate.

### B. Multi-Experiment Anomaly Training & Inference
- **`POST /api/v1/anomalies/{dataset_id}/train?experiment_label=E1`**: Train Isolation Forest on selected `feature_groups`.
- **`POST /api/v1/anomalies/{dataset_id}/baseline`**: Train non-ML statistical baseline (z-score threshold rule).
- **`GET /api/v1/anomalies/{dataset_id}/experiments`**: List all trained experiments stored for the dataset.
- **`GET /api/v1/anomalies/{dataset_id}/users?experiment_label=E1`**: Retrieve per-user anomaly scores and classifications for an experiment.
- **`GET /api/v1/anomalies/{dataset_id}/summary?experiment_label=E1`**: Retrieve aggregate anomaly statistics.
- **`GET /api/v1/anomalies/{dataset_id}/model?experiment_label=E1`**: Inspect stored experiment hyperparameters and feature stats.

### C. Research Evaluation & Model Comparison
- **`GET /api/v1/evaluation/{dataset_id}/{experiment_label}`**: Evaluate a single experiment against ground truth labels (confusion matrix, precision, recall, F1, accuracy, ROC-AUC, PR-AUC).
- **`GET /api/v1/evaluation/{dataset_id}/compare`**: Evaluates all trained experiments and returns a comparison table sorted by PR-AUC descending.

#### Example `/compare` Output:
```json
{
  "dataset_id": "da130e5a-78e0-4d82-b2c2-c6875e143239",
  "total_experiments_evaluated": 5,
  "headline_metric": "pr_auc",
  "experiments": [
    {
      "experiment_label": "E4",
      "model_type": "IsolationForest",
      "feature_count": 19,
      "pr_auc": 0.75,
      "roc_auc": 0.9167,
      "precision": 0.5,
      "recall": 0.5,
      "f1_score": 0.5,
      "accuracy": 0.8182
    },
    {
      "experiment_label": "Baseline",
      "model_type": "StatisticalBaseline",
      "feature_count": 3,
      "pr_auc": 0.60,
      "roc_auc": 0.5556,
      "precision": 0.3333,
      "recall": 0.5,
      "f1_score": 0.4,
      "accuracy": 0.7273
    },
    {
      "experiment_label": "E3",
      "model_type": "IsolationForest",
      "feature_count": 11,
      "pr_auc": 0.5833,
      "roc_auc": 0.9167,
      "precision": 0.5,
      "recall": 0.5,
      "f1_score": 0.5,
      "accuracy": 0.8182
    },
    {
      "experiment_label": "E2",
      "model_type": "IsolationForest",
      "feature_count": 14,
      "pr_auc": 0.4167,
      "roc_auc": 0.8056,
      "precision": 0.5,
      "recall": 0.5,
      "f1_score": 0.5,
      "accuracy": 0.8182
    },
    {
      "experiment_label": "E1",
      "model_type": "IsolationForest",
      "feature_count": 6,
      "pr_auc": 0.3095,
      "roc_auc": 0.6389,
      "precision": 0.0,
      "recall": 0.0,
      "f1_score": 0.0,
      "accuracy": 0.7273
    }
  ]
}
```

---

## 10.5. Train/Test Split Service & Entity-Level Held-Out Evaluation Protocol

To prevent over-optimistic evaluation and measure out-of-sample performance on unseen accounts, GraphFin provides an entity-level train/test split service alongside the existing in-sample mode.

### 1. Evaluation Modes

- **`in_sample`**: Pipeline validation on the full feature population, upper-bound calibration, and sanity-checking model training without partition constraints.
- **`held_out`**: Entity-level held-out evaluation where the Isolation Forest/baseline is fit on the training entity rows and evaluated on the test entity rows.

### 2. Why Held-Out Evaluation Matters
- **Over-Optimistic In-Sample Numbers**: In-sample evaluation evaluates models on the very entities used to construct trees and population percentiles, which can conceal overfitting.
- **Reviewer Scrutiny**: Reviewers legitimately question papers reporting only in-sample metrics; reporting both `in_sample` and `held_out` modes transparently demonstrates why feature engineering choices matter.
- **Entity-Level Out-of-Sample Generalization**: Evaluates detection accuracy on newly registered accounts or counterparties not present during model fitting.

### 3. Entity-Level Partitioning Protocol

> [!NOTE]
> - No label leakage and no test-row leakage during model fitting under the entity-level held-out evaluation protocol.
> - Graph features are currently derived from the full transaction network before the entity-level split; therefore this is not a completely isolated inductive graph-learning evaluation.

- **Entity-Level Partitioning**: Because feature vectors represent account-level behavior, transactions for a given account belong **strictly** to either the train partition or the test partition. A user is never split across train and test.
- **Fit Isolation**: Isolation Forest trees and statistical baseline parameters are fit strictly on the train partition (`X_train`). Test partition entities are evaluated only at prediction/scoring time.
- **Percentile Reference Isolation**: Explainability reason codes use per-feature percentiles (p10, p50, p90, min, max, mean) computed strictly from `X_train`.
- **Stratified Partitioning**: The split preserves ground-truth class prevalence when both classes have $\ge 2$ members, with automatic fallback and documented warnings if positive samples are too few.

### 4. API Workflow

#### Step 1: Create an Entity Split
```bash
POST /api/v1/datasets/{dataset_id}/splits
Content-Type: application/json

{
  "split_label": "default",
  "test_size": 0.3,
  "random_state": 42,
  "stratify_by_label": true
}
```

#### Step 2: Inspect Split Summary
```bash
GET /api/v1/datasets/{dataset_id}/splits/default
```

#### Step 3: Train Model on Train Partition
```bash
POST /api/v1/anomalies/{dataset_id}/train
Content-Type: application/json

{
  "experiment_label": "e4_heldout",
  "feature_groups": ["graph", "behavioral", "temporal"],
  "split_label": "default"
}
```

#### Step 4: Evaluate Against Test Partition
```bash
GET /api/v1/evaluation/{dataset_id}/e4_heldout
```
The response returns `evaluation_mode: "held_out"`, `split_label: "default"`, and `usable_labeled_user_count` matching the test partition size.

#### Step 5: Compare Multi-Mode Experiments
```bash
GET /api/v1/evaluation/{dataset_id}/compare
```
Experiments are ranked by PR-AUC and explicitly grouped in `by_evaluation_mode` (`"in_sample"` and `"held_out"`).

---

## 11. System Limitations & Research Boundaries

1. **Unsupervised Setting with Offline Evaluation**: Ground-truth labels are strictly held out for validation and never guide model tree construction.
2. **Entity-Level Scope**: Anomaly detection operates at the user/account entity level, identifying anomalous nodes rather than individual transaction IDs.
3. **Imbalanced Classes**: Real-world financial transaction networks contain rare anomaly signals. PR-AUC and F1 scores must be prioritized over raw accuracy.
4. **Dataset Scoping**: Relative risk scores and anomaly boundaries are computed within each uploaded dataset's population distribution.
5. **Graph Construction and Inductive Scope**: Graph features are currently derived from the full transaction network before the entity-level split; therefore this is not a completely isolated inductive graph-learning evaluation.
