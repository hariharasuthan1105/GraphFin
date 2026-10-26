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

import secrets

def hash_examiner_password(password: str, salt: bytes = None) -> str:
    """Generate salted scrypt hash (RFC 7914 / NIST SP 800-132)."""
    salt = salt or secrets.token_bytes(16)
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024,
    )
    return f"scrypt$16384$8$1${salt.hex()}${key.hex()}"


def verify_examiner_password(password: str, stored_hash: str) -> bool:
    """Constant-time verification of password against stored hash.
    Supports salted scrypt ($scrypt$16384$8$1$salt$key) and sha256 hex fallback."""
    if not password or not stored_hash:
        return False
    try:
        if stored_hash.startswith("scrypt$"):
            parts = stored_hash.split("$")
            if len(parts) == 6:
                _, n_str, r_str, p_str, salt_hex, key_hex = parts
                salt = bytes.fromhex(salt_hex)
                expected_key = bytes.fromhex(key_hex)
                computed = hashlib.scrypt(
                    password.encode("utf-8"),
                    salt=salt,
                    n=int(n_str),
                    r=int(r_str),
                    p=int(p_str),
                    maxmem=32 * 1024 * 1024,
                )
                return hmac.compare_digest(computed, expected_key)
        if len(stored_hash) == 64:
            input_hash = hashlib.sha256(password.encode("utf-8")).hexdigest().lower()
            return hmac.compare_digest(input_hash, stored_hash.lower())
    except Exception:
        return False
    return False


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
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
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

    # 3. Constant-time comparison of username and salted password hash
    input_user = body.username.strip()
    user_matches = hmac.compare_digest(input_user.lower(), config.examiner_username.lower())
    pwd_matches = verify_examiner_password(body.password, config.examiner_password_hash)

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
        "session_token": session_token,
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
