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
    Float,
    ForeignKey,
    Table,
    Column,
    JSON,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# Many-to-many association table for project managers
project_managers = Table(
    'project_managers',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('construction_projects.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now())
)

# Many-to-many association table for user domains
user_domains = Table(
    'user_domains',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('domain', String(50), primary_key=True),  # construction, hr, it
    Column('assigned_at', DateTime(timezone=True), server_default=func.now())
)

# User-Project access table (simple read access like Autoprotokol)
user_project_access = Table(
    'user_project_access',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('project_id', Integer, ForeignKey('construction_projects.id', ondelete='CASCADE'), primary_key=True),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
)


class UserRole(str, Enum):
    """User roles in the system.

    Hierarchy (from lowest to highest):
    - viewer: Read-only access to reports
    - user: Can upload files and view own reports
    - manager: Can view all reports, download risk briefs
    - admin: Full access including user management
    - superuser: System-level access
    """
    VIEWER = "viewer"
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPERUSER = "superuser"


def _build_domain_enum() -> type:
    """Build Domain enum dynamically from registry."""
    try:
        from backend.domains.registry import DOMAINS
        members = {d_id.upper(): d_id for d_id in DOMAINS}
    except Exception:
        # Fallback if registry not ready (migrations, tests)
        members = {
            "CONSTRUCTION": "construction",
            "DCT": "dct",
            "FTA": "fta",
            "BUSINESS": "business",
            "CEO": "ceo",
        }
    return Enum("Domain", members, type=str)


Domain = _build_domain_enum()


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
        lazy="select"
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
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
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
    # Legacy single domain field (kept for backwards compatibility)
    domain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Active domain for current session (used by frontend switcher)
    active_domain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Tenant (multi-tenancy)
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # SSO fields
    sso_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sso_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

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
        lazy="select"
    )
    domain_assignments: Mapped[list["UserDomainAssignment"]] = relationship(
        "UserDomainAssignment",
        back_populates="user",
        foreign_keys="UserDomainAssignment.user_id",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    project_access_records: Mapped[list["UserProjectAccessRecord"]] = relationship(
        "UserProjectAccessRecord",
        back_populates="user",
        foreign_keys="UserProjectAccessRecord.user_id",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    @property
    def domains(self) -> list[str]:
        """Get list of assigned domains."""
        return [da.domain for da in self.domain_assignments]

    @property
    def has_multiple_domains(self) -> bool:
        """Check if user has access to multiple domains."""
        return len(self.domain_assignments) > 1

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


class UserDomainAssignment(Base):
    """
    User domain assignment for multi-domain access.

    Allows users to have access to multiple domains (construction, hr, it).
    """
    __tablename__ = "user_domain_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "domain", name="uq_user_domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    assigned_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="domain_assignments",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<UserDomainAssignment(user_id={self.user_id}, domain='{self.domain}')>"


class UserProjectAccessRecord(Base):
    """
    User project access for dashboard read permissions.

    Simple model: if record exists, user has read access to project.
    Similar to Autoprotokol's UserProjectAccess.
    """
    __tablename__ = "user_project_access_records"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_user_project"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("construction_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    granted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="project_access_records",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<UserProjectAccessRecord(user_id={self.user_id}, project_id={self.project_id})>"


class TranscriptionJob(Base):
    """
    Central transcription job tracking for all domains.

    Stores metadata and results of processed transcriptions
    for statistics and analytics across all domains.

    Attributes:
        id: Primary key
        job_id: Unique job identifier (UUID)
        domain: Domain (construction, hr, it)
        meeting_type: Meeting type within domain
        status: Processing status
        user_id: User who uploaded (nullable for anonymous)
        tenant_id: Associated tenant
        project_id: Construction project (for construction domain)
        source_filename: Original file name
        source_size_bytes: File size in bytes
        audio_duration_seconds: Audio/video duration
        processing_time_seconds: Time taken to process
        segment_count: Number of transcript segments
        speaker_count: Number of identified speakers
        input_tokens: Gemini input tokens used
        output_tokens: Gemini output tokens used
        artifacts: JSON with generated artifacts flags
        error_message: Error details if failed
        created_at: Job creation timestamp
        started_at: Processing start timestamp
        completed_at: Processing completion timestamp
    """
    __tablename__ = "transcription_jobs"
    __table_args__ = (
        Index("idx_job_user_status_created", "user_id", "status", "created_at"),
        Index("idx_job_status_created", "status", "created_at"),
        CheckConstraint(
            "status IN ('pending','queued','processing','completed','failed','expired')",
            name="ck_job_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # Domain and type
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="construction")
    meeting_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="pending")

    # User and tenant
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Project (for construction domain)
    project_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("construction_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Visibility
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")

    # Source file info
    source_filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audio_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Processing stats
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    segment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    speaker_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # AI token usage (for cost calculation)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Per-model token breakdown (Flash = translate, Pro = reports/analysis)
    flash_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    flash_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    pro_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    pro_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")

    # Artifacts generated (JSON: {transcript: true, tasks: true, report: false, analysis: false})
    artifacts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<TranscriptionJob(id={self.id}, job_id='{self.job_id}', domain='{self.domain}', status='{self.status}')>"
