"""Domain exceptions and FastAPI exception handlers.

A small hierarchy of application errors keeps the service layer free of HTTP
concerns; handlers translate them into consistent JSON responses.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger("exceptions")


class AppError(Exception):
    """Base application error with an HTTP status and stable error code."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "app_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"


class PermissionError(AppError):  # noqa: A001 - intentional domain name
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limited"


class ExternalServiceError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "external_service_error"


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("app_error", code=exc.error_code, message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "validation_error",
                "Request validation failed.",
                {"errors": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "An unexpected error occurred."),
        )
