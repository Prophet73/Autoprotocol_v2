"""
Construction project management service.

Provides business logic for:
- Project CRUD operations
- Project code validation
- Dashboard statistics
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, func, and_, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import ConstructionProject, ConstructionReportDB, ReportStatus
from backend.shared.models import User, project_managers
from .project_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectCodeValidation,
    ProjectSummary,
    ProjectDashboardResponse,
    CalendarEvent,
    CalendarResponse,
)


class ProjectService:
    """Service for construction project management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(
        self,
        data: ProjectCreate,
        tenant_id: Optional[int] = None,
    ) -> ConstructionProject:
        """
        Create a new project with specified or auto-generated code.

        Args:
            data: Project creation data (including optional project_code)
            tenant_id: Override tenant ID

        Returns:
            Created project

        Raises:
            ValueError: If provided project_code already exists
        """
        # Check if project_code is provided and unique
        if data.project_code:
            existing = await self.get_project_by_code(data.project_code)
            if existing:
                raise ValueError(f"Project code {data.project_code} already exists")

        project = ConstructionProject(
            name=data.name,
            description=data.description,
            tenant_id=tenant_id or data.tenant_id,
            manager_id=data.manager_id,
        )

        # Set project_code if provided (otherwise model default will generate it)
        if data.project_code:
            project.project_code = data.project_code

        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def get_project(self, project_id: int) -> Optional[ConstructionProject]:
        """Get project by ID."""
        result = await self.db.execute(
            select(ConstructionProject)
            .options(selectinload(ConstructionProject.manager))
            .where(ConstructionProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_project_by_code(self, code: str) -> Optional[ConstructionProject]:
        """Get project by 4-digit code."""
        result = await self.db.execute(
            select(ConstructionProject)
            .options(selectinload(ConstructionProject.manager))
            .where(ConstructionProject.project_code == code)
        )
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        tenant_id: Optional[int] = None,
        manager_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> ProjectListResponse:
        """
        List projects with filtering.

        Args:
            tenant_id: Filter by tenant
            manager_id: Filter by manager
            is_active: Filter by active status
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of projects with total count
        """
        query = select(ConstructionProject).options(
            selectinload(ConstructionProject.manager)
        )

        # Apply filters
        if tenant_id is not None:
            query = query.where(ConstructionProject.tenant_id == tenant_id)
        if manager_id is not None:
            query = query.where(ConstructionProject.manager_id == manager_id)
        if is_active is not None:
            query = query.where(ConstructionProject.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(
            ConstructionProject.created_at.desc()
        )
        result = await self.db.execute(query)
        projects = result.scalars().all()

        # Build response with report counts
        project_responses = []
        for project in projects:
            report_count = await self._get_report_count(project.id)
            project_responses.append(ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                project_code=project.project_code,
                tenant_id=project.tenant_id,
                manager_id=project.manager_id,
                manager_name=project.manager.full_name if project.manager else None,
                is_active=project.is_active,
                report_count=report_count,
                created_at=project.created_at,
                updated_at=project.updated_at,
            ))

        return ProjectListResponse(projects=project_responses, total=total)

    async def update_project(
        self,
        project_id: int,
        data: ProjectUpdate,
    ) -> Optional[ConstructionProject]:
        """
        Update a project.

        Args:
            project_id: Project ID
            data: Update data

        Returns:
            Updated project or None if not found

        Raises:
            ValueError: If project_code already exists
        """
        import logging
        logger = logging.getLogger(__name__)

        project = await self.get_project(project_id)
        if not project:
            return None

        logger.info(f"[update_project] Current project: id={project.id}, code={project.project_code}")
        logger.info(f"[update_project] Update data: name={data.name}, project_code={data.project_code}, description={data.description}, manager_id={data.manager_id}")

        if data.name is not None:
            project.name = data.name
        if data.project_code is not None and data.project_code != project.project_code:
            logger.info(f"[update_project] Updating project_code from {project.project_code} to {data.project_code}")
            # Check uniqueness
            existing = await self.get_project_by_code(data.project_code)
            if existing and existing.id != project_id:
                logger.warning(f"[update_project] Code {data.project_code} already exists for project {existing.id}")
                raise ValueError(f"Project code {data.project_code} already exists")
            project.project_code = data.project_code
            logger.info(f"[update_project] Project code updated successfully")
        if data.description is not None:
            project.description = data.description
        if data.manager_id is not None:
            project.manager_id = data.manager_id
        if data.is_active is not None:
            project.is_active = data.is_active

        await self.db.flush()
        await self.db.refresh(project)
        logger.info(f"[update_project] After flush - project code is now: {project.project_code}")
        return project

    async def archive_project(self, project_id: int) -> bool:
        """
        Archive a project (set is_active=False).

        Args:
            project_id: Project ID

        Returns:
            True if archived, False if not found
        """
        project = await self.get_project(project_id)
        if not project:
            return False

        project.is_active = False
        await self.db.flush()
        return True

    async def delete_project(self, project_id: int) -> bool:
        """
        Delete a project.

        Args:
            project_id: Project ID

        Returns:
            True if deleted, False if not found
        """
        project = await self.get_project(project_id)
        if not project:
            return False

        await self.db.delete(project)
        await self.db.flush()
        return True

    async def validate_code(self, code: str) -> ProjectCodeValidation:
        """
        Validate a project code for anonymous upload.

        Args:
            code: 4-digit project code

        Returns:
            Validation result with project info if valid
        """
        if len(code) != 4 or not code.isdigit():
            return ProjectCodeValidation(
                valid=False,
                message="Invalid code format. Must be 4 digits."
            )

        project = await self.get_project_by_code(code)
        if not project:
            return ProjectCodeValidation(
                valid=False,
                message="Project not found with this code."
            )

        if not project.is_active:
            return ProjectCodeValidation(
                valid=False,
                message="Project is archived and not accepting uploads."
            )

        return ProjectCodeValidation(
            valid=True,
            project_id=project.id,
            project_name=project.name,
            tenant_id=project.tenant_id,
            domain_type="construction",  # Domain type for routing
            message="Valid project code."
        )

    async def assign_manager(self, project_id: int, user_id: int) -> bool:
        """
        Assign a user as manager to a project.

        Args:
            project_id: Project ID
            user_id: User ID to assign

        Returns:
            True if assigned successfully
        """
        try:
            # Check user exists
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            if not user_result.scalar_one_or_none():
                return False

            # Check if already assigned
            existing = await self.db.execute(
                select(project_managers).where(
                    and_(
                        project_managers.c.project_id == project_id,
                        project_managers.c.user_id == user_id
                    )
                )
            )
            if existing.first():
                return False  # Already assigned

            # Insert assignment
            await self.db.execute(
                insert(project_managers).values(
                    project_id=project_id,
                    user_id=user_id
                )
            )
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False

    async def remove_manager(self, project_id: int, user_id: int) -> bool:
        """
        Remove a user from project managers.

        Args:
            project_id: Project ID
            user_id: User ID to remove

        Returns:
            True if removed successfully
        """
        try:
            result = await self.db.execute(
                delete(project_managers).where(
                    and_(
                        project_managers.c.project_id == project_id,
                        project_managers.c.user_id == user_id
                    )
                )
            )
            await self.db.commit()
            return result.rowcount > 0
        except Exception:
            await self.db.rollback()
            return False

    async def get_manager_projects(
        self,
        manager_id: int,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> ProjectListResponse:
        """
        Get projects where user is assigned as manager (via many-to-many).

        Args:
            manager_id: User ID of the manager
            is_active: Filter by active status
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of projects
        """
        # Build query joining with project_managers table
        query = (
            select(ConstructionProject)
            .options(selectinload(ConstructionProject.manager))
            .join(
                project_managers,
                ConstructionProject.id == project_managers.c.project_id
            )
            .where(project_managers.c.user_id == manager_id)
        )

        if is_active is not None:
            query = query.where(ConstructionProject.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(
            ConstructionProject.created_at.desc()
        )
        result = await self.db.execute(query)
        projects = result.scalars().all()

        # Build response with report counts
        project_responses = []
        for project in projects:
            report_count = await self._get_report_count(project.id)
            project_responses.append(ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                project_code=project.project_code,
                tenant_id=project.tenant_id,
                manager_id=project.manager_id,
                manager_name=project.manager.full_name if project.manager else None,
                is_active=project.is_active,
                report_count=report_count,
                created_at=project.created_at,
                updated_at=project.updated_at,
            ))

        return ProjectListResponse(projects=project_responses, total=total)

    async def get_dashboard_projects(
        self,
        manager_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
    ) -> ProjectDashboardResponse:
        """
        Get projects dashboard with statistics.

        Args:
            manager_id: Filter by manager
            tenant_id: Filter by tenant

        Returns:
            Dashboard with project summaries
        """
        query = select(ConstructionProject)

        if manager_id is not None:
            query = query.where(ConstructionProject.manager_id == manager_id)
        if tenant_id is not None:
            query = query.where(ConstructionProject.tenant_id == tenant_id)

        result = await self.db.execute(query)
        projects = result.scalars().all()

        summaries = []
        active_count = 0

        for project in projects:
            if project.is_active:
                active_count += 1

            # Get report statistics
            stats = await self._get_project_stats(project.id)
            summaries.append(ProjectSummary(
                id=project.id,
                name=project.name,
                project_code=project.project_code,
                is_active=project.is_active,
                **stats
            ))

        return ProjectDashboardResponse(
            projects=summaries,
            total_projects=len(projects),
            active_projects=active_count,
        )

    async def get_calendar_events(
        self,
        project_ids: Optional[List[int]] = None,
        manager_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CalendarResponse:
        """
        Get calendar events (reports) for specified projects.

        Args:
            project_ids: List of project IDs to filter
            manager_id: Filter by manager's projects
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Calendar events
        """
        query = select(ConstructionReportDB).options(
            selectinload(ConstructionReportDB.project)
        )

        # Filter by projects
        if project_ids:
            query = query.where(ConstructionReportDB.project_id.in_(project_ids))
        elif manager_id:
            # Get projects managed by user
            project_query = select(ConstructionProject.id).where(
                ConstructionProject.manager_id == manager_id
            )
            project_result = await self.db.execute(project_query)
            manager_project_ids = [p for p in project_result.scalars().all()]
            if manager_project_ids:
                query = query.where(
                    ConstructionReportDB.project_id.in_(manager_project_ids)
                )
            else:
                return CalendarResponse(events=[], total=0)

        # Filter by date range
        if start_date:
            query = query.where(ConstructionReportDB.created_at >= start_date)
        if end_date:
            query = query.where(ConstructionReportDB.created_at <= end_date)

        query = query.order_by(ConstructionReportDB.created_at.desc())

        result = await self.db.execute(query)
        reports = result.scalars().all()

        events = []
        for report in reports:
            events.append(CalendarEvent(
                id=report.id,
                title=report.title or f"Report {report.job_id[:8]}",
                project_id=report.project_id or 0,
                project_name=report.project.name if report.project else "Unassigned",
                meeting_date=report.meeting_date,
                status=report.status,
                created_at=report.created_at,
            ))

        return CalendarResponse(events=events, total=len(events))

    async def _get_report_count(self, project_id: int) -> int:
        """Get total report count for project."""
        result = await self.db.execute(
            select(func.count(ConstructionReportDB.id))
            .where(ConstructionReportDB.project_id == project_id)
        )
        return result.scalar() or 0

    async def _get_project_stats(self, project_id: int) -> dict:
        """Get statistics for a project."""
        # Total reports
        total_result = await self.db.execute(
            select(func.count(ConstructionReportDB.id))
            .where(ConstructionReportDB.project_id == project_id)
        )
        total = total_result.scalar() or 0

        # By status
        completed_result = await self.db.execute(
            select(func.count(ConstructionReportDB.id))
            .where(and_(
                ConstructionReportDB.project_id == project_id,
                ConstructionReportDB.status == ReportStatus.COMPLETED
            ))
        )
        completed = completed_result.scalar() or 0

        pending_result = await self.db.execute(
            select(func.count(ConstructionReportDB.id))
            .where(and_(
                ConstructionReportDB.project_id == project_id,
                ConstructionReportDB.status.in_([
                    ReportStatus.PENDING,
                    ReportStatus.PROCESSING
                ])
            ))
        )
        pending = pending_result.scalar() or 0

        failed_result = await self.db.execute(
            select(func.count(ConstructionReportDB.id))
            .where(and_(
                ConstructionReportDB.project_id == project_id,
                ConstructionReportDB.status == ReportStatus.FAILED
            ))
        )
        failed = failed_result.scalar() or 0

        # Last report date
        last_report_result = await self.db.execute(
            select(ConstructionReportDB.created_at)
            .where(ConstructionReportDB.project_id == project_id)
            .order_by(ConstructionReportDB.created_at.desc())
            .limit(1)
        )
        last_report = last_report_result.scalar_one_or_none()

        return {
            "total_reports": total,
            "completed_reports": completed,
            "pending_reports": pending,
            "failed_reports": failed,
            "open_risks": 0,  # TODO: Implement risk counting from result_json
            "last_report_date": last_report,
        }
