"""Comprehensive Security Regression Tests for GraphFin Web Gateway."""
import hashlib
import json
import os
import secrets
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
import httpx

from gateway.app import create_gateway_app
from gateway.config import GatewayConfig
from gateway.security import create_signed_session, verify_session

TEST_EXAMINER_USER = "test_evaluator"
TEST_EXAMINER_PWD = "SecureTestPassword2026!Exam"
TEST_EXAMINER_HASH = hashlib.sha256(TEST_EXAMINER_PWD.encode("utf-8")).hexdigest()


@pytest.fixture
def gateway_client():
    secret = secrets.token_bytes(32)
    config = GatewayConfig(
        env="test",
        session_secret=secret,
        backend_url="http://graphfin-backend-research:10000",
        backend_host="graphfin-backend-research",
        backend_token="test-secret-backend-token-43-chars-placeholder",
        examiner_username=TEST_EXAMINER_USER,
        examiner_password_hash=TEST_EXAMINER_HASH,
        cookie_secure=False,
    )
    app = create_gateway_app(config)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    app.state.http_client = mock_client
    with TestClient(app, base_url="http://localhost:8000") as client:
        yield client, mock_client, config


def test_public_health_and_session_unauthenticated(gateway_client):
    client, _, _ = gateway_client
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "graphfin-web"

    r = client.get("/api/auth/session")
    assert r.status_code == 200
    assert r.json()["authenticated"] is False


def test_research_routes_open_to_visitors(gateway_client):
    client, mock_http, _ = gateway_client
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b'{"status": "ok"}',
    )
    research_paths = [
        "/api/v1/research/overview",
        "/api/v1/research/datasets",
        "/api/v1/research/experiments",
        "/api/v1/graph-explorer/catalog",
        "/api/v1/graph-explorer/neighborhood",
    ]
    for path in research_paths:
        r = client.get(path)
        # Should proxy successfully without 401
        assert r.status_code == 200


def test_invalid_login_rejected(gateway_client):
    client, _, _ = gateway_client
    r = client.post("/api/auth/login", json={"username": "wrong_user", "password": "wrong_password"})
    assert r.status_code == 401
    assert r.json()["error"] == "INVALID_CREDENTIALS"


def test_valid_login_sets_secure_session_cookie(gateway_client):
    client, _, config = gateway_client
    r = client.post("/api/auth/login", json={"username": TEST_EXAMINER_USER, "password": TEST_EXAMINER_PWD})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "authenticated"
    assert data["user"] == TEST_EXAMINER_USER
    assert "csrf_token" in data

    cookie = r.cookies.get(config.cookie_name)
    assert cookie is not None

    session = verify_session(config.session_secret, cookie)
    assert session is not None
    assert session["uid"] == TEST_EXAMINER_USER
    assert session["role"] == "examiner"


def test_authenticated_examiner_proxies_to_backend(gateway_client):
    client, mock_http, config = gateway_client
    # Log in
    login_resp = client.post("/api/auth/login", json={"username": TEST_EXAMINER_USER, "password": TEST_EXAMINER_PWD})
    assert login_resp.status_code == 200

    # Configure mock upstream response
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=json.dumps({"status": "available", "datasets": ["ibm-5k", "ibm-50k"]}).encode(),
    )

    r = client.get("/api/v1/research/datasets")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "available"

    # Verify authorization header and host were attached server-to-server
    call_kwargs = mock_http.request.call_args[1]
    assert call_kwargs["headers"]["Host"] == config.backend_host
    assert call_kwargs["headers"]["Authorization"] == f"Bearer {config.backend_token}"
    assert call_kwargs["method"] == "GET"


def test_unsafe_http_methods_rejected(gateway_client):
    client, _, _ = gateway_client
    methods = ["POST", "PUT", "DELETE", "PATCH"]
    for method in methods:
        r = client.request(method, "/api/v1/research/overview")
        assert r.status_code == 405
        assert r.json()["error"] == "GATEWAY_READ_ONLY"


def test_disallowed_operational_routes_rejected(gateway_client):
    client, _, _ = gateway_client
    client.post("/api/auth/login", json={"username": TEST_EXAMINER_USER, "password": TEST_EXAMINER_PWD})
    forbidden_routes = [
        "/api/v1/transactions",
        "/api/v1/transactions/upload",
        "/api/v1/anomalies/paysim/train",
        "/api/v1/stream/simulate",
        "/api/v1/tax/calculate",
        "/docs",
        "/api/v1/openapi.json",
    ]
    for route in forbidden_routes:
        r = client.get(route)
        assert r.status_code == 404


def test_csrf_protection_on_logout(gateway_client):
    client, _, config = gateway_client
    login_resp = client.post("/api/auth/login", json={"username": TEST_EXAMINER_USER, "password": TEST_EXAMINER_PWD})
    csrf_token = login_resp.json()["csrf_token"]

    bad_logout = client.post("/api/auth/logout")
    assert bad_logout.status_code == 403
    assert bad_logout.json()["error"] == "CSRF_VALIDATION_FAILED"

    good_logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert good_logout.status_code == 200

    sess_check = client.get("/api/auth/session")
    assert sess_check.json()["authenticated"] is False


def test_security_headers_present(gateway_client):
    client, _, _ = gateway_client
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in resp.headers


def test_path_traversal_blocked(gateway_client):
    client, _, _ = gateway_client
    traversal_paths = [
        "/../../etc/passwd",
        "/../../../backend/runtime.py",
        "/..%2F..%2Fetc/passwd",
        "/./../../render.yaml",
    ]
    for p in traversal_paths:
        r = client.get(p)
        # Traversal attempts must never return 200 or file contents outside dist
        assert r.status_code in (400, 404)


def test_production_mode_fails_fast_without_required_secrets():
    old_env = dict(os.environ)
    try:
        os.environ["GRAPHFIN_GATEWAY_ENV"] = "production"
        os.environ.pop("GRAPHFIN_SESSION_SECRET", None)
        os.environ.pop("GRAPHFIN_BACKEND_TOKEN", None)
        os.environ.pop("GRAPHFIN_PRIVATE_TOKEN", None)
        os.environ.pop("EXAMINER_USERNAME", None)
        os.environ.pop("EXAMINER_PASSWORD_HASH", None)

        with pytest.raises(ValueError, match="GRAPHFIN_SESSION_SECRET"):
            GatewayConfig.from_environment()

        os.environ["GRAPHFIN_SESSION_SECRET"] = "a" * 32
        with pytest.raises(ValueError, match="GRAPHFIN_BACKEND_TOKEN"):
            GatewayConfig.from_environment()

        os.environ["GRAPHFIN_BACKEND_TOKEN"] = "token" * 10
        with pytest.raises(ValueError, match="EXAMINER_USERNAME"):
            GatewayConfig.from_environment()

        os.environ["EXAMINER_USERNAME"] = "examiner"
        with pytest.raises(ValueError, match="EXAMINER_PASSWORD_HASH"):
            GatewayConfig.from_environment()
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_auth_not_configured_fails_closed():
    secret = secrets.token_bytes(32)
    # Config without examiner credentials
    config = GatewayConfig(
        env="test",
        session_secret=secret,
        backend_url="http://graphfin-backend-research:10000",
        backend_host="graphfin-backend-research",
        backend_token="test-token",
        examiner_username="",
        examiner_password_hash="",
    )
    app = create_gateway_app(config)
    with TestClient(app) as client:
        r = client.post("/api/auth/login", json={"username": "examiner", "password": "password"})
        assert r.status_code == 503
        assert r.json()["error"] == "AUTH_NOT_CONFIGURED"
