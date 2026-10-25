"""Versioned baseline contracts and evaluation-only label identity."""
import hashlib

BASELINES = {
    "e0-offline-signed-zero-v1": {
        "formula": "max_j z_j; z_j=(x_j-mean_train_j)/std_train_j if std>1e-9 else 0",
        "preprocessing": "train-only ddof=0; float32 features; score rounded 4dp",
        "risk": "all-account percentile for presentation; raw rounded z for evaluation",
    },
    "e0-transfer-signed-unit-v1": {
        "formula": "max_j (x_j-mean_source_train_j)/denom_j; denom=std if std>=1e-9 else 1",
        "preprocessing": "source-only ddof=0; float32 features; unrounded raw z",
        "risk": "raw maximum signed z",
    },
    "e0-replay-absolute-leading-v1": {
        "formula": "max_j abs(x_j-mean_j)/std_j; zero if std<=1e-8",
        "preprocessing": "rounded stored statistics; missing indices use leading columns",
        "risk": "clip(100*z/max(2*threshold,1),0,100)",
    },
    "e0-source-signed-zero-v2": {
        "formula": "max_j z_j; z_j=(x_j-mean_train_j)/std_train_j if std>1e-9 else 0",
        "preprocessing": "float64 train-only ddof=0 statistics from existing float32 features; unrounded scores",
        "risk": "raw maximum signed z; higher is more anomalous",
    },
}
PAYSIM_LABEL_HASHES = {
    "59b99a79e6c77b09fb5f63d03037a003e9b08deaea4f9227b8843a16f0abfecb": "paysim-research-774",
    "3cf7a6f6c0bae57393fc59679cb586c2d797b7edeb8663524aa88ae18debb085": "paysim-application-2606",
}


def label_identity(content):
    digest = hashlib.sha256(content).hexdigest()
    known = PAYSIM_LABEL_HASHES.get(digest)
    return {"label_set_id": known or "sha256:" + digest, "sha256": digest,
            "provenance_status": "unresolved_conflict" if known else "unverified_uploaded",
            "definition": "declared account involvement; original evidence horizon unknown" if known else "user-supplied evaluation labels; provenance not independently verified"}


def baseline_contract(version, feature_names):
    return {"implementation_id": version, "feature_names": list(feature_names), **BASELINES[version]}
