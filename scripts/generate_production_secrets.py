"""Cryptographic secret generator for GraphFin Render production deployment.

Generates:
1. GRAPHFIN_SESSION_SECRET: 32 cryptographically secure random bytes for session cookie signing.
2. GRAPHFIN_PRIVATE_TOKEN / GRAPHFIN_BACKEND_TOKEN: Canonical 256-bit base64url token matching backend validator.
3. EXAMINER_PASSWORD_HASH helper: Computes SHA-256 digest of operator-supplied examiner password.

DO NOT commit generated production values to version control.
"""
import base64
import hashlib
import os
import secrets
import sys


def generate_secrets():
    print("=" * 70)
    print("GraphFin Production Secrets Generator")
    print("=" * 70)

    # 1. Session secret
    session_secret = secrets.token_hex(32)  # 64 chars hex (256-bit)

    # 2. Canonical 256-bit private token for server-to-server auth
    raw_token_bytes = secrets.token_bytes(32)
    canonical_token = base64.urlsafe_b64encode(raw_token_bytes).decode("ascii").rstrip("=")
    assert len(canonical_token) == 43, f"Unexpected token length: {len(canonical_token)}"

    print("\n[1] Gateway Session Signing Secret (configure on 'graphfin-web'):")
    print(f"GRAPHFIN_SESSION_SECRET={session_secret}")

    print("\n[2] Shared Private Service Token (configure on BOTH services):")
    print(f"# Configure on 'graphfin-web':")
    print(f"GRAPHFIN_BACKEND_TOKEN={canonical_token}")
    print(f"# Configure on 'graphfin-backend-research':")
    print(f"GRAPHFIN_PRIVATE_TOKEN={canonical_token}")

    print("\n[3] Examiner Credentials (configure on 'graphfin-web'):")
    user = input("Enter production examiner username [default: examiner]: ").strip() or "examiner"
    pwd = input("Enter production examiner password: ").strip()

    if not pwd:
        print("ERROR: Password cannot be empty.")
        sys.exit(1)

    pwd_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
    print(f"\nEXAMINER_USERNAME={user}")
    print(f"EXAMINER_PASSWORD_HASH={pwd_hash}")

    print("\n" + "=" * 70)
    print("Copy these values into your Render Dashboard Environment Settings.")
    print("DO NOT commit these values to Git or send them over unencrypted channels.")
    print("=" * 70)


if __name__ == "__main__":
    generate_secrets()
