"""
Standardized logging configuration.
"""
import logging
import sys
from .config import settings


def setup_logging():
    """Configure root logger with consistent formatting and level."""
    log_format = (
        "[%(asctime)s] [%(process)d] [%(levelname)s] [%(name)s]: %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set external libraries to warning to keep logs clean
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
