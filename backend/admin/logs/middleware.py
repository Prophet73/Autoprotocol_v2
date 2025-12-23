"""
Error logging middleware.

Catches 500 exceptions and saves them to the ErrorLog table.
"""
import logging
import traceback
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.shared.database import get_db_context
from backend.shared.models import ErrorLog

logger = logging.getLogger(__name__)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs 500 errors to the database.

    Catches unhandled exceptions and records:
    - Endpoint and method
    - Exception type and message
    - User ID (if authenticated)
    - Request body (truncated)
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log any 500 errors."""
        try:
            response = await call_next(request)

            # Log 5xx responses that weren't caught as exceptions
            if response.status_code >= 500:
                await self._log_error(
                    request=request,
                    status_code=response.status_code,
                    error_type="HTTPError",
                    error_detail=f"Server returned status {response.status_code}",
                )

            return response

        except Exception as exc:
            # Log the exception
            error_detail = traceback.format_exc()
            error_type = type(exc).__name__

            await self._log_error(
                request=request,
                status_code=500,
                error_type=error_type,
                error_detail=error_detail,
            )

            # Re-raise the exception to let FastAPI handle it
            raise

    async def _log_error(
        self,
        request: Request,
        status_code: int,
        error_type: str,
        error_detail: str,
    ) -> None:
        """
        Save error to database.

        Args:
            request: FastAPI request
            status_code: HTTP status code
            error_type: Exception class name
            error_detail: Full error message/traceback
        """
        try:
            # Get user ID from request state if available
            user_id = None
            if hasattr(request.state, "user") and request.state.user:
                user_id = request.state.user.id

            # Get request body (if available and not too large)
            request_body = None
            try:
                # Only try to get body for certain content types
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    body = await request.body()
                    if len(body) < 5000:  # Limit body size
                        request_body = body.decode("utf-8", errors="ignore")
            except Exception:
                pass  # Ignore body read errors

            # Save to database
            async with get_db_context() as db:
                error_log = ErrorLog(
                    endpoint=str(request.url.path),
                    method=request.method,
                    error_type=error_type,
                    error_detail=error_detail[:5000],  # Limit detail size
                    status_code=status_code,
                    user_id=user_id,
                    request_body=request_body,
                )
                db.add(error_log)
                await db.commit()

            logger.info(
                f"Logged error: {error_type} on {request.method} {request.url.path}"
            )

        except Exception as log_error:
            # Don't let logging errors break the app
            logger.error(f"Failed to log error to database: {log_error}")


def setup_error_logging(app: ASGIApp) -> ErrorLoggingMiddleware:
    """
    Create and return error logging middleware.

    Usage:
        app.add_middleware(ErrorLoggingMiddleware)

    Or:
        middleware = setup_error_logging(app)
    """
    return ErrorLoggingMiddleware(app)
