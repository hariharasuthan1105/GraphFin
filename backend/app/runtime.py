"""Explicit profile selection. Importing on Render alone never grants trust.

The original research_demo module is kept byte-for-byte for local use.
"""
import os
from fastapi import FastAPI
from .research_demo import create_app as create_local_app, TITLE
from .api.routes import research, dataset_reports, graph_explorer
from .core.exceptions import register_exception_handlers
from .core.private_access import PrivatePolicy, PrivateReadOnlyBoundary


def create_app():
    profile = os.environ.get('GRAPHFIN_SECURITY_PROFILE', 'local_demo')
    if profile == 'local_demo':
        return create_local_app()
    if profile != 'render_private':
        raise ValueError('Unknown GraphFin security profile.')
    policy = PrivatePolicy.from_environment()
    application = FastAPI(title=TITLE, version='render-private-review-v1',
                          docs_url=None, redoc_url=None, openapi_url=None)
    register_exception_handlers(application)
    application.add_middleware(PrivateReadOnlyBoundary, policy=policy)
    for router in (research.router, dataset_reports.router, graph_explorer.router):
        application.include_router(router, prefix='/api/v1')

    @application.get('/health')
    @application.get('/api/v1/health')
    async def health():
        return {'status': 'healthy', 'mode': 'render-private-review',
                'public_deployment_approved': False}
    return application


app = create_app()
