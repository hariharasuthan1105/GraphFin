"""
Custom exceptions and standardized error response models.
"""
from typing import Any, List, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from .logging import get_logger

logger = get_logger(__name__)


class ErrorDetail(BaseModel):
    loc: Optional[List[str]] = None
    msg: str
    type: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[List[Any]] = None


class BaseAppException(Exception):
    """Base exception for application errors."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_SERVER_ERROR"

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[List[Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        self.details = details or []


class ValidationException(BaseAppException):
    """Raised when incoming transaction or payload validation fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "INVALID_TRANSACTION_DATA"


class DataNotFoundException(BaseAppException):
    """Raised when requested entity or dataset is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "DATA_NOT_FOUND"


class NotFoundException(BaseAppException):
    """Raised when a requested dataset or entity is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class GraphProcessingException(BaseAppException):
    """Raised when graph construction or metric calculation fails."""
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    error_code = "GRAPH_PROCESSING_ERROR"


class ModelNotTrainedException(BaseAppException):
    """Raised when anomaly endpoints are called before a model has been trained for the dataset."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "MODEL_NOT_FOUND"


def register_exception_handlers(app):
    """Register uniform JSON exception handlers for the FastAPI app."""

    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException):
        logger.warning(
            f"Handled application exception [{exc.error_code}]: {exc.message} "
            f"at {request.method} {request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            f"Validation error for {request.method} {request.url.path}: {exc.errors()}"
        )
        formatted_details = []
        for err in exc.errors():
            formatted_details.append({
                "loc": [str(x) for x in err.get("loc", [])],
                "msg": err.get("msg", ""),
                "type": err.get("type", "")
            })

        return JSONResponse(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request payload failed validation schema.",
                "details": formatted_details,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled exception at {request.method} {request.url.path}: {str(exc)}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please check server logs.",
                "details": [str(exc)] if app.debug else [],
            },
        )
