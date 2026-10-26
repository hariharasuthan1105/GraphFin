"""Controlled loopback-only saved-evidence app; never mounts operational routes.

python -m uvicorn backend.app.research_demo:app --host 127.0.0.1 --port 8000 --no-proxy-headers
"""
from dataclasses import dataclass
import ipaddress
import os
from urllib.parse import urlsplit

from fastapi import FastAPI
from starlette.responses import JSONResponse

from .api.routes import research, dataset_reports, graph_explorer
from .core.exceptions import register_exception_handlers

TITLE = "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions"
LOCAL_HOSTS = frozenset(("localhost", "127.0.0.1", "::1"))


def local_origin(value):
    """Validate an exact local browser origin, without resolving DNS."""
    try:
        parsed = urlsplit(value)
        parsed.port  # Reject malformed/out-of-range ports.
        return (parsed.scheme in ("http", "https") and parsed.hostname in LOCAL_HOSTS
                and parsed.username is None and parsed.password is None
                and parsed.path in ("", "/") and not parsed.query and not parsed.fragment)
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class DemoPolicy:
    origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")
    enable_docs: bool = False

    def __post_init__(self):
        if any(not local_origin(origin) for origin in self.origins):
            raise ValueError("Controlled demo origins must be explicit loopback URLs.")

    @classmethod
    def from_environment(cls):
        flag = os.environ.get("GRAPHFIN_DEMO_ENABLE_DOCS", "0")
        if flag not in ("0", "1"):
            raise ValueError("GRAPHFIN_DEMO_ENABLE_DOCS must be 0 or 1.")
        raw = os.environ.get("GRAPHFIN_DEMO_ORIGINS")
        origins = cls().origins if raw is None else tuple(
            item.strip().rstrip("/") for item in raw.split(",") if item.strip())
        return cls(origins=origins, enable_docs=flag == "1")


class LocalReadOnlyBoundary:
    def __init__(self, app, policy):
        self.app = app
        self.policy = policy

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def private_send(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", [])
                           if k.lower() not in (b"cache-control", b"x-content-type-options")]
                message = {**message, "headers": headers + [
                    (b"cache-control", b"private, no-store"),
                    (b"x-content-type-options", b"nosniff")]}
            await send(message)

        async def deny(code, error, message):
            response = JSONResponse({"error": error, "message": message, "details": []},
                                    status_code=code,
                                    headers={"Allow": "GET"} if code == 405 else None)
            await response(scope, receive, private_send)

        try:
            peer = ipaddress.ip_address((scope.get("client") or ("", 0))[0])
            peer = getattr(peer, "ipv4_mapped", None) or peer
            allowed = peer.is_loopback
        except ValueError:
            allowed = False
        if not allowed:
            await deny(403, "DEMO_LOCAL_ONLY", "Controlled demonstration accepts loopback peers only.")
            return
        hosts = [v.decode("latin-1") for k, v in scope["headers"] if k.lower() == b"host"]
        if (len(hosts) != 1 or any(c in hosts[0] for c in "/\\?#@")
                or not local_origin("http://" + hosts[0])):
            await deny(400, "DEMO_HOST_DENIED", "A loopback Host header is required.")
            return
        origins = [v.decode("latin-1") for k, v in scope["headers"] if k.lower() == b"origin"]
        if len(origins) > 1 or (origins and origins[0] not in self.policy.origins):
            await deny(403, "DEMO_ORIGIN_DENIED", "Browser origin is not approved for this local demonstration.")
            return
        if scope["method"] != "GET":
            await deny(405, "DEMO_READ_ONLY", "Controlled demonstration supports GET requests only.")
            return
        await self.app(scope, receive, private_send)


def create_app(policy=None):
    policy = policy if policy is not None else DemoPolicy.from_environment()
    application = FastAPI(
        title=TITLE, version="controlled-research-demo-v1",
        docs_url="/docs" if policy.enable_docs else None, redoc_url=None,
        openapi_url="/api/v1/openapi.json" if policy.enable_docs else None,
    )
    register_exception_handlers(application)
    application.add_middleware(LocalReadOnlyBoundary, policy=policy)
    # Deliberately avoid main.py/api.router: those mount legacy mutation/raw APIs.
    for router in (research.router, dataset_reports.router, graph_explorer.router):
        application.include_router(router, prefix="/api/v1")

    @application.get("/health")
    @application.get("/api/v1/health")
    async def health():
        return {"status": "healthy", "mode": "controlled-research-demo",
                "public_deployment_approved": False}

    return application


app = create_app()
