"""GraphFin Public Web Application & Examiner Gateway Entry Point."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx

from .auth import router as auth_router
from .config import GatewayConfig
from .proxy import router as proxy_router

TITLE = "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize connection-pooled async client for upstream private backend communication if not already injected
    created_client = False
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

    app = FastAPI(
        title=TITLE,
        version="graphfin-web-gateway-v1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.config = config

    # Security Headers Middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response

    # Mount API routers
    app.include_router(auth_router)
    app.include_router(proxy_router)

    @app.get("/health")
    async def gateway_health():
        return {
            "status": "healthy",
            "service": "graphfin-web",
            "role": "public-examiner-gateway",
            "backend_configured": bool(config.backend_url),
        }

    # Static assets and SPA HTML fallback with directory traversal protection
    root_dir = Path(__file__).resolve().parents[1]
    dist_dir = root_dir / "frontend" / "dist"

    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
            # Also mount under /GraphFin/assets for backwards compatibility
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
