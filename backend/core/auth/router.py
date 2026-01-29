"""
Authentication router.

Endpoints for:
- Login (get JWT token)
- Register (create account)
- Me (get current user)
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import User
from .dependencies import (
    verify_password,
    get_password_hash,
    create_access_token,
    CurrentUser,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


router = APIRouter(prefix="/auth", tags=["Авторизация"])


# =============================================================================
# Schemas
# =============================================================================

class Token(BaseModel):
    """Ответ с JWT токеном."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """Ответ с информацией о текущем пользователе."""
    id: int
    email: str
    username: str | None
    full_name: str | None
    role: str
    domain: str | None  # Legacy single domain
    domains: list[str] = []  # Multiple domains
    active_domain: str | None = None  # Currently selected domain
    is_superuser: bool
    tenant_id: int | None

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    """Запрос на регистрацию нового пользователя."""
    email: EmailStr
    password: str
    full_name: str | None = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/login",
    response_model=Token,
    summary="Вход в систему",
    description="Получение JWT токена по email/username и паролю."
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Аутентификация по email/username и паролю.

    Возвращает JWT токен для авторизации.

    Использование токена в заголовке Authorization:
    `Authorization: Bearer <token>`
    """
    # Поиск пользователя по email ИЛИ username
    result = await db.execute(
        select(User).where(
            or_(
                User.email == form_data.username,
                User.username == form_data.username
            )
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    # Создание токена доступа
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/register",
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация",
    description="Создание нового аккаунта пользователя."
)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserInfo:
    """
    Регистрация нового пользователя.

    Примечание: Новые пользователи создаются с ролью 'user'.
    Права суперпользователя должны быть выданы другим суперпользователем.
    """
    # Проверка существования email
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Создание пользователя
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserInfo.model_validate(user)


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Текущий пользователь",
    description="Получение информации о текущем авторизованном пользователе."
)
async def get_me(current_user: CurrentUser) -> UserInfo:
    """Получить информацию о текущем пользователе."""
    return UserInfo.model_validate(current_user)


class SetDomainRequest(BaseModel):
    """Запрос на установку активного домена."""
    domain: str


@router.post(
    "/me/domain",
    response_model=UserInfo,
    summary="Переключить домен",
    description="Установить активный домен для текущей сессии."
)
async def set_active_domain(
    data: SetDomainRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserInfo:
    """
    Установить активный домен для текущего пользователя.

    Пользователь должен иметь доступ к домену (или быть суперпользователем).
    """
    # Проверка доступа пользователя к домену
    allowed_domains = current_user.domains if current_user.domains else []

    # Суперпользователи имеют доступ к любому домену
    if current_user.is_superuser:
        allowed_domains = ["construction", "dct"]

    if data.domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No access to domain: {data.domain}. Allowed: {allowed_domains}"
        )

    # Обновление активного домена
    current_user.active_domain = data.domain
    await db.commit()
    await db.refresh(current_user)

    return UserInfo.model_validate(current_user)


# =============================================================================
# Инструменты разработчика (только в режиме разработки)
# =============================================================================

import os
import warnings

# DEV_MODE по умолчанию отключён из соображений безопасности
# Включается только в явном окружении разработки
_env = os.getenv("ENVIRONMENT", "production").lower()
DEV_MODE = _env in ("development", "dev", "local")

if DEV_MODE:
    warnings.warn(
        "DEV_MODE is enabled! /auth/dev/* endpoints are accessible. "
        "Set ENVIRONMENT=production to disable.",
        UserWarning
    )


class DevLoginRequest(BaseModel):
    """Запрос быстрого входа - выбор роли для входа."""
    role: str  # admin, manager, user


class DevUsersList(BaseModel):
    """Список доступных тестовых пользователей."""
    users: list[dict]
    enabled: bool


@router.get(
    "/dev/users",
    response_model=DevUsersList,
    summary="[DEV] Список тестовых пользователей",
    description="Получение списка доступных тестовых пользователей (только в dev режиме)."
)
async def dev_list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DevUsersList:
    """Получить список доступных тестовых пользователей для быстрого входа."""
    if not DEV_MODE:
        return DevUsersList(users=[], enabled=False)

    # Получение существующих пользователей
    result = await db.execute(select(User).where(User.is_active == True))
    users = result.scalars().all()

    return DevUsersList(
        users=[
            {
                "email": u.email,
                "role": u.role,
                "is_superuser": u.is_superuser,
                "full_name": u.full_name,
                "domain": u.active_domain or u.domain,
            }
            for u in users
        ],
        enabled=True
    )


@router.post(
    "/dev/login",
    response_model=Token,
    summary="[DEV] Быстрый вход для тестирования",
    description="Вход под тестовым пользователем по роли или email (только в dev режиме)."
)
async def dev_login(
    data: DevLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Быстрый вход под определённой ролью или существующим пользователем для тестирования.

    Принимает:
    - Название роли (admin/manager/user) - создаёт пользователя если не существует
    - Email адрес - входит под существующим пользователем
    """
    if not DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login disabled in production"
        )

    # Маппинг роли на конфигурацию пользователя
    role_configs = {
        "admin": {
            "email": "admin@dev.local",
            "role": "admin",
            "is_superuser": True,
            "full_name": "Dev Admin",
        },
        "manager": {
            "email": "manager@dev.local",
            "role": "manager",
            "is_superuser": False,
            "full_name": "Dev Manager",
        },
        "user": {
            "email": "user@dev.local",
            "role": "user",
            "is_superuser": False,
            "full_name": "Dev User",
        },
    }

    user = None

    # Проверка является ли ввод email (содержит @)
    if "@" in data.role:
        # Вход под существующим пользователем по email
        result = await db.execute(
            select(User).where(User.email == data.role, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {data.role} not found"
            )
    elif data.role in role_configs:
        # Вход по роли - найти или создать
        config = role_configs[data.role]

        result = await db.execute(
            select(User).where(User.email == config["email"])
        )
        user = result.scalar_one_or_none()

        if not user:
            # Создание dev пользователя
            user = User(
                email=config["email"],
                hashed_password=get_password_hash("devpassword"),
                full_name=config["full_name"],
                role=config["role"],
                is_superuser=config["is_superuser"],
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input. Use role ({list(role_configs.keys())}) or email address."
        )

    # Создание токена доступа
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
