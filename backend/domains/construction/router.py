"""
Роутер домена строительства.

Эндпоинты для:
- Управление проектами (CRUD)
- Валидация кода проекта (публичный)
- Дашборд менеджера (календарь, статистика проектов)
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


router = APIRouter(prefix="/construction", tags=["Домен - Строительство"])


# =============================================================================
# Project CRUD Endpoints
# =============================================================================

@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать проект",
    description="Создание нового строительного проекта с автогенерацией 4-значного кода."
)
async def create_project(
    data: ProjectCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    """Создание нового строительного проекта."""
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
    summary="Список проектов",
    description="Получение списка строительных проектов с фильтрацией."
)
async def list_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: Optional[bool] = Query(None, description="Фильтр по статусу активности"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> ProjectListResponse:
    """Список строительных проектов."""
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
    summary="Получить проект по ID",
    description="Получение детальной информации о конкретном проекте."
)
async def get_project(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    """Получить проект по ID."""
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
    summary="Обновить проект",
    description="Обновление данных проекта."
)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    """Обновление проекта."""
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
    summary="Архивировать проект",
    description="Архивация проекта (установка is_active=False)."
)
async def archive_project(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Архивация проекта."""
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
    summary="Удалить проект",
    description="Безвозвратное удаление проекта и всех связанных отчётов."
)
async def delete_project(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Удаление проекта."""
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
# Manager Assignment Endpoints
# =============================================================================

@router.post(
    "/projects/{project_id}/managers/{user_id}",
    response_model=dict,
    summary="Назначить менеджера на проект",
    description="Добавление пользователя в список менеджеров проекта."
)
async def assign_manager(
    project_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Назначить менеджера на проект."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can assign managers"
        )

    service = ProjectService(db)
    project = await service.get_project(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    success = await service.assign_manager(project_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign manager. User may not exist or is already assigned."
        )

    return {"message": f"Manager {user_id} assigned to project {project_id}"}


@router.delete(
    "/projects/{project_id}/managers/{user_id}",
    response_model=dict,
    summary="Удалить менеджера с проекта",
    description="Удаление пользователя из списка менеджеров проекта."
)
async def remove_manager(
    project_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Удалить менеджера с проекта."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can remove managers"
        )

    service = ProjectService(db)
    success = await service.remove_manager(project_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove manager. Assignment may not exist."
        )

    return {"message": f"Manager {user_id} removed from project {project_id}"}


@router.get(
    "/my-projects",
    response_model=ProjectListResponse,
    summary="Мои проекты",
    description="Получение списка проектов, на которых текущий пользователь назначен менеджером."
)
async def get_my_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: Optional[bool] = Query(None, description="Фильтр по статусу активности"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> ProjectListResponse:
    """Получить проекты текущего менеджера."""
    service = ProjectService(db)
    return await service.get_manager_projects(
        manager_id=current_user.id,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


# =============================================================================
# Public Endpoints (for anonymous upload)
# =============================================================================

@router.get(
    "/validate-code/{code}",
    response_model=ProjectCodeValidation,
    summary="Проверить код проекта",
    description="Валидация 4-значного кода проекта для анонимной загрузки. Публичный эндпоинт."
)
async def validate_project_code(
    code: str = Path(..., min_length=4, max_length=4, pattern="^[0-9]{4}$"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> ProjectCodeValidation:
    """
    Валидация кода проекта для анонимной загрузки.

    Это ПУБЛИЧНЫЙ эндпоинт - авторизация не требуется.
    Используется интерфейсом загрузчика для проверки кодов перед загрузкой файла.
    """
    service = ProjectService(db)
    return await service.validate_code(code)


# =============================================================================
# Dashboard Endpoints
# =============================================================================

@router.get(
    "/dashboard/projects",
    response_model=ProjectDashboardResponse,
    summary="Дашборд проектов",
    description="Получение проектов со сводкой статусов для дашборда менеджера."
)
async def get_dashboard_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    my_projects_only: bool = Query(False, description="Показать только мои проекты"),
) -> ProjectDashboardResponse:
    """
    Дашборд проектов со статистикой.

    Возвращает список проектов с:
    - Количеством отчётов по статусам
    - Количеством открытых рисков
    - Датой последнего отчёта
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
    summary="События календаря",
    description="Получение отчётов как событий календаря для проектов пользователя."
)
async def get_calendar_events(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    project_ids: Optional[str] = Query(
        None,
        description="ID проектов через запятую для фильтрации"
    ),
    start_date: Optional[datetime] = Query(None, description="Фильтр по начальной дате"),
    end_date: Optional[datetime] = Query(None, description="Фильтр по конечной дате"),
) -> CalendarResponse:
    """
    Получение событий календаря (отчётов) для указанных проектов.

    Если project_ids не указаны, показываются события для всех
    проектов, которыми управляет пользователь.
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
