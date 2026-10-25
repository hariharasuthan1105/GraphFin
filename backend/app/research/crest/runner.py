"""Append-only E6 research stage; source fit once, batched scoring, no evaluation metrics."""
import io
import json
import os
from pathlib import Path
import platform
import re
import time
import tracemalloc
import joblib
import numpy as np
import sklearn
from ...services.feature_service import CANONICAL_TRANSFER_FEATURES
from ...services.research_protocol import ROOT, PROTOCOL, canonical, sha
from .schemas import VERSION
from .artifacts import load_bundle
from .frozen_scorer import FrozenE4
from .statistics import influence, stratum, summarize, rank_accounts


def run(config, source_directory, evaluation_directory, output_root, run_id):
    root = Path(output_root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+",run_id):
        raise ValueError("Invalid run ID.")
    if root.is_relative_to(ROOT) and not root.is_relative_to(ROOT/"data/results/v2"):
        raise ValueError("Repository E6 outputs must be under data/results/v2.")
    dest = root/run_id
    if dest.exists():
        raise FileExistsError("E6 run exists; append-only output required.")
    start = time.perf_counter()
    source = load_bundle(source_directory, config.source_manifest_sha256, config.source_dataset_id)
    evaluation = load_bundle(evaluation_directory, config.evaluation_manifest_sha256, config.evaluation_dataset_id)
    train_ids, eval_ids = sorted(config.train_ids), sorted(config.evaluation_ids)
    if not set(train_ids) <= set(source["baseline"]) or not set(eval_ids) <= set(evaluation["baseline"]):
        raise ValueError("Configured training/evaluation membership absent from baseline artifacts.")
    if source["manifest"]["source"]["transactions_sha256"] == evaluation["manifest"]["source"]["transactions_sha256"] and set(train_ids)&set(eval_ids):
        raise ValueError("Held-out membership overlap under dataset aliases.")
    train = [source["baseline"][u] for u in train_ids]
    fit_start = time.perf_counter()
    detector = FrozenE4(train,config,CANONICAL_TRANSFER_FEATURES)
    fit_seconds = time.perf_counter()-fit_start
    model_bytes = io.BytesIO()
    joblib.dump({"model":detector.model,"identity":detector.identity,"model_id":detector.model_id},model_bytes)
    model_content = model_bytes.getvalue()
    accepted = sorted([r for r in evaluation["records"] if r["status"]=="accepted" and r["focal_account"] in eval_ids],
                      key=lambda r:(r["focal_account"],r["intervention_id"]))
    values = [evaluation["baseline"][u] for u in eval_ids] + [r["intervened_features"] for r in accepted]
    score_start = time.perf_counter()
    raw, q = detector.score(values,CANONICAL_TRANSFER_FEATURES,detector.identity,config.batch_size)
    scoring_seconds = time.perf_counter()-score_start
    original = {u:(float(raw[i]),float(q[i])) for i,u in enumerate(eval_ids)}
    profiles = []
    for i,r in enumerate(accepted,start=len(eval_ids)):
        raw0,q0 = original[r["focal_account"]]
        profiles.append({**r,"raw_baseline_score":raw0,"raw_intervened_score":float(raw[i]),
                         "calibrated_baseline_score":q0,"calibrated_intervened_score":float(q[i]),
                         **influence(q0,q[i]),"budget_stratum":stratum(r,config)})
    accounts = []
    for u in eval_ids:
        rows = [r for r in profiles if r["focal_account"]==u]
        rejects = [r for r in evaluation["records"] if r["status"]=="rejected" and r["focal_account"]==u]
        statistics = summarize(rows,rejects,config,evaluation["configuration"].families)
        most = sorted(rows,key=lambda r:(-r["absolute_change"],r["intervention_id"]))[0] if rows else None
        accounts.append({"dataset_id":config.evaluation_dataset_id,"source_dataset_id":config.source_dataset_id,
            "model_id":detector.model_id,"split_id":config.split_id,"account_id":u,
            "raw_baseline_score":original[u][0],"calibrated_score":original[u][1],
            "statistics":statistics,"intervention_budget":evaluation["manifest"]["budget"],
            "most_influential_omission":most,
            "evidence_warnings":[] if statistics["evidence_status"]=="available" else ["insufficient_or_partial_evidence"],
            "interpretation":"model sensitivity only; not causal evidence or an allegation"})
    rankings = {mode:rank_accounts(accounts,mode,config) for mode in config.modes}
    dest.mkdir(parents=True,exist_ok=False)
    replay = {"configuration":config.model_dump(),
              "source_directory":os.path.relpath(Path(source_directory).resolve(),dest),
              "evaluation_directory":os.path.relpath(Path(evaluation_directory).resolve(),dest)}
    (dest/"config.json").write_bytes(canonical(replay))
    (dest/"model.joblib").write_bytes(model_content)
    (dest/"calibration.json").write_bytes(canonical({"implementation_id":"source-empirical-midcdf-v1",
        "source_train_ids":train_ids,"raw_training_scores":detector.training_scores.tolist(),
        "sorted_reference":detector.calibrator.reference.tolist(),"source_training_features":train,
        "formula":"(# reference < s + 0.5 * # reference == s) / N",
        "boundary":"below min = 0, above max = 1; percentiles are not fraud probabilities"}))
    # Exclude Phase 3 runtime from scientific outputs so replay bytes are stable.
    clean_profiles = [{k:v for k,v in r.items() if k!="runtime_seconds"} for r in profiles]
    for a in accounts:
        if a["most_influential_omission"]:
            a["most_influential_omission"].pop("runtime_seconds",None)
    with (dest/"intervention_scores.jsonl").open("wb") as handle:
        for r in clean_profiles:
            handle.write(canonical(r)+b"\n")
    (dest/"accounts.json").write_bytes(canonical(accounts))
    (dest/"rankings.json").write_bytes(canonical(rankings))
    report = "# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions\n\n"
    report += "E6_CREST prototype: fixed source E4, empirical percentiles, no label-based evaluation or weight selection.\n\n"
    report += "| Account | Raw s0 | q0 | D | R | Evidence |\n|---|---:|---:|---:|---:|---|\n"
    for a in accounts:
        s = a["statistics"]
        report += f"| {a['account_id']} | {a['raw_baseline_score']:.8g} | {a['calibrated_score']:.8g} | {s['sensitivity']} | {s['robustness']} | {s['evidence_status']} |\n"
    report += "\nConcentration is diagnostic by family/budget stratum; undefined values are retained. These are not fraud probabilities or causal explanations.\n"
    (dest/"report.md").write_text(report,encoding="utf-8")
    files = ["config.json","model.joblib","calibration.json","intervention_scores.jsonl","accounts.json","rankings.json","report.md"]
    code = {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted((ROOT/"backend/app").rglob("*.py"))}
    manifest = {"protocol":PROTOCOL,"stage":"e6-crest-scoring","project_title":"Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions",
        "algorithm":{"implementation_id":VERSION,"modes":config.modes},
        "configuration":config.model_dump(),"configuration_sha256":sha(canonical(config.model_dump())),
        "source":source["manifest"]["source"],"evaluation":evaluation["manifest"]["source"],
        "intervention_artifacts":{"source_manifest_sha256":source["manifest_sha256"],"evaluation_manifest_sha256":evaluation["manifest_sha256"]},
        "historical_cutoffs":{"source":source["manifest"]["historical_cutoff"],"evaluation":evaluation["manifest"]["historical_cutoff"]},
        "feature_inputs":{"source_baseline_sha256":source["manifest"]["artifact_sha256"]["baseline.json"],
            "evaluation_baseline_sha256":evaluation["manifest"]["artifact_sha256"]["baseline.json"],
            "evaluation_interventions_sha256":evaluation["manifest"]["artifact_sha256"]["interventions.jsonl"],
            "evaluation_matrix_sha256":sha(np.asarray(values,dtype=np.float32).tobytes())},
        "feature_schema":{"version":"canonical19-plus-egonet4-v1","selected":CANONICAL_TRANSFER_FEATURES},
        "model_identity":detector.identity,"model_id":detector.model_id,"model_sha256":sha(model_content),
        "preprocessing":{"implementation_id":"identity-float32-v1","fit_statistics":"none; matches Phase 2 raw-feature E4"},
        "hyperparameters":detector.model.get_params(),"model_seed":config.model_seed,"graph_seed":evaluation["manifest"]["graph_seed"],
        "intervention_seed":evaluation["manifest"]["intervention_seed"],"split_policy":"explicit predeclared membership; no stratification or labels",
        "membership":{"train_ids":train_ids,"evaluation_ids":eval_ids},"training_matrix_sha256":detector.training_matrix_sha256,
        "calibration_reference":"calibration.json","equations":{"raw":"-IsolationForest.decision_function",
            "delta":"q0-qm","D":"mean of valid family median signed deltas",
            "R":"mean of sufficiently supported family (1-median absolute delta)",
            "concentration":"sum((positive_delta/sum_positive_delta)^2) within family and budget stratum; diagnostic only",
            "hybrid":"clip(q0+alpha*D-beta*q0*(1-R),0,1)"},
        "versions":{"python":platform.python_version(),"numpy":np.__version__,"sklearn":sklearn.__version__},
        "code_files":code,"code_sha256":sha(canonical(code)),
        "artifacts":{p:p for p in files},"artifact_sha256":{p:sha((dest/p).read_bytes()) for p in files},
        "timing_seconds":{"source_fit":fit_seconds,"batch_scoring":scoring_seconds,"total":time.perf_counter()-start},
        "memory":{"peak_traced_python_bytes":tracemalloc.get_traced_memory()[1] if tracemalloc.is_tracing() else None,
                  "scope":"caller-enabled tracemalloc; excludes untraced native/RSS memory"},
        "limitations":["no accuracy/novelty validation","transductive source representations","PaySim provenance unresolved",
                       "family aggregates may pool different budgets unless ranking_stratum specified",
                       "calibration saturation can conceal raw score changes","no concentration ranking contribution"]}
    (dest/"manifest.json").write_bytes(canonical(manifest))
    return manifest
