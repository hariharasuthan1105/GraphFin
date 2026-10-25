"""Strict reuse of completed Phase 3 artifacts; no graph or label service access."""
import json
import re
from pathlib import Path
import numpy as np
from ...services.research_protocol import PROTOCOL, canonical, sha
from ...services.feature_service import CANONICAL_TRANSFER_FEATURES
from ..interventions.schemas import InterventionConfig, VERSION as INTERVENTION_VERSION
from ..interventions.historical_evidence import event_time
from .frozen_scorer import matrix


def load_bundle(directory, expected_manifest_sha256, dataset_id):
    root = Path(directory).resolve()
    raw = (root/"manifest.json").read_bytes()
    if sha(raw) != expected_manifest_sha256:
        raise ValueError("Intervention manifest checksum mismatch.")
    m = json.loads(raw)
    if m["protocol"] != PROTOCOL or m["stage"] != "evidence-interventions" or m["algorithm"]["implementation_id"] != INTERVENTION_VERSION:
        raise ValueError("Unsupported intervention protocol/implementation.")
    if m["source"]["dataset_id"] != dataset_id:
        raise ValueError("Intervention dataset identity mismatch.")
    if any(not re.fullmatch(r"[0-9a-f]{64}",m["source"].get(k,"")) for k in ["transactions_sha256","history_sha256"]):
        raise ValueError("Missing or malformed dataset/history hash.")
    if m["feature_schema"] != {"version":"canonical19-plus-egonet4-v1","selected":CANONICAL_TRANSFER_FEATURES}:
        raise ValueError("Intervention feature schema mismatch.")
    for name,digest in m["artifact_sha256"].items():
        path = (root/name).resolve()
        if not path.is_relative_to(root) or sha(path.read_bytes()) != digest:
            raise ValueError("Intervention artifact checksum/path mismatch.")
    for name in ["config.json","baseline.json","interventions.jsonl"]:
        if name not in m["artifact_sha256"]:
            raise ValueError("Required artifact not checksummed.")
    configuration = json.loads((root/"config.json").read_bytes())
    if configuration != m["configuration"] or sha(canonical(configuration)) != m["configuration_sha256"]:
        raise ValueError("Intervention configuration mismatch.")
    cfg_raw = dict(configuration)
    focals = cfg_raw.pop("focal_accounts")
    cfg = InterventionConfig(**cfg_raw)
    if cfg.dataset_id != dataset_id or cfg.budget.model_dump() != m["budget"] or cfg.time_kind != m["historical_cutoff"]["time_kind"] or cfg.cutoff != m["historical_cutoff"]["value"]:
        raise ValueError("Intervention configuration identity mismatch.")
    if m["historical_cutoff"]["boundary"] != "<=" or m["source"]["source_identity"] != cfg.source_identity or list(cfg.families) != m["algorithm"]["families"]:
        raise ValueError("Intervention cutoff/source/family metadata mismatch.")
    baseline = json.loads((root/"baseline.json").read_bytes())
    vectors = baseline["focal_features"]
    if set(vectors) != set(focals) or len(focals) != len(set(focals)):
        raise ValueError("Baseline focal coverage mismatch.")
    universe = baseline["account_universe"]
    if len(set(universe)) != len(universe) or not set(focals) <= set(universe):
        raise ValueError("Account universe mismatch.")
    matrix(list(vectors.values()),CANONICAL_TRANSFER_FEATURES)
    rows = [json.loads(line) for line in (root/"interventions.jsonl").read_text().splitlines()]
    if any(sum(r.get("status")==status for r in rows)!=m["results"][status] for status in ["accepted","rejected"]):
        raise ValueError("Intervention result coverage mismatch.")
    if m["population"]["focals"] != len(focals) or m["population"]["accounts"] != len(universe):
        raise ValueError("Intervention population mismatch.")
    seen = set()
    for r in rows:
        focal = r["focal_account"]
        if focal not in vectors or r["status"] not in ("accepted","rejected"):
            raise ValueError("Invalid intervention focal/status.")
        if r["status"] == "rejected":
            if not r.get("reason"):
                raise ValueError("Rejected intervention missing reason.")
            if r.get("family") is not None and r["family"] not in cfg.families:
                raise ValueError("Rejected intervention family mismatch.")
            continue
        if r["family"] not in cfg.families or r["intervention_id"] in seen:
            raise ValueError("Invalid family or duplicate intervention identity.")
        seen.add(r["intervention_id"])
        if r["baseline_features"] != vectors[focal]:
            raise ValueError("Intervention/baseline vector mismatch.")
        matrix([r["intervened_features"]], CANONICAL_TRANSFER_FEATURES)
        if not np.array_equal(np.array(r["intervened_features"])-np.array(r["baseline_features"]),r["feature_difference"]):
            raise ValueError("Feature difference mismatch.")
        ids = r["omitted_transaction_ids"]
        n, total = len(ids), vectors[focal][6]
        if not n or len(set(ids)) != n or r["omitted_count"] != n or total <= 0:
            raise ValueError("Invalid omission cardinality.")
        if not np.isclose(r["omitted_fraction"],n/total,rtol=0,atol=1e-12):
            raise ValueError("Omission fraction mismatch.")
        amount_fraction = r["omitted_amount_fraction"]
        if not np.isfinite(amount_fraction) or not 0 < amount_fraction <= 1:
            raise ValueError("Invalid omitted amount fraction.")
        if n > cfg.budget.max_count or n/total > cfg.budget.max_fraction or total-n < cfg.budget.min_retained or (
            cfg.budget.max_amount_fraction is not None and amount_fraction > cfg.budget.max_amount_fraction):
            raise ValueError("Accepted intervention exceeds budget.")
        expected = sha(canonical([INTERVENTION_VERSION,dataset_id,m["source"]["history_sha256"],
            event_time(cfg.cutoff,cfg.time_kind),universe,focal,r["family"],r["candidate_key"],ids,cfg.model_dump()]))
        if expected != r["intervention_id"]:
            raise ValueError("Intervention semantic identity mismatch.")
    for focal in focals:
        if sum(r["focal_account"]==focal and r["status"]=="accepted" for r in rows) > cfg.budget.max_interventions:
            raise ValueError("Accepted intervention count exceeds configured cap.")
    return {"manifest":m,"manifest_sha256":sha(raw),"configuration":cfg,"baseline":vectors,"records":rows}
