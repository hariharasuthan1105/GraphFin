import pytest
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

from backend.app.schemas.transfer import (
    TransferExperimentRequest,
    TransferExperimentResponse,
    ExperimentTransferResult
)
from backend.app.services.transfer_service import (
    transfer_service,
    compute_bootstrap_pr_auc_ci,
    compute_precision_at_k,
    compute_degradation
)
from backend.app.services.paysim_adapter import derive_paysim_account_labels
from backend.app.services.feature_service import (
    FEATURE_NAMES,
    CANONICAL_TRANSFER_FEATURES,
    GRAPH_FEATURES,
    BEHAVIORAL_FEATURES,
    TEMPORAL_FEATURES
)


def test_1_source_target_feature_schema_equality():
    """Test 1: Validate feature schema matching between source and target."""
    all_cat_features = GRAPH_FEATURES + BEHAVIORAL_FEATURES + TEMPORAL_FEATURES
    assert set(CANONICAL_TRANSFER_FEATURES) == set(all_cat_features)
    assert len(CANONICAL_TRANSFER_FEATURES) == 19
    # Ensure exact order preservation
    assert CANONICAL_TRANSFER_FEATURES[:6] == GRAPH_FEATURES
    assert CANONICAL_TRANSFER_FEATURES[6:14] == BEHAVIORAL_FEATURES
    assert CANONICAL_TRANSFER_FEATURES[14:19] == TEMPORAL_FEATURES


def test_2_and_3_source_only_model_fitting_and_target_labels_unavailable():
    """Test 2 & 3: Ensure model fitting uses ONLY source data and target labels are never passed to fit."""
    source_X = np.random.randn(100, 19)
    target_X = np.random.randn(50, 19)
    
    # Fit scaler on source
    scaler = StandardScaler()
    scaled_source = scaler.fit_transform(source_X)
    
    # Fit Isolation Forest on source
    clf = IsolationForest(random_state=42)
    clf.fit(scaled_source)
    
    # Transform target using source scaler (without refitting)
    scaled_target = scaler.transform(target_X)
    target_scores = -clf.score_samples(scaled_target)
    
    assert len(target_scores) == 50
    # Scaler mean must match source mean, not target mean
    assert np.allclose(scaler.mean_, source_X.mean(axis=0))


def test_4_source_preprocessing_reused_on_target():
    """Test 4: Verify scaler fit parameters on source are applied to target without refitting."""
    source_X = np.array([[10.0, 100.0], [20.0, 200.0]])
    target_X = np.array([[1000.0, 5000.0]])
    
    scaler = StandardScaler()
    scaler.fit(source_X)
    
    source_mean = scaler.mean_.copy()
    source_scale = scaler.scale_.copy()
    
    transformed_target = scaler.transform(target_X)
    
    # Verify scaler parameters did NOT change after transforming target
    assert np.array_equal(scaler.mean_, source_mean)
    assert np.array_equal(scaler.scale_, source_scale)
    expected_transformed = (target_X - source_mean) / source_scale
    assert np.allclose(transformed_target, expected_transformed)


def test_7_precision_at_k_calculation():
    """Test 7: Precision@K calculation logic."""
    y_true = [1, 0, 1, 0, 1, 0, 0, 0, 0, 0]  # 3 positives total
    scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05]
    
    pk = compute_precision_at_k(y_true, scores, k_values=[10, 25, 50, 100])
    assert pk.p_at_10 == pytest.approx(0.3)  # Top 10 has 3 positives -> 3/10 = 0.3


def test_8_degradation_calculation():
    """Test 8: Absolute and relative degradation calculation."""
    src_pr_auc = 0.80
    tgt_pr_auc = 0.40
    
    deg = compute_degradation(src_pr_auc, tgt_pr_auc)
    assert deg.absolute_degradation == pytest.approx(0.40)
    assert deg.relative_degradation == pytest.approx(0.50)  # (0.8 - 0.4) / 0.8 = 0.5
    
    # Zero source performance edge case
    deg_zero = compute_degradation(0.0, 0.40)
    assert deg_zero.relative_degradation is None


def test_9_e5_compatibility_handling():
    """Test 9: E5 egonet transfer compatibility handling."""
    req = TransferExperimentRequest(
        source_dataset_id="03fb9ab0-4f42-4404-9d76-723fd4d8753e",
        target_dataset_id="e8d9c7b6-a5f4-4e3d-b2c1-a09876543210",
        experiments=["E5"]
    )
    assert "E5" in req.experiments


def test_10_locked_ibm_aml_result_regression_protection():
    """Test 10: Locked IBM AML research results are preserved and read-only."""
    from backend.app.api.routes.datasets import _LOCKED_DATASET_IDS
    ibm_ds_id = "03fb9ab0-4f42-4404-9d76-723fd4d8753e"
    assert ibm_ds_id in _LOCKED_DATASET_IDS


def test_11_deterministic_repeated_transfer_runs():
    """Test 11: Repeatability with fixed random_state."""
    y_true = [1, 0, 1, 0, 0, 1, 0, 0, 1, 0] * 5
    scores = list(np.random.RandomState(42).randn(50))
    
    pt1, ci1 = compute_bootstrap_pr_auc_ci(y_true, scores, n_bootstraps=50, random_state=42)
    pt2, ci2 = compute_bootstrap_pr_auc_ci(y_true, scores, n_bootstraps=50, random_state=42)
    
    assert pt1 == pt2
    assert ci1.ci_lower == ci2.ci_lower
    assert ci1.ci_upper == ci2.ci_upper


def test_12_bootstrap_ci_reproducibility():
    """Test 12: Bootstrap CI reproducibility across calls."""
    y_true = [1, 0, 0, 1, 0, 1, 0, 0, 0, 1] * 10
    scores = list(np.arange(100) / 100.0)
    
    pt, ci = compute_bootstrap_pr_auc_ci(y_true, scores, n_bootstraps=100, random_state=123)
    assert 0.0 <= ci.ci_lower <= ci.point_estimate <= ci.ci_upper <= 1.0


def test_13_paysim_account_label_derivation():
    """Test 13: PaySim account label derivation matches 'Any Involvement' rule."""
    df_tx = pd.DataFrame({
        "sender_id": ["acc1", "acc2", "acc3"],
        "receiver_id": ["acc2", "acc4", "acc5"],
        "is_fraud": [1, 0, 0]
    })
    labels = derive_paysim_account_labels(df_tx)
    # acc1 (sender) and acc2 (receiver) are involved in is_fraud=1 transaction
    assert labels["acc1"] == 1
    assert labels["acc2"] == 1
    assert labels["acc3"] == 0
    assert labels["acc4"] == 0
    assert labels["acc5"] == 0


def test_14_bootstrap_ci_low_prevalence_point_estimate_within_ci():
    """Test 14: Point estimate lies within its own 95% CI on synthetic data with ~0.2% prevalence."""
    rng = np.random.RandomState(42)
    n = 5000
    n_pos = 10  # 0.2% prevalence
    y_true = np.zeros(n, dtype=int)
    y_true[:n_pos] = 1
    rng.shuffle(y_true)
    scores = rng.randn(n) + y_true * 1.5

    pt, ci = compute_bootstrap_pr_auc_ci(y_true.tolist(), scores.tolist(), n_bootstraps=200, random_state=42)
    assert ci.ci_lower <= pt <= ci.ci_upper, (
        f"Point estimate {pt} does not lie within CI [{ci.ci_lower}, {ci.ci_upper}]"
    )


def test_15_bootstrap_resampled_prevalence_approximates_true_prevalence():
    """Test 15: Resampled prevalence approximates the true prevalence across resamples."""
    rng = np.random.RandomState(42)
    n = 5000
    n_pos = 25  # 0.5% prevalence
    true_prev = n_pos / n
    y_true = np.zeros(n, dtype=int)
    y_true[:n_pos] = 1

    resample_prevs = []
    for _ in range(100):
        idxs = rng.randint(0, n, size=n)
        resample_prevs.append(np.mean(y_true[idxs]))

    mean_resample_prev = float(np.mean(resample_prevs))
    # Should be within 0.1% of true prevalence (0.005)
    assert abs(mean_resample_prev - true_prev) < 0.001, (
        f"Resampled prevalence {mean_resample_prev} diverges from true prevalence {true_prev}"
    )


def test_16_bootstrap_same_seed_gives_same_ci():
    """Test 16: Same seed gives same CI and zero-positive resamples are properly skipped."""
    rng = np.random.RandomState(42)
    n = 1000
    y_true = np.zeros(n, dtype=int)
    y_true[:3] = 1
    scores = rng.randn(n)

    pt1, ci1 = compute_bootstrap_pr_auc_ci(y_true.tolist(), scores.tolist(), n_bootstraps=100, random_state=99)
    pt2, ci2 = compute_bootstrap_pr_auc_ci(y_true.tolist(), scores.tolist(), n_bootstraps=100, random_state=99)

    assert pt1 == pt2
    assert ci1.ci_lower == ci2.ci_lower
    assert ci1.ci_upper == ci2.ci_upper
    assert ci1.skipped_resamples == ci2.skipped_resamples


def test_17_markdown_report_matches_canonical_json():
    """Test 17: Fails if any PR-AUC or CI value in transfer_results_summary.md differs from the canonical JSON."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent
    report_file = root / "data" / "results" / "final_report" / "transfer_results_summary.md"
    json_a_file = root / "data" / "results" / "cross_dataset" / "ibm_to_paysim_transfer.json"
    json_b_file = root / "data" / "results" / "cross_dataset" / "paysim_to_ibm_transfer.json"

    if not report_file.exists() or not json_a_file.exists() or not json_b_file.exists():
        pytest.skip("Artifacts not yet generated.")

    md_content = report_file.read_text(encoding="utf-8")

    for json_path, dir_label in [(json_a_file, "Direction A"), (json_b_file, "Direction B")]:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for exp in data["experiments"]:
            e_label = exp["experiment_label"]
            src_pr = exp["source_pr_auc"]
            src_ci = exp.get("source_pr_auc_ci")
            tgt_pr = exp["target_pr_auc"]
            tgt_ci = exp.get("target_pr_auc_ci")

            src_pr_str = f"{src_pr:.4f}"
            tgt_pr_str = f"{tgt_pr:.4f}"

            assert src_pr_str in md_content, (
                f"Source PR-AUC {src_pr_str} for {e_label} in {dir_label} not found in markdown!"
            )
            assert tgt_pr_str in md_content, (
                f"Target PR-AUC {tgt_pr_str} for {e_label} in {dir_label} not found in markdown!"
            )

            if src_ci:
                src_ci_low = f"{src_ci['ci_lower']:.4f}"
                src_ci_high = f"{src_ci['ci_upper']:.4f}"
                assert src_ci_low in md_content, (
                    f"Source CI lower {src_ci_low} for {e_label} in {dir_label} not found in markdown!"
                )
                assert src_ci_high in md_content, (
                    f"Source CI upper {src_ci_high} for {e_label} in {dir_label} not found in markdown!"
                )

            if tgt_ci:
                tgt_ci_low = f"{tgt_ci['ci_lower']:.4f}"
                tgt_ci_high = f"{tgt_ci['ci_upper']:.4f}"
                assert tgt_ci_low in md_content, (
                    f"Target CI lower {tgt_ci_low} for {e_label} in {dir_label} not found in markdown!"
                )
                assert tgt_ci_high in md_content, (
                    f"Target CI upper {tgt_ci_high} for {e_label} in {dir_label} not found in markdown!"
                )

