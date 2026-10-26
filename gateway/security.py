"""Cryptographic session and CSRF security management."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional, Tuple


def generate_csrf_token() -> str:
    """Generate a high-entropy 256-bit URL-safe CSRF token."""
    return secrets.token_urlsafe(32)


def create_signed_session(secret: bytes, user_id: str, role: str, ttl: int = 7200) -> Tuple[str, str]:
    """Create a signed session string containing user metadata and a fresh CSRF token."""
    csrf_token = generate_csrf_token()
    now = int(time.time())
    payload = {
        "uid": user_id,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "csrf": csrf_token,
        "nonce": secrets.token_hex(8),
    }
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(raw_json).decode("ascii").rstrip("=")
    signature = hmac.new(secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
    encoded_sig = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    session_token = f"{encoded_payload}.{encoded_sig}"
    return session_token, csrf_token


def verify_session(secret: bytes, session_token: str) -> Optional[dict]:
    """Verify session signature and expiration using constant-time comparisons."""
    if not session_token or "." not in session_token:
        return None
    try:
        encoded_payload, encoded_sig = session_token.split(".", 1)
        expected_sig = hmac.new(secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(encoded_sig + "=" * (-len(encoded_sig) % 4))
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        payload = json.loads(payload_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            return None
        now = int(time.time())
        if payload.get("exp", 0) <= now:
            return None
        return payload
    except Exception:
        return None
