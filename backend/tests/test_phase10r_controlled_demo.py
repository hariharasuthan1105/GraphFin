"""Controlled-profile access regressions; synthetic saved-artifact fixtures only."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.tests.test_phase9_graph_explorer import lens
from backend.tests.test_phase7_research_api import research
from backend.app.main import app as legacy_app
from backend.app.research_demo import create_app, DemoPolicy


@pytest.fixture
def demo(lens):
    app = create_app()
    app.dependency_overrides.update(legacy_app.dependency_overrides)
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 42000)) as client:
        yield client, app, lens


def test_saved_workflow_and_pdf_survive(demo):
    c, _, _ = demo
    for path in ("/health", "/api/v1/health", "/api/v1/research/overview",
                 "/api/v1/research/datasets/ibm-5k", "/api/v1/research/experiments",
                 "/api/v1/research/model-seeds", "/api/v1/research/reproducibility"):
        response = c.get(path)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
    response = c.get("/api/v1/research-reports/datasets/ibm-5k/report.pdf")
    assert response.status_code == 200 and response.content.startswith(b"%PDF-")
    opening = c.get("/api/v1/graph-explorer/session", params={
        "dataset_id": "ibm-5k", "experiment_id": "baseline-5k-E4-s42-m42"}).json()
    response = c.get("/api/v1/graph-explorer/neighborhood",
                     headers={"X-Graph-Session": opening["session_id"]},
                     params={"focus_ref": opening["focus_ref"]})
    assert response.status_code == 200 and response.json()["nodes"]
    assert "SECRET_" not in response.text


@pytest.mark.parametrize("path", [
    "/api/v1/graph/paysim/summary", "/api/v1/graph/paysim/nodes",
    "/api/v1/analytics/paysim/features", "/api/v1/datasets",
    "/api/v1/transactions", "/api/v1/anomalies/paysim",
    "/api/v1/evaluation/paysim", "/api/v1/reports/generate",
    "/api/v1/stream/status", "/api/v1/tax/config", "/docs", "/api/v1/openapi.json"])
def test_legacy_raw_operational_and_docs_routes_absent(demo, path):
    assert demo[0].get(path).status_code == 404


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def test_non_read_methods_denied_before_handlers(demo, method):
    response = demo[0].request(method, "/api/v1/research/overview")
    assert response.status_code == 405 and response.headers["allow"] == "GET"
    assert response.json()["error"] == "DEMO_READ_ONLY"


@pytest.mark.parametrize("peer", ["203.0.113.5", "::ffff:203.0.113.5", "testclient"])
def test_nonlocal_peers_cannot_spoof_forwarded_headers(peer):
    with TestClient(create_app(), base_url="http://127.0.0.1", client=(peer, 1234)) as c:
        response = c.get("/health", headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 403
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("host", ["public.example", "localhost.evil", "user@localhost", "localhost:99999",
                                  "localhost/", "localhost\\escape", "localhost?query", "localhost#fragment"])
def test_public_or_malformed_host_rejected(demo, host):
    assert demo[0].get("/health", headers={"Host": host}).status_code == 400


def test_origin_allowlist_and_no_cors_wildcard(demo):
    c, _, _ = demo
    assert c.get("/health", headers={"Origin": "https://untrusted.invalid"}).status_code == 403
    response = c.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-credentials" not in response.headers


@pytest.mark.parametrize("origin", ["*", "https://public.example", "http://user:pass@localhost", "http://localhost/path"])
def test_configuration_cannot_expand_origins_to_public_hosts(origin):
    with pytest.raises(ValueError, match="loopback"):
        DemoPolicy(origins=(origin,))


def test_docs_opt_in_never_mounts_legacy_routes():
    app = create_app(DemoPolicy(enable_docs=True))
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 1234)) as c:
        schema = c.get("/api/v1/openapi.json").json()
    paths = schema["paths"]
    assert len(paths) == 20 and all(set(v) == {"get"} for v in paths.values())
    assert not any(p.startswith(("/api/v1/graph/", "/api/v1/anomalies/")) for p in paths)


def test_invalid_docs_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("GRAPHFIN_DEMO_ENABLE_DOCS", "yes")
    with pytest.raises(ValueError, match="0 or 1"):
        create_app()


def test_environment_origin_configuration(monkeypatch):
    monkeypatch.setenv("GRAPHFIN_DEMO_ORIGINS", "http://127.0.0.1:4290")
    policy = DemoPolicy.from_environment()
    assert policy.origins == ("http://127.0.0.1:4290",)


def test_profile_startup_does_not_fit_load_or_preload(demo):
    app = demo[1]
    def forbidden(*args, **kwargs):
        raise AssertionError("Controlled demo must not start operational computations")
    with patch("sklearn.ensemble.IsolationForest.fit", forbidden), \
         patch("joblib.load", forbidden), \
         patch("backend.app.services.dataset_registry.dataset_registry.load_paysim", forbidden), \
         patch("backend.app.services.graph_service.GraphService.build_graph", forbidden):
        with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 1234)) as c:
            assert c.get("/api/v1/research/overview").status_code == 200


def test_fresh_import_excludes_main_and_operational_router():
    env = dict(os.environ, GRAPHFIN_DEMO_ENABLE_DOCS="0")
    code = "import sys,json; import backend.app.research_demo; print(json.dumps({'main': 'backend.app.main' in sys.modules, 'router': 'backend.app.api.router' in sys.modules}))"
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {"main": False, "router": False}


@pytest.mark.parametrize("peer", ["127.0.0.1", "::1", "::ffff:127.0.0.1"])
def test_local_peers_are_accepted(peer):
    with TestClient(create_app(), base_url="http://127.0.0.1", client=(peer, 1234)) as c:
        assert c.get("/health").status_code == 200


def test_duplicate_host_or_origin_headers_are_denied(demo):
    c, _, _ = demo
    assert c.get("/health", headers=[("Host", "localhost"), ("Host", "127.0.0.1")]).status_code == 400
    assert c.get("/health", headers=[("Origin", "http://127.0.0.1:5173"),
                                    ("Origin", "http://127.0.0.1:5173")]).status_code == 403


def test_websocket_operational_access_is_denied(demo):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect) as exc:
        with demo[0].websocket_connect("/api/v1/stream/ws"):
            pass
    assert exc.value.code == 1008
