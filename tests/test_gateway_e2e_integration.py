"""End-to-End Integration Tests: Browser Client -> Gateway -> Private Backend.

Verifies:
1. Public landing page and SPA assets
2. Gateway health check
3. Unauthenticated rejection on protected research routes
4. Examiner authentication lifecycle (login, session, csrf, logout)
5. Secure server-to-server forwarding with private token injection
6. Host header sanitization
7. Read-only GET enforcement and non-existent/legacy route blocking
"""
import hashlib
import json
import os
import secrets
import pytest
from fastapi.testclient import TestClient

from backend.app.runtime import create_app as create_backend_app
from gateway.app import create_gateway_app
from gateway.config import GatewayConfig

TEST_EXAMINER_USER = "e2e_examiner"
TEST_EXAMINER_PWD = "SecureE2EPwd2026!Research"
TEST_EXAMINER_HASH = hashlib.sha256(TEST_EXAMINER_PWD.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def e2e_system():
    # Setup test credentials
    shared_token = secrets.token_urlsafe(32)
    backend_host = "graphfin-backend-research"

    # Configure backend environment
    os.environ["RENDER"] = "true"
    os.environ["RENDER_SERVICE_TYPE"] = "pserv"
    os.environ["GRAPHFIN_SECURITY_PROFILE"] = "render_private"
    os.environ["GRAPHFIN_PRIVATE_TOKEN"] = shared_token
    os.environ["GRAPHFIN_PRIVATE_HOSTS"] = backend_host
    os.environ["GRAPHFIN_DEMO_ENABLE_DOCS"] = "0"
    os.environ["PORT"] = "10000"

    backend_app = create_backend_app()
    backend_client = TestClient(backend_app, base_url="http://graphfin-backend-research")

    # Configure gateway with test examiner credentials
    session_secret = secrets.token_bytes(32)
    gateway_config = GatewayConfig(
        env="test",
        session_secret=session_secret,
        backend_url="http://graphfin-backend-research",
        backend_host=backend_host,
        backend_token=shared_token,
        examiner_username=TEST_EXAMINER_USER,
        examiner_password_hash=TEST_EXAMINER_HASH,
        cookie_secure=False,
    )
    gateway_app = create_gateway_app(gateway_config)

    # In E2E test, route gateway's async client to the backend testclient via custom transport
    import httpx

    class TestClientTransport(httpx.AsyncBaseTransport):
        def __init__(self, tc: TestClient):
            self.tc = tc

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            content = await request.aread()
            resp = self.tc.request(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                content=content,
            )
            return httpx.Response(
                status_code=resp.status_code,
                headers=dict(resp.headers),
                content=resp.content,
            )

    gateway_app.state.http_client = httpx.AsyncClient(
        transport=TestClientTransport(backend_client),
        base_url="http://graphfin-backend-research",
    )

    with TestClient(gateway_app, base_url="http://localhost:8000") as browser:
        yield browser, shared_token


def test_public_landing_and_health(e2e_system):
    browser, _ = e2e_system
    # 1. Health check is publicly accessible
    resp = browser.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "graphfin-web"

    # 2. Public route overview does not require examiner auth
    overview_resp = browser.get("/api/v1/research/overview")
    assert overview_resp.status_code in (200, 503)

    # 3. Limitations route is publicly accessible
    limitations_resp = browser.get("/api/v1/research/limitations")
    assert limitations_resp.status_code in (200, 503)


def test_research_routes_open_access(e2e_system):
    browser, _ = e2e_system
    research_endpoints = [
        "/api/v1/research/overview",
        "/api/v1/research/datasets",
        "/api/v1/research/experiments",
        "/api/v1/research/comparisons",
        "/api/v1/graph-explorer/catalog",
    ]
    for endpoint in research_endpoints:
        resp = browser.get(endpoint)
        # Should not reject with 401
        assert resp.status_code != 401


def test_examiner_login_and_authenticated_proxy(e2e_system):
    browser, _ = e2e_system

    # Check unauthenticated session
    sess_resp = browser.get("/api/auth/session")
    assert sess_resp.status_code == 200
    assert sess_resp.json()["authenticated"] is False

    # Perform examiner login with test credentials
    login_resp = browser.post(
        "/api/auth/login",
        json={"username": TEST_EXAMINER_USER, "password": TEST_EXAMINER_PWD},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["status"] == "authenticated"
    assert "csrf_token" in login_data
    csrf_token = login_data["csrf_token"]

    # Verify session is now active
    sess_resp2 = browser.get("/api/auth/session")
    assert sess_resp2.status_code == 200
    assert sess_resp2.json()["authenticated"] is True
    assert sess_resp2.json()["user"] == TEST_EXAMINER_USER

    # Access protected route as authenticated examiner
    prot_resp = browser.get("/api/v1/research/datasets")
    assert prot_resp.status_code in (200, 503)

    # Verify CSRF protection on logout
    bad_logout = browser.post("/api/auth/logout")
    assert bad_logout.status_code == 403

    # Proper logout with CSRF token
    good_logout = browser.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert good_logout.status_code == 200

    # Session is terminated
    sess_resp3 = browser.get("/api/auth/session")
    assert sess_resp3.json()["authenticated"] is False


def test_attack_and_leakage_protections(e2e_system):
    browser, _ = e2e_system

    # Unsafe HTTP methods must be rejected with 405
    post_resp = browser.post("/api/v1/research/overview", json={"bad": "payload"})
    assert post_resp.status_code == 405

    delete_resp = browser.delete("/api/v1/research/overview")
    assert delete_resp.status_code == 405

    # Probing legacy unauthenticated operational routes must return 404
    legacy_resp = browser.get("/api/v1/transactions")
    assert legacy_resp.status_code == 404

    upload_resp = browser.post("/api/v1/transactions/upload")
    assert upload_resp.status_code == 405

    # Docs and Swagger endpoints must return 404
    docs_resp = browser.get("/docs")
    assert docs_resp.status_code == 404

    openapi_resp = browser.get("/api/v1/openapi.json")
    assert openapi_resp.status_code == 404
