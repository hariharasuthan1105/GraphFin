# Cross-Dataset Transfer Experiment Results

## Canonical Transfer Artifacts

This directory contains the canonical evaluation results for the cross-dataset transfer experiments between IBM AML Large and PaySim (full simulation step range 1–741):

1. **`ibm_to_paysim_transfer.json`**:
   - **Source Dataset**: IBM AML Large (`03fb9ab0-4f42-4404-9d76-723fd4d8753e`, 50,000 accounts)
   - **Target Dataset**: PaySim (`e8d9c7b6-a5f4-4e3d-b2c1-a09876543210`, 547,686 accounts)
   - **Direction**: `IBM AML->PaySim`
   - **Content**: E0–E5 transfer evaluation metrics, prevalence-preserving bootstrap 95% CIs, Precision@K, and feature shift diagnostics.

2. **`paysim_to_ibm_transfer.json`**:
   - **Source Dataset**: PaySim (`e8d9c7b6-a5f4-4e3d-b2c1-a09876543210`, 547,686 accounts)
   - **Target Dataset**: IBM AML Large (`03fb9ab0-4f42-4404-9d76-723fd4d8753e`, 50,000 accounts)
   - **Direction**: `PaySim->IBM AML`
   - **Content**: E0–E5 transfer evaluation metrics, prevalence-preserving bootstrap 95% CIs, Precision@K, and feature shift diagnostics.

## Archived Artifacts

- **`archive/`**: Contains superseded and duplicate files (`transfer_ibm_aml_to_paysim.json`, `transfer_paysim_to_ibm_aml.json`) from prior runs.
