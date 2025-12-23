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
from sqlalchemy import select
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


router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    full_name: str | None
    role: str
    domain: str | None
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
    summary="Login",
    description="Get JWT access token using email and password."
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Login with email and password.

    Returns JWT token for authentication.

    Use this token in Authorization header:
    `Authorization: Bearer <token>`
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
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
    summary="Register",
    description="Create a new user account."
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
    summary="Get current user",
    description="Get information about the currently authenticated user."
)
async def get_me(current_user: CurrentUser) -> UserInfo:
    """Get current user info."""
    return UserInfo.model_validate(current_user)
