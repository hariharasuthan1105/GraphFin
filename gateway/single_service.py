"""GraphFin Single-Service Entry Point for Render Free Tier.

Runs the complete application in one FastAPI process:
- New React Research Dashboard (SPA)
- Examiner Login / Logout & Session Middleware
- In-process read-only Research API, PDF Reporting, and Graph Explorer
Zero loopback HTTP requests, zero cloud secret spoofing, zero paid services.
"""
from fastapi import FastAPI
from .app import create_gateway_app
from .config import GatewayConfig


def create_single_service_app(config: GatewayConfig = None) -> FastAPI:
    if config is None:
        config = GatewayConfig.from_environment(mode="single_service")
    return create_gateway_app(config)


app = create_single_service_app()
