"""
Configuration module for the Financial Anomaly Detection backend.
Loads settings from environment variables and provides sensible defaults.
"""
from pathlib import Path
import os
from typing import List
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Base directories
CORE_DIR = Path(__file__).resolve().parent
APP_DIR = CORE_DIR.parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings:
    """Application configuration settings."""

    PROJECT_NAME: str = os.getenv(
        "PROJECT_NAME",
        "Financial Anomaly Detection API",
    )
    PROJECT_DESCRIPTION: str = (
        "Backend foundation for Machine Learning Enhanced Graph-Based Anomaly "
        "Detection for Financial Transactions. Provides transaction ingestion, "
        "graph construction, and behavioral/temporal feature extraction."
    )
    VERSION: str = os.getenv("API_VERSION", "1.0.0")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # CORS
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    # Directories
    ROOT_DIR: Path = PROJECT_ROOT
    DATA_DIR: Path = PROJECT_ROOT / "data"
    DATA_RAW_DIR: Path = DATA_DIR / "raw"
    DATA_PROCESSED_DIR: Path = DATA_DIR / "processed"
    MODELS_DIR: Path = DATA_DIR / "models"
    DATA_SIMULATIONS_DIR: Path = DATA_DIR / "simulations"
    DEFAULT_SAMPLE_CSV: Path = DATA_RAW_DIR / "sample_transactions.csv"

    def __init__(self):
        # Ensure directories exist
        self.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_SIMULATIONS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
