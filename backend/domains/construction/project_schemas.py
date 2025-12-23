"""
Schemas for construction project management.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base project fields."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Request to create a new project."""
    tenant_id: Optional[int] = None
    manager_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    """Request to update a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class ProjectResponse(ProjectBase):
    """Project response with all fields."""
    id: int
    project_code: str
    tenant_id: Optional[int]
    manager_id: Optional[int]
    manager_name: Optional[str] = None
    is_active: bool
    report_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """List of projects response."""
    projects: List[ProjectResponse]
    total: int


class ProjectCodeValidation(BaseModel):
    """Response for project code validation."""
    valid: bool
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    tenant_id: Optional[int] = None
    message: str = ""


class ProjectSummary(BaseModel):
    """Project summary with statistics."""
    id: int
    name: str
    project_code: str
    is_active: bool
    total_reports: int = 0
    completed_reports: int = 0
    pending_reports: int = 0
    failed_reports: int = 0
    open_risks: int = 0
    last_report_date: Optional[datetime] = None


class ProjectDashboardResponse(BaseModel):
    """Dashboard data for projects."""
    projects: List[ProjectSummary]
    total_projects: int
    active_projects: int


class CalendarEvent(BaseModel):
    """Calendar event for report scheduling."""
    id: int
    title: str
    project_id: int
    project_name: str
    meeting_date: Optional[datetime]
    status: str
    created_at: datetime


class CalendarResponse(BaseModel):
    """Calendar data response."""
    events: List[CalendarEvent]
    total: int
