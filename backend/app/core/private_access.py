"""Small shared-secret service boundary; no data/ML/network discovery code."""
import base64
from dataclasses import dataclass, field
import hashlib
import hmac
import os
import re
from starlette.responses import JSONResponse

HOST_LABEL = re.compile(r'[a-z][a-z0-9-]{0,61}[a-z0-9]|[a-z]')
TOKEN = re.compile(r'[A-Za-z0-9_-]{43}')


def authority(value, port):
    """Exact Render internal single-label DNS authority, optional explicit port.

    No wildcard, IP literal, public FQDN, userinfo, trailing dot or URL is supported.
    Render service-address hostname comes from operator-reviewed Connect/Internal.
    """
    if not isinstance(value, str) or not value.isascii() or value != value.strip():
        raise ValueError('Invalid private Host configuration.')
    parts = value.lower().split(':')
    if len(parts) not in (1, 2) or not HOST_LABEL.fullmatch(parts[0]) or parts[0] == 'localhost':
        raise ValueError('Invalid private Host configuration.')
    if len(parts) == 2 and parts[1] != str(port):
        raise ValueError('Private Host port must match the configured service port.')
    return value.lower()


def secret_digest(value):
    # Exactly 32 random bytes, encoded canonically as unpadded base64url.
    # Shape validation does not prove entropy: generation must use a CSPRNG.
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError('A canonical 256-bit private credential is required.')
    decoded = base64.urlsafe_b64decode(value + '=')
    if base64.urlsafe_b64encode(decoded).decode().rstrip('=') != value:
        raise ValueError('A canonical 256-bit private credential is required.')
    return hashlib.sha256(value.encode('ascii')).digest()


@dataclass(frozen=True)
class PrivatePolicy:
    hosts: frozenset[str]
    digests: tuple[bytes, bytes] = field(repr=False)

    @classmethod
    def from_environment(cls):
        if os.environ.get('RENDER') != 'true' or os.environ.get('RENDER_SERVICE_TYPE') != 'pserv':
            raise ValueError('Private profile requires explicit Render private-service configuration.')
        if os.environ.get('GRAPHFIN_DEMO_ENABLE_DOCS', '0') != '0' or os.environ.get('GRAPHFIN_DEMO_ORIGINS', ''):
            raise ValueError('Private profile forbids browser origins and API docs.')
        raw_port = os.environ.get('PORT', '10000')
        if not re.fullmatch(r'[1-9][0-9]{0,4}', raw_port) or not 1 <= int(raw_port) <= 65535:
            raise ValueError('Invalid private service port.')
        raw_hosts = os.environ.get('GRAPHFIN_PRIVATE_HOSTS', '')
        entries = raw_hosts.split(',')
        if not raw_hosts or len(entries) > 8 or any(not v for v in entries):
            raise ValueError('An explicit private Host allowlist is required.')
        hosts = frozenset(authority(v, int(raw_port)) for v in entries)
        if len(hosts) != len(entries):
            raise ValueError('Duplicate private Host configuration.')
        current = secret_digest(os.environ.get('GRAPHFIN_PRIVATE_TOKEN'))
        previous_raw = os.environ.get('GRAPHFIN_PRIVATE_PREVIOUS_TOKEN')
        previous = secret_digest(previous_raw) if previous_raw is not None else bytes(32)
        if hmac.compare_digest(current, previous):
            raise ValueError('Rotation credentials must be distinct.')
        return cls(hosts, (current, previous))

    def authenticates(self, value):
        # Always compare both fixed-length digests; never short-circuit rotation checks.
        candidate = hashlib.sha256(value).digest()
        accepted = False
        for digest in self.digests:
            accepted |= hmac.compare_digest(candidate, digest)
        return accepted


class PrivateReadOnlyBoundary:
    def __init__(self, app, policy):
        self.app, self.policy = app, policy

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            await send({'type': 'websocket.close', 'code': 1008})
            return
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def private_send(message):
            if message['type'] == 'http.response.start':
                headers = [(k, v) for k, v in message.get('headers', [])
                           if k.lower() not in (b'cache-control', b'x-content-type-options')]
                message = {**message, 'headers': headers + [(b'cache-control', b'private, no-store'),
                                                           (b'x-content-type-options', b'nosniff')]}
            await send(message)

        async def deny(status, code):
            headers = {'WWW-Authenticate': 'Bearer'} if status == 401 else {'Allow': 'GET'} if status == 405 else {}
            response = JSONResponse({'error': code, 'message': 'Request denied.', 'details': []},
                                    status_code=status, headers=headers)
            await response(scope, receive, private_send)

        hosts = [v for k, v in scope['headers'] if k.lower() == b'host']
        try:
            host = hosts[0].decode('ascii') if len(hosts) == 1 else ''
            # No trimming, forwarded-header fallback or DNS resolution.
            valid_host = bool(host and host == host.strip() and host.lower() in self.policy.hosts)
        except UnicodeDecodeError:
            valid_host = False
        if not valid_host:
            await deny(400, 'PRIVATE_HOST_DENIED')
            return
        if any(k.lower() == b'origin' for k, _ in scope['headers']):
            await deny(403, 'PRIVATE_ORIGIN_DENIED')
            return
        credentials = [v for k, v in scope['headers'] if k.lower() == b'authorization']
        raw = credentials[0] if len(credentials) == 1 else b''
        token = raw[7:] if len(raw) == 50 and raw.startswith(b'Bearer ') else b''
        if not self.policy.authenticates(token):
            await deny(401, 'PRIVATE_AUTH_REQUIRED')
            return
        if scope['method'] != 'GET':
            await deny(405, 'PRIVATE_READ_ONLY')
            return
        await self.app(scope, receive, private_send)
