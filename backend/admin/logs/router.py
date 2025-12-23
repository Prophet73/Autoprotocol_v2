"""
Error logs router.

Endpoints for viewing and managing error logs.
All endpoints require superuser privileges.
"""
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.core.auth.dependencies import SuperUser
from .service import ErrorLogService
from .schemas import ErrorLogResponse, ErrorLogListResponse, ErrorLogSummary


router = APIRouter(prefix="/logs", tags=["Admin - Error Logs"])


@router.get(
    "/",
    response_model=ErrorLogListResponse,
    summary="List error logs",
    description="Get paginated list of error logs with optional filtering."
)
async def list_logs(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Records per page"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint (partial match)"),
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
) -> ErrorLogListResponse:
    """
    List error logs with pagination and filtering.

    Requires superuser privileges.
    """
    service = ErrorLogService(db)
    return await service.list_logs(
        page=page,
        page_size=page_size,
        endpoint_filter=endpoint,
        error_type_filter=error_type,
        status_code_filter=status_code,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/summary",
    response_model=ErrorLogSummary,
    summary="Get error log summary",
    description="Get aggregated error statistics."
)
async def get_summary(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ErrorLogSummary:
    """
    Get error log summary statistics.

    Includes:
    - Total errors
    - Errors today and this week
    - Breakdown by endpoint, error type, and status code
    """
    service = ErrorLogService(db)
    return await service.get_summary()


@router.get(
    "/{log_id}",
    response_model=ErrorLogResponse,
    summary="Get error log by ID",
    description="Get detailed information about a specific error log."
)
async def get_log(
    log_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ErrorLogResponse:
    """Get error log details by ID."""
    service = ErrorLogService(db)
    log = await service.get_log(log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error log with id {log_id} not found"
        )
    return ErrorLogResponse(
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


@router.delete(
    "/cleanup",
    summary="Delete old error logs",
    description="Delete error logs older than specified number of days."
)
async def cleanup_logs(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365, description="Delete logs older than this many days"),
) -> dict:
    """
    Delete old error logs.

    Args:
        days: Number of days to keep logs (default 30)

    Returns:
        Number of deleted logs
    """
    service = ErrorLogService(db)
    deleted = await service.delete_old_logs(days=days)
    return {
        "message": f"Deleted {deleted} error logs older than {days} days",
        "deleted": deleted,
    }
