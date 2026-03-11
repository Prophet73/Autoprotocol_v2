"""
Error logging service.

Provides methods for:
- Saving error logs
- Querying error logs
- Getting error summaries
- Logging internal/Celery errors to ErrorLog table
"""
import logging
import traceback
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.shared.models import ErrorLog, User
from .schemas import ErrorLogResponse, ErrorLogListResponse, ErrorLogSummary

logger = logging.getLogger(__name__)


def _escape_like_pattern(value: str) -> str:
    """
    Escape special characters in LIKE pattern to prevent LIKE injection.

    Args:
        value: User-provided search string.

    Returns:
        Escaped string safe for use in LIKE queries.
    """
    # Escape backslash first, then other special chars
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


class ErrorLogService:
    """Service for error log management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(
        self,
        endpoint: str,
        method: str,
        error_type: str,
        error_detail: str,
        status_code: int = 500,
        user_id: Optional[int] = None,
        request_body: Optional[str] = None,
    ) -> ErrorLog:
        """
        Create a new error log entry.

        Args:
            endpoint: API endpoint that caused the error
            method: HTTP method
            error_type: Exception class name
            error_detail: Full error message/traceback
            status_code: HTTP status code
            user_id: ID of user who triggered the error
            request_body: Request payload (truncated)

        Returns:
            Created error log
        """
        # Truncate request body for security
        if request_body and len(request_body) > 2000:
            request_body = request_body[:2000] + "...[truncated]"

        log = ErrorLog(
            endpoint=endpoint,
            method=method,
            error_type=error_type,
            error_detail=error_detail,
            status_code=status_code,
            user_id=user_id,
            request_body=request_body,
        )

        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def list_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        endpoint_filter: Optional[str] = None,
        error_type_filter: Optional[str] = None,
        status_code_filter: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ErrorLogListResponse:
        """
        List error logs with pagination and filtering.

        Args:
            page: Page number (1-based)
            page_size: Records per page
            endpoint_filter: Filter by endpoint (partial match)
            error_type_filter: Filter by error type
            status_code_filter: Filter by status code
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Paginated list of error logs
        """
        query = select(ErrorLog).options(selectinload(ErrorLog.user))

        # Apply filters
        if endpoint_filter:
            # Escape LIKE wildcards to prevent LIKE injection
            escaped = _escape_like_pattern(endpoint_filter)
            query = query.where(ErrorLog.endpoint.ilike(f"%{escaped}%", escape="\\"))
        if error_type_filter:
            query = query.where(ErrorLog.error_type == error_type_filter)
        if status_code_filter:
            query = query.where(ErrorLog.status_code == status_code_filter)
        if start_date:
            query = query.where(ErrorLog.timestamp >= start_date)
        if end_date:
            query = query.where(ErrorLog.timestamp <= end_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(desc(ErrorLog.timestamp))
        result = await self.db.execute(query)
        logs = result.scalars().all()

        # Convert to response
        log_responses = []
        for log in logs:
            response = ErrorLogResponse(
                id=log.id,
                timestamp=log.timestamp,
                endpoint=log.endpoint,
                method=log.method,
                error_type=log.error_type,
                error_detail=log.error_detail,
                user_id=log.user_id,
                user_email=log.user.email if log.user else None,
                request_body=log.request_body,
                status_code=log.status_code,
            )
            log_responses.append(response)

        return ErrorLogListResponse(
            logs=log_responses,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_log(self, log_id: int) -> Optional[ErrorLog]:
        """Get error log by ID."""
        result = await self.db.execute(
            select(ErrorLog)
            .options(selectinload(ErrorLog.user))
            .where(ErrorLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_summary(self) -> ErrorLogSummary:
        """Get error log summary statistics."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        # Total errors
        total_result = await self.db.execute(
            select(func.count(ErrorLog.id))
        )
        total = total_result.scalar() or 0

        # Errors today
        today_result = await self.db.execute(
            select(func.count(ErrorLog.id))
            .where(ErrorLog.timestamp >= today_start)
        )
        today = today_result.scalar() or 0

        # Errors this week
        week_result = await self.db.execute(
            select(func.count(ErrorLog.id))
            .where(ErrorLog.timestamp >= week_start)
        )
        this_week = week_result.scalar() or 0

        # By endpoint (top 10)
        endpoint_result = await self.db.execute(
            select(ErrorLog.endpoint, func.count(ErrorLog.id))
            .group_by(ErrorLog.endpoint)
            .order_by(desc(func.count(ErrorLog.id)))
            .limit(10)
        )
        by_endpoint = {ep: count for ep, count in endpoint_result.all()}

        # By error type
        type_result = await self.db.execute(
            select(ErrorLog.error_type, func.count(ErrorLog.id))
            .group_by(ErrorLog.error_type)
            .order_by(desc(func.count(ErrorLog.id)))
            .limit(10)
        )
        by_error_type = {et: count for et, count in type_result.all()}

        # By status code
        code_result = await self.db.execute(
            select(ErrorLog.status_code, func.count(ErrorLog.id))
            .group_by(ErrorLog.status_code)
            .order_by(desc(func.count(ErrorLog.id)))
        )
        by_status_code = {code: count for code, count in code_result.all()}

        return ErrorLogSummary(
            total_errors=total,
            errors_today=today,
            errors_this_week=this_week,
            by_endpoint=by_endpoint,
            by_error_type=by_error_type,
            by_status_code=by_status_code,
        )

    async def delete_old_logs(self, days: int = 30) -> int:
        """
        Delete error logs older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted records
        """
        cutoff = datetime.now() - timedelta(days=days)

        # Count before delete
        count_result = await self.db.execute(
            select(func.count(ErrorLog.id))
            .where(ErrorLog.timestamp < cutoff)
        )
        count = count_result.scalar() or 0

        if count > 0:
            # Delete old logs
            from sqlalchemy import delete
            await self.db.execute(
                delete(ErrorLog).where(ErrorLog.timestamp < cutoff)
            )
            await self.db.flush()

        return count


async def _log_celery_error_async(
    task_name: str,
    error: Exception,
    user_id: Optional[int] = None,
    context: Optional[str] = None,
) -> None:
    """
    Save a Celery/internal error to the ErrorLog table.

    Args:
        task_name: Celery task name (used as endpoint).
        error: The exception that occurred.
        user_id: Optional uploader/user ID associated with the task.
        context: Optional extra context (e.g. job_id) stored in request_body.
    """
    from backend.shared.database import get_db_context

    try:
        error_detail = traceback.format_exception(type(error), error, error.__traceback__)
        detail_str = "".join(error_detail)[:2000]

        async with get_db_context() as db:
            service = ErrorLogService(db)
            await service.create_log(
                endpoint=task_name,
                method="CELERY",
                error_type=type(error).__name__,
                error_detail=detail_str,
                status_code=500,
                user_id=user_id,
                request_body=context,
            )
    except Exception as log_err:
        logger.error(f"Failed to write Celery error to ErrorLog: {log_err}")


def log_celery_error(
    task_name: str,
    error: Exception,
    user_id: Optional[int] = None,
    context: Optional[str] = None,
) -> None:
    """
    Sync wrapper: log a Celery task error to the ErrorLog table.

    Safe to call from synchronous Celery tasks — uses run_async internally.
    """
    from backend.shared.async_utils import run_async

    try:
        run_async(_log_celery_error_async(task_name, error, user_id, context))
    except Exception as e:
        logger.error(f"log_celery_error failed: {e}")
