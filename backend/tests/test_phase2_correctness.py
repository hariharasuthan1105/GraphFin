"""Focused scientific-correctness regressions; run in the disposable verifier."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from backend.app.core.exceptions import ModelNotTrainedException, ValidationException, NotFoundException
from backend.app.services.anomaly_service import AnomalyService, anomaly_service
from backend.app.services.artifact_integrity import ROOT, protected_sha, verify_protected, guard_output
from backend.app.services.baseline_service import baseline_service
from backend.app.services.dataset_registry import dataset_registry
from backend.app.services.evaluation_service import evaluation_service
from backend.app.services.label_registry import label_registry
from backend.app.services.research_identity import baseline_contract, label_identity
from backend.app.services.research_protocol import ResearchConfig, InputSpec, run, fit_and_score, sha
from backend.app.services.split_service import split_service
from backend.app.services.transfer_service import compute_bootstrap_pr_auc_ci
from backend.app.schemas.anomaly import BaselineTrainRequest


_persistence_directories = set()


@pytest.mark.parametrize("iteration", [0, 1])
def test_persistence_isolated_between_test_cases(tmp_path, iteration):
    from backend.app.core.config import settings
    directory = settings.DATA_PROCESSED_DIR.resolve()
    assert directory == (tmp_path / "processed").resolve()
    assert split_service.storage_dir.resolve() == directory
    assert directory not in _persistence_directories
    assert not list(directory.iterdir())
    assert not label_registry._labels and not split_service._splits
    _persistence_directories.add(directory)
    # Leave deliberately conflicting persisted/in-memory state for fixture isolation.
    (directory / "paysim_labels.csv").write_text("user_id,label\nSTALE,1\n")
    label_registry._labels["paysim"] = {"STALE": True}
    split_service._splits[("paysim", "stale")] = object()


def artifact(split="A"):
    identity = {"dataset_id": "fixture", "experiment_label": "E4", "split_label": split}
    return {**identity, "metadata": dict(identity)}


@pytest.mark.parametrize("storage", ["cache", "disk"])
def test_missing_explicit_split_never_uses_alias(tmp_path, storage):
    service = AnomalyService(models_dir=tmp_path)
    if storage == "cache":
        service._cache[("fixture", "E4", None)] = artifact("A")
    else:
        joblib.dump(artifact("A"), tmp_path / "fixture__E4.joblib")
    with pytest.raises(ModelNotTrainedException, match="Model missing"):
        service._load_artifact("fixture", "E4", "B")
    assert service._load_artifact("fixture", "E4")["split_label"] == "A"


@pytest.mark.parametrize("storage", ["cache", "disk"])
@pytest.mark.parametrize("level,field", [("root", "dataset_id"), ("root", "experiment_label"), ("root", "split_label"),
                                        ("metadata", "dataset_id"), ("metadata", "experiment_label"), ("metadata", "split_label")])
def test_wrong_identity_rejected_and_cache_evicted(tmp_path, storage, level, field):
    service = AnomalyService(models_dir=tmp_path)
    wrong = artifact()
    (wrong if level == "root" else wrong["metadata"])[field] = "wrong"
    key = ("fixture", "E4", "A")
    if storage == "cache":
        service._cache[key] = wrong
    else:
        joblib.dump(wrong, tmp_path / "fixture__E4__A.joblib")
    with pytest.raises(ModelNotTrainedException):
        service._load_artifact(*key)
    assert key not in service._cache


def test_correct_split_and_corrupt_file_fail_closed(tmp_path):
    service = AnomalyService(models_dir=tmp_path)
    path = tmp_path / "fixture__E4__A.joblib"
    joblib.dump(artifact(), path)
    assert service._load_artifact("fixture", "E4", "A") == artifact()
    service._cache.clear()
    path.write_bytes(b"corrupt")
    joblib.dump(artifact(), tmp_path / "fixture__E4.joblib")
    with pytest.raises(ModelNotTrainedException):
        service._load_artifact("fixture", "E4", "A")


def test_legacy_default_unsplit_without_experiment_field(tmp_path):
    service = AnomalyService(models_dir=tmp_path)
    legacy = {"dataset_id": "fixture", "metadata": {"dataset_id": "fixture"}}
    joblib.dump(legacy, tmp_path / "fixture.joblib")
    assert service._load_artifact("fixture") == legacy
    with pytest.raises(ModelNotTrainedException):
        service._load_artifact("fixture", "default", "A")


@pytest.fixture
def heldout():
    rows = [[str(i), f"U{i}", f"U{(i+1)%20}", float(i+1), f"2026-01-{i+1:02d}"] for i in range(20)]
    df = pd.DataFrame(rows, columns=["transaction_id", "sender_id", "receiver_id", "amount", "timestamp"])
    ds = dataset_registry.create_dataset(df)
    labels = "user_id,label\n" + "\n".join(f"U{i},{int(i < 6)}" for i in range(20))
    label_registry.store_labels_from_csv(ds, labels.encode())
    split = split_service.create_split(ds, test_size=.3, random_state=7, split_label="A")
    baseline_service.train_baseline(ds, BaselineTrainRequest(experiment_label="E0", feature_groups=["graph"], split_label="A"))
    return ds, split


def test_evaluation_exact_heldout_and_stale_membership(heldout):
    ds, split = heldout
    metrics = evaluation_service.evaluate_experiment(ds, "E0", split_label="A")
    cm = metrics.confusion_matrix
    assert cm.tp + cm.fp + cm.tn + cm.fn == len(split.test_user_ids)
    model = anomaly_service._load_artifact(ds, "E0", "A")
    model["user_ids"][0] = split.test_user_ids[0]
    with pytest.raises(ValidationException, match="training entities"):
        evaluation_service.evaluate_experiment(ds, "E0", split_label="A")


def test_evaluation_missing_coverage_rejected(heldout, monkeypatch):
    ds, _ = heldout
    monkeypatch.setattr(anomaly_service, "predict_user_anomalies", lambda **kw: SimpleNamespace(users=[]))
    with pytest.raises(ValidationException, match="coverage"):
        evaluation_service.evaluate_experiment(ds, "E0", split_label="A")


def test_split_cache_identity_and_overlap_rejected(heldout):
    ds, split = heldout
    split.dataset_id = "wrong"
    with pytest.raises(NotFoundException):
        split_service.get_split(ds, "A")
    split.dataset_id = ds
    split.train_user_ids.append(split.test_user_ids[0])
    with pytest.raises(NotFoundException, match="overlapping"):
        split_service.get_split(ds, "A")


@pytest.mark.parametrize("labels,scores", [([1,0,1,0], [1,1,1,1]), ([0,1,0,1,0], [.2,.2,.4,.8,.8]),
                                          ([1]+[0]*19, list(range(20))), ([1,1,1], [1,2,2]), ([0,0,0], [1,1,2]), ([],[])])
def test_bootstrap_matches_sklearn_each_draw(labels, scores):
    point, ci = compute_bootstrap_pr_auc_ci(labels, scores, 100, 23)
    truth, values = np.asarray(labels), np.asarray(scores)
    rng = np.random.RandomState(23)
    expected, skipped = [], 0
    for _ in range(100):
        idx = rng.randint(0, len(labels), len(labels)) if labels else []
        if not len(idx) or not truth[idx].sum():
            skipped += 1
        else:
            expected.append(average_precision_score(truth[idx], values[idx]))
    assert ci.skipped_resamples == skipped
    assert ci.valid_resamples == len(expected)
    assert ci.point_defined == bool(sum(labels))
    if sum(labels):
        assert point == average_precision_score(labels, scores)
    if expected:
        assert (ci.ci_lower, ci.ci_upper) == tuple(round(float(v),4) for v in np.percentile(expected,[2.5,97.5]))
    else:
        assert not ci.interval_defined and ci.undefined_reason
    assert (point, ci) == compute_bootstrap_pr_auc_ci(labels, scores, 100, 23)


def test_tie_permutation_point_and_no_rounding():
    assert compute_bootstrap_pr_auc_ci([1,0,1,0], [1]*4, 20)[0] == .5
    assert compute_bootstrap_pr_auc_ci([0,0,1,1], [1]*4, 20)[0] == .5
    assert compute_bootstrap_pr_auc_ci([0,1], [0.10000001,0.10000002], 20)[0] == 1


@pytest.mark.parametrize("labels,scores", [([2,0],[1,2]), ([1],[float("nan")]), ([1,0],[1])])
def test_bootstrap_rejects_invalid_input(labels,scores):
    with pytest.raises(ValueError):
        compute_bootstrap_pr_auc_ci(labels,scores)


def test_label_identity_and_explicit_acknowledgement(heldout):
    ds, _ = heldout
    for filename, name in [("paysim_labels.csv","paysim-research-774"),("paysim_account_labels.csv","paysim-application-2606")]:
        identity = label_identity((ROOT/"data/research"/filename).read_bytes())
        assert identity["label_set_id"] == name and identity["provenance_status"] == "unresolved_conflict"
        label_registry._identities[ds] = identity
        with pytest.raises(ValidationException, match="unresolved"):
            label_registry.require_research_identity(ds)
        with pytest.raises(ValidationException, match="does not match"):
            label_registry.require_research_identity(ds,"wrong",True)
        assert label_registry.require_research_identity(ds,name,True) == identity


def config_fixture(tmp_path, experiment="E4"):
    tx = tmp_path/"transactions.csv"
    lbl = tmp_path/"labels.csv"
    tx.write_text("transaction_id,sender_id,receiver_id,amount,timestamp\n" + "\n".join(
        f"{i},U{i},U{(i+1)%20},{i+1},2026-01-{i+1:02d}" for i in range(20)))
    lbl.write_text("user_id,label\n"+"\n".join(f"U{i},{int(i<6)}" for i in range(20)))
    spec = InputSpec(dataset_id="fixture",family="custom",transactions=tx.name,transactions_sha256=sha(tx.read_bytes()),
                     labels=lbl.name,labels_sha256=sha(lbl.read_bytes()),label_set_id="fixture-labels",
                     label_definition="synthetic test labels",provenance_status="declared_not_independently_verified")
    return ResearchConfig(source=spec,experiment=experiment,split_seed=7,model_seed=11,bootstrap_seed=13,n_estimators=10,n_bootstraps=20)


@pytest.mark.parametrize("experiment", ["E0","E1","E2","E3","E4","E5"])
def test_configured_run_repeat_and_saved_config_replay(tmp_path,experiment):
    cfg = config_fixture(tmp_path,experiment)
    output = tmp_path/"runs"
    a = run(cfg,tmp_path,output,"first")
    saved = ResearchConfig.model_validate_json((output/"first/config.json").read_text())
    b = run(saved,output/"first",output,"second")
    assert a["split_sha256"] == b["split_sha256"]
    assert a["artifact_sha256"]["source_held_out_scores.csv"] == b["artifact_sha256"]["source_held_out_scores.csv"]
    assert a["artifact_sha256"]["results.json"] == b["artifact_sha256"]["results.json"]
    assert (a["split_seed"],a["model_seed"],a["bootstrap_seed"]) == (7,11,13)
    scores = pd.read_csv(output/"first/source_held_out_scores.csv")
    split = json.loads((output/"first/split.json").read_text())
    assert set(scores.account_id) == set(split["test_ids"])
    assert not set(split["train_ids"]) & set(scores.account_id)
    with pytest.raises(FileExistsError):
        run(cfg,tmp_path,output,"first")


def test_target_labels_cannot_change_fitted_scores(tmp_path):
    cfg = config_fixture(tmp_path)
    cfg.target = cfg.source.model_copy(deep=True)
    cfg.target.dataset_id = "target"
    first = run(cfg,tmp_path,tmp_path/"runs","first")
    lbl = tmp_path/"target_labels.csv"
    lbl.write_text("user_id,label\n"+"\n".join(f"U{i},{int(i>=6)}" for i in range(20)))
    cfg.target.labels = lbl.name
    cfg.target.labels_sha256 = sha(lbl.read_bytes())
    second = run(cfg,tmp_path,tmp_path/"runs","second")
    for domain in ["source","target"]:
        a = pd.read_csv(tmp_path/f"runs/first/{domain}_held_out_scores.csv")
        b = pd.read_csv(tmp_path/f"runs/second/{domain}_held_out_scores.csv")
        np.testing.assert_array_equal(a.raw_anomaly_score,b.raw_anomaly_score)
    assert first["fitted_parameters"] == second["fitted_parameters"]


def test_input_hash_and_paysim_provenance_fail_closed(tmp_path):
    cfg = config_fixture(tmp_path)
    cfg.source.transactions_sha256 = "wrong"
    with pytest.raises(ValueError,match="checksum"):
        run(cfg,tmp_path,tmp_path/"runs","bad")
    cfg = config_fixture(tmp_path)
    cfg.source.family = "paysim"
    with pytest.raises(ValueError,match="unresolved"):
        run(cfg,tmp_path,tmp_path/"runs","bad")
    assert not (tmp_path/"runs/bad").exists()


def test_baseline_versions_and_constant_column_math(tmp_path):
    cfg = config_fixture(tmp_path,"E0")
    scores, _, _ = fit_and_score(np.array([[5,4],[5,6]]),[np.array([[8,2],[5,8]])],cfg)
    np.testing.assert_array_equal(scores[0],[0,3])
    versions = ["e0-offline-signed-zero-v1","e0-transfer-signed-unit-v1","e0-replay-absolute-leading-v1","e0-source-signed-zero-v2"]
    assert len({baseline_contract(v,["x"])["implementation_id"] for v in versions}) == 4


def test_protected_bytes_and_separate_crlf_equivalence():
    assert verify_protected() == []
    legacy = {"json":"e16e2d5948b66f0cde493fadf43e1491fee219b582faa6a38eabfe53be786ad2",
              "csv":"ba89012faf612cfe96d9e5049a869c40596894d167d37bb26a1581d976efa40a"}
    for suffix, old_hash in legacy.items():
        name = f"data/results/final_e0_e4_comparison.{suffix}"
        raw = (ROOT/name).read_bytes()
        assert sha(raw) == protected_sha(name)
        assert sha(raw.replace(b"\n",b"\r\n")) == old_hash
        assert sha(raw+b" ") != protected_sha(name)
        with pytest.raises(ValueError,match="Protected"):
            guard_output(ROOT/name)
