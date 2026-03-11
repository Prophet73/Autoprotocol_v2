"""
System settings service.

Provides CRUD operations for dynamic system configuration.
Settings are stored in the database and can be changed without redeployment.

Priority: DB value (admin changed) > env var (shared/config.py) > hardcoded default.
"""
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.admin.models import SystemSetting
from backend.shared import config
from .schemas import (
    SettingResponse,
    SettingListResponse,
    CreateSettingRequest,
    UpdateSettingRequest,
)


# Default settings with metadata for UI rendering.
# Values come from backend.shared.config (single source of truth).
DEFAULT_SETTINGS = {
    "gemini_translate_model": {
        "value": config.TRANSLATE_MODEL,
        "description": "Gemini модель для перевода (Flash — быстрая, дешёвая)",
        "input_type": "select",
        "options": [
            "gemini-3.1-flash-lite-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ],
        "category": "llm",
    },
    "gemini_report_model": {
        "value": config.REPORT_MODEL,
        "description": "Gemini модель для отчётов и анализа (Pro — качественная)",
        "input_type": "select",
        "options": [
            "gemini-3.1-pro-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-pro",
        ],
        "category": "llm",
    },
    "max_file_size_mb": {
        "value": str(config.MAX_FILE_SIZE_MB),
        "description": "Макс. размер загружаемого файла в МБ",
        "input_type": "number",
        "category": "limits",
    },
    "job_ttl_hours": {
        "value": str(config.JOB_TTL_HOURS),
        "description": "Часов хранения данных задачи в Redis",
        "input_type": "number",
        "category": "retention",
    },
    "audio_retention_days": {
        "value": str(config.AUDIO_RETENTION_DAYS),
        "description": "Дней хранения аудио/видео файлов (отчёты сохраняются)",
        "input_type": "number",
        "category": "retention",
    },
    "error_log_retention_days": {
        "value": str(config.ERROR_LOG_RETENTION_DAYS),
        "description": "Дней хранения логов ошибок в БД",
        "input_type": "number",
        "category": "retention",
    },
}


def get_setting_value(key: str, default: str) -> str:
    """Read a setting from DB with fallback to default.

    Works from both sync (Celery) and async (FastAPI) contexts.
    Use for runtime-changeable settings (admin panel).
    """
    from backend.shared.database import get_db_context
    from backend.shared.async_utils import run_async

    async def _fetch():
        async with get_db_context() as db:
            service = SettingsService(db)
            return await service.get_value(key, default=default)

    try:
        return run_async(_fetch())
    except Exception:
        return default


def _setting_metadata(key: str) -> dict:
    """Get metadata for a known default setting."""
    meta = DEFAULT_SETTINGS.get(key, {})
    return {
        "input_type": meta.get("input_type", "text"),
        "options": meta.get("options"),
        "category": meta.get("category", "other"),
        "default_value": meta.get("value"),
    }


class SettingsService:
    """Service for system settings management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_settings(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> SettingListResponse:
        """
        List all settings: merge defaults with DB overrides.

        Default settings always appear. If a DB record exists for a key,
        its value overrides the default and is_default=False.
        Custom (non-default) DB settings are appended at the end.
        """
        # Load all DB settings
        result = await self.db.execute(
            select(SystemSetting).order_by(SystemSetting.key)
        )
        db_settings = {s.key: s for s in result.scalars().all()}

        merged: list[SettingResponse] = []

        # 1. Default settings (in definition order)
        for key, meta in DEFAULT_SETTINGS.items():
            db_row = db_settings.pop(key, None)
            if db_row:
                merged.append(SettingResponse(
                    key=key,
                    value=db_row.value,
                    description=meta["description"],
                    updated_at=db_row.updated_at,
                    updated_by=db_row.updated_by,
                    is_default=False,
                    default_value=meta["value"],
                    input_type=meta.get("input_type", "text"),
                    options=meta.get("options"),
                    category=meta.get("category", "other"),
                ))
            else:
                merged.append(SettingResponse(
                    key=key,
                    value=meta["value"],
                    description=meta["description"],
                    updated_at=None,
                    updated_by=None,
                    is_default=True,
                    default_value=meta["value"],
                    input_type=meta.get("input_type", "text"),
                    options=meta.get("options"),
                    category=meta.get("category", "other"),
                ))

        # 2. Custom settings (in DB but not in defaults)
        for key, db_row in db_settings.items():
            merged.append(SettingResponse(
                key=key,
                value=db_row.value,
                description=db_row.description,
                updated_at=db_row.updated_at,
                updated_by=db_row.updated_by,
                is_default=False,
                default_value=None,
                input_type="text",
                options=None,
                category="custom",
            ))

        total = len(merged)
        page = merged[skip:skip + limit]

        return SettingListResponse(settings=page, total=total)

    async def get_setting(self, key: str) -> Optional[SystemSetting]:
        """Get setting by key."""
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        return result.scalar_one_or_none()

    async def get_value(self, key: str, default: str = None) -> Optional[str]:
        """
        Get setting value by key.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        setting = await self.get_setting(key)
        if setting:
            return setting.value
        return default

    async def create_setting(
        self,
        request: CreateSettingRequest,
        updated_by: str = None,
    ) -> SystemSetting:
        """
        Create a new setting.

        Args:
            request: Create request
            updated_by: Email of user creating the setting

        Returns:
            Created setting

        Raises:
            ValueError: If key already exists
        """
        existing = await self.get_setting(request.key)
        if existing:
            raise ValueError(f"Setting with key '{request.key}' already exists")

        setting = SystemSetting(
            key=request.key,
            value=request.value,
            description=request.description,
            updated_by=updated_by,
        )

        self.db.add(setting)
        await self.db.flush()
        await self.db.refresh(setting)
        return setting

    async def update_setting(
        self,
        key: str,
        request: UpdateSettingRequest,
        updated_by: str = None,
    ) -> SettingResponse:
        """
        Update a setting. Uses upsert for default settings not yet in DB.

        Returns:
            Updated setting as SettingResponse (with metadata).
        """
        setting = await self.get_setting(key)

        if setting:
            setting.value = request.value
            if request.description is not None:
                setting.description = request.description
            setting.updated_by = updated_by
            await self.db.flush()
            await self.db.refresh(setting)
        else:
            # Default setting being customized for the first time — create DB row
            meta = DEFAULT_SETTINGS.get(key)
            if not meta:
                raise ValueError(f"Setting with key '{key}' not found")
            setting = SystemSetting(
                key=key,
                value=request.value,
                description=request.description or meta["description"],
                updated_by=updated_by,
            )
            self.db.add(setting)
            await self.db.flush()
            await self.db.refresh(setting)

        metadata = _setting_metadata(key)
        return SettingResponse(
            key=setting.key,
            value=setting.value,
            description=setting.description,
            updated_at=setting.updated_at,
            updated_by=setting.updated_by,
            is_default=False,
            **metadata,
        )

    async def upsert_setting(
        self,
        key: str,
        value: str,
        description: str = None,
        updated_by: str = None,
    ) -> SystemSetting:
        """
        Create or update a setting.

        Args:
            key: Setting key
            value: Setting value
            description: Optional description
            updated_by: Email of user

        Returns:
            Created or updated setting
        """
        setting = await self.get_setting(key)

        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.updated_by = updated_by
        else:
            setting = SystemSetting(
                key=key,
                value=value,
                description=description,
                updated_by=updated_by,
            )
            self.db.add(setting)

        await self.db.flush()
        await self.db.refresh(setting)
        return setting

    async def delete_setting(self, key: str) -> bool:
        """
        Delete a setting (resets to default if it's a known setting).

        Args:
            key: Setting key

        Returns:
            True if deleted, False if not found in DB
        """
        setting = await self.get_setting(key)
        if not setting:
            return False

        await self.db.delete(setting)
        await self.db.flush()
        return True

    async def reset_to_default(self, key: str) -> SettingResponse:
        """
        Reset a setting to its default value by removing the DB override.

        Returns:
            The setting with default value.

        Raises:
            ValueError: If key is not a known default setting.
        """
        meta = DEFAULT_SETTINGS.get(key)
        if not meta:
            raise ValueError(f"Setting '{key}' has no default value")

        # Remove DB override if exists
        setting = await self.get_setting(key)
        if setting:
            await self.db.delete(setting)
            await self.db.flush()

        return SettingResponse(
            key=key,
            value=meta["value"],
            description=meta["description"],
            updated_at=None,
            updated_by=None,
            is_default=True,
            default_value=meta["value"],
            input_type=meta.get("input_type", "text"),
            options=meta.get("options"),
            category=meta.get("category", "other"),
        )

    async def bulk_update(
        self,
        settings: dict[str, str],
        updated_by: str = None,
    ) -> List[SystemSetting]:
        """
        Update multiple settings at once.

        Args:
            settings: Key -> value mapping
            updated_by: Email of user

        Returns:
            List of updated settings
        """
        results = []
        for key, value in settings.items():
            setting = await self.upsert_setting(
                key=key,
                value=value,
                updated_by=updated_by,
            )
            results.append(setting)
        return results
