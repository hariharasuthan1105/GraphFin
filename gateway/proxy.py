"""Secure forwarder between public gateway and private FastAPI backend with rate limiting and response constraints."""
from collections import defaultdict
import re
import time
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
import httpx

from .auth import get_current_session
from .config import GatewayConfig

router = APIRouter(prefix="/api/v1", tags=["Research Gateway Proxy"])

# Exact regex pattern of authorized read-only backend route endpoints
ALLOWED_ROUTE_PATTERN = re.compile(
    r"^/api/v1/("
    r"health|"
    r"research/overview|"
    r"research/datasets|"
    r"research/experiments(?:/[a-zA-Z0-9_-]+(?:/(metrics|rankings|provenance))?)?|"
    r"research/comparisons|"
    r"research/reproducibility|"
    r"research/model-seeds|"
    r"research/diagnostics(?:/[a-zA-Z0-9_-]+)?|"
    r"research/limitations|"
    r"research-reports/datasets/[a-zA-Z0-9_-]+/report\.pdf|"
    r"graph-explorer/catalog|"
    r"graph-explorer/session|"
    r"graph-explorer/neighborhood"
    r")$"
)

PUBLIC_READ_ROUTES = frozenset([
    "/api/v1/health",
    "/api/v1/research/overview",
    "/api/v1/research/limitations",
])

# In-memory sliding-window rate limiter per client IP
_rate_limits: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(request: Request, config: GatewayConfig) -> bool:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - 60.0
    # Keep only requests within the last 60 seconds
    timestamps = [t for t in _rate_limits[ip] if t > cutoff]
    _rate_limits[ip] = timestamps
    if len(timestamps) >= config.rate_limit_per_minute:
        return False
    _rate_limits[ip].append(now)
    return True


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def gateway_proxy(request: Request, path: str):
    config: GatewayConfig = request.app.state.config
    full_path = "/api/v1/" + path.lstrip("/")

    # 1. Enforce GET-only read semantics
    if request.method != "GET":
        return JSONResponse(
            {"error": "GATEWAY_READ_ONLY", "message": "Research gateway permits GET operations only.", "details": []},
            status_code=405,
            headers={"Allow": "GET"},
        )

    # 2. Enforce exact route pattern allowlist
    if not ALLOWED_ROUTE_PATTERN.match(full_path):
        return JSONResponse(
            {"error": "GATEWAY_ROUTE_FORBIDDEN", "message": "The requested API route is not accessible.", "details": []},
            status_code=404,
        )

    # 3. Enforce rate limiting
    if not _check_rate_limit(request, config):
        return JSONResponse(
            {"error": "RATE_LIMIT_EXCEEDED", "message": "Request rate limit exceeded. Please wait.", "details": []},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    # 4. Check examiner session for protected research endpoints
    session = get_current_session(request, config)
    if full_path not in PUBLIC_READ_ROUTES and not session:
        return JSONResponse(
            {
                "error": "EXAMINER_AUTH_REQUIRED",
                "message": "Examiner authentication is required to access protected research endpoints.",
                "details": [],
            },
            status_code=401,
            headers={"WWW-Authenticate": "Cookie"},
        )

    # 5. Prepare upstream request
    upstream_url = f"{config.backend_url}{full_path}"
    query_string = request.url.query
    if query_string:
        upstream_url = f"{upstream_url}?{query_string}"

    headers = {
        "Host": config.backend_host,
        "Accept": request.headers.get("Accept", "application/json"),
        "User-Agent": "GraphFin-WebGateway/1.0",
    }
    if config.backend_token:
        headers["Authorization"] = f"Bearer {config.backend_token}"

    # Safely forward bounded graph session capability if present
    graph_session = request.headers.get("X-Graph-Session")
    if graph_session and re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", graph_session):
        headers["X-Graph-Session"] = graph_session

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        upstream_response = await client.request(
            method="GET",
            url=upstream_url,
            headers=headers,
        )
    except httpx.ConnectError:
        return JSONResponse(
            {
                "error": "BACKEND_UNAVAILABLE",
                "message": "Private research backend is currently unreachable across the private network.",
                "details": [],
            },
            status_code=503,
        )
    except httpx.TimeoutException:
        return JSONResponse(
            {
                "error": "BACKEND_TIMEOUT",
                "message": "Private research backend request timed out.",
                "details": [],
            },
            status_code=504,
        )

    # 6. Enforce response size limits
    if len(upstream_response.content) > config.max_proxy_response_bytes:
        return JSONResponse(
            {
                "error": "UPSTREAM_RESPONSE_TOO_LARGE",
                "message": "Upstream response exceeds gateway maximum allowed size.",
                "details": [],
            },
            status_code=502,
        )

    # 7. Forward upstream response with strict security headers
    response_headers = {
        "Cache-Control": "private, no-store, max-age=0",
        "X-Content-Type-Options": "nosniff",
    }
    content_type = upstream_response.headers.get("Content-Type", "application/json")
    response_headers["Content-Type"] = content_type

    if "X-Graph-Session" in upstream_response.headers:
        response_headers["X-Graph-Session"] = upstream_response.headers["X-Graph-Session"]
    if "Vary" in upstream_response.headers:
        response_headers["Vary"] = upstream_response.headers["Vary"]

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=content_type,
    )
