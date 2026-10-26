"""GraphFin Public Web Application & Examiner Gateway Entry Point."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx

from .auth import router as auth_router, get_current_session
from .config import GatewayConfig
from .proxy import router as proxy_router, ALLOWED_ROUTE_PATTERN, PUBLIC_READ_ROUTES, _check_rate_limit
from backend.app.api.routes import research, dataset_reports, graph_explorer
from backend.app.core.exceptions import register_exception_handlers

TITLE = "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions"


def _apply_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )


class WebSocketRejectMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: GatewayConfig = getattr(app.state, "config", None)
    created_client = False
    # Only two-tier mode requires an upstream HTTP connection pool
    if config and config.mode == "two_tier":
        if not hasattr(app.state, "http_client") or app.state.http_client is None:
            timeout = httpx.Timeout(15.0, connect=5.0)
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
            app.state.http_client = httpx.AsyncClient(timeout=timeout, limits=limits)
            created_client = True
    yield
    if created_client and hasattr(app.state, "http_client") and app.state.http_client:
        await app.state.http_client.aclose()


def create_gateway_app(config: GatewayConfig = None) -> FastAPI:
    config = config or GatewayConfig.from_environment()

    version = (
        "graphfin-free-single-service-v1"
        if config.mode == "single_service"
        else "graphfin-web-gateway-v1"
    )
    app = FastAPI(
        title=TITLE,
        version=version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.config = config

    # Register standard exception handlers so research errors format consistently
    register_exception_handlers(app)

    # Reject WebSockets with 1008
    app.add_middleware(WebSocketRejectMiddleware)

    # Unified Security & In-Process Route Guard Middleware
    @app.middleware("http")
    async def security_and_routing_middleware(request: Request, call_next):
        # 1. Host validation
        host = request.headers.get("host", "")
        if any(c in host for c in "/\\?#@") or not host:
            response = JSONResponse(
                {"error": "HOST_DENIED", "message": "Valid Host header is required.", "details": []},
                status_code=400,
            )
            _apply_security_headers(response)
            return response

        # 2. In single_service mode, enforce research API constraints directly in-process
        if config.mode == "single_service" and request.url.path.startswith("/api/v1"):
            path = request.url.path

            # Enforce GET-only read semantics
            if request.method != "GET":
                response = JSONResponse(
                    {"error": "GATEWAY_READ_ONLY", "message": "Research gateway permits GET operations only.", "details": []},
                    status_code=405,
                    headers={"Allow": "GET"},
                )
                _apply_security_headers(response)
                return response

            # Enforce exact route pattern allowlist
            if not ALLOWED_ROUTE_PATTERN.match(path):
                response = JSONResponse(
                    {"error": "GATEWAY_ROUTE_FORBIDDEN", "message": "The requested API route is not accessible.", "details": []},
                    status_code=404,
                )
                _apply_security_headers(response)
                return response

            # Enforce rate limiting
            if not _check_rate_limit(request, config):
                response = JSONResponse(
                    {"error": "RATE_LIMIT_EXCEEDED", "message": "Request rate limit exceeded. Please wait.", "details": []},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
                _apply_security_headers(response)
                return response

            # Enforce examiner authentication on protected routes
            if path not in PUBLIC_READ_ROUTES:
                session = get_current_session(request, config)
                if not session:
                    response = JSONResponse(
                        {
                            "error": "EXAMINER_AUTH_REQUIRED",
                            "message": "Examiner authentication is required to access protected research endpoints.",
                            "details": [],
                        },
                        status_code=401,
                        headers={"WWW-Authenticate": "Cookie"},
                    )
                    _apply_security_headers(response)
                    return response

        response = await call_next(request)
        _apply_security_headers(response)
        if config.mode == "single_service" and request.url.path.startswith("/api/v1"):
            response.headers["Cache-Control"] = "private, no-store, max-age=0"
        return response

    # Mount Auth router (examiner login, logout, session)
    app.include_router(auth_router)

    if config.mode == "single_service":
        # In-process mounting of approved read-only research routers
        app.include_router(research.router, prefix="/api/v1")
        app.include_router(dataset_reports.router, prefix="/api/v1")
        app.include_router(graph_explorer.router, prefix="/api/v1")
    else:
        # Two-tier mode: proxy to private upstream backend
        app.include_router(proxy_router)

    @app.get("/health")
    @app.get("/api/v1/health")
    async def gateway_health():
        role = "public-research-service" if config.mode == "single_service" else "public-examiner-gateway"
        return {
            "status": "healthy",
            "service": "graphfin-web",
            "mode": config.mode,
            "role": role,
            "backend_configured": True if config.mode == "single_service" else bool(config.backend_url),
        }

    # Static assets and SPA HTML fallback with directory traversal protection
    root_dir = Path(__file__).resolve().parents[1]
    dist_dir = root_dir / "frontend" / "dist"

    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
            app.mount("/GraphFin/assets", StaticFiles(directory=str(assets_dir)), name="gh_pages_assets")

        dist_resolved = dist_dir.resolve()

        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            raw_path = request.scope.get("raw_path", b"")
            normalized = full_path.lstrip("/")

            # Reject API, docs, traversal markers in raw or decoded path
            if (
                normalized.startswith("api/")
                or normalized in ("docs", "redoc", "openapi.json")
                or b".." in raw_path
                or b"/." in raw_path
                or ".." in full_path
                or normalized.startswith(".")
                or "etc/passwd" in normalized
            ):
                return JSONResponse({"error": "NOT_FOUND", "message": "Not Found"}, status_code=404)

            # Strict directory traversal protection: ensure file stays within dist_dir
            if full_path:
                try:
                    # Defensive asset resolution if requested via nested path
                    if "assets/" in normalized and assets_dir.exists():
                        asset_name = normalized[normalized.index("assets/") + len("assets/"):]
                        asset_file = (assets_dir / asset_name).resolve()
                        if asset_file.is_file() and str(asset_file).startswith(str(assets_dir.resolve())):
                            return FileResponse(asset_file)

                    file_path = (dist_dir / full_path).resolve()
                    if file_path.is_file() and str(file_path).startswith(str(dist_resolved)):
                        return FileResponse(file_path)
                except Exception:
                    pass
                # Any non-existent file with an extension (.py, .yaml, .env, .txt, etc.) must return 404
                if "." in Path(normalized).name:
                    return JSONResponse({"error": "NOT_FOUND", "message": "Asset not found"}, status_code=404)

            # Default to index.html for SPA client-side routing
            index_path = dist_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return JSONResponse({"status": "Frontend build pending."}, status_code=200)

    return app


app = create_gateway_app()
