"""A single source fit, identity preprocessing and a frozen empirical mid-CDF."""
import numpy as np
from sklearn.ensemble import IsolationForest
from ...services.feature_service import CANONICAL_TRANSFER_FEATURES
from ...services.research_protocol import canonical, sha


def matrix(values, names):
    if list(names) != CANONICAL_TRANSFER_FEATURES:
        raise ValueError("Exact ordered canonical 19-feature schema required.")
    x = np.asarray(values, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != 19 or not np.isfinite(x).all():
        raise ValueError("Finite N-by-19 feature matrix required.")
    return x


class EmpiricalCalibrator:
    def __init__(self, source_training_scores):
        scores = np.asarray(source_training_scores, dtype=np.float64)
        if scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all():
            raise ValueError("Finite nonempty source-training scores required.")
        self.reference = np.sort(scores).copy()
        self.reference.setflags(write=False)

    def transform(self, scores):
        scores = np.asarray(scores, dtype=np.float64)
        if scores.ndim != 1 or not np.isfinite(scores).all():
            raise ValueError("Finite score vector required.")
        lo = np.searchsorted(self.reference, scores, side="left")
        hi = np.searchsorted(self.reference, scores, side="right")
        return (lo+hi) / (2*len(self.reference))


class FrozenE4:
    def __init__(self, train_features, config, feature_names):
        x = matrix(train_features, feature_names)
        if len(x) != len(config.train_ids):
            raise ValueError("Training row/membership count mismatch.")
        self.identity = {"source_dataset_id": config.source_dataset_id, "split_id": config.split_id,
                         "train_ids": sorted(config.train_ids), "source_manifest_sha256": config.source_manifest_sha256}
        self.model = IsolationForest(n_estimators=config.n_estimators, max_samples=config.max_samples,
            contamination=config.contamination, random_state=config.model_seed, n_jobs=1)
        self.model.fit(x)  # Only fit in this package; no label or evaluation vector argument.
        self.training_scores = -self.model.decision_function(x)
        self.calibrator = EmpiricalCalibrator(self.training_scores)
        self.training_matrix_sha256 = sha(x.tobytes())
        self.model_id = sha(canonical({**self.identity, "training_matrix_sha256":self.training_matrix_sha256,
                                      "params":self.model.get_params(), "preprocessing":"identity-float32-v1"}))

    def score(self, values, names, identity, batch_size=1024):
        if identity != self.identity:
            raise ValueError("Frozen model source/split/membership identity mismatch; no fallback.")
        x = matrix(values,names)
        raw = np.concatenate([-self.model.decision_function(x[i:i+batch_size])
                              for i in range(0,len(x),batch_size)]) if len(x) else np.array([])
        return raw, self.calibrator.transform(raw)
