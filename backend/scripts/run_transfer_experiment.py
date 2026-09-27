import json
import time
from pathlib import Path
import pandas as pd

from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.label_registry import label_registry
from backend.app.services.split_service import split_service
from backend.app.services.transfer_service import transfer_service
from backend.app.schemas.transfer import TransferExperimentRequest
from backend.app.core.config import settings

def main():
    print("Initializing Cross-Dataset Transfer Experiment...", flush=True)
    t0 = time.time()

    ibm_ds_id = "03fb9ab0-4f42-4404-9d76-723fd4d8753e"
    ps_ds_id = "e8d9c7b6-a5f4-4e3d-b2c1-a09876543210"

    print("Loading IBM AML dataset into registry...", flush=True)
    store_ibm = dataset_registry.get(ibm_ds_id)
    with open("data/research/ibm_aml_large_50k_labels.csv", "rb") as f:
        label_registry.store_labels_from_csv(ibm_ds_id, f.read())
    split_service.create_split(ibm_ds_id, test_size=0.30, random_state=42, split_label="research-split")

    print("Loading PaySim dataset into registry...", flush=True)
    ps_tx = pd.read_csv("data/research/paysim_transactions.csv")
    ps_csv_path = settings.DATA_PROCESSED_DIR / f"{ps_ds_id}.csv"
    settings.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ps_tx.to_csv(ps_csv_path, index=False)

    store_ps = dataset_registry.get(ps_ds_id)
    with open("data/research/paysim_labels.csv", "rb") as f:
        label_registry.store_labels_from_csv(ps_ds_id, f.read())
    split_service.create_split(ps_ds_id, test_size=0.30, random_state=42, split_label="research-split")

    print(f"Datasets loaded successfully in {time.time()-t0:.2f} seconds.", flush=True)

    out_dir = Path("data/results/cross_dataset")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. IBM -> PaySim
    print("\n==========================================", flush=True)
    print("Running EXPERIMENT A: IBM AML -> PaySim", flush=True)
    print("==========================================", flush=True)
    t_start = time.time()
    req_a = TransferExperimentRequest(
        source_dataset_id=ibm_ds_id,
        target_dataset_id=ps_ds_id,
        experiments=["E0", "E1", "E2", "E3", "E4", "E5"],
        n_bootstraps=100
    )
    res_a = transfer_service.evaluate_transfer(req_a)
    print(f"Experiment A completed in {time.time()-t_start:.2f} seconds.", flush=True)
    
    with open(out_dir / "ibm_to_paysim_transfer.json", "w") as f:
        f.write(res_a.model_dump_json(indent=2))

    # Print summary table A
    print("\nDirection A (IBM AML -> PaySim):", flush=True)
    print(f"{'Exp':<6} | {'Src PR-AUC (95% CI)':<26} | {'Tgt PR-AUC (95% CI)':<26} | {'P@10':<6} | {'P@25':<6} | {'P@50':<6} | {'P@100':<6}", flush=True)
    print("-" * 95, flush=True)
    for exp in res_a.experiments:
        src_ci = f"{exp.source_pr_auc:.4f} ({exp.source_pr_auc_ci.ci_lower:.4f}-{exp.source_pr_auc_ci.ci_upper:.4f})"
        tgt_ci = f"{exp.target_pr_auc:.4f} ({exp.target_pr_auc_ci.ci_lower:.4f}-{exp.target_pr_auc_ci.ci_upper:.4f})"
        pk = exp.precision_at_k
        print(f"{exp.experiment_label:<6} | {src_ci:<26} | {tgt_ci:<26} | {pk.p_at_10:<6.2f} | {pk.p_at_25:<6.2f} | {pk.p_at_50:<6.2f} | {pk.p_at_100:<6.2f}", flush=True)

    # 2. PaySim -> IBM
    print("\n==========================================", flush=True)
    print("Running EXPERIMENT B: PaySim -> IBM AML", flush=True)
    print("==========================================", flush=True)
    t_start = time.time()
    req_b = TransferExperimentRequest(
        source_dataset_id=ps_ds_id,
        target_dataset_id=ibm_ds_id,
        experiments=["E0", "E1", "E2", "E3", "E4", "E5"],
        n_bootstraps=100
    )
    res_b = transfer_service.evaluate_transfer(req_b)
    print(f"Experiment B completed in {time.time()-t_start:.2f} seconds.", flush=True)

    with open(out_dir / "paysim_to_ibm_transfer.json", "w") as f:
        f.write(res_b.model_dump_json(indent=2))

    # Print summary table B
    print("\nDirection B (PaySim -> IBM AML):", flush=True)
    print(f"{'Exp':<6} | {'Src PR-AUC (95% CI)':<26} | {'Tgt PR-AUC (95% CI)':<26} | {'P@10':<6} | {'P@25':<6} | {'P@50':<6} | {'P@100':<6}", flush=True)
    print("-" * 95, flush=True)
    for exp in res_b.experiments:
        src_ci = f"{exp.source_pr_auc:.4f} ({exp.source_pr_auc_ci.ci_lower:.4f}-{exp.source_pr_auc_ci.ci_upper:.4f})"
        tgt_ci = f"{exp.target_pr_auc:.4f} ({exp.target_pr_auc_ci.ci_lower:.4f}-{exp.target_pr_auc_ci.ci_upper:.4f})"
        pk = exp.precision_at_k
        print(f"{exp.experiment_label:<6} | {src_ci:<26} | {tgt_ci:<26} | {pk.p_at_10:<6.2f} | {pk.p_at_25:<6.2f} | {pk.p_at_50:<6.2f} | {pk.p_at_100:<6.2f}", flush=True)

    print("\nAll Cross-Dataset Transfer Experiments Finished Successfully!", flush=True)

if __name__ == "__main__":
    main()
