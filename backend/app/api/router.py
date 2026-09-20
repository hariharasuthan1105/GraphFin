"""
Aggregated API v1 Router.
"""
from fastapi import APIRouter
from .routes import health, transactions, graph, analytics, anomalies, datasets, evaluation, stream, reports

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

