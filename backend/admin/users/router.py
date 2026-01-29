"""
Роутер управления пользователями (админ-панель).

Эндпоинты для администраторов: управление пользователями, ролями и доменами.
Админы могут управлять пользователями, но не могут:
- Назначать роли admin/superuser (только superuser может)
- Изменять/удалять superuser'ов
"""
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import UserRole, Domain
from backend.core.auth.dependencies import AdminUser
from backend.core.auth.hub_sync import HubSyncService
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
    ProjectUserAccessList,
    BatchUpdateProjectAccessRequest,
    BatchUpdateProjectAccessResponse,
)


router = APIRouter(prefix="/users", tags=["Админ - Пользователи"])


def _check_admin_permissions(current_user, target_user=None, new_role=None, new_is_superuser=None):
    """
    Проверка прав админа на операцию.
    
    Админ (не superuser) не может:
    - Изменять superuser'ов
    - Назначать роли admin/superuser
    - Устанавливать is_superuser=True
    """
    if current_user.is_superuser:
        return  # superuser может всё
    
    # Админ не может изменять superuser'ов
    if target_user and target_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только superuser может изменять других superuser'ов"
        )
    
    # Админ не может назначать роли admin/superuser
    if new_role and new_role in (UserRole.ADMIN, UserRole.SUPERUSER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только superuser может назначать роли admin и superuser"
        )
    
    # Админ не может устанавливать is_superuser=True
    if new_is_superuser is True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только superuser может назначать права superuser"
        )


@router.get(
    "",
    response_model=UserListResponse,
    summary="Список пользователей",
    description="Получение списка пользователей с пагинацией и фильтрацией по роли/домену."
)
async def list_users(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(100, ge=1, le=1000, description="Максимум записей"),
    role: Optional[UserRole] = Query(None, description="Фильтр по роли"),
    domain: Optional[Domain] = Query(None, description="Фильтр по домену"),
) -> UserListResponse:
    """
    Список всех пользователей с ролями и доменами.

    Требует прав суперпользователя.
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Получить детали пользователя по ID."""
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return UserResponse.model_validate(user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пользователя",
    description="Создание нового пользователя с указанной ролью и доменом."
)
async def create_user(
    request: CreateUserRequest,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Создать нового пользователя.

    Админы не могут создавать пользователей с ролью admin/superuser.
    Пароль хешируется перед сохранением.
    """
    # Проверка прав
    _check_admin_permissions(
        current_user, 
        new_role=request.role, 
        new_is_superuser=request.is_superuser
    )
    
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssignRoleResponse:
    """
    Назначить роль и домен пользователю.

    Админы не могут назначать роли admin/superuser.
    Установка роли 'superuser' автоматически устанавливает is_superuser=True.
    """
    service = UserService(db)
    
    # Проверка прав - сначала получим целевого пользователя
    target_user = await service.get_user(request.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {request.user_id} not found"
        )
    
    _check_admin_permissions(current_user, target_user=target_user, new_role=request.role)
    
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Обновить данные пользователя."""
    service = UserService(db)
    
    # Проверка прав
    target_user = await service.get_user(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    _check_admin_permissions(
        current_user, 
        target_user=target_user, 
        new_role=request.role,
        new_is_superuser=request.is_superuser
    )
    
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Удалить пользователя.

    Нельзя удалить самого себя или superuser'а (если вы не superuser).
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    service = UserService(db)
    
    # Проверка прав
    target_user = await service.get_user(user_id)
    if target_user:
        _check_admin_permissions(current_user, target_user=target_user)
    
    deleted = await service.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )


# =============================================================================
# Управление доменами
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Назначить несколько доменов пользователю.

    Заменяет все существующие назначения доменов.
    Доступные домены: construction, dct, general
    """
    service = UserService(db)
    
    # Проверка прав
    target_user = await service.get_user(user_id)
    if target_user:
        _check_admin_permissions(current_user, target_user=target_user)
    
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    """Получить список доменов пользователя."""
    service = UserService(db)
    return await service.get_user_domains(user_id)


# =============================================================================
# Управление доступом к проектам
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectAccessResponse:
    """
    Выдать пользователю доступ на чтение проекта.

    Аналогично модели доступа Autoprotokol.
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectAccessResponse:
    """Отозвать у пользователя доступ к проекту."""
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProjectAccessList:
    """Получить список ID проектов, к которым пользователь имеет доступ."""
    service = UserService(db)
    project_ids = await service.get_user_project_ids(user_id)
    return UserProjectAccessList(user_id=user_id, project_ids=project_ids)


@router.put(
    "/{user_id}/projects",
    response_model=BatchUpdateProjectAccessResponse,
    summary="Batch обновление доступа к проектам",
    description="Заменить все текущие доступы к проектам на новый список."
)
async def batch_update_project_access(
    user_id: int,
    request: BatchUpdateProjectAccessRequest,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchUpdateProjectAccessResponse:
    """
    Batch обновление доступа к проектам.

    Заменяет все текущие доступы на указанный список project_ids.
    Эффективнее чем множество отдельных grant/revoke вызовов.
    """
    service = UserService(db)
    result = await service.batch_update_project_access(
        user_id=user_id,
        project_ids=request.project_ids,
        granted_by_id=current_user.id
    )
    return BatchUpdateProjectAccessResponse(
        user_id=user_id,
        granted=result["granted"],
        revoked=result["revoked"],
        total=result["total"]
    )


# =============================================================================
# Пользователи проекта (обратный поиск)
# =============================================================================

@router.get(
    "/by-project/{project_id}",
    response_model=ProjectUserAccessList,
    summary="Пользователи проекта",
    description="Получить список пользователей, имеющих доступ к проекту."
)
async def get_project_users(
    project_id: int,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_details: bool = False,
) -> ProjectUserAccessList:
    """Получить список пользователей с доступом к проекту."""
    service = UserService(db)
    user_ids = await service.get_project_user_ids(project_id)

    result = ProjectUserAccessList(project_id=project_id, user_ids=user_ids)

    # Optionally include full user details
    if include_details and user_ids:
        users = []
        for user_id in user_ids:
            user = await service.get_user(user_id)
            if user:
                users.append(UserResponse.model_validate(user))
        result.users = users

    return result


# =============================================================================
# Hub Sync
# =============================================================================

@router.post(
    "/sync-from-hub",
    summary="Синхронизация из Hub",
    description="Синхронизировать пользователей из Hub SSO в локальную БД."
)
async def sync_users_from_hub(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Синхронизировать всех пользователей из Hub.

    - Новые пользователи создаются автоматически
    - Существующие обновляются (имя, статус)
    - Локальные роли и права сохраняются

    Требует HUB_SERVICE_TOKEN в .env
    """
    try:
        sync_service = HubSyncService(db)
        stats = await sync_service.sync_all_users()
        return {
            "success": True,
            "stats": stats
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )
