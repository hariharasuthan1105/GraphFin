"""Configuration for GraphFin Web Gateway."""
from dataclasses import dataclass
import os
import secrets


@dataclass(frozen=True)
class GatewayConfig:
    env: str
    session_secret: bytes
    backend_url: str
    backend_host: str
    backend_token: str
    examiner_username: str = ""
    examiner_password_hash: str = ""
    cookie_name: str = "graphfin_examiner_session"
    session_ttl: int = 7200  # 2 hours
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    rate_limit_per_minute: int = 120
    max_proxy_response_bytes: int = 10 * 1024 * 1024  # 10 MB

    @classmethod
    def from_environment(cls):
        env = os.environ.get("GRAPHFIN_GATEWAY_ENV", "development").lower()
        secret_str = os.environ.get("GRAPHFIN_SESSION_SECRET")
        if not secret_str:
            if env == "production":
                raise ValueError("GRAPHFIN_SESSION_SECRET must be set in production.")
            secret = secrets.token_bytes(32)
        else:
            if len(secret_str) < 32:
                raise ValueError("GRAPHFIN_SESSION_SECRET must be at least 32 characters.")
            secret = secret_str.encode("utf-8")

        backend_url = os.environ.get("GRAPHFIN_BACKEND_URL", "http://graphfin-backend-research:10000").rstrip("/")
        backend_host = os.environ.get("GRAPHFIN_BACKEND_HOST", "graphfin-backend-research")
        backend_token = os.environ.get("GRAPHFIN_BACKEND_TOKEN") or os.environ.get("GRAPHFIN_PRIVATE_TOKEN", "")

        examiner_user = os.environ.get("EXAMINER_USERNAME", "")
        examiner_hash = os.environ.get("EXAMINER_PASSWORD_HASH", "")

        # Strict production validation - zero hardcoded fallback credentials allowed
        if env == "production":
            if not backend_token:
                raise ValueError("GRAPHFIN_BACKEND_TOKEN must be configured in production.")
            if not examiner_user:
                raise ValueError("EXAMINER_USERNAME must be configured in production.")
            if not examiner_hash:
                raise ValueError("EXAMINER_PASSWORD_HASH must be configured in production.")

        is_render = os.environ.get("RENDER") == "true"
        cookie_secure = is_render or os.environ.get("GRAPHFIN_COOKIE_SECURE", "0") == "1"

        return cls(
            env=env,
            session_secret=secret,
            backend_url=backend_url,
            backend_host=backend_host,
            backend_token=backend_token,
            examiner_username=examiner_user,
            examiner_password_hash=examiner_hash,
            cookie_secure=cookie_secure,
        )
