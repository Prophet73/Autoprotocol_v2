"""
System settings service.

Provides CRUD operations for dynamic system configuration.
Settings are stored in the database and can be changed without redeployment.
"""
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.admin.models import SystemSetting
from .schemas import (
    SettingResponse,
    SettingListResponse,
    CreateSettingRequest,
    UpdateSettingRequest,
)


# Default settings to initialize on first run
DEFAULT_SETTINGS = {
    "llm_model": {
        "value": "gemini-2.0-flash",
        "description": "LLM model for translation and report generation"
    },
    "whisper_model": {
        "value": "large-v3",
        "description": "Whisper model for transcription (tiny, base, small, medium, large-v2, large-v3)"
    },
    "max_file_size_mb": {
        "value": "500",
        "description": "Maximum upload file size in megabytes"
    },
    "job_ttl_hours": {
        "value": "24",
        "description": "Hours to keep job data in Redis before auto-cleanup"
    },
    "audio_retention_days": {
        "value": "7",
        "description": "Days to keep audio/video files before cleanup (reports are preserved)"
    },
    "error_log_retention_days": {
        "value": "30",
        "description": "Days to keep error logs in database"
    },
    "enable_emotions": {
        "value": "true",
        "description": "Enable emotion analysis by default"
    },
    "enable_diarization": {
        "value": "true",
        "description": "Enable speaker diarization by default"
    },
    "default_language": {
        "value": "ru",
        "description": "Default transcription language"
    },
    "batch_size": {
        "value": "16",
        "description": "Batch size for Whisper inference"
    },
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
        List all system settings.

        Args:
            skip: Records to skip
            limit: Max records to return

        Returns:
            List of settings with total count
        """
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(SystemSetting)
        )
        total = count_result.scalar() or 0

        # Get settings
        result = await self.db.execute(
            select(SystemSetting)
            .offset(skip)
            .limit(limit)
            .order_by(SystemSetting.key)
        )
        settings = result.scalars().all()

        return SettingListResponse(
            settings=[SettingResponse.model_validate(s) for s in settings],
            total=total,
        )

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
    ) -> SystemSetting:
        """
        Update an existing setting.

        Args:
            key: Setting key
            request: Update request
            updated_by: Email of user updating the setting

        Returns:
            Updated setting

        Raises:
            ValueError: If setting not found
        """
        setting = await self.get_setting(key)
        if not setting:
            raise ValueError(f"Setting with key '{key}' not found")

        setting.value = request.value
        if request.description is not None:
            setting.description = request.description
        setting.updated_by = updated_by

        await self.db.flush()
        await self.db.refresh(setting)
        return setting

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
        Delete a setting.

        Args:
            key: Setting key

        Returns:
            True if deleted, False if not found
        """
        setting = await self.get_setting(key)
        if not setting:
            return False

        await self.db.delete(setting)
        await self.db.flush()
        return True

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

    async def initialize_defaults(self, updated_by: str = None) -> int:
        """
        Initialize default settings if they don't exist.

        Args:
            updated_by: Email of user

        Returns:
            Number of settings created
        """
        created = 0
        for key, data in DEFAULT_SETTINGS.items():
            existing = await self.get_setting(key)
            if not existing:
                setting = SystemSetting(
                    key=key,
                    value=data["value"],
                    description=data["description"],
                    updated_by=updated_by,
                )
                self.db.add(setting)
                created += 1

        if created > 0:
            await self.db.flush()

        return created
