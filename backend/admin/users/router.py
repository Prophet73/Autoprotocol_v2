"""
Admin user management router.

Endpoints for superusers to manage users, roles, and domains.
All endpoints require superuser privileges.
"""
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import UserRole, Domain
from backend.core.auth.dependencies import SuperUser
from .service import UserService
from .schemas import (
    UserResponse,
    UserListResponse,
    AssignRoleRequest,
    AssignRoleResponse,
    CreateUserRequest,
    UpdateUserRequest,
    ProjectAccessResponse,
    UserProjectAccessList,
)


router = APIRouter(prefix="/users", tags=["Админ - Пользователи"])


@router.get(
    "/",
    response_model=UserListResponse,
    summary="Список пользователей",
    description="Получение списка пользователей с пагинацией и фильтрацией по роли/домену."
)
async def list_users(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    domain: Optional[Domain] = Query(None, description="Filter by domain"),
) -> UserListResponse:
    """
    List all users with their roles and domains.

    Requires superuser privileges.
    """
    service = UserService(db)
    return await service.list_users(
        skip=skip,
        limit=limit,
        role_filter=role,
        domain_filter=domain,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Получить пользователя",
    description="Получение детальной информации о пользователе по ID."
)
async def get_user(
    user_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Get user details by ID."""
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return UserResponse.model_validate(user)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пользователя",
    description="Создание нового пользователя с указанной ролью и доменом."
)
async def create_user(
    request: CreateUserRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Create a new user (superuser only).

    Password will be hashed before storage.
    """
    service = UserService(db)
    try:
        user = await service.create_user(request)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/assign-role",
    response_model=AssignRoleResponse,
    summary="Назначить роль",
    description="Назначение роли и домена пользователю."
)
async def assign_role(
    request: AssignRoleRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssignRoleResponse:
    """
    Assign role and domain to a user.

    Requires superuser privileges.
    Setting role to 'superuser' automatically sets is_superuser=True.
    """
    service = UserService(db)
    try:
        user = await service.assign_role(request)
        return AssignRoleResponse(
            message=f"Role '{request.role.value}' assigned to user {user.email}",
            user=UserResponse.model_validate(user)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Обновить пользователя",
    description="Обновление данных пользователя (частичное)."
)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Update user details."""
    service = UserService(db)
    try:
        user = await service.update_user(user_id, request)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя",
    description="Безвозвратное удаление аккаунта пользователя."
)
async def delete_user(
    user_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a user.

    Cannot delete yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    service = UserService(db)
    deleted = await service.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )


# =============================================================================
# Domain Management Endpoints
# =============================================================================

@router.post(
    "/{user_id}/domains",
    response_model=UserResponse,
    summary="Назначить домены",
    description="Назначить пользователю доступ к нескольким доменам (заменяет текущие)."
)
async def assign_domains(
    user_id: int,
    domains: list[str],
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Assign multiple domains to a user.

    Replaces all existing domain assignments.
    Valid domains: construction, hr, it, general
    """
    service = UserService(db)
    try:
        user = await service.assign_domains(
            user_id=user_id,
            domains=domains,
            assigned_by_id=current_user.id
        )
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{user_id}/domains",
    response_model=list[str],
    summary="Получить домены пользователя",
    description="Получить список доменов, к которым пользователь имеет доступ."
)
async def get_user_domains(
    user_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    """Get list of domains assigned to user."""
    service = UserService(db)
    return await service.get_user_domains(user_id)


# =============================================================================
# Project Access Management Endpoints
# =============================================================================

@router.post(
    "/{user_id}/projects/{project_id}",
    response_model=ProjectAccessResponse,
    summary="Дать доступ к проекту",
    description="Выдать пользователю права на чтение проекта (dashboard)."
)
async def grant_project_access(
    user_id: int,
    project_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectAccessResponse:
    """
    Grant user read access to a project.

    Similar to Autoprotokol's access model.
    """
    service = UserService(db)
    granted = await service.grant_project_access(
        user_id=user_id,
        project_id=project_id,
        granted_by_id=current_user.id
    )
    return ProjectAccessResponse(
        user_id=user_id,
        project_id=project_id,
        granted=granted,
        message="Access granted" if granted else "Access already exists"
    )


@router.delete(
    "/{user_id}/projects/{project_id}",
    response_model=ProjectAccessResponse,
    summary="Отозвать доступ к проекту",
    description="Отозвать у пользователя права на чтение проекта."
)
async def revoke_project_access(
    user_id: int,
    project_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectAccessResponse:
    """Revoke user's read access to a project."""
    service = UserService(db)
    revoked = await service.revoke_project_access(user_id, project_id)
    return ProjectAccessResponse(
        user_id=user_id,
        project_id=project_id,
        granted=not revoked,
        message="Access revoked" if revoked else "Access didn't exist"
    )


@router.get(
    "/{user_id}/projects",
    response_model=UserProjectAccessList,
    summary="Проекты пользователя",
    description="Получить список проектов, к которым пользователь имеет доступ."
)
async def get_user_projects(
    user_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProjectAccessList:
    """Get list of project IDs user has access to."""
    service = UserService(db)
    project_ids = await service.get_user_project_ids(user_id)
    return UserProjectAccessList(user_id=user_id, project_ids=project_ids)
