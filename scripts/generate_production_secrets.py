"""Cryptographic secret generator for GraphFin Single-Service Render Free Tier deployment.

Generates:
1. GRAPHFIN_SESSION_SECRET: Cryptographically secure 256-bit random secret for session cookie signing.
2. EXAMINER_PASSWORD_HASH: Salted scrypt password hash (RFC 7914 / NIST SP 800-132).
3. Production environment variables for single-service Render Web Service deployment.

DO NOT commit generated production values to version control.
"""
import os
import secrets
import sys

from gateway.auth import hash_examiner_password


def generate_secrets(username: str = None, password: str = None):
    print("=" * 70)
    print("GraphFin Single-Service Production Secrets Generator (Render Free Tier)")
    print("=" * 70)

    # 1. Session secret (256-bit entropy)
    session_secret = secrets.token_hex(32)

    # 2. Examiner Credentials
    if not username:
        if sys.stdin.isatty():
            username = input("Enter production examiner username [default: examiner]: ").strip() or "examiner"
        else:
            username = "examiner"

    if not password:
        if sys.stdin.isatty():
            password = input("Enter production examiner password: ").strip()
        else:
            password = secrets.token_urlsafe(24)
            print(f"[Generated Secure Random Password: {password}]")

    if not password:
        print("ERROR: Password cannot be empty.")
        sys.exit(1)

    # Salted scrypt key derivation (RFC 7914, N=16384, r=8, p=1)
    pwd_hash = hash_examiner_password(password)

    print()
    print("--- RENDER ENVIRONMENT VARIABLES (Single Free Web Service) ---")
    print("GRAPHFIN_GATEWAY_ENV=production")
    print("GRAPHFIN_DEPLOYMENT_MODE=single_service")
    print(f"GRAPHFIN_SESSION_SECRET={session_secret}")
    print(f"EXAMINER_USERNAME={username}")
    print(f"EXAMINER_PASSWORD_HASH={pwd_hash}")

    print()
    print("=" * 70)
    print("Add these 5 environment variables to your existing Render Web Service:")
    print("Render Dashboard -> graphfin-backend -> Environment")
    print("=" * 70)


if __name__ == "__main__":
    u = sys.argv[1] if len(sys.argv) > 1 else None
    p = sys.argv[2] if len(sys.argv) > 2 else None
    generate_secrets(u, p)
