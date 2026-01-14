"""
Admin-specific database models.

Contains:
- SystemSetting: Dynamic system configuration
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database import Base


class SystemSetting(Base):
    """
    System settings for dynamic configuration.

    Allows changing application behavior without redeployment.
    Examples: LLM model selection, feature flags, rate limits.

    Attributes:
        key: Unique setting identifier (e.g., "llm_model", "max_file_size")
        value: Setting value (stored as string, parse as needed)
        description: Human-readable description of the setting
        updated_at: Last modification timestamp
        updated_by: Email of user who last modified
    """
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        nullable=False
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemSetting(key='{self.key}', value='{self.value[:50]}...')>"
