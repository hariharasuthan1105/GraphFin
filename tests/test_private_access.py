"""Security fixtures generate credentials at runtime; no values are persisted."""
from dataclasses import dataclass, field
import hashlib
import os
import secrets
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.app.runtime import create_app
from backend.app.core.private_access import PrivatePolicy, secret_digest
from backend.app.research_demo import create_app as original_local_app

HOST = 'graphfin-test-internal'


@dataclass
class Case:
    client: TestClient
    token: str = field(repr=False)
    previous: str = field(repr=False)

    def headers(self):
        return {'Authorization': 'Bearer ' + self.token}


@pytest.fixture
def private_case(monkeypatch):
    token, previous = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    values = dict(GRAPHFIN_SECURITY_PROFILE='render_private', RENDER='true',
                  RENDER_SERVICE_TYPE='pserv', PORT='10000', GRAPHFIN_PRIVATE_HOSTS=HOST,
                  GRAPHFIN_PRIVATE_TOKEN=token, GRAPHFIN_PRIVATE_PREVIOUS_TOKEN=previous,
                  GRAPHFIN_DEMO_ENABLE_DOCS='0', GRAPHFIN_DEMO_ORIGINS='')
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    with TestClient(create_app(), base_url='http://' + HOST, client=('10.20.30.40', 12345)) as client:
        yield Case(client, token, previous)


def test_explicit_private_startup_and_authorized_health(private_case):
    c = private_case
    r = c.client.get('/health', headers=c.headers())
    assert r.status_code == 200 and r.json()['mode'] == 'render-private-review'
    assert r.headers['cache-control'] == 'private, no-store'
    assert r.headers['x-content-type-options'] == 'nosniff'
    assert c.token not in r.text and c.previous not in r.text


def test_real_entry_import_uses_explicit_private_environment(private_case):
    import subprocess
    import sys
    from pathlib import Path
    p = subprocess.run([sys.executable, '-m', 'scripts.check_startup'],
                       cwd=Path(__file__).resolve().parents[1],
                       capture_output=True, text=True, timeout=15)
    assert p.returncode == 0
    import json
    assert json.loads(p.stdout)['mode'] == 'render_private'
    assert private_case.token not in p.stdout + p.stderr


def test_explicit_authority_port_supported(private_case, monkeypatch):
    monkeypatch.setenv('GRAPHFIN_PRIVATE_HOSTS', HOST + ':10000')
    with TestClient(create_app(), base_url='http://' + HOST + ':10000') as c:
        assert c.get('/health', headers=private_case.headers()).status_code == 200


def test_no_automatic_cloud_profile(monkeypatch):
    monkeypatch.delenv('GRAPHFIN_SECURITY_PROFILE', raising=False)
    monkeypatch.setenv('RENDER', 'true')
    monkeypatch.setenv('RENDER_SERVICE_TYPE', 'pserv')
    with TestClient(create_app(), base_url='http://127.0.0.1', client=('10.1.2.3', 12345)) as c:
        assert c.get('/health').status_code == 403


def test_original_local_entry_unchanged_under_private_environment(private_case):
    with TestClient(original_local_app(), base_url='http://127.0.0.1', client=('10.1.2.3', 12345)) as c:
        assert c.get('/health').status_code == 403


@pytest.mark.parametrize('path', ['/health', '/api/v1/research/overview', '/api/v1/research/datasets',
                                  '/api/v1/research-reports/datasets/ibm-5k/report.pdf',
                                  '/api/v1/graph-explorer/catalog'])
def test_no_authentication_bypass(private_case, path):
    r = private_case.client.get(path)
    assert r.status_code == 401
    assert r.headers['www-authenticate'] == 'Bearer'
    assert set(r.json()) == {'error', 'message', 'details'} and r.json()['details'] == []


def test_invalid_authentication(private_case):
    bad = secrets.token_urlsafe(32)
    r = private_case.client.get('/health', headers={'Authorization': 'Bearer ' + bad})
    assert r.status_code == 401 and bad not in r.text


def test_query_auth_is_never_accepted(private_case):
    assert private_case.client.get('/health', params={'token': private_case.token}).status_code == 401


def test_duplicate_authorization_rejected(private_case):
    h = private_case.headers()['Authorization']
    assert private_case.client.get('/health', headers=[('Authorization', h), ('Authorization', h)]).status_code == 401


def test_rotation_previous_credential_accepted(private_case):
    assert private_case.client.get('/health', headers={'Authorization': 'Bearer ' + private_case.previous}).status_code == 200


def test_removed_previous_credential_rejected(private_case, monkeypatch):
    monkeypatch.delenv('GRAPHFIN_PRIVATE_PREVIOUS_TOKEN')
    with TestClient(create_app(), base_url='http://' + HOST) as c:
        assert c.get('/health', headers={'Authorization': 'Bearer ' + private_case.previous}).status_code == 401


@pytest.mark.parametrize('host', ['public.invalid', 'localhost', '*', 'user@' + HOST,
                                 HOST + '/path', HOST + '.', HOST + ':9999', HOST + ' ', ' ' + HOST])
def test_bad_request_hosts(private_case, host):
    assert private_case.client.get('/health', headers={**private_case.headers(), 'Host': host}).status_code == 400


@pytest.mark.parametrize('hosts', [[], [(b'host', HOST.encode()), (b'host', HOST.encode())]])
def test_missing_and_duplicate_host(private_case, hosts):
    # HTTP TestClient restores a missing Host; supply the actual ASGI scope instead.
    import asyncio
    from backend.app.core.private_access import PrivateReadOnlyBoundary
    sent = []
    async def inner(scope, receive, send):
        raise AssertionError('Denied request reached a data handler.')
    async def receive():
        return {'type': 'http.request', 'body': b''}
    async def send(message):
        sent.append(message)
    boundary = PrivateReadOnlyBoundary(inner, PrivatePolicy.from_environment())
    asyncio.run(boundary({'type': 'http', 'method': 'GET', 'headers': hosts}, receive, send))
    assert sent[0]['status'] == 400


def test_forwarded_host_never_substitutes_for_host(private_case):
    assert private_case.client.get('/health', headers={**private_case.headers(), 'Host': 'evil.invalid',
                    'X-Forwarded-Host': HOST, 'X-Forwarded-For': '127.0.0.1'}).status_code == 400


@pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
def test_read_only_with_approved_credential(private_case, method):
    assert private_case.client.request(method, '/api/v1/research/overview', headers=private_case.headers()).status_code == 405


@pytest.mark.parametrize('path', ['/api/v1/transactions', '/api/v1/datasets', '/api/v1/anomalies/paysim',
                                  '/api/v1/anomalies/paysim/train', '/api/v1/graph/paysim/nodes',
                                  '/api/v1/reports/generate', '/docs', '/api/v1/openapi.json'])
def test_legacy_and_docs_not_mounted(private_case, path):
    assert private_case.client.get(path, headers=private_case.headers()).status_code == 404


def test_browser_origin_not_allowed(private_case):
    r = private_case.client.get('/health', headers={**private_case.headers(), 'Origin': 'http://' + HOST})
    assert r.status_code == 403 and 'access-control-allow-origin' not in r.headers


def test_missing_artifacts_and_no_record_disclosure(private_case):
    c = private_case
    r = c.client.get('/api/v1/research/overview', headers=c.headers())
    assert r.status_code == 200 and r.json()['status'] in ('verified', 'unavailable')
    d = c.client.get('/api/v1/research/diagnostics', headers=c.headers()).json()
    assert d['status'] in ('exploratory', 'unavailable')
    assert c.client.get('/api/v1/research/datasets', headers=c.headers()).status_code in (200, 503)
    g = c.client.get('/api/v1/graph-explorer/catalog', headers=c.headers()).json()
    assert all(x['status'] == 'unavailable' and x['approved_scope_nodes'] == 0 for x in g['datasets'])


def test_explicit_missing_artifacts_and_no_record_disclosure(private_case, tmp_path):
    from backend.app.services.research_catalog_service import ResearchCatalogService, get_research_catalog
    empty_catalog = ResearchCatalogService(root=tmp_path)
    private_case.client.app.dependency_overrides[get_research_catalog] = lambda: empty_catalog
    try:
        c = private_case
        r = c.client.get('/api/v1/research/overview', headers=c.headers())
        assert r.status_code == 200 and r.json()['status'] == 'unavailable' and r.json()['datasets'] == []
        d = c.client.get('/api/v1/research/diagnostics', headers=c.headers()).json()
        assert d['status'] == 'unavailable' and d['items'] == []
        assert c.client.get('/api/v1/research/datasets', headers=c.headers()).status_code == 503
        g = c.client.get('/api/v1/graph-explorer/catalog', headers=c.headers()).json()
        assert all(x['status'] == 'unavailable' and x['approved_scope_nodes'] == 0 for x in g['datasets'])
    finally:
        private_case.client.app.dependency_overrides.pop(get_research_catalog, None)


@pytest.mark.parametrize('key', ['GRAPHFIN_PRIVATE_TOKEN', 'GRAPHFIN_PRIVATE_HOSTS'])
def test_missing_required_configuration(private_case, monkeypatch, key):
    monkeypatch.delenv(key)
    with pytest.raises(ValueError):
        create_app()


@pytest.mark.parametrize('key,value', [
    ('GRAPHFIN_SECURITY_PROFILE', 'unknown'), ('RENDER', 'false'), ('RENDER_SERVICE_TYPE', 'web'),
    ('GRAPHFIN_PRIVATE_TOKEN', 'invalid'), ('GRAPHFIN_PRIVATE_HOSTS', '*'),
    ('GRAPHFIN_PRIVATE_HOSTS', 'localhost'), ('GRAPHFIN_PRIVATE_HOSTS', 'service.onrender.com'),
    ('GRAPHFIN_PRIVATE_HOSTS', '10.0.0.1'), ('GRAPHFIN_PRIVATE_HOSTS', HOST + ':9999'),
    ('GRAPHFIN_PRIVATE_HOSTS', HOST + ',' + HOST), ('GRAPHFIN_PRIVATE_HOSTS', HOST + ','),
    ('GRAPHFIN_DEMO_ENABLE_DOCS', '1'), ('GRAPHFIN_DEMO_ORIGINS', 'http://localhost:5173'),
    ('PORT', '0'), ('PORT', '65536')])
def test_insecure_startup_rejected(private_case, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        create_app()


def test_duplicate_rotation_credential_rejected(private_case, monkeypatch):
    monkeypatch.setenv('GRAPHFIN_PRIVATE_PREVIOUS_TOKEN', private_case.token)
    with pytest.raises(ValueError):
        create_app()


def test_both_digests_use_constant_time_comparison(private_case):
    policy = PrivatePolicy.from_environment()
    with patch('backend.app.core.private_access.hmac.compare_digest', wraps=__import__('hmac').compare_digest) as compare:
        assert policy.authenticates(private_case.token.encode()) is True
        assert compare.call_count == 2
    assert private_case.token not in repr(policy)


def test_websocket_denied(private_case):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect) as error:
        with private_case.client.websocket_connect('/anything', headers=private_case.headers()):
            pass
    assert error.value.code == 1008
