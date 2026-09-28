import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score

from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.label_registry import label_registry
from backend.app.services.split_service import split_service
from backend.app.services.feature_service import CANONICAL_TRANSFER_FEATURES, FEATURE_NAMES, GRAPH_FEATURES, BEHAVIORAL_FEATURES, TEMPORAL_FEATURES
from backend.app.services.anomaly_service import anomaly_service, FEATURE_GROUP_MAP
from backend.app.core.config import settings


def compute_permutation_importance(
    model: IsolationForest,
    scaler: StandardScaler,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list,
    n_repeats: int = 10,
    random_state: int = 42
) -> pd.DataFrame:
    """
    Compute PR-AUC permutation importance on held-out test evaluation set.
    """
    rng = np.random.RandomState(random_state)
    
    # Stratified subsample if > 10,000 test entities for computational speed
    if len(X_test) > 10000:
        pos_idxs = np.where(y_test == 1)[0]
        neg_idxs = np.where(y_test == 0)[0]
        max_neg = min(len(neg_idxs), 10000 - len(pos_idxs))
        sub_idxs = np.concatenate([pos_idxs, rng.choice(neg_idxs, size=max_neg, replace=False)])
        X_test = X_test[sub_idxs]
        y_test = y_test[sub_idxs]

    scaled_test = scaler.transform(X_test)
    base_scores = -model.score_samples(scaled_test)
    base_pr_auc = float(average_precision_score(y_test, base_scores)) if len(np.unique(y_test)) > 1 else 0.0

    importances = []
    for j, feat in enumerate(feature_names):
        feat_drop_scores = []
        for _ in range(n_repeats):
            X_perm = X_test.copy()
            X_perm[:, j] = rng.permutation(X_perm[:, j])
            scaled_perm = scaler.transform(X_perm)
            perm_scores = -model.score_samples(scaled_perm)
            perm_pr_auc = float(average_precision_score(y_test, perm_scores)) if len(np.unique(y_test)) > 1 else 0.0
            feat_drop_scores.append(base_pr_auc - perm_pr_auc)

        importances.append({
            "feature": feat,
            "importance_mean": round(float(np.mean(feat_drop_scores)), 6),
            "importance_std": round(float(np.std(feat_drop_scores)), 6),
        })

    df_imp = pd.DataFrame(importances).sort_values(by="importance_mean", ascending=False).reset_index(drop=True)
    return df_imp


def main():
    print("Executing Phase A/B/C Research Experiments...", flush=True)
    out_dir = Path("data/results/permutation_and_casestudy")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load IBM AML 50K
    ibm_ds_id = "03fb9ab0-4f42-4404-9d76-723fd4d8753e"
    store_ibm = dataset_registry.get(ibm_ds_id)
    with open("data/research/ibm_aml_large_50k_labels.csv", "rb") as f:
        label_registry.store_labels_from_csv(ibm_ds_id, f.read())
    split_ibm = split_service.create_split(ibm_ds_id, test_size=0.30, random_state=42, split_label="research-split")

    ibm_uids, ibm_matrix, ibm_fnames = store_ibm.get_feature_matrix()
    ibm_labels = label_registry.get_labels(ibm_ds_id)
    ibm_uid_map = {u: i for i, u in enumerate(ibm_uids)}

    ibm_train_idxs = [ibm_uid_map[u] for u in split_ibm.train_user_ids if u in ibm_uid_map]
    ibm_test_idxs = [ibm_uid_map[u] for u in split_ibm.test_user_ids if u in ibm_uid_map]

    canon_cols = [ibm_fnames.index(f) for f in CANONICAL_TRANSFER_FEATURES]
    X_ibm_train = ibm_matrix[ibm_train_idxs][:, canon_cols]
    X_ibm_test = ibm_matrix[ibm_test_idxs][:, canon_cols]
    y_ibm_test = np.array([ibm_labels.get(ibm_uids[i], 0) for i in ibm_test_idxs])

    scaler_ibm = StandardScaler()
    scaled_ibm_train = scaler_ibm.fit_transform(X_ibm_train)

    clf_ibm_e4 = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    clf_ibm_e4.fit(scaled_ibm_train)

    print("Computing Permutation Importance for IBM AML (E4 Full)...", flush=True)
    imp_ibm = compute_permutation_importance(
        clf_ibm_e4, scaler_ibm, X_ibm_test, y_ibm_test, CANONICAL_TRANSFER_FEATURES, n_repeats=10, random_state=42
    )
    imp_ibm.to_csv(out_dir / "permutation_importance_ibm_aml.csv", index=False)

    # 2. Load PaySim
    ps_ds_id = "e8d9c7b6-a5f4-4e3d-b2c1-a09876543210"
    ps_tx = pd.read_csv("data/research/paysim_transactions.csv")
    ps_csv_path = settings.DATA_PROCESSED_DIR / f"{ps_ds_id}.csv"
    ps_tx.to_csv(ps_csv_path, index=False)
    store_ps = dataset_registry.get(ps_ds_id)
    with open("data/research/paysim_labels.csv", "rb") as f:
        label_registry.store_labels_from_csv(ps_ds_id, f.read())
    split_ps = split_service.create_split(ps_ds_id, test_size=0.30, random_state=42, split_label="research-split")

    ps_uids, ps_matrix, ps_fnames = store_ps.get_feature_matrix()
    ps_labels = label_registry.get_labels(ps_ds_id)
    ps_uid_map = {u: i for i, u in enumerate(ps_uids)}

    ps_train_idxs = [ps_uid_map[u] for u in split_ps.train_user_ids if u in ps_uid_map]
    ps_test_idxs = [ps_uid_map[u] for u in split_ps.test_user_ids if u in ps_uid_map]

    canon_cols_ps = [ps_fnames.index(f) for f in CANONICAL_TRANSFER_FEATURES]
    X_ps_train = ps_matrix[ps_train_idxs][:, canon_cols_ps]
    X_ps_test = ps_matrix[ps_test_idxs][:, canon_cols_ps]
    y_ps_test = np.array([ps_labels.get(ps_uids[i], 0) for i in ps_test_idxs])

    scaler_ps = StandardScaler()
    scaled_ps_train = scaler_ps.fit_transform(X_ps_train)

    clf_ps_e4 = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    clf_ps_e4.fit(scaled_ps_train)

    print("Computing Permutation Importance for PaySim (E4 Full)...", flush=True)
    imp_ps = compute_permutation_importance(
        clf_ps_e4, scaler_ps, X_ps_test, y_ps_test, CANONICAL_TRANSFER_FEATURES, n_repeats=10, random_state=42
    )
    imp_ps.to_csv(out_dir / "permutation_importance_paysim.csv", index=False)

    # 3. Cross-Comparison Table
    merged_imp = pd.merge(
        imp_ibm[["feature", "importance_mean"]].rename(columns={"importance_mean": "IBM_AML_Importance"}),
        imp_ps[["feature", "importance_mean"]].rename(columns={"importance_mean": "PaySim_Importance"}),
        on="feature"
    ).sort_values(by="IBM_AML_Importance", ascending=False).reset_index(drop=True)

    merged_imp.to_csv(out_dir / "permutation_importance_cross_comparison.csv", index=False)
    print("\nPermutation Importance Cross-Comparison Table:", flush=True)
    print(merged_imp.to_string(index=False), flush=True)

    # 4. Phase C Case Study
    print("\nExecuting Phase C Case Study Selection...", flush=True)
    scaled_ps_test = scaler_ps.transform(X_ps_test)
    scores_ps = -clf_ps_e4.score_samples(scaled_ps_test)

    test_uids = [ps_uids[i] for i in ps_test_idxs]
    df_eval = pd.DataFrame({
        "account_id": test_uids,
        "score": scores_ps,
        "label": y_ps_test
    }).sort_values(by="score", ascending=False).reset_index(drop=True)

    df_eval["rank"] = df_eval.index + 1
    top10_pos = df_eval[(df_eval["rank"] <= 10) & (df_eval["label"] == 1)]

    if top10_pos.empty:
        top_pos = df_eval[df_eval["label"] == 1].iloc[0]
    else:
        top_pos = top10_pos.iloc[0]

    case_acc_id = str(top_pos["account_id"])
    case_rank = int(top_pos["rank"])
    case_score = float(top_pos["score"])
    case_idx = ps_uid_map[case_acc_id]
    case_feat_vector = ps_matrix[case_idx][canon_cols_ps]

    ps_means = np.mean(ps_matrix[:, canon_cols_ps], axis=0)
    ps_stds = np.std(ps_matrix[:, canon_cols_ps], axis=0)

    case_study_rows = []
    for j, fname in enumerate(CANONICAL_TRANSFER_FEATURES):
        val = float(case_feat_vector[j])
        mu = float(ps_means[j])
        sigma = float(ps_stds[j])
        z = (val - mu) / sigma if sigma > 1e-9 else 0.0
        case_study_rows.append({
            "feature": fname,
            "value": round(val, 4),
            "dataset_mean": round(mu, 4),
            "dataset_std": round(sigma, 4),
            "z_score": round(float(z), 2)
        })

    df_case = pd.DataFrame(case_study_rows).sort_values(by="z_score", ascending=False, key=abs).reset_index(drop=True)

    case_study_artifact = {
        "account_id": case_acc_id,
        "rank": case_rank,
        "anomaly_score": round(case_score, 4),
        "ground_truth_label": 1,
        "dataset": "PaySim",
        "notice": "This is presented as an anomaly explanation, not as evidence that this account committed fraud.",
        "top_unusual_features": df_case.head(5).to_dict(orient="records"),
        "full_feature_profile": df_case.to_dict(orient="records")
    }

    with open(out_dir / "case_study_account_profile.json", "w") as f:
        json.dump(case_study_artifact, f, indent=2)

    print(f"\nPhase C Case Study Account Selected: {case_acc_id} (Rank #{case_rank}, Score={case_score:.4f})", flush=True)
    print(df_case.head(5).to_string(index=False), flush=True)
    print("\nPhase A/B/C Executed Successfully!", flush=True)


if __name__ == "__main__":
    main()
