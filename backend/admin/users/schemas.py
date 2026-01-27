"""
Схемы для эндпоинтов управления пользователями.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

from backend.shared.models import UserRole, Domain


class UserResponse(BaseModel):
    """Информация о пользователе."""
    id: int = Field(..., description="ID пользователя")
    email: str = Field(..., description="Email адрес")
    full_name: Optional[str] = Field(None, description="Полное имя")
    is_active: bool = Field(..., description="Активен ли аккаунт")
    is_superuser: bool = Field(..., description="Суперпользователь")
    role: str = Field(..., description="Роль (admin, manager, user)")
    domain: Optional[str] = Field(None, description="Основной домен (legacy)")
    domains: List[str] = Field(default=[], description="Список доменов")
    active_domain: Optional[str] = Field(None, description="Активный домен")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Список пользователей."""
    users: List[UserResponse] = Field(..., description="Пользователи")
    total: int = Field(..., description="Общее количество")


class AssignRoleRequest(BaseModel):
    """Запрос на назначение роли и домена."""
    user_id: int = Field(..., description="ID пользователя")
    role: UserRole = Field(..., description="Роль")
    domain: Optional[Domain] = Field(None, description="Домен")


class AssignRoleResponse(BaseModel):
    """Ответ после назначения роли."""
    message: str = Field(..., description="Сообщение")
    user: UserResponse = Field(..., description="Обновлённый пользователь")


class CreateUserRequest(BaseModel):
    """Запрос на создание пользователя (только админ)."""
    email: EmailStr = Field(..., description="Email адрес")
    password: str = Field(..., description="Пароль")
    full_name: Optional[str] = Field(None, description="Полное имя")
    role: UserRole = Field(default=UserRole.USER, description="Роль")
    domain: Optional[Domain] = Field(None, description="Домен")
    is_superuser: bool = Field(default=False, description="Суперпользователь")


class UpdateUserRequest(BaseModel):
    """Запрос на обновление данных пользователя."""
    full_name: Optional[str] = Field(None, description="Полное имя")
    is_active: Optional[bool] = Field(None, description="Активен ли аккаунт")
    is_superuser: Optional[bool] = Field(None, description="Суперпользователь")
    role: Optional[UserRole] = Field(None, description="Роль")
    domain: Optional[Domain] = Field(None, description="Основной домен")
    domains: Optional[List[str]] = Field(None, description="Список доменов")
    active_domain: Optional[str] = Field(None, description="Активный домен")


# Схемы управления доменами
class AssignDomainsRequest(BaseModel):
    """Запрос на назначение нескольких доменов."""
    user_id: int = Field(..., description="ID пользователя")
    domains: List[str] = Field(..., description="Домены: construction, hr, it")


class SetActiveDomainRequest(BaseModel):
    """Запрос на установку активного домена."""
    domain: str = Field(..., description="Домен")


# Схемы доступа к проектам
class GrantProjectAccessRequest(BaseModel):
    """Запрос на предоставление доступа к проекту."""
    user_id: int = Field(..., description="ID пользователя")
    project_id: int = Field(..., description="ID проекта")


class RevokeProjectAccessRequest(BaseModel):
    """Запрос на отзыв доступа к проекту."""
    user_id: int = Field(..., description="ID пользователя")
    project_id: int = Field(..., description="ID проекта")


class ProjectAccessResponse(BaseModel):
    """Ответ операций с доступом к проекту."""
    user_id: int = Field(..., description="ID пользователя")
    project_id: int = Field(..., description="ID проекта")
    granted: bool = Field(..., description="Доступ предоставлен")
    message: str = Field(..., description="Сообщение")


class UserProjectAccessList(BaseModel):
    """Список проектов с доступом пользователя."""
    user_id: int = Field(..., description="ID пользователя")
    project_ids: List[int] = Field(..., description="ID проектов")


class ProjectUserAccessList(BaseModel):
    """Список пользователей с доступом к проекту."""
    project_id: int = Field(..., description="ID проекта")
    user_ids: List[int] = Field(..., description="ID пользователей")
    users: List[UserResponse] = Field(default=[], description="Информация о пользователях")


class BatchUpdateProjectAccessRequest(BaseModel):
    """Запрос на batch-обновление доступа к проектам."""
    project_ids: List[int] = Field(..., description="Список ID проектов (заменяет все текущие)")


class BatchUpdateProjectAccessResponse(BaseModel):
    """Ответ batch-обновления доступа к проектам."""
    user_id: int = Field(..., description="ID пользователя")
    granted: int = Field(..., description="Количество выданных доступов")
    revoked: int = Field(..., description="Количество отозванных доступов")
    total: int = Field(..., description="Итоговое количество доступов")
