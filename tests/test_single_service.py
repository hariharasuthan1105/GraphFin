"""Targeted regression tests for the GraphFin Free Tier Single-Service Architecture."""
import hashlib
import json
import os
import secrets
import pytest
from starlette.testclient import TestClient

from gateway.auth import hash_examiner_password
from gateway.config import GatewayConfig
from gateway.single_service import create_single_service_app

TEST_EXAMINER_USER = "examiner"
TEST_EXAMINER_PWD = "CorrectExaminerPassword123!"


@pytest.fixture
def single_service_client():
    secret = secrets.token_bytes(32)
    pwd_hash = hash_examiner_password(TEST_EXAMINER_PWD)
    config = GatewayConfig(
        env="test",
        session_secret=secret,
        examiner_username=TEST_EXAMINER_USER,
        examiner_password_hash=pwd_hash,
        mode="single_service",
        cookie_secure=False,
    )
    app = create_single_service_app(config)
    with TestClient(app, base_url="http://testserver") as client:
        yield client, config


def test_single_service_health_and_root(single_service_client):
    client, _ = single_service_client
    # Health endpoint
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["mode"] == "single_service"
    assert data["role"] == "public-research-service"

    # API v1 health
    r_api = client.get("/api/v1/health")
    assert r_api.status_code == 200
    assert r_api.json()["mode"] == "single_service"

    # Root endpoint serves SPA index.html with correct project title
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "<!doctype html>" in r_root.text.lower()
    assert "GraphFin" in r_root.text or "Anomaly Detection" in r_root.text


def test_single_service_unauthenticated_protection(single_service_client):
    client, _ = single_service_client
    # Public routes allowed unauthenticated (returns 200 or 503 when research results are unavailable)
    assert client.get("/api/v1/research/overview").status_code == 200
    assert client.get("/api/v1/research/limitations").status_code in (200, 503)

    # Protected routes reject unauthenticated visitors with 401
    for path in [
        "/api/v1/research/datasets",
        "/api/v1/research/experiments",
        "/api/v1/research/comparisons",
        "/api/v1/research/reproducibility",
        "/api/v1/research/model-seeds",
        "/api/v1/research/diagnostics",
        "/api/v1/graph-explorer/catalog",
        "/api/v1/graph-explorer/session",
        "/api/v1/graph-explorer/neighborhood",
        "/api/v1/research-reports/datasets/ibm-5k/report.pdf",
    ]:
        res = client.get(path)
        assert res.status_code == 401, f"Expected 401 for {path}, got {res.status_code}"
        assert res.json()["error"] == "EXAMINER_AUTH_REQUIRED"
        assert res.headers.get("WWW-Authenticate") == "Cookie"


def test_single_service_login_logout_flow(single_service_client):
    client, config = single_service_client

    # 1. Check initial session state
    r_sess = client.get("/api/auth/session")
    assert r_sess.status_code == 200
    assert r_sess.json()["authenticated"] is False

    # 2. Invalid password rejected
    r_bad = client.post("/api/auth/login", json={"username": TEST_EXAMINER_USER, "password": "WrongPassword"})
    assert r_bad.status_code == 401
    assert r_bad.json()["error"] == "INVALID_CREDENTIALS"

    # 3. Valid scrypt login succeeds and sets session cookie
    r_login = client.post("/api/auth/login", json={"username": TEST_EXAMINER_USER, "password": TEST_EXAMINER_PWD})
    assert r_login.status_code == 200
    body = r_login.json()
    assert body["user"] == TEST_EXAMINER_USER
    csrf_token = body["csrf_token"]
    assert csrf_token is not None
    assert config.cookie_name in client.cookies

    # 4. Authenticated examiner can access protected research endpoints
    r_overview = client.get("/api/v1/research/overview")
    assert r_overview.status_code == 200

    r_cat = client.get("/api/v1/graph-explorer/catalog")
    assert r_cat.status_code == 200
    assert "datasets" in r_cat.json()

    # 5. Logout without CSRF token is rejected
    r_unprotected_logout = client.post("/api/auth/logout")
    assert r_unprotected_logout.status_code == 403
    assert r_unprotected_logout.json()["error"] == "CSRF_VALIDATION_FAILED"

    # 6. Logout with CSRF token succeeds and clears session
    r_logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert r_logout.status_code == 200

    # 7. Subsequent request to protected route is rejected
    assert client.get("/api/v1/graph-explorer/catalog").status_code == 401


def test_single_service_unsafe_methods_and_disallowed_routes(single_service_client):
    client, _ = single_service_client
    # Unsafe HTTP methods on /api/v1 return 405
    for method in ["POST", "PUT", "DELETE", "PATCH"]:
        res = client.request(method, "/api/v1/research/overview")
        assert res.status_code == 405
        assert res.headers.get("Allow") == "GET"
        assert res.json()["error"] == "GATEWAY_READ_ONLY"

    # Disallowed legacy routes return 404
    for route in [
        "/api/v1/transactions",
        "/api/v1/datasets",
        "/api/v1/anomalies/paysim",
        "/api/v1/anomalies/paysim/train",
        "/api/v1/graph/paysim/nodes",
        "/api/v1/reports/generate",
    ]:
        res = client.get(route)
        assert res.status_code == 404
        assert res.json()["error"] == "GATEWAY_ROUTE_FORBIDDEN"


def test_single_service_docs_and_traversal_blocked(single_service_client):
    client, _ = single_service_client
    # Swagger and OpenAPI docs return 404
    for doc in ["/docs", "/redoc", "/openapi.json", "/api/v1/openapi.json"]:
        assert client.get(doc).status_code == 404

    # Path traversal attempts return 404
    for evil in [
        "/..%2F..%2Fetc/passwd",
        "/static/../../etc/passwd",
        "/.env",
        "/render.yaml",
        "/backend/app/main.py",
    ]:
        assert client.get(evil).status_code == 404


def test_single_service_security_headers(single_service_client):
    client, _ = single_service_client
    res = client.get("/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in res.headers.get("Content-Security-Policy", "")


def test_single_service_bearer_auth_and_cors(single_service_client):
    client, _ = single_service_client

    # 1. CORS preflight (OPTIONS)
    r_opts = client.options(
        "/api/v1/research/overview",
        headers={
            "Origin": "https://hariharasuthan1105.github.io",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r_opts.status_code == 200
    assert r_opts.headers.get("access-control-allow-origin") == "https://hariharasuthan1105.github.io"

    # 2. Login returns session_token
    r_login = client.post("/api/auth/login", json={"username": TEST_EXAMINER_USER, "password": TEST_EXAMINER_PWD})
    assert r_login.status_code == 200
    session_token = r_login.json()["session_token"]
    assert session_token is not None

    # 3. Access protected route using Authorization: Bearer <session_token> without cookies
    client_no_cookie = TestClient(client.app, base_url="http://testserver")
    r_bearer = client_no_cookie.get(
        "/api/v1/graph-explorer/catalog",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert r_bearer.status_code == 200
    assert "datasets" in r_bearer.json()
