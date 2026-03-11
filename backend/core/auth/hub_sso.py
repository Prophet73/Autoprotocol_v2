"""
Hub SSO Integration (clean implementation).

Provides two endpoints:
- `/auth/hub/login` — redirects to Hub OAuth authorize URL and stores state
- `/auth/hub/callback` — exchanges code, creates/updates local user, then redirects

Frontend expects the callback to redirect to `/auth/callback?token=<local_jwt>&redirect=<path>`
so the front-end can read `token` and finish login.
"""

import os
import secrets
from urllib.parse import urlencode, quote_plus

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
import logging
from redis import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import User
from .dependencies import (
    create_access_token,
    create_refresh_token,
)


router = APIRouter(prefix="/auth/hub", tags=["Hub SSO"])

# Hub Configuration
HUB_URL = os.getenv("HUB_URL", "https://ai-hub.svrd.ru")
# HUB_INTERNAL_URL — URL для API-вызовов из backend контейнера (token, userinfo).
# В dev используется внутренний Docker hostname mock-hub вместо localhost.
# По умолчанию равен HUB_URL (в проде они совпадают).
HUB_INTERNAL_URL = os.getenv("HUB_INTERNAL_URL", HUB_URL)
HUB_CLIENT_ID = os.getenv("HUB_CLIENT_ID", "")
HUB_CLIENT_SECRET = os.getenv("HUB_CLIENT_SECRET", "")
HUB_REDIRECT_URI = os.getenv("HUB_REDIRECT_URI", "")

# Hub logout URL (configurable; common patterns: /logout, /accounts/logout, /oauth/logout)
HUB_LOGOUT_URL = os.getenv("HUB_LOGOUT_URL", "")

# SSO state storage in Redis (survives API restarts, supports multiple replicas)
_SSO_STATE_PREFIX = "sso:state:"
_SSO_STATE_TTL = 600  # 10 minutes expiry for OAuth states
_redis: Redis | None = None


def _get_sso_redis() -> Redis:
    """Get Redis connection for SSO state storage."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
    return _redis


def _store_state(state: str, redirect_to: str) -> None:
    """Store OAuth state in Redis with TTL."""
    _get_sso_redis().setex(f"{_SSO_STATE_PREFIX}{state}", _SSO_STATE_TTL, redirect_to)


def _pop_state(state: str) -> str | None:
    """Retrieve and delete OAuth state from Redis. Returns redirect_to or None."""
    r = _get_sso_redis()
    key = f"{_SSO_STATE_PREFIX}{state}"
    pipe = r.pipeline()
    pipe.get(key)
    pipe.delete(key)
    result = pipe.execute()
    return result[0]  # GET result


@router.get("/check")
async def hub_check():
    """Check if Hub SSO is configured (used by frontend to detect SSO at runtime)."""
    return {"configured": bool(HUB_CLIENT_ID and HUB_REDIRECT_URI), "hub_url": HUB_URL or None}


@router.get("/login")
async def hub_login(redirect_to: str = "/admin"):
    # Validate redirect_to to prevent open redirect
    if not redirect_to.startswith("/") or redirect_to.startswith("//") or "://" in redirect_to:
        redirect_to = "/admin"

    if not HUB_CLIENT_ID or not HUB_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hub SSO not configured"
        )

    state = secrets.token_urlsafe(32)
    _store_state(state, redirect_to)

    params = {
        "client_id": HUB_CLIENT_ID,
        "redirect_uri": HUB_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }

    auth_url = f"{HUB_URL}/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def hub_callback(
    code: str = Query(None),
    state: str = Query(""),
    error: str = Query(None),
    error_description: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    logger = logging.getLogger(__name__)

    # Verify state (CSRF protection) — reject unknown/expired states
    redirect_to = _pop_state(state)
    if redirect_to is None:
        logger.warning("Hub OAuth callback with invalid/expired state: %s", state[:16])
        return RedirectResponse(url="/login?error=invalid_state&manual=true")

    # Handle error responses from Hub (e.g. login_required, access_denied)
    if error:
        logger.warning("Hub OAuth error: %s - %s", error, error_description)
        err_msg = quote_plus(error_description or error)
        return RedirectResponse(url=f"/login?error={err_msg}&manual=true")

    if not code:
        return RedirectResponse(url="/login?error=missing_code&manual=true")

    # Prepare token exchange payload
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": HUB_REDIRECT_URI,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Try RFC6749 recommended Basic auth first
            resp = await client.post(
                f"{HUB_INTERNAL_URL}/oauth/token",
                data=token_data,
                auth=(HUB_CLIENT_ID, HUB_CLIENT_SECRET) if HUB_CLIENT_ID and HUB_CLIENT_SECRET else None,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Detect if server requires client credentials in request body
            resp_text_lower = ""
            try:
                resp_text_lower = resp.text.lower() if resp is not None and resp.text is not None else ""
            except Exception:
                resp_text_lower = ""

            needs_body_credentials = (
                resp.status_code in (400, 401)
                or ("client_id" in resp_text_lower and ("missing" in resp_text_lower or "field required" in resp_text_lower))
            )

            if needs_body_credentials and HUB_CLIENT_ID and HUB_CLIENT_SECRET:
                body = dict(token_data)
                body.update({"client_id": HUB_CLIENT_ID, "client_secret": HUB_CLIENT_SECRET})
                resp = await client.post(
                    f"{HUB_INTERNAL_URL}/oauth/token",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            try:
                resp_text = resp.text
            except Exception:
                resp_text = "<unreadable>"

            logger.info("Hub token endpoint: status=%s", resp.status_code)

            if resp.status_code != 200:
                logger.debug("Hub token error: %s", resp_text[:200])
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to exchange code: {resp_text}"
                )

            tokens = resp.json()
            logger.debug("Hub token response keys: %s", list(tokens.keys()))
            hub_access_token = tokens.get("access_token")

            # Get userinfo
            userinfo_resp = await client.get(
                f"{HUB_INTERNAL_URL}/oauth/userinfo",
                headers={"Authorization": f"Bearer {hub_access_token}"},
            )

            if userinfo_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get user info from Hub"
                )

            userinfo = userinfo_resp.json()

    except httpx.RequestError as e:
        logger.exception("HTTP request to Hub failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to Hub: {str(e)}"
        )

    # Map Hub user info to local user
    email = userinfo.get("email")
    full_name = userinfo.get("name") or userinfo.get("preferred_username")
    sso_id = str(userinfo.get("sub") or userinfo.get("id") or "")

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Hub")

    # Find existing user by email or sso id
    result = await db.execute(
        select(User).where((User.email == email) | ((User.sso_provider == "hub") & (User.sso_id == sso_id)))
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Create new SSO user (no usable password)
        user = User(
            email=email,
            full_name=full_name,
            hashed_password="!SSO_ONLY_NO_PASSWORD_LOGIN",
            is_active=True,
            is_superuser=False,
            role="user",
            sso_provider="hub",
            sso_id=sso_id,
        )
        db.add(user)
    else:
        # Update basic fields
        user.full_name = full_name or user.full_name
        user.sso_provider = "hub"
        user.sso_id = sso_id or user.sso_id

    await db.commit()

    # Issue local JWT pair and redirect to frontend callback with tokens
    local_token = create_access_token({"sub": user.email})
    local_refresh = create_refresh_token({"sub": user.email})

    # Build frontend callback URL: /auth/callback?token=...&refresh=...&redirect=/admin
    redirect_param = quote_plus(redirect_to)
    target = f"/auth/callback?token={local_token}&refresh={local_refresh}&redirect={redirect_param}"
    return RedirectResponse(url=target)


@router.get("/logout")
async def hub_logout(request: Request):
    """Log out from both local app and Hub SSO session.

    Redirects to Hub's logout page which clears the Hub session,
    then Hub redirects back to the app's login page.
    """
    login_path = "/login?manual=true"

    if not HUB_URL or not HUB_CLIENT_ID:
        return RedirectResponse(url=login_path)

    # Derive app base URL from HUB_REDIRECT_URI
    # e.g. "https://autoprotocol.svrd.ru/auth/hub/callback" → "https://autoprotocol.svrd.ru"
    app_base = ""
    if HUB_REDIRECT_URI:
        idx = HUB_REDIRECT_URI.find("/auth/hub/callback")
        if idx > 0:
            app_base = HUB_REDIRECT_URI[:idx]

    if not app_base:
        app_base = f"{request.url.scheme}://{request.url.netloc}"

    post_logout_url = f"{app_base}{login_path}"

    # Use configured logout URL or default to {HUB_URL}/logout
    logout_base = HUB_LOGOUT_URL or f"{HUB_URL}/logout"
    separator = "&" if "?" in logout_base else "?"
    hub_logout_url = f"{logout_base}{separator}redirect_uri={quote_plus(post_logout_url)}"

    return RedirectResponse(url=hub_logout_url)
