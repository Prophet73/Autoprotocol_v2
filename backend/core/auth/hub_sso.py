"""
Hub SSO Integration.

OAuth2 authentication via Hub (corporate SSO gateway).
"""
import os
import secrets
from datetime import timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import User
from .dependencies import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES


router = APIRouter(prefix="/auth/hub", tags=["Hub SSO"])

# Hub Configuration
HUB_URL = os.getenv("HUB_URL", "https://ai-hub.svrd.ru")
HUB_CLIENT_ID = os.getenv("HUB_CLIENT_ID", "")
HUB_CLIENT_SECRET = os.getenv("HUB_CLIENT_SECRET", "")
HUB_REDIRECT_URI = os.getenv("HUB_REDIRECT_URI", "")  # e.g., https://whisperx.svrd.ru/auth/hub/callback

# In-memory state storage (use Redis in production)
_pending_states: dict[str, str] = {}


@router.get("/login")
async def hub_login(redirect_to: str = "/admin"):
    """
    Initiate Hub SSO login.

    Redirects user to Hub for authentication.
    """
    if not HUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hub SSO not configured"
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    _pending_states[state] = redirect_to

    # Build Hub authorization URL
    params = {
        "client_id": HUB_CLIENT_ID,
        "redirect_uri": HUB_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{HUB_URL}/oauth/authorize?{query_string}"

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def hub_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Hub OAuth2 callback.

    Exchanges authorization code for tokens and creates/updates local user.
    """
    # Verify state
    redirect_to = _pending_states.pop(state, None)
    if redirect_to is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                f"{HUB_URL}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": HUB_REDIRECT_URI,
                    "client_id": HUB_CLIENT_ID,
                    "client_secret": HUB_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to exchange code: {token_response.text}"
                )

            tokens = token_response.json()
            access_token = tokens.get("access_token")

            # Get user info from Hub
            userinfo_response = await client.get(
                f"{HUB_URL}/oauth/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get user info from Hub"
                )

            userinfo = userinfo_response.json()

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to Hub: {str(e)}"
        )

    # Extract user data from Hub userinfo
    email = userinfo.get("email")
    full_name = userinfo.get("name") or userinfo.get("display_name")
    hub_user_id = userinfo.get("sub") or userinfo.get("id")
    is_admin = userinfo.get("is_admin", False)
    department = userinfo.get("department")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Hub"
        )

    # Find or create user
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user from Hub data
        user = User(
            email=email,
            full_name=full_name,
            hashed_password="",  # No password for SSO users
            is_active=True,
            is_superuser=is_admin,
            role="admin" if is_admin else "user",
            sso_provider="hub",
            sso_id=str(hub_user_id),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update existing user with latest Hub data
        user.full_name = full_name or user.full_name
        if is_admin and not user.is_superuser:
            user.is_superuser = True
            user.role = "admin"
        user.sso_provider = "hub"
        user.sso_id = str(hub_user_id)
        await db.commit()

    # Create local JWT token
    local_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Redirect to frontend with token
    # Frontend will store this token and complete login
    frontend_callback = f"/auth/callback?token={local_token}&redirect={redirect_to}"

    return RedirectResponse(url=frontend_callback)


@router.get("/check")
async def check_hub_config():
    """Check if Hub SSO is configured."""
    return {
        "configured": bool(HUB_CLIENT_ID and HUB_CLIENT_SECRET),
        "hub_url": HUB_URL if HUB_CLIENT_ID else None,
    }
