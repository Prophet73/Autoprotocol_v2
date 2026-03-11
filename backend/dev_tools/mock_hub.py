"""
Mock Hub SSO — локальный OAuth2 сервер для dev окружения.

Эмулирует Hub SSO (ai-hub.svrd.ru) для тестирования полного SSO-флоу
без подключения к реальному Hub. Только для разработки.

Запуск:
    /venv/bin/python -m uvicorn backend.dev_tools.mock_hub:app --host 0.0.0.0 --port 8100

Реализует:
    GET  /check               — /auth/hub/check совместимость
    GET  /oauth/authorize     — страница выбора пользователя
    POST /oauth/authorize     — обработка выбора, redirect с code
    POST /oauth/token         — обмен code → opaque access token
    GET  /oauth/userinfo      — данные пользователя по токену
"""

import logging
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

# =============================================================================
# In-memory state (dev only, single instance)
# =============================================================================

_codes: dict[str, dict] = {}   # code → userinfo dict
_tokens: dict[str, dict] = {}  # token → userinfo dict

# =============================================================================
# Mock users
# =============================================================================

MOCK_USERS = [
    {
        "sub": "mock-superadmin",
        "email": "admin@mock.dev",
        "name": "Dev Superadmin",
        "preferred_username": "dev-superadmin",
        # Internal fields for seeding (stripped before storing in _codes/_tokens)
        "_role": "superuser",
        "_is_superuser": True,
    },
    {
        "sub": "mock-manager",
        "email": "manager@mock.dev",
        "name": "Dev Manager",
        "preferred_username": "dev-manager",
        "_role": "manager",
        "_is_superuser": False,
    },
    {
        "sub": "mock-user",
        "email": "user@mock.dev",
        "name": "Dev User",
        "preferred_username": "dev-user",
        "_role": "user",
        "_is_superuser": False,
    },
    {
        "sub": "mock-viewer",
        "email": "viewer@mock.dev",
        "name": "Dev Viewer",
        "preferred_username": "dev-viewer",
        "_role": "viewer",
        "_is_superuser": False,
    },
]

# Role → (border color, background color, text color)
ROLE_STYLES: dict[str, tuple[str, str, str]] = {
    "superuser": ("#7c3aed", "#f5f3ff", "#5b21b6"),
    "manager":   ("#2563eb", "#eff6ff", "#1d4ed8"),
    "user":      ("#059669", "#ecfdf5", "#047857"),
    "viewer":    ("#6b7280", "#f9fafb", "#374151"),
}

# =============================================================================
# DB seed
# =============================================================================

async def _seed_dev_users() -> None:
    """Создаёт/обновляет mock-пользователей в БД с нужными ролями."""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.warning("Mock Hub: DATABASE_URL не задан, пропускаем seed")
        return

    seed_rows = [
        ("admin@mock.dev",   "Dev Superadmin", True,  "superuser", "mock-superadmin"),
        ("manager@mock.dev", "Dev Manager",    False, "manager",   "mock-manager"),
        ("user@mock.dev",    "Dev User",       False, "user",      "mock-user"),
        ("viewer@mock.dev",  "Dev Viewer",     False, "viewer",    "mock-viewer"),
    ]

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            for email, name, is_super, role, sso_id in seed_rows:
                await session.execute(
                    text("""
                        INSERT INTO users
                            (email, hashed_password, full_name, is_active,
                             is_superuser, role, sso_provider, sso_id)
                        VALUES
                            (:email, '!SSO_ONLY_NO_PASSWORD_LOGIN', :name, true,
                             :is_super, :role, 'hub', :sso_id)
                        ON CONFLICT (email) DO UPDATE SET
                            is_superuser = EXCLUDED.is_superuser,
                            role         = EXCLUDED.role,
                            sso_provider = EXCLUDED.sso_provider,
                            sso_id       = EXCLUDED.sso_id
                    """),
                    {"email": email, "name": name, "is_super": is_super,
                     "role": role, "sso_id": sso_id},
                )
            await session.commit()
        logger.info("Mock Hub: dev users seeded (%d rows)", len(seed_rows))
    except Exception as exc:
        logger.warning("Mock Hub: seed failed (tables may not exist yet): %s", exc)
    finally:
        await engine.dispose()

# =============================================================================
# App
# =============================================================================

@asynccontextmanager
async def lifespan(_: FastAPI):
    await _seed_dev_users()
    yield


app = FastAPI(title="Mock Hub SSO (dev only)", docs_url=None, redoc_url=None, lifespan=lifespan)

# =============================================================================
# Endpoints
# =============================================================================

@app.get("/check")
async def check():
    """Совместимость с /auth/hub/check — всегда сообщает что SSO настроен."""
    return {"configured": True, "hub_url": None}


@app.get("/oauth/authorize", response_class=HTMLResponse)
async def authorize_get(
    redirect_uri: str = Query(default=""),
    state: str = Query(default=""),
    client_id: str = Query(default=""),
    response_type: str = Query(default="code"),
    scope: str = Query(default=""),
):
    """Страница выбора пользователя для mock SSO входа."""
    buttons_html = ""
    for user in MOCK_USERS:
        role = user["_role"]
        border, bg, color = ROLE_STYLES.get(role, ("#6b7280", "#f9fafb", "#374151"))
        buttons_html += f"""
        <form method="post" action="/oauth/authorize">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="user_email" value="{user['email']}">
            <button type="submit" style="
                width: 100%; padding: 14px 16px; margin-bottom: 8px;
                border: 1.5px solid {border}; border-radius: 8px;
                background: {bg}; color: {color};
                font-size: 14px; font-weight: 600; cursor: pointer;
                display: flex; justify-content: space-between; align-items: center;
                transition: opacity 0.15s;
            " onmouseover="this.style.opacity=0.8" onmouseout="this.style.opacity=1">
                <span>{user['name']}</span>
                <span style="font-size: 12px; font-weight: 400; opacity: 0.75;">
                    {user['email']} &middot; {role}
                </span>
            </button>
        </form>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mock Hub SSO</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #111827; min-height: 100vh;
      display: flex; align-items: center; justify-content: center;
    }}
    .card {{
      background: #fff; border-radius: 14px; padding: 32px;
      width: 420px; max-width: 92vw;
      box-shadow: 0 20px 60px rgba(0,0,0,0.4);
    }}
    .badge {{
      display: inline-flex; align-items: center; gap: 6px;
      background: #fef3c7; color: #92400e;
      border: 1px solid #f59e0b; border-radius: 6px;
      font-size: 11px; font-weight: 700; padding: 3px 10px;
      margin-bottom: 18px; text-transform: uppercase; letter-spacing: 0.05em;
    }}
    h1 {{ font-size: 20px; color: #111827; margin-bottom: 6px; }}
    .sub {{ font-size: 13px; color: #6b7280; margin-bottom: 22px; line-height: 1.5; }}
    .footer {{
      margin-top: 20px; font-size: 11px; color: #9ca3af;
      text-align: center; padding-top: 16px;
      border-top: 1px solid #f3f4f6;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">⚠ DEV ONLY</div>
    <h1>Mock Hub SSO</h1>
    <p class="sub">
      Локальный fake OAuth сервер. Выберите роль для входа —
      пользователь будет создан автоматически.
    </p>
    {buttons_html}
    <div class="footer">SeverinAutoprotocol &middot; Mock Hub &middot; dev environment</div>
  </div>
</body>
</html>"""


@app.post("/oauth/authorize")
async def authorize_post(
    redirect_uri: str = Form(...),
    state: str = Form(...),
    user_email: str = Form(...),
):
    """Обрабатывает выбор пользователя, генерирует code, редиректит в callback."""
    user = next((u for u in MOCK_USERS if u["email"] == user_email), None)
    if not user:
        sep = "&" if "?" in redirect_uri else "?"
        return RedirectResponse(
            url=f"{redirect_uri}{sep}error=user_not_found&state={state}",
            status_code=302,
        )

    # Сохраняем только OAuth-совместимые поля (без _role, _is_superuser)
    code = secrets.token_urlsafe(24)
    _codes[code] = {k: v for k, v in user.items() if not k.startswith("_")}

    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        url=f"{redirect_uri}{sep}code={code}&state={state}",
        status_code=302,
    )


@app.post("/oauth/token")
async def token_endpoint(request: Request):
    """Обменивает authorization code на opaque access token."""
    form = await request.form()
    code = str(form.get("code", ""))

    if not code or code not in _codes:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Invalid or expired code"},
            status_code=400,
        )

    userinfo = _codes.pop(code)
    access_token = secrets.token_urlsafe(32)
    _tokens[access_token] = userinfo

    return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}


@app.get("/oauth/userinfo")
async def userinfo_endpoint(request: Request):
    """Возвращает данные пользователя по access token."""
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()

    if not token or token not in _tokens:
        return JSONResponse(
            {"error": "invalid_token"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _tokens[token]
