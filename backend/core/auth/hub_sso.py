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
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
import logging
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
HUB_REDIRECT_URI = os.getenv("HUB_REDIRECT_URI", "")

# In-memory state storage (simple; replace with Redis in production)
_pending_states: dict[str, str] = {}


@router.get("/login")
async def hub_login(redirect_to: str = "/admin"):
    if not HUB_CLIENT_ID or not HUB_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hub SSO not configured"
        )

    state = secrets.token_urlsafe(32)
    _pending_states[state] = redirect_to

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
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    logger = logging.getLogger(__name__)

    # Verify state and get redirect target
    redirect_to = _pending_states.pop(state, "/admin")

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
                f"{HUB_URL}/oauth/token",
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
                    f"{HUB_URL}/oauth/token",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            try:
                resp_text = resp.text
            except Exception:
                resp_text = "<unreadable>"

            logger.info("Hub token endpoint: status=%s body=%s", resp.status_code, resp_text)

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to exchange code: {resp_text}"
                )

            tokens = resp.json()
            hub_access_token = tokens.get("access_token")

            # Get userinfo
            userinfo_resp = await client.get(
                f"{HUB_URL}/oauth/userinfo",
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

    created = False
    if user is None:
        # Create new SSO user (no usable password)
        user = User(
            email=email,
            full_name=full_name,
            hashed_password="",
            is_active=True,
            is_superuser=False,
            role="user",
            sso_provider="hub",
            sso_id=sso_id,
        )
        db.add(user)
        created = True
    else:
        # Update basic fields
        user.full_name = full_name or user.full_name
        user.sso_provider = "hub"
        user.sso_id = sso_id or user.sso_id

    await db.commit()

    # Issue local JWT and redirect to frontend callback with token
    local_token = create_access_token({"sub": user.email})

    # Build frontend callback URL: /auth/callback?token=...&redirect=/admin
    redirect_param = quote_plus(redirect_to)
    target = f"/auth/callback?token={local_token}&redirect={redirect_param}"
    return RedirectResponse(url=target)
