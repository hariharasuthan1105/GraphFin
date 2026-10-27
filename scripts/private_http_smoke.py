"""Portable synthetic HTTP validation; credentials exist only in process memory.

Uses a loopback listener even when simulating private-service environment markers.
This is not a Render deployment or proof of Linux signal delivery.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uvicorn


def run():
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    host, token = 'graphfin-validation-internal', secrets.token_urlsafe(32)
    values = dict(GRAPHFIN_SECURITY_PROFILE='render_private', RENDER='true', RENDER_SERVICE_TYPE='pserv',
                  GRAPHFIN_PRIVATE_HOSTS=host, GRAPHFIN_PRIVATE_TOKEN=token, PORT=str(port),
                  GRAPHFIN_DEMO_ENABLE_DOCS='0', GRAPHFIN_DEMO_ORIGINS='')
    previous = {k: os.environ.get(k) for k in values}
    old_rotation = os.environ.pop('GRAPHFIN_PRIVATE_PREVIOUS_TOKEN', None)
    os.environ.update(values)
    # Factory avoids stale global app state when called from a test process.
    config = uvicorn.Config('backend.app.runtime:create_app', factory=True, host='127.0.0.1', port=port,
                            proxy_headers=False, access_log=False, log_config=str(root / 'logging.json'),
                            timeout_graceful_shutdown=15)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run)
    checks = []
    def request(path, expected, auth=True, extra=None, method='GET'):
        headers = {'Host': host}
        if auth:
            headers['Authorization'] = 'Bearer ' + token
        headers.update(extra or {})
        req = Request(f'http://127.0.0.1:{port}' + path, headers=headers, method=method)
        try:
            with urlopen(req, timeout=2) as response:
                status, body = response.status, response.read()
        except HTTPError as response:
            status, body = response.code, response.read()
        if status != expected:
            raise AssertionError('Unexpected synthetic HTTP status.')
        if token.encode() in body:
            raise AssertionError('Credential appeared in response.')
        checks.append({'path': path, 'method': method, 'expected': expected, 'actual': status})
        if body:
            try:
                return json.loads(body)
            except (ValueError, UnicodeDecodeError):
                return body
        return None
    try:
        thread.start()
        deadline = time.monotonic() + 15
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.1)
        if not server.started:
            raise AssertionError('Synthetic private server startup failed.')
        request('/health', 401, auth=False)
        request('/health', 401, extra={'Authorization': 'Bearer ' + secrets.token_urlsafe(32)})
        request('/health', 200)
        request('/health', 400, extra={'Host': 'unapproved.invalid', 'X-Forwarded-Host': host})
        request('/health', 403, extra={'Origin': 'https://unapproved.invalid'})
        overview = request('/api/v1/research/overview', 200)
        assert overview['status'] in ('verified', 'unavailable')
        request('/api/v1/research/datasets', 200 if overview['status'] == 'verified' else 503)
        diagnostics = request('/api/v1/research/diagnostics', 200)
        assert diagnostics['status'] in ('exploratory', 'unavailable')
        request('/api/v1/research-reports/datasets/ibm-5k/report.pdf', 200 if overview['status'] == 'verified' else 503)
        request('/api/v1/transactions', 404)
        request('/api/v1/anomalies/paysim/train', 405, method='POST')
    finally:
        server.should_exit = True
        thread.join(timeout=20)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if old_rotation is not None:
            os.environ['GRAPHFIN_PRIVATE_PREVIOUS_TOKEN'] = old_rotation
    assert not thread.is_alive()
    with socket.socket() as sock:
        sock.settimeout(.3)
        assert sock.connect_ex(('127.0.0.1', port)) != 0
    return {'checks': checks, 'clean_should_exit_shutdown': True,
            'platform': __import__('sys').platform, 'public_binding_executed': False,
            'render_service_created': False}


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
