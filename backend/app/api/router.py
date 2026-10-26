"""
Aggregated API v1 Router.
"""
from fastapi import APIRouter
from .routes import health, transactions, graph, analytics, anomalies, datasets, evaluation, stream, reports, tax
from .routes import research
from .routes import dataset_reports
from .routes import graph_explorer

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(transactions.router)
api_router.include_router(graph.router)
api_router.include_router(analytics.router)
api_router.include_router(anomalies.router)
api_router.include_router(datasets.router)
api_router.include_router(evaluation.router)
api_router.include_router(stream.router)
api_router.include_router(reports.router)
api_router.include_router(tax.router)
api_router.include_router(research.router)
api_router.include_router(dataset_reports.router)
api_router.include_router(graph_explorer.router)

