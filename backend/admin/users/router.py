"""
Admin user management router.

Endpoints for superusers to manage users, roles, and domains.
All endpoints require superuser privileges.
"""
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import User, UserRole, Domain
from backend.core.auth.dependencies import SuperUser
from .service import UserService
from .schemas import (
    UserResponse,
    UserListResponse,
    AssignRoleRequest,
    AssignRoleResponse,
    CreateUserRequest,
    UpdateUserRequest,
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
