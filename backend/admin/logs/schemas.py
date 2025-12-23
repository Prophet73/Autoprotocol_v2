"""
Schemas for error log endpoints.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ErrorLogResponse(BaseModel):
    """Error log entry response."""
    id: int
    timestamp: datetime
    endpoint: str
    method: str
    error_type: str
    error_detail: str
    user_id: Optional[int]
    user_email: Optional[str] = None
    request_body: Optional[str]
    status_code: int

    class Config:
        from_attributes = True


class ErrorLogListResponse(BaseModel):
    """List of error logs response."""
    logs: List[ErrorLogResponse]
    total: int
    page: int
    page_size: int


class ErrorLogSummary(BaseModel):
    """Summary of error logs."""
    total_errors: int
    errors_today: int
    errors_this_week: int
    by_endpoint: dict[str, int]
    by_error_type: dict[str, int]
    by_status_code: dict[int, int]
