"""
Construction domain router.

Endpoints for:
- Project management (CRUD)
- Project code validation (public)
- Manager dashboard (calendar, project stats)
"""
from datetime import datetime
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import User
from backend.core.auth.dependencies import CurrentUser, OptionalUser
from .project_service import ProjectService
from .project_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectCodeValidation,
    ProjectDashboardResponse,
    CalendarResponse,
)


router = APIRouter(prefix="/construction", tags=["Construction Domain"])


# =============================================================================
# Project CRUD Endpoints
# =============================================================================

@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new project",
    description="Create a new construction project with auto-generated 4-digit code."
)
async def create_project(
    data: ProjectCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    """Create a new construction project."""
    service = ProjectService(db)

    # Use user's tenant if not specified
    tenant_id = data.tenant_id or current_user.tenant_id

    project = await service.create_project(data, tenant_id=tenant_id)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        project_code=project.project_code,
        tenant_id=project.tenant_id,
        manager_id=project.manager_id,
        manager_name=None,
        is_active=project.is_active,
        report_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="List projects",
    description="Get list of construction projects with filtering."
)
async def list_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> ProjectListResponse:
    """List construction projects."""
    service = ProjectService(db)

    # Filter by user's tenant unless superuser
    tenant_id = None if current_user.is_superuser else current_user.tenant_id

    return await service.list_projects(
        tenant_id=tenant_id,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID",
    description="Get detailed information about a specific project."
)
async def get_project(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    """Get project by ID."""
    service = ProjectService(db)
    project = await service.get_project(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Check access (same tenant or superuser)
    if not current_user.is_superuser and project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )

    report_count = await service._get_report_count(project.id)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        project_code=project.project_code,
        tenant_id=project.tenant_id,
        manager_id=project.manager_id,
        manager_name=project.manager.full_name if project.manager else None,
        is_active=project.is_active,
        report_count=report_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
    description="Update project details."
)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    """Update a project."""
    service = ProjectService(db)

    # Check project exists and access
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    if not current_user.is_superuser and project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )

    project = await service.update_project(project_id, data)
    report_count = await service._get_report_count(project.id)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        project_code=project.project_code,
        tenant_id=project.tenant_id,
        manager_id=project.manager_id,
        manager_name=project.manager.full_name if project.manager else None,
        is_active=project.is_active,
        report_count=report_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post(
    "/projects/{project_id}/archive",
    response_model=dict,
    summary="Archive project",
    description="Archive a project (set is_active=False)."
)
async def archive_project(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Archive a project."""
    service = ProjectService(db)

    # Check project exists and access
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    if not current_user.is_superuser and project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )

    await service.archive_project(project_id)
    return {"message": f"Project '{project.name}' has been archived"}


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Permanently delete a project and all associated reports."
)
async def delete_project(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a project."""
    service = ProjectService(db)

    # Check project exists and access
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete projects"
        )

    await service.delete_project(project_id)


# =============================================================================
# Public Endpoints (for anonymous upload)
# =============================================================================

@router.get(
    "/validate-code/{code}",
    response_model=ProjectCodeValidation,
    summary="Validate project code",
    description="Validate a 4-digit project code for anonymous upload. Public endpoint."
)
async def validate_project_code(
    code: str = Path(..., min_length=4, max_length=4, pattern="^[0-9]{4}$"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> ProjectCodeValidation:
    """
    Validate a project code for anonymous upload.

    This is a PUBLIC endpoint - no authentication required.
    Used by the uploader UI to validate codes before file upload.
    """
    service = ProjectService(db)
    return await service.validate_code(code)


# =============================================================================
# Dashboard Endpoints
# =============================================================================

@router.get(
    "/dashboard/projects",
    response_model=ProjectDashboardResponse,
    summary="Get projects dashboard",
    description="Get projects with status summary for manager dashboard."
)
async def get_dashboard_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    my_projects_only: bool = Query(False, description="Only show projects I manage"),
) -> ProjectDashboardResponse:
    """
    Get projects dashboard with statistics.

    Returns list of projects with:
    - Report counts by status
    - Open risks count
    - Last report date
    """
    service = ProjectService(db)

    manager_id = current_user.id if my_projects_only else None
    tenant_id = None if current_user.is_superuser else current_user.tenant_id

    return await service.get_dashboard_projects(
        manager_id=manager_id,
        tenant_id=tenant_id,
    )


@router.get(
    "/dashboard/calendar",
    response_model=CalendarResponse,
    summary="Get calendar events",
    description="Get reports as calendar events for user's assigned projects."
)
async def get_calendar_events(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    project_ids: Optional[str] = Query(
        None,
        description="Comma-separated project IDs to filter"
    ),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
) -> CalendarResponse:
    """
    Get calendar events (reports) for specified projects.

    If no project_ids provided, shows events for all projects
    the user manages.
    """
    service = ProjectService(db)

    # Parse project IDs
    parsed_project_ids = None
    if project_ids:
        try:
            parsed_project_ids = [int(p.strip()) for p in project_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_ids format. Must be comma-separated integers."
            )

    return await service.get_calendar_events(
        project_ids=parsed_project_ids,
        manager_id=current_user.id if not parsed_project_ids else None,
        start_date=start_date,
        end_date=end_date,
    )
