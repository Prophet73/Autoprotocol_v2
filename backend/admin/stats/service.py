"""
Comprehensive statistics service.

Provides aggregated statistics for:
- Global overview (all domains)
- Domain-specific stats
- User activity
- Cost analytics
- Timeline data
"""
import os
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, case, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import User, TranscriptionJob
from backend.domains.base_schemas import DOMAIN_MEETING_TYPES, get_meeting_types
from backend.core.storage.job_store import get_job_store
from backend.core.transcription.models import JobStatus
from .schemas import (
    # New comprehensive schemas
    GeminiPricing,
    StatsFilters,
    KPIStats,
    MeetingTypeStats,
    DomainStats,
    DomainsBreakdown,
    ProjectStats,
    ProjectsBreakdown,
    UsersStats,
    UserActivityStats,
    CostStats,
    TimelinePoint,
    TimelineStats,
    ErrorStats,
    ArtifactsStats,
    OverviewStatsResponse,
    DomainStatsResponse,
    UsersStatsResponse,
    CostStatsResponse,
    FullDashboardResponse,
    # Legacy schemas
    GlobalStatsResponse,
    UserStatsLegacy as UserStats,
    TranscriptionStats,
    StorageStats,
    DomainStatsLegacy,
    SystemHealthResponse,
)

logger = logging.getLogger(__name__)

# Data directories
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"

# Domain display names
DOMAIN_DISPLAY_NAMES = {
    "construction": "Строительство",
    "hr": "HR",
    "it": "IT",
    "general": "Общий",
}


class StatsService:
    """Comprehensive statistics service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # New Comprehensive Stats Methods
    # =========================================================================

    async def get_dashboard_stats(
        self,
        filters: Optional[StatsFilters] = None
    ) -> FullDashboardResponse:
        """Get complete dashboard statistics."""
        filters = filters or StatsFilters()

        return FullDashboardResponse(
            overview=await self.get_kpi_stats(filters),
            domains=await self.get_domains_breakdown(filters),
            users=await self.get_users_stats(filters),
            costs=await self.get_cost_stats(filters),
            timeline=await self.get_timeline_stats(filters),
            artifacts=await self.get_artifacts_stats(filters),
            errors=await self.get_error_stats(filters),
            filters_applied=filters,
            generated_at=datetime.now(),
        )

    async def get_overview_stats(
        self,
        filters: Optional[StatsFilters] = None
    ) -> OverviewStatsResponse:
        """Get overview statistics."""
        filters = filters or StatsFilters()

        return OverviewStatsResponse(
            kpi=await self.get_kpi_stats(filters),
            domains=await self.get_domains_breakdown(filters),
            timeline=await self.get_timeline_stats(filters),
            artifacts=await self.get_artifacts_stats(filters),
            filters_applied=filters,
            generated_at=datetime.now(),
        )

    async def get_kpi_stats(self, filters: StatsFilters) -> KPIStats:
        """Get key performance indicators."""
        query = self._build_base_query(filters)

        # Aggregate stats
        result = await self.db.execute(
            select(
                func.count(TranscriptionJob.id).label("total"),
                func.sum(case((TranscriptionJob.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((TranscriptionJob.status == "failed", 1), else_=0)).label("failed"),
                func.sum(case((TranscriptionJob.status == "pending", 1), else_=0)).label("pending"),
                func.sum(case((TranscriptionJob.status == "processing", 1), else_=0)).label("processing"),
                func.sum(TranscriptionJob.processing_time_seconds).label("total_processing"),
                func.sum(TranscriptionJob.audio_duration_seconds).label("total_audio"),
                func.sum(TranscriptionJob.input_tokens).label("total_input_tokens"),
                func.sum(TranscriptionJob.output_tokens).label("total_output_tokens"),
            ).where(query)
        )
        row = result.fetchone()

        if not row or row.total == 0:
            return KPIStats()

        total = row.total or 0
        completed = row.completed or 0
        failed = row.failed or 0
        pending = row.pending or 0
        processing = row.processing or 0
        total_processing = row.total_processing or 0
        total_audio = row.total_audio or 0
        total_input = row.total_input_tokens or 0
        total_output = row.total_output_tokens or 0

        total_cost = GeminiPricing.calculate_cost(total_input, total_output)
        success_rate = (completed / total * 100) if total > 0 else 0
        avg_processing = (total_processing / completed / 60) if completed > 0 else 0
        avg_cost = (total_cost / completed) if completed > 0 else 0

        return KPIStats(
            total_jobs=total,
            completed_jobs=completed,
            failed_jobs=failed,
            pending_jobs=pending,
            processing_jobs=processing,
            success_rate=round(success_rate, 1),
            total_processing_hours=round(total_processing / 3600, 2),
            avg_processing_minutes=round(avg_processing, 2),
            total_audio_hours=round(total_audio / 3600, 2),
            total_cost_usd=round(total_cost, 4),
            avg_cost_per_job=round(avg_cost, 4),
        )

    async def get_domains_breakdown(self, filters: StatsFilters) -> DomainsBreakdown:
        """Get statistics breakdown by domains."""
        domains_list = []

        for domain_id in DOMAIN_MEETING_TYPES.keys():
            # Skip if filter is set to different domain
            if filters.domain and filters.domain != domain_id:
                continue

            domain_filters = StatsFilters(
                date_from=filters.date_from,
                date_to=filters.date_to,
                domain=domain_id,
                user_id=filters.user_id,
            )

            domain_stats = await self._get_single_domain_stats(domain_id, domain_filters)
            domains_list.append(domain_stats)

        return DomainsBreakdown(domains=domains_list)

    async def _get_single_domain_stats(
        self,
        domain_id: str,
        filters: StatsFilters
    ) -> DomainStats:
        """Get stats for a single domain."""
        query = self._build_base_query(filters)

        # Aggregate for domain
        result = await self.db.execute(
            select(
                func.count(TranscriptionJob.id).label("total"),
                func.sum(case((TranscriptionJob.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((TranscriptionJob.status == "failed", 1), else_=0)).label("failed"),
                func.sum(TranscriptionJob.processing_time_seconds).label("total_processing"),
                func.sum(TranscriptionJob.audio_duration_seconds).label("total_audio"),
                func.sum(TranscriptionJob.input_tokens).label("total_input"),
                func.sum(TranscriptionJob.output_tokens).label("total_output"),
            ).where(query)
        )
        row = result.fetchone()

        total = row.total or 0 if row else 0
        completed = row.completed or 0 if row else 0
        failed = row.failed or 0 if row else 0
        total_processing = row.total_processing or 0 if row else 0
        total_audio = row.total_audio or 0 if row else 0
        total_input = row.total_input or 0 if row else 0
        total_output = row.total_output or 0 if row else 0

        success_rate = (completed / total * 100) if total > 0 else 0
        total_cost = GeminiPricing.calculate_cost(total_input, total_output)

        # Get meeting type breakdown
        meeting_types_stats = await self._get_meeting_types_stats(domain_id, filters)

        return DomainStats(
            domain=domain_id,
            display_name=DOMAIN_DISPLAY_NAMES.get(domain_id, domain_id),
            total_jobs=total,
            completed_jobs=completed,
            failed_jobs=failed,
            success_rate=round(success_rate, 1),
            total_processing_hours=round(total_processing / 3600, 2),
            total_audio_hours=round(total_audio / 3600, 2),
            total_cost_usd=round(total_cost, 4),
            meeting_types=meeting_types_stats,
        )

    async def _get_meeting_types_stats(
        self,
        domain_id: str,
        filters: StatsFilters
    ) -> List[MeetingTypeStats]:
        """Get meeting type stats for a domain."""
        meeting_types = get_meeting_types(domain_id)
        if not meeting_types:
            return []

        stats_list = []
        base_query = self._build_base_query(filters)

        # Query for each meeting type
        for mt in meeting_types:
            result = await self.db.execute(
                select(
                    func.count(TranscriptionJob.id).label("count"),
                    func.sum(case((TranscriptionJob.status == "completed", 1), else_=0)).label("completed"),
                    func.sum(case((TranscriptionJob.status == "failed", 1), else_=0)).label("failed"),
                    func.sum(TranscriptionJob.processing_time_seconds).label("processing"),
                    func.sum(TranscriptionJob.audio_duration_seconds).label("audio"),
                ).where(
                    and_(base_query, TranscriptionJob.meeting_type == mt.id)
                )
            )
            row = result.fetchone()

            count = row.count or 0 if row else 0
            completed = row.completed or 0 if row else 0
            failed = row.failed or 0 if row else 0
            processing = row.processing or 0 if row else 0
            audio = row.audio or 0 if row else 0

            success_rate = (completed / count * 100) if count > 0 else 0

            stats_list.append(MeetingTypeStats(
                meeting_type=mt.id,
                name=mt.name,
                count=count,
                completed=completed,
                failed=failed,
                success_rate=round(success_rate, 1),
                total_processing_seconds=processing,
                total_audio_seconds=audio,
            ))

        return stats_list

    async def get_domain_stats(
        self,
        domain_id: str,
        filters: Optional[StatsFilters] = None
    ) -> DomainStatsResponse:
        """Get detailed stats for a specific domain."""
        filters = filters or StatsFilters()
        filters.domain = domain_id

        domain_stats = await self._get_single_domain_stats(domain_id, filters)

        # Get projects breakdown for construction domain
        projects = None
        if domain_id == "construction":
            projects = await self._get_projects_breakdown(filters)

        return DomainStatsResponse(
            domain=domain_stats,
            projects=projects,
            timeline=await self.get_timeline_stats(filters),
            errors=await self.get_error_stats(filters),
            filters_applied=filters,
            generated_at=datetime.now(),
        )

    async def _get_projects_breakdown(self, filters: StatsFilters) -> ProjectsBreakdown:
        """Get project stats for construction domain."""
        from backend.domains.construction.models import ConstructionProject

        # Get all projects with stats
        result = await self.db.execute(
            select(
                ConstructionProject.id,
                ConstructionProject.name,
                ConstructionProject.project_code,
                func.count(TranscriptionJob.id).label("total"),
                func.sum(case((TranscriptionJob.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((TranscriptionJob.status == "failed", 1), else_=0)).label("failed"),
                func.sum(TranscriptionJob.processing_time_seconds).label("processing"),
                func.sum(TranscriptionJob.audio_duration_seconds).label("audio"),
                func.max(TranscriptionJob.created_at).label("last_activity"),
            )
            .outerjoin(TranscriptionJob, TranscriptionJob.project_id == ConstructionProject.id)
            .where(ConstructionProject.is_active == True)
            .group_by(ConstructionProject.id)
            .order_by(func.count(TranscriptionJob.id).desc())
        )
        rows = result.fetchall()

        projects = []
        for row in rows:
            total = row.total or 0
            completed = row.completed or 0
            success_rate = (completed / total * 100) if total > 0 else 0

            projects.append(ProjectStats(
                project_id=row.id,
                project_name=row.name,
                project_code=row.project_code,
                total_jobs=total,
                completed_jobs=completed,
                failed_jobs=row.failed or 0,
                success_rate=round(success_rate, 1),
                total_processing_hours=round((row.processing or 0) / 3600, 2),
                total_audio_hours=round((row.audio or 0) / 3600, 2),
                last_activity=row.last_activity,
            ))

        return ProjectsBreakdown(
            projects=projects,
            total_projects=len(projects),
        )

    async def get_users_stats(
        self,
        filters: Optional[StatsFilters] = None
    ) -> UsersStats:
        """Get user statistics."""
        filters = filters or StatsFilters()

        # Total users
        total_result = await self.db.execute(select(func.count(User.id)))
        total_users = total_result.scalar() or 0

        # Users by role
        role_result = await self.db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        by_role = {role: count for role, count in role_result.all()}

        # Users by domain (from domain_assignments)
        from backend.shared.models import UserDomainAssignment
        domain_result = await self.db.execute(
            select(
                UserDomainAssignment.domain,
                func.count(distinct(UserDomainAssignment.user_id))
            ).group_by(UserDomainAssignment.domain)
        )
        by_domain = {domain: count for domain, count in domain_result.all()}

        # Active users (with jobs)
        active_result = await self.db.execute(
            select(func.count(distinct(TranscriptionJob.user_id)))
            .where(TranscriptionJob.user_id.isnot(None))
        )
        active_users = active_result.scalar() or 0

        # Top users by job count
        top_result = await self.db.execute(
            select(
                User.id,
                User.email,
                User.full_name,
                User.role,
                func.count(TranscriptionJob.id).label("total_jobs"),
                func.sum(case((TranscriptionJob.status == "completed", 1), else_=0)).label("completed"),
                func.max(TranscriptionJob.created_at).label("last_activity"),
            )
            .join(TranscriptionJob, TranscriptionJob.user_id == User.id)
            .group_by(User.id)
            .order_by(func.count(TranscriptionJob.id).desc())
            .limit(10)
        )

        top_users = []
        for row in top_result.fetchall():
            # Get domains used by this user
            domains_result = await self.db.execute(
                select(distinct(TranscriptionJob.domain))
                .where(TranscriptionJob.user_id == row.id)
            )
            domains_used = [d[0] for d in domains_result.fetchall() if d[0]]

            top_users.append(UserActivityStats(
                user_id=row.id,
                email=row.email,
                full_name=row.full_name,
                role=row.role,
                total_jobs=row.total_jobs or 0,
                completed_jobs=row.completed or 0,
                domains_used=domains_used,
                last_activity=row.last_activity,
            ))

        return UsersStats(
            total_users=total_users,
            active_users=active_users,
            by_role=by_role,
            by_domain=by_domain,
            top_users=top_users,
        )

    async def get_cost_stats(
        self,
        filters: Optional[StatsFilters] = None
    ) -> CostStats:
        """Get AI cost statistics."""
        filters = filters or StatsFilters()
        query = self._build_base_query(filters)

        # Total tokens
        result = await self.db.execute(
            select(
                func.sum(TranscriptionJob.input_tokens).label("input"),
                func.sum(TranscriptionJob.output_tokens).label("output"),
                func.count(TranscriptionJob.id).label("count"),
            ).where(and_(query, TranscriptionJob.status == "completed"))
        )
        row = result.fetchone()

        total_input = row.input or 0 if row else 0
        total_output = row.output or 0 if row else 0
        count = row.count or 0 if row else 0

        total_cost = GeminiPricing.calculate_cost(total_input, total_output)
        avg_cost = total_cost / count if count > 0 else 0

        # Cost by domain
        domain_result = await self.db.execute(
            select(
                TranscriptionJob.domain,
                func.sum(TranscriptionJob.input_tokens).label("input"),
                func.sum(TranscriptionJob.output_tokens).label("output"),
            )
            .where(and_(query, TranscriptionJob.status == "completed"))
            .group_by(TranscriptionJob.domain)
        )

        by_domain = {}
        for row in domain_result.fetchall():
            if row.domain:
                cost = GeminiPricing.calculate_cost(row.input or 0, row.output or 0)
                by_domain[row.domain] = round(cost, 4)

        return CostStats(
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cost_usd=round(total_cost, 4),
            avg_cost_per_job=round(avg_cost, 4),
            by_domain=by_domain,
        )

    async def get_timeline_stats(
        self,
        filters: Optional[StatsFilters] = None,
        days: int = 30
    ) -> TimelineStats:
        """Get timeline statistics."""
        filters = filters or StatsFilters()

        # Default to last 30 days if no date range
        end_date = filters.date_to or date.today()
        start_date = filters.date_from or (end_date - timedelta(days=days))

        query = self._build_base_query(StatsFilters(
            date_from=start_date,
            date_to=end_date,
            domain=filters.domain,
            meeting_type=filters.meeting_type,
        ))

        # Group by date
        result = await self.db.execute(
            select(
                func.date(TranscriptionJob.created_at).label("date"),
                func.count(TranscriptionJob.id).label("jobs"),
                func.sum(case((TranscriptionJob.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((TranscriptionJob.status == "failed", 1), else_=0)).label("failed"),
            )
            .where(query)
            .group_by(func.date(TranscriptionJob.created_at))
            .order_by(func.date(TranscriptionJob.created_at))
        )

        points = []
        for row in result.fetchall():
            points.append(TimelinePoint(
                date=str(row.date),
                jobs=row.jobs or 0,
                completed=row.completed or 0,
                failed=row.failed or 0,
            ))

        return TimelineStats(
            points=points,
            period="daily",
            total_days=(end_date - start_date).days,
        )

    async def get_error_stats(
        self,
        filters: Optional[StatsFilters] = None
    ) -> ErrorStats:
        """Get error statistics."""
        filters = filters or StatsFilters()
        query = self._build_base_query(filters)

        # Total errors
        total_result = await self.db.execute(
            select(func.count(TranscriptionJob.id))
            .where(and_(query, TranscriptionJob.status == "failed"))
        )
        total_errors = total_result.scalar() or 0

        # Total jobs for error rate
        total_jobs_result = await self.db.execute(
            select(func.count(TranscriptionJob.id)).where(query)
        )
        total_jobs = total_jobs_result.scalar() or 0
        error_rate = (total_errors / total_jobs * 100) if total_jobs > 0 else 0

        # Errors by stage
        stage_result = await self.db.execute(
            select(
                TranscriptionJob.error_stage,
                func.count(TranscriptionJob.id)
            )
            .where(and_(query, TranscriptionJob.status == "failed"))
            .group_by(TranscriptionJob.error_stage)
        )
        by_stage = {stage or "unknown": count for stage, count in stage_result.all()}

        # Errors by domain
        domain_result = await self.db.execute(
            select(
                TranscriptionJob.domain,
                func.count(TranscriptionJob.id)
            )
            .where(and_(query, TranscriptionJob.status == "failed"))
            .group_by(TranscriptionJob.domain)
        )
        by_domain = {domain or "unknown": count for domain, count in domain_result.all()}

        # Recent errors
        recent_result = await self.db.execute(
            select(
                TranscriptionJob.job_id,
                TranscriptionJob.domain,
                TranscriptionJob.source_filename,
                TranscriptionJob.error_stage,
                TranscriptionJob.error_message,
                TranscriptionJob.created_at,
            )
            .where(and_(query, TranscriptionJob.status == "failed"))
            .order_by(TranscriptionJob.created_at.desc())
            .limit(15)
        )

        recent_errors = []
        for row in recent_result.fetchall():
            recent_errors.append({
                "job_id": row.job_id,
                "domain": row.domain,
                "filename": row.source_filename,
                "stage": row.error_stage,
                "message": row.error_message[:200] if row.error_message else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        return ErrorStats(
            total_errors=total_errors,
            error_rate=round(error_rate, 1),
            by_stage=by_stage,
            by_domain=by_domain,
            recent_errors=recent_errors,
        )

    async def get_artifacts_stats(
        self,
        filters: Optional[StatsFilters] = None
    ) -> ArtifactsStats:
        """Get artifacts generation statistics."""
        filters = filters or StatsFilters()
        query = self._build_base_query(filters)

        # Get completed jobs with artifacts
        result = await self.db.execute(
            select(TranscriptionJob.artifacts)
            .where(and_(query, TranscriptionJob.status == "completed"))
        )

        total = 0
        transcripts = 0
        tasks = 0
        reports = 0
        analysis = 0

        for row in result.fetchall():
            total += 1
            artifacts = row.artifacts or {}
            if artifacts.get("transcript"):
                transcripts += 1
            if artifacts.get("tasks"):
                tasks += 1
            if artifacts.get("report"):
                reports += 1
            if artifacts.get("analysis"):
                analysis += 1

        return ArtifactsStats(
            transcripts_generated=transcripts,
            tasks_generated=tasks,
            reports_generated=reports,
            analysis_generated=analysis,
            transcript_rate=round(transcripts / total * 100, 1) if total > 0 else 0,
            tasks_rate=round(tasks / total * 100, 1) if total > 0 else 0,
            report_rate=round(reports / total * 100, 1) if total > 0 else 0,
            analysis_rate=round(analysis / total * 100, 1) if total > 0 else 0,
        )

    def _build_base_query(self, filters: StatsFilters):
        """Build base SQLAlchemy query with filters."""
        conditions = []

        if filters.date_from:
            conditions.append(TranscriptionJob.created_at >= datetime.combine(filters.date_from, datetime.min.time()))
        if filters.date_to:
            conditions.append(TranscriptionJob.created_at <= datetime.combine(filters.date_to, datetime.max.time()))
        if filters.domain:
            conditions.append(TranscriptionJob.domain == filters.domain)
        if filters.meeting_type:
            conditions.append(TranscriptionJob.meeting_type == filters.meeting_type)
        if filters.project_id:
            conditions.append(TranscriptionJob.project_id == filters.project_id)
        if filters.user_id:
            conditions.append(TranscriptionJob.user_id == filters.user_id)
        if filters.status:
            conditions.append(TranscriptionJob.status == filters.status)

        if conditions:
            return and_(*conditions)
        return True  # No filters

    # =========================================================================
    # Legacy Methods (for backwards compatibility)
    # =========================================================================

    async def get_user_stats(self) -> UserStats:
        """Get user statistics (legacy)."""
        total_result = await self.db.execute(select(func.count(User.id)))
        total = total_result.scalar() or 0

        active_result = await self.db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active = active_result.scalar() or 0

        super_result = await self.db.execute(
            select(func.count(User.id)).where(User.is_superuser == True)
        )
        superusers = super_result.scalar() or 0

        role_result = await self.db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        by_role = {role: count for role, count in role_result.all()}

        domain_result = await self.db.execute(
            select(User.domain, func.count(User.id))
            .where(User.domain.isnot(None))
            .group_by(User.domain)
        )
        by_domain = {domain: count for domain, count in domain_result.all()}

        return UserStats(
            total_users=total,
            active_users=active,
            superusers=superusers,
            by_role=by_role,
            by_domain=by_domain,
        )

    def get_transcription_stats(self) -> TranscriptionStats:
        """Get transcription job statistics from Redis (legacy)."""
        try:
            job_store = get_job_store()
            jobs = job_store.list_jobs(limit=10000)

            stats = TranscriptionStats()
            for job in jobs:
                stats.total += 1
                if job.status == JobStatus.PENDING:
                    stats.pending += 1
                elif job.status == JobStatus.PROCESSING:
                    stats.processing += 1
                elif job.status == JobStatus.COMPLETED:
                    stats.completed += 1
                elif job.status == JobStatus.FAILED:
                    stats.failed += 1

            return stats
        except Exception as e:
            logger.error(f"Failed to get transcription stats: {e}")
            return TranscriptionStats()

    def get_storage_stats(self) -> StorageStats:
        """Calculate storage usage (legacy)."""
        try:
            uploads_bytes = self._get_directory_size(UPLOAD_DIR)
            outputs_bytes = self._get_directory_size(OUTPUT_DIR)
            total_bytes = uploads_bytes + outputs_bytes

            return StorageStats(
                total_bytes=total_bytes,
                total_mb=round(total_bytes / (1024 * 1024), 2),
                total_gb=round(total_bytes / (1024 * 1024 * 1024), 3),
                uploads_bytes=uploads_bytes,
                outputs_bytes=outputs_bytes,
            )
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return StorageStats()

    def _get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory recursively."""
        if not path.exists():
            return 0

        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception as e:
            logger.warning(f"Error calculating size for {path}: {e}")

        return total

    def get_domain_stats(self) -> DomainStatsLegacy:
        """Get transcription count by domain (legacy)."""
        return DomainStatsLegacy()

    async def get_global_stats(self) -> GlobalStatsResponse:
        """Get all global statistics (legacy)."""
        user_stats = await self.get_user_stats()
        transcription_stats = self.get_transcription_stats()
        storage_stats = self.get_storage_stats()
        domain_stats = self.get_domain_stats()

        try:
            job_store = get_job_store()
            redis_connected = job_store.health_check()
        except Exception as e:
            logger.debug(f"Redis health check failed: {e}")
            redis_connected = False

        gpu_available = self._check_gpu()

        return GlobalStatsResponse(
            users=user_stats,
            transcriptions=transcription_stats,
            storage=storage_stats,
            domains=domain_stats,
            redis_connected=redis_connected,
            gpu_available=gpu_available,
            generated_at=datetime.now(),
        )

    def _check_gpu(self) -> bool:
        """Check if GPU is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    async def get_system_health(self) -> SystemHealthResponse:
        """Get system health status."""
        import psutil

        try:
            job_store = get_job_store()
            redis_ok = job_store.health_check()
        except Exception as e:
            logger.debug(f"Redis health check failed: {e}")
            redis_ok = False

        try:
            await self.db.execute(select(1))
            db_ok = True
        except Exception as e:
            logger.debug(f"Database health check failed: {e}")
            db_ok = False

        gpu_ok = self._check_gpu()
        celery_ok = self._check_celery()

        disk = psutil.disk_usage("/")
        memory = psutil.virtual_memory()

        all_ok = redis_ok and db_ok
        status = "healthy" if all_ok else "degraded"

        return SystemHealthResponse(
            status=status,
            redis=redis_ok,
            database=db_ok,
            gpu=gpu_ok,
            celery=celery_ok,
            disk_usage_percent=disk.percent,
            memory_usage_percent=memory.percent,
        )

    def _check_celery(self) -> bool:
        """Check if Celery is reachable."""
        try:
            from backend.tasks.celery_app import celery_app
            celery_app.control.ping(timeout=1.0)
            return True
        except Exception as e:
            logger.debug(f"Celery health check failed: {e}")
            return False
