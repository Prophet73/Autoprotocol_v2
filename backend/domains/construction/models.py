"""
Construction domain database models.

Contains:
- ConstructionProject: Project with 4-digit access code
- ConstructionReport: Report linked to project and transcription
"""
import secrets
import string
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    Integer,
    Float,
    ForeignKey,
    JSON,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.database import Base


def generate_project_code() -> str:
    """Generate a unique 4-digit project code."""
    return ''.join(secrets.choice(string.digits) for _ in range(4))


class ConstructionProject(Base):
    """
    Construction project model.

    Projects group related reports and have a 4-digit access code
    for anonymous uploads.

    Attributes:
        id: Primary key
        name: Project name
        project_code: Unique 4-digit code for anonymous access
        description: Project description
        tenant_id: Associated tenant (organization)
        manager_id: Assigned project manager
        is_active: Whether project accepts new uploads
        created_at: Project creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "construction_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_code: Mapped[str] = mapped_column(
        String(4),
        unique=True,
        index=True,
        nullable=False,
        default=generate_project_code
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Tenant (organization)
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Project manager
    manager_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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
    manager: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[manager_id],
        lazy="selectin"
    )
    reports: Mapped[List["ConstructionReportDB"]] = relationship(
        "ConstructionReportDB",
        back_populates="project",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    # Many-to-many relationship for multiple managers
    managers: Mapped[List["User"]] = relationship(
        "User",
        secondary="project_managers",
        lazy="selectin",
        backref="managed_projects"
    )

    def __repr__(self) -> str:
        return f"<ConstructionProject(id={self.id}, name='{self.name}', code='{self.project_code}')>"


# Import User and project_managers for relationships
from backend.shared.models import User, project_managers


class ReportStatus(str):
    """Report processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConstructionReportDB(Base):
    """
    Construction report database model.

    Stores metadata and results of processed transcriptions
    linked to construction projects.

    Attributes:
        id: Primary key
        job_id: Reference to Redis job (transcription ID)
        project_id: Associated construction project
        tenant_id: Associated tenant
        uploaded_by_id: User who uploaded (nullable for anonymous)
        title: Report title
        meeting_date: Date of the meeting
        status: Processing status
        audio_file_path: Path to original audio file
        audio_size_bytes: Size of audio file
        transcript_path: Path to transcript output
        report_path: Path to generated report
        tasks_path: Path to tasks file
        analysis_path: Path to analysis file
        result_json: Full JSON result data
        processing_time: Time taken to process
        segment_count: Number of transcript segments
        speaker_count: Number of identified speakers
        error_message: Error details if failed
        created_at: Upload timestamp
        completed_at: Processing completion timestamp
    """
    __tablename__ = "construction_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # Project linkage
    project_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("construction_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Tenant
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Uploader (nullable for anonymous uploads via project code)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Guest UID for anonymous users (stored in localStorage on frontend)
    guest_uid: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True
    )

    # Report metadata
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meeting_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=ReportStatus.PENDING,
        nullable=False,
        index=True
    )

    # File paths
    audio_file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    audio_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    report_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    tasks_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    analysis_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Result data
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Processing stats
    processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    segment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    speaker_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    project: Mapped[Optional["ConstructionProject"]] = relationship(
        "ConstructionProject",
        back_populates="reports",
        lazy="selectin"
    )
    uploaded_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[uploaded_by_id],
        lazy="selectin"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_construction_reports_project_status", "project_id", "status"),
        Index("ix_construction_reports_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ConstructionReportDB(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"
