"""
Authentication and authorization dependencies for FastAPI.

Provides:
- get_current_user: Extract user from JWT token
- require_superuser: Ensure user has superuser privileges
- get_optional_user: Get user if authenticated, None otherwise
"""
import os
import uuid
from typing import Optional, Annotated
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import User


# Configuration
_env = os.getenv("ENVIRONMENT", "production").lower()
_is_production = _env not in ("development", "dev", "local")

# SECRET_KEY is required in production
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if _is_production:
        raise RuntimeError(
            "SECRET_KEY environment variable is required in production. "
            "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    else:
        # Only use dev key in development environment
        SECRET_KEY = "dev-secret-key-for-local-development-only"
        import warnings
        warnings.warn(
            "Using development SECRET_KEY. This is insecure! "
            "Set SECRET_KEY environment variable in production.",
            UserWarning
        )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Payload data (should contain 'sub' with user email)
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "access",
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT refresh token.

    Args:
        data: Payload data (should contain 'sub' with user email)
        expires_delta: Token expiration time (default: 7 days)

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get current authenticated user from JWT token.

    Raises:
        HTTPException 401: If token is missing or invalid
        HTTPException 401: If user not found or inactive

    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"email": user.email}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type", "access")
        if email is None:
            raise credentials_exception
        # Reject refresh tokens used as access tokens
        if token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Get user from database
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    return user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Does not raise exceptions for missing/invalid tokens.

    Usage:
        @app.get("/public-or-private")
        async def route(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello, {user.email}"}
            return {"message": "Hello, anonymous"}
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type", "access")
        if email is None:
            return None
        # Reject refresh tokens used as access tokens
        if token_type != "access":
            return None
    except JWTError:
        return None

    result = await db.execute(
        select(User).where(User.email == email, User.is_active)
    )
    return result.scalar_one_or_none()


async def require_superuser(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Ensure current user is a superuser.

    Raises:
        HTTPException 403: If user is not a superuser

    Usage:
        @app.get("/admin")
        async def admin_route(user: User = Depends(require_superuser)):
            return {"admin": user.email}
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Ensure current user is an admin or superuser.
    
    Admins have the same privileges as superusers, except:
    - Cannot modify superusers
    - Cannot assign admin role to others
    - Cannot access /admin/settings

    Raises:
        HTTPException 403: If user is not an admin or superuser

    Usage:
        @app.get("/admin/users")
        async def admin_route(user: User = Depends(require_admin)):
            return {"admin": user.email}
    """
    if not user.is_superuser and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
SuperUser = Annotated[User, Depends(require_superuser)]
AdminUser = Annotated[User, Depends(require_admin)]
