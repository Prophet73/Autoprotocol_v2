"""
Admin-specific database models.

Contains:
- SystemSetting: Dynamic system configuration
- PromptTemplate: Dynamic prompts with JSON schemas
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, Boolean, Integer, JSON, func
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


class PromptTemplate(Base):
    """
    Dynamic prompt template with JSON schema for structured output.

    Enables creating new report types without code changes.
    The response_schema defines the expected LLM output structure.

    Attributes:
        id: Primary key
        name: Template name (e.g., "weekly_summary", "risk_assessment")
        slug: URL-friendly identifier
        domain: Domain this template belongs to (e.g., "construction", "hr", "universal")
        description: Human-readable description
        system_prompt: LLM system prompt (personality/context)
        user_prompt_template: User prompt template with {placeholders}
        response_schema: JSON Schema for structured output
        is_active: Whether template is available for use
        is_default: Whether this is the default template for domain
        version: Template version for tracking changes
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: Email of creator
    """
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Prompts
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)

    # JSON Schema for structured output
    response_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<PromptTemplate(id={self.id}, slug='{self.slug}', domain='{self.domain}')>"
