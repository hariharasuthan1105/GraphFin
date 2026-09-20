"""
Main FastAPI Application Entrypoint.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import pandas as pd

from .core.config import settings
from .core.exceptions import register_exception_handlers
from .core.logging import get_logger, setup_logging
from .api.router import api_router
from .services.preprocessing import PreprocessingService
from .services.dataset_registry import dataset_registry

# Configure logging on module load
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown hooks."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")

    # Preload sample transactions if available
    if settings.DEFAULT_SAMPLE_CSV.exists():
        try:
            logger.info(f"Preloading default sample transactions from {settings.DEFAULT_SAMPLE_CSV}...")
            content = settings.DEFAULT_SAMPLE_CSV.read_bytes()
            clean_df, errors, warnings = PreprocessingService().process_csv(content)
            dataset_id = dataset_registry.create_dataset(clean_df)
            logger.info(
                f"Sample dataset preloaded successfully under dataset_id '{dataset_id}' "
                f"({len(clean_df)} transactions, {len(errors)} rejected, {len(warnings)} warnings)."
            )
        except Exception as e:
            logger.warning(f"Could not preload sample transactions: {e}")
    else:
        logger.info(
            f"No sample transactions found at {settings.DEFAULT_SAMPLE_CSV}. "
            "Backend initialized with empty dataset registry."
        )

    yield

    logger.info("Shutting down Financial Anomaly Detection backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register uniform exception handlers
register_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
