"""
Authentication router.

Endpoints for:
- Login (get JWT token)
- Register (create account)
- Me (get current user)
"""
from datetime import timedelta
from typing import Annotated
import os

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import User, Domain
from .dependencies import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    CurrentUser,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM,
)


router = APIRouter(prefix="/auth", tags=["Авторизация"])

# Если нужно разрешить только вход через SSO — включите переменную окружения SSO_ONLY
SSO_ONLY = os.getenv("SSO_ONLY", "false").lower() in ("1", "true", "yes")
# Open registration control: disabled by default for security
REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "false").lower() in ("1", "true", "yes")

# Login rate limit (configurable via env, Redis-backed via `limits` library)
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5/minute")

# Lazy-initialized Redis-backed rate limiter
_login_limiter = None
_login_rate = None


def _get_login_limiter():
    """Get or create Redis-backed login rate limiter (lazy singleton)."""
    global _login_limiter, _login_rate
    if _login_limiter is None:
        from limits import parse
        from limits.storage import RedisStorage
        from limits.strategies import FixedWindowRateLimiter
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        storage = RedisStorage(redis_url)
        _login_limiter = FixedWindowRateLimiter(storage)
        _login_rate = parse(RATE_LIMIT_LOGIN)
    return _login_limiter, _login_rate


def _check_login_rate_limit(request: Request) -> None:
    """Check login rate limit via Redis. Fails open if Redis unavailable."""
    try:
        limiter, rate = _get_login_limiter()
        client_ip = request.client.host if request.client else "unknown"
        if not limiter.hit(rate, "login", client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много попыток входа. Повторите позже.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Fail open — don't block login if Redis is down


# =============================================================================
# Schemas
# =============================================================================

class Token(BaseModel):
    """Ответ с JWT токеном."""
    access_token: str
    refresh_token: str | None = None
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
    password: str = Field(..., min_length=8, max_length=128)
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
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Аутентификация по email/username и паролю.

    Возвращает JWT токен для авторизации.

    Использование токена в заголовке Authorization:
    `Authorization: Bearer <token>`
    """
    # Rate limiting via Redis (works across multiple workers)
    _check_login_rate_limit(request)

    # Если система настроена на работу только через SSO — запрещаем локальный вход
    if SSO_ONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local authentication is disabled. Use SSO at /auth/hub/login",
        )
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

    # Создание токенов доступа
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
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
    # Если система работает только через SSO — регистрация локальных аккаунтов запрещена
    if SSO_ONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local registration is disabled. Use SSO to provision accounts.",
        )
    # Open registration disabled by default — use admin panel or set REGISTRATION_ENABLED=true
    if not REGISTRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled. Contact administrator.",
        )
    # Проверка существования email
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"  # Generic message to prevent email enumeration
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


class RefreshRequest(BaseModel):
    """Запрос на обновление токена."""
    refresh_token: str


@router.post(
    "/refresh",
    response_model=Token,
    summary="Обновить токен",
    description="Обмен refresh токена на новую пару access + refresh токенов."
)
async def refresh_token(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Обменять refresh токен на новую пару токенов.

    Refresh токен одноразовый — после использования выдаётся новый.
    """
    from jose import JWTError, jwt as jose_jwt

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jose_jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        if email is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.email == email, User.is_active)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception

    # Issue new token pair
    new_access = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh = create_refresh_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


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

    # Суперпользователи и админы имеют доступ к любому домену
    if current_user.is_superuser or current_user.role == "admin":
        allowed_domains = [d.value for d in Domain]

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
