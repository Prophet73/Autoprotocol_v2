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
    # Contractors (organizations with roles)
    contractors: Mapped[List["ProjectContractor"]] = relationship(
        "ProjectContractor",
        back_populates="project",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ConstructionProject(id={self.id}, name='{self.name}', code='{self.project_code}')>"


# Import User and project_managers for relationships
from backend.shared.models import User


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
    report_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    risk_brief_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

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
    attendees: Mapped[List["MeetingAttendee"]] = relationship(
        "MeetingAttendee",
        back_populates="report",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_construction_reports_project_status", "project_id", "status"),
        Index("ix_construction_reports_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ConstructionReportDB(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"


class ReportAnalytics(Base):
    """
    Analytics data extracted from processed report.

    Contains AI-generated insights, challenges, and health status.
    """
    __tablename__ = "report_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("construction_reports.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Status and health
    health_status: Mapped[str] = mapped_column(
        String(20),
        default="stable",
        nullable=False
    )  # critical, attention, stable

    # AI-generated content
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_indicators: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    challenges: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    achievements: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Toxicity analysis
    toxicity_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    toxicity_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship
    report: Mapped["ConstructionReportDB"] = relationship(
        "ConstructionReportDB",
        lazy="selectin"
    )
    problems: Mapped[List["ReportProblem"]] = relationship(
        "ReportProblem",
        back_populates="analytics",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ReportAnalytics(id={self.id}, report_id={self.report_id}, health='{self.health_status}')>"


class ReportProblem(Base):
    """
    Problems/issues identified in report analytics.

    Manager can mark problems as resolved.
    """
    __tablename__ = "report_problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analytics_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("report_analytics.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Problem details
    problem_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(20),
        default="attention",
        nullable=False
    )  # critical, attention

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="new",
        nullable=False
    )  # new, done
    resolved_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    analytics: Mapped["ReportAnalytics"] = relationship(
        "ReportAnalytics",
        back_populates="problems",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ReportProblem(id={self.id}, severity='{self.severity}', status='{self.status}')>"


# =============================================================================
# УЧАСТНИКИ СОВЕЩАНИЙ
# =============================================================================

class ContractorRole(str):
    """Стандартные роли контрагентов на проекте."""
    CUSTOMER = "customer"                # Заказчик
    TECH_CUSTOMER = "tech_customer"      # Технический заказчик
    GENERAL_CONTRACTOR = "general"       # Генподрядчик
    SUBCONTRACTOR = "subcontractor"      # Субподрядчик
    DESIGNER = "designer"                # Проектировщик
    AUTHOR_SUPERVISION = "author"        # Авторский надзор
    CONSTRUCTION_CONTROL = "control"     # Стройконтроль

    @classmethod
    def labels(cls) -> dict:
        return {
            cls.CUSTOMER: "Заказчик",
            cls.TECH_CUSTOMER: "Технический заказчик",
            cls.GENERAL_CONTRACTOR: "Генподрядчик",
            cls.SUBCONTRACTOR: "Субподрядчик",
            cls.DESIGNER: "Проектировщик",
            cls.AUTHOR_SUPERVISION: "Авторский надзор",
            cls.CONSTRUCTION_CONTROL: "Стройконтроль",
        }


class Organization(Base):
    """
    Организация-контрагент на проекте.

    Например: ООО "Монолит", НПО "Проект", Severin Development
    """
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    project_roles: Mapped[List["ProjectContractor"]] = relationship(
        "ProjectContractor",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    persons: Mapped[List["Person"]] = relationship(
        "Person",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"


class ProjectContractor(Base):
    """
    Связь проекта с организацией и её ролью.

    Одна организация может иметь разные роли на разных проектах.
    """
    __tablename__ = "project_contractors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("construction_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # ContractorRole values

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    project: Mapped["ConstructionProject"] = relationship(
        "ConstructionProject",
        lazy="selectin"
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="project_roles",
        lazy="selectin"
    )

    # Unique constraint: one org can have one role per project
    __table_args__ = (
        Index("ix_project_contractors_unique", "project_id", "organization_id", "role", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ProjectContractor(project_id={self.project_id}, org_id={self.organization_id}, role='{self.role}')>"


class Person(Base):
    """
    Человек в организации.

    Может участвовать в совещаниях от имени организации.
    """
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # ГИП, директор, инженер
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="persons",
        lazy="selectin"
    )
    attendances: Mapped[List["MeetingAttendee"]] = relationship(
        "MeetingAttendee",
        back_populates="person",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Person(id={self.id}, name='{self.full_name}')>"


class MeetingAttendee(Base):
    """
    Участник конкретного совещания.

    Связывает отчёт (совещание) с человеком.
    """
    __tablename__ = "meeting_attendees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("construction_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    report: Mapped["ConstructionReportDB"] = relationship(
        "ConstructionReportDB",
        lazy="selectin"
    )
    person: Mapped["Person"] = relationship(
        "Person",
        back_populates="attendances",
        lazy="selectin"
    )

    # Unique constraint: person can attend meeting only once
    __table_args__ = (
        Index("ix_meeting_attendees_unique", "report_id", "person_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<MeetingAttendee(report_id={self.report_id}, person_id={self.person_id})>"
