"""Examiner authentication and session management with zero hardcoded credentials."""
from collections import defaultdict
import hashlib
import hmac
import os
import time
from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import GatewayConfig
from .security import create_signed_session, verify_session

router = APIRouter(prefix="/api/auth", tags=["Examiner Authentication"])

# In-memory brute-force protection: track failed attempts per client IP
# Structure: client_ip -> list of failure timestamps
_failed_attempts: dict[str, list[float]] = defaultdict(list)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300  # 5 minutes


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=64)
    password: str = Field(..., max_length=128)


def get_current_session(request: Request, config: GatewayConfig) -> dict | None:
    token = request.cookies.get(config.cookie_name)
    if not token:
        return None
    return verify_session(config.session_secret, token)


def _client_ip(request: Request) -> str:
    # Use direct client host (not unverified XFF) to prevent spoofing
    return request.client.host if request.client else "unknown"


@router.get("/session")
async def session_status(request: Request):
    config: GatewayConfig = request.app.state.config
    session = get_current_session(request, config)
    if not session:
        return {"authenticated": False, "role": "public", "user": None, "csrf_token": None}
    return {
        "authenticated": True,
        "role": session.get("role", "examiner"),
        "user": session.get("uid", "examiner"),
        "csrf_token": session.get("csrf"),
    }


@router.post("/login")
async def login(request: Request, body: LoginRequest, response: Response):
    config: GatewayConfig = request.app.state.config
    ip = _client_ip(request)
    now = time.time()

    # 1. Check brute-force lockout window
    recent_failures = [t for t in _failed_attempts[ip] if now - t < LOCKOUT_WINDOW_SECONDS]
    _failed_attempts[ip] = recent_failures
    if len(recent_failures) >= MAX_FAILED_ATTEMPTS:
        return JSONResponse(
            {
                "error": "TOO_MANY_FAILED_ATTEMPTS",
                "message": "Too many failed login attempts. Access temporarily restricted. Try again later.",
            },
            status_code=429,
            headers={"Retry-After": str(LOCKOUT_WINDOW_SECONDS)},
        )

    # 2. Verify that examiner credentials are configured in gateway environment
    if not config.examiner_username or not config.examiner_password_hash:
        return JSONResponse(
            {
                "error": "AUTH_NOT_CONFIGURED",
                "message": "Examiner evaluation credentials are not configured in this gateway instance.",
            },
            status_code=503,
        )

    # 3. Constant-time comparison of username and SHA-256 password hash
    input_user = body.username.strip()
    input_hash = hashlib.sha256(body.password.encode("utf-8")).hexdigest()

    user_matches = hmac.compare_digest(input_user.lower(), config.examiner_username.lower())
    pwd_matches = hmac.compare_digest(input_hash.lower(), config.examiner_password_hash.lower())

    if not (user_matches and pwd_matches):
        _failed_attempts[ip].append(now)
        return JSONResponse(
            {"error": "INVALID_CREDENTIALS", "message": "Invalid examiner username or password."},
            status_code=401,
        )

    # Clear failure records on successful login
    _failed_attempts.pop(ip, None)

    # 4. Issue signed session cookie and CSRF token
    session_token, csrf_token = create_signed_session(
        config.session_secret, user_id=input_user, role="examiner", ttl=config.session_ttl
    )

    response.set_cookie(
        key=config.cookie_name,
        value=session_token,
        max_age=config.session_ttl,
        httponly=True,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        path="/",
    )
    return {
        "status": "authenticated",
        "user": input_user,
        "role": "examiner",
        "csrf_token": csrf_token,
        "message": "Examiner session established.",
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    x_csrf_token: str = Header(None, alias="X-CSRF-Token"),
):
    config: GatewayConfig = request.app.state.config
    session = get_current_session(request, config)
    if session:
        expected_csrf = session.get("csrf")
        if not x_csrf_token or not hmac.compare_digest(x_csrf_token, expected_csrf):
            return JSONResponse(
                {"error": "CSRF_VALIDATION_FAILED", "message": "Valid CSRF token is required to log out."},
                status_code=403,
            )

    response.delete_cookie(key=config.cookie_name, path="/")
    return {"status": "logged_out", "message": "Examiner session terminated."}
