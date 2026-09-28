# GraphFin Research Data Guide

This directory documents the research datasets, download sources, reproduction commands, and directory layouts for the GraphFin benchmark and cross-dataset transfer experiments.

---

## 1. Primary Datasets

### A. IBM Transactions for Anti-Money Laundering (AML)
- **Source**: Kaggle — [IBM Transactions for Anti-Money Laundering (AML)](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml)
- **Variant Used**: `HI-Small_Trans.csv` (High Laundering Ratio, Small Network, ~5.08M transactions)
- **Target Fixture**: `data/research/ibm_aml_large_50k.csv` and `data/research/ibm_aml_large_50k_labels.csv`
- **Specification**: 50,000 sampled accounts, 49,992 active graph nodes, 249 positive laundering accounts (0.498% prevalence).

### B. PaySim Synthetic Financial Dataset
- **Source**: Kaggle — [PaySim Synthetic Dataset for Mobile Money AML/Fraud](https://www.kaggle.com/datasets/ealaxi/paysim1)
- **Raw File**: `PS_20174392719_1491204439457_log.csv` (~6.36M transactions, 744 simulation steps / 31 days, ~471 MB uncompressed)
- **Target Fixture**: `data/research/paysim_transactions.csv` and `data/research/paysim_labels.csv`
- **Specification**: 300,000 uniform random transactions (`random_state=42`), covering steps 1–741 across 552 unique simulation steps. 547,686 unique accounts, 774 positive accounts (0.1413% prevalence).

---

## 2. Reproduction Commands

### IBM AML Large (50,000 Accounts)
```bash
python backend/scripts/convert_ibm_aml.py \
  --input data/raw/HI-Small_Trans.csv \
  --output-tx data/research/ibm_aml_large_50k.csv \
  --output-labels data/research/ibm_aml_large_50k_labels.csv \
  --sample-accounts 50000 \
  --seed 42 \
  --chunksize 100000
```

### PaySim Full-Range Uniform Sample (300,000 Transactions)
```bash
python backend/scripts/convert_paysim.py \
  --input data/raw/PS_20174392719_1491204439457_log.csv \
  --output-tx data/research/paysim_transactions.csv \
  --output-labels data/research/paysim_labels.csv \
  --sample-rows 300000 \
  --seed 42
```

---

## 3. Directory Structure & Version Control Policy

```
data/
├── README.md                          # This guide
├── raw/
│   ├── .gitkeep
│   ├── PS_20174392719_*.csv           # [GITIGNORED] Raw 471MB PaySim log
│   └── sample_transactions.csv        # Minimal smoke-test fixture (tracked)
├── processed/
│   └── .gitkeep                       # [GITIGNORED] Runtime cache
├── research/
│   ├── README.md                      # Detailed IBM AML fixture specifications
│   ├── ibm_aml_large_50k_labels.csv   # Ground-truth label file
│   ├── paysim_labels.csv              # PaySim ground-truth label file
│   └── paysim_transactions.csv        # 21.9 MB sampled transaction fixture
└── results/
    ├── final_e0_e4_comparison.json    # [LOCKED] Baseline IBM benchmark
    ├── final_e0_e4_comparison.csv     # [LOCKED] Baseline IBM benchmark
    ├── cross_dataset/
    │   ├── README.md                  # Documents canonical transfer files
    │   ├── ibm_to_paysim_transfer.json# Canonical Direction A transfer results
    │   ├── paysim_to_ibm_transfer.json# Canonical Direction B transfer results
    │   └── archive/                   # Deprecated/duplicate result files
    ├── permutation_and_casestudy/
    │   ├── permutation_importance_ibm_aml.csv
    │   ├── permutation_importance_paysim.csv
    │   ├── permutation_importance_cross_comparison.csv
    │   └── case_study_account_profile.json
    └── final_report/
        ├── transfer_results_summary.md
        ├── permutation_importance_summary.md
        ├── case_study.md
        └── paper_reportable_status.md
```

### File Size and Tracking Rules
- All files over 50 MB (including raw PaySim data, runtime processed files) are excluded via `.gitignore`.
- Locked baseline comparison artifacts (`final_e0_e4_comparison.json`, `final_e0_e4_comparison.csv`) are cryptographically frozen.
- All report markdown documents in `data/results/final_report/` are generated deterministically by `backend/scripts/generate_final_reports.py` directly from canonical JSON and CSV artifacts.
