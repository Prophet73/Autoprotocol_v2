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
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """Current user info response."""
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
    """Registration request."""
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
    Login with email/username and password.

    Returns JWT token for authentication.

    Use this token in Authorization header:
    `Authorization: Bearer <token>`
    """
    # Find user by email OR username
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

    # Create access token
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
    Register a new user.

    Note: New users are created with 'user' role.
    Superuser privileges must be granted by another superuser.
    """
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
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
    """Get current user info."""
    return UserInfo.model_validate(current_user)


class SetDomainRequest(BaseModel):
    """Request to set active domain."""
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
    Set active domain for current user.

    User must have access to the domain (or be superuser).
    """
    # Check if user has access to domain
    allowed_domains = current_user.domains if current_user.domains else []

    # Superusers can access any domain
    if current_user.is_superuser:
        allowed_domains = ["construction", "hr", "it", "general"]

    if data.domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No access to domain: {data.domain}. Allowed: {allowed_domains}"
        )

    # Update active domain
    current_user.active_domain = data.domain
    await db.commit()
    await db.refresh(current_user)

    return UserInfo.model_validate(current_user)


# =============================================================================
# Dev Tools (only in development mode)
# =============================================================================

import os
import warnings

# DEV_MODE is disabled by default for security
# Only enable in explicit development environment
_env = os.getenv("ENVIRONMENT", "production").lower()
DEV_MODE = _env in ("development", "dev", "local")

if DEV_MODE:
    warnings.warn(
        "DEV_MODE is enabled! /auth/dev/* endpoints are accessible. "
        "Set ENVIRONMENT=production to disable.",
        UserWarning
    )


class DevLoginRequest(BaseModel):
    """Dev login request - select role to login as."""
    role: str  # admin, manager, user


class DevUsersList(BaseModel):
    """List of available dev users."""
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
    """List available dev users for quick login."""
    if not DEV_MODE:
        return DevUsersList(users=[], enabled=False)

    # Get existing users
    result = await db.execute(select(User).where(User.is_active == True))
    users = result.scalars().all()

    return DevUsersList(
        users=[
            {
                "email": u.email,
                "role": u.role,
                "is_superuser": u.is_superuser,
                "full_name": u.full_name,
            }
            for u in users
        ],
        enabled=True
    )


@router.post(
    "/dev/login",
    response_model=Token,
    summary="[DEV] Быстрый вход для тестирования",
    description="Вход под тестовым пользователем по роли (только в dev режиме)."
)
async def dev_login(
    data: DevLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Quick login as a specific role for development testing.

    Creates user if doesn't exist:
    - admin: admin@dev.local
    - manager: manager@dev.local
    - user: user@dev.local
    """
    if not DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login disabled in production"
        )

    # Map role to user config
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

    if data.role not in role_configs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Available: {list(role_configs.keys())}"
        )

    config = role_configs[data.role]

    # Find or create user
    result = await db.execute(
        select(User).where(User.email == config["email"])
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create dev user
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

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
