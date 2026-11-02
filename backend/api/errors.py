"""Discovery Engine - Standardized API error handling and exceptions (Phase 7, P7.2)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from engine.errors import ColdStartUnsupported, UnknownItem, UnknownType, UnknownUser
from engine.logging_utils import get_logger

logger = get_logger("api.errors")


class APIError(Exception):
    """Base class for application-level API errors with structured payloads."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class DuplicateIDsError(APIError):
    """Raised when duplicate item IDs are submitted in a cold-start history."""

    def __init__(
        self,
        message: str = "Duplicate item IDs found in cold-start history.",
        duplicates: list[str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="duplicate_ids",
            message=message,
            details={"duplicates": duplicates or []},
        )


class ContentTypeUnavailableError(APIError):
    """Raised when a valid content type cannot serve requests due to startup/artifact issues."""

    def __init__(self, content_type: str, reason: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="type_unavailable",
            message=f"Content type '{content_type}' is currently unavailable for serving.",
            details={"content_type": content_type, "reason": reason},
        )


class InvalidAPIKeyError(APIError):
    """Raised when an invalid or missing API key is provided."""

    def __init__(self, message: str = "Invalid or missing API key.") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message=message,
            details=None,
        )


class PayloadTooLargeError(APIError):
    """Raised when request payload exceeds configured byte size limit."""

    def __init__(self, message: str = "Request body exceeds maximum allowed size (1MB).") -> None:
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code="payload_too_large",
            message=message,
            details=None,
        )


class InvalidRequestError(APIError):
    """Raised when request parameters violate semantic rules (422 invalid_request)."""

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_request",
            message=message,
            details=details,
        )


class ChatUnavailableError(APIError):
    """Raised when chat assistant is disabled (503 chat_unavailable)."""

    def __init__(self, message: str = "Chat assistant is currently disabled.") -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="chat_unavailable",
            message=message,
            details=None,
        )


class ChatRateLimitedError(APIError):
    """Raised when IP request rate limit is exceeded (429 chat_rate_limited)."""

    def __init__(
        self,
        retry_after: int,
        message: str = "Too many chat requests from this IP. Please wait before retrying.",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="chat_rate_limited",
            message=message,
            details={"retry_after_s": retry_after},
        )
        self.retry_after = retry_after
        self.headers = {"Retry-After": str(retry_after)}


def _make_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Helper to generate standard Discovery Engine error responses."""
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    """Handler for application-level APIError exceptions."""
    headers = getattr(exc, "headers", None)
    return _make_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        headers=headers,
    )


async def unknown_type_handler(_request: Request, exc: UnknownType) -> JSONResponse:
    """Handler for engine.errors.UnknownType (404 unknown_type)."""
    return _make_error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="unknown_type",
        message=str(exc),
        details={"content_type": exc.content_type, "available": exc.available},
    )


async def unknown_user_handler(_request: Request, exc: UnknownUser) -> JSONResponse:
    """Handler for engine.errors.UnknownUser (404 unknown_user)."""
    return _make_error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="unknown_user",
        message=str(exc),
        details={"user_id": exc.user_id, "content_type": exc.content_type},
    )


async def unknown_item_handler(_request: Request, exc: UnknownItem) -> JSONResponse:
    """Handler for engine.errors.UnknownItem (404 unknown_item)."""
    return _make_error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="unknown_item",
        message=str(exc),
        details={"item_id": exc.item_id, "content_type": exc.content_type},
    )


async def cold_start_unsupported_handler(
    _request: Request, exc: ColdStartUnsupported
) -> JSONResponse:
    """Handler for engine.errors.ColdStartUnsupported (409 cold_start_unsupported)."""
    return _make_error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="cold_start_unsupported",
        message=str(exc),
        details={"model_name": exc.model_name},
    )


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for FastAPI Pydantic RequestValidationError (422 validation_error)."""
    # Clean errors to ensure JSON serialization
    errors = exc.errors()
    clean_errors = []
    for err in errors:
        loc = [str(x) for x in err.get("loc", ())]
        clean_errors.append(
            {
                "loc": loc,
                "msg": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            }
        )
    return _make_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message="Request validation failed.",
        details=clean_errors,
    )


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handler for standard Starlette/FastAPI HTTPExceptions."""
    code_map = {
        status.HTTP_401_UNAUTHORIZED: "unauthorized",
        status.HTTP_403_FORBIDDEN: "forbidden",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
        status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
    }
    code = code_map.get(exc.status_code, "http_error")
    msg = exc.detail if isinstance(exc.detail, str) else "HTTP exception occurred."
    return _make_error_response(
        status_code=exc.status_code,
        code=code,
        message=msg,
        details=None,
    )


async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected internal errors (500 internal_error).

    Guarantees no stack trace or internal exception details leak to client.
    """
    logger.exception("Unhandled server exception encountered: %s", exc)
    return _make_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An internal server error occurred.",
        details=None,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all unified exception handlers on the FastAPI application."""
    app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UnknownType, unknown_type_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UnknownUser, unknown_user_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UnknownItem, unknown_item_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ColdStartUnsupported, cold_start_unsupported_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)
