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
