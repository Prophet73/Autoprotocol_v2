"""
Shared database models.

Contains core models used across the application:
- User: Authentication and authorization
- ErrorLog: System error tracking
"""
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    Integer,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserRole(str, Enum):
    """User roles in the system."""
    USER = "user"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class Domain(str, Enum):
    """Available domains for role assignment."""
    CONSTRUCTION = "construction"
    HR = "hr"
    GENERAL = "general"


class Tenant(Base):
    """
    Tenant model for multi-tenancy support.

    Represents an organization/company that uses the system.

    Attributes:
        id: Primary key
        name: Organization name
        slug: URL-friendly identifier
        is_active: Whether tenant is active
        created_at: Tenant creation timestamp
    """
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}')>"


class User(Base):
    """
    User model for authentication and authorization.

    Attributes:
        id: Primary key
        email: Unique email address
        hashed_password: Bcrypt hashed password
        full_name: User's full name
        is_active: Whether user can login
        is_superuser: Whether user has admin access
        role: User role (user, admin, superuser)
        domain: Assigned domain (construction, hr, general)
        tenant_id: Associated tenant (organization)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Role and domain
    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.USER.value,
        nullable=False
    )
    domain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Tenant (multi-tenancy)
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

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

    # Relationships
    tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant",
        back_populates="users",
        lazy="selectin"
    )
    error_logs: Mapped[list["ErrorLog"]] = relationship(
        "ErrorLog",
        back_populates="user",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class ErrorLog(Base):
    """
    Error log model for tracking system errors.

    Automatically populated by error logging middleware.

    Attributes:
        id: Primary key
        timestamp: When the error occurred
        endpoint: API endpoint that caused the error
        method: HTTP method (GET, POST, etc.)
        error_type: Exception class name
        error_detail: Full error message/traceback
        user_id: User who triggered the error (if authenticated)
        request_body: Request payload (truncated for security)
        status_code: HTTP status code returned
    """
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    error_type: Mapped[str] = mapped_column(String(255), nullable=False)
    error_detail: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    request_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, default=500, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="error_logs",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ErrorLog(id={self.id}, endpoint='{self.endpoint}', error_type='{self.error_type}')>"
