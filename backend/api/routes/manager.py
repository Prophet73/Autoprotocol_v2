"""
Manager Dashboard API Routes.

Provides endpoints for:
- Dashboard view with KPIs, calendar, attention items, activity feed
- Analytics detail view
- Problem status management
- Report downloads
"""
import os
from datetime import datetime, timedelta
from typing import Annotated, Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, and_, or_, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from backend.shared.database import get_db
from backend.core.utils.file_security import validate_file_path

# Base data directory for file validation
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
from backend.shared.models import User
from backend.core.auth.dependencies import CurrentUser
# Import directly from models to avoid heavy dependencies chain
from backend.domains.construction.models import (
    ConstructionProject,
    ConstructionReportDB,
    ReportAnalytics,
    ReportProblem,
)


router = APIRouter(prefix="/manager", tags=["Manager Dashboard"])


# =============================================================================
# Schemas
# =============================================================================

class KPIResponse(BaseModel):
    """Key Performance Indicators."""
    total_jobs: int = 0
    attention_jobs: int = 0
    critical_jobs: int = 0


class CalendarEventResponse(BaseModel):
    """Calendar event for display."""
    id: int
    title: str
    date: str  # ISO date string
    status: str  # critical, attention, stable
    project_id: int
    project_code: str
    project_name: str


class AttentionItemResponse(BaseModel):
    """Attention item (problem) for display."""
    id: int
    analytics_id: int
    problem_text: str
    status: str  # new, done
    severity: str  # critical, attention
    source_file: str
    project_name: str
    created_at: datetime


class ActivityFeedItemResponse(BaseModel):
    """Activity feed item."""
    id: int
    title: str
    project_name: str
    status: str  # critical, attention, stable
    created_at: datetime


class ProjectHealthResponse(BaseModel):
    """Project health summary."""
    id: int
    name: str
    project_code: str
    health: str  # critical, attention, stable
    total_reports: int = 0
    open_issues: int = 0


class PulseChartResponse(BaseModel):
    """Pulse chart data for stacked bar chart."""
    labels: List[str] = []
    critical: List[int] = []
    attention: List[int] = []
    stable: List[int] = []


class DashboardViewResponse(BaseModel):
    """Complete dashboard view response."""
    kpi: KPIResponse
    calendar_events: List[CalendarEventResponse] = []
    attention_items: List[AttentionItemResponse] = []
    activity_feed: List[ActivityFeedItemResponse] = []
    projects_health: List[ProjectHealthResponse] = []
    pulse_chart: PulseChartResponse


class KeyIndicator(BaseModel):
    """Dynamic indicator for analytics detail (Autoprotocol format)."""
    indicator_name: str
    status: str  # "Критический", "Есть риски", "В норме"
    comment: str


class Challenge(BaseModel):
    """Challenge/problem with recommendation."""
    text: str
    recommendation: str


class ReportFiles(BaseModel):
    """Report file paths."""
    main: Optional[str] = None
    detailed: Optional[str] = None
    transcript: Optional[str] = None
    tasks: Optional[str] = None


class AnalyticsDetailResponse(BaseModel):
    """Analytics detail response."""
    id: int
    summary: str = ""
    status: str = "stable"  # critical, attention, stable
    key_indicators: List[KeyIndicator] = []
    challenges: List[Challenge] = []
    achievements: List[str] = []
    toxicity_level: float = 0.0
    toxicity_details: str = ""
    report_files: ReportFiles
    # Flags for download buttons (Autoprotocol format)
    has_main_report: bool = False
    has_detailed_report: bool = False
    has_transcript: bool = False
    has_tasks: bool = False
    filename: str = ""  # Original filename for display


class ProblemStatusUpdate(BaseModel):
    """Request to update problem status."""
    problem_id: int
    status: str = Field(..., pattern="^(new|done)$")


# =============================================================================
# Helper Functions
# =============================================================================

async def get_user_project_ids(db: AsyncSession, user: User) -> List[int]:
    """Get project IDs accessible by user."""
    if user.is_superuser:
        # Superuser sees all projects
        result = await db.execute(
            select(ConstructionProject.id)
        )
    else:
        # Manager sees their assigned projects
        result = await db.execute(
            select(ConstructionProject.id)
            .where(
                or_(
                    ConstructionProject.manager_id == user.id,
                    ConstructionProject.tenant_id == user.tenant_id
                )
            )
        )
    return [row[0] for row in result.fetchall()]


# =============================================================================
# Dashboard View Endpoint
# =============================================================================

@router.get(
    "/dashboard-view",
    response_model=DashboardViewResponse,
    summary="Get dashboard view",
    description="Returns complete dashboard data including KPIs, calendar, attention items, activity feed, and project health."
)
async def get_dashboard_view(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
) -> DashboardViewResponse:
    """Get complete dashboard view data."""

    # Get accessible project IDs
    project_ids = await get_user_project_ids(db, current_user)
    if not project_ids:
        return DashboardViewResponse(
            kpi=KPIResponse(),
            pulse_chart=PulseChartResponse()
        )

    # Filter by specific project if requested
    if project_id and project_id in project_ids:
        project_ids = [project_id]
    elif project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )

    # Parse date filters
    date_from = None
    date_to = None
    if start_date:
        try:
            date_from = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    if end_date:
        try:
            date_to = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            pass

    # Build base query for reports
    base_filter = [ConstructionReportDB.project_id.in_(project_ids)]
    if date_from:
        base_filter.append(ConstructionReportDB.created_at >= date_from)
    if date_to:
        base_filter.append(ConstructionReportDB.created_at <= date_to)

    # Get reports with analytics
    reports_query = (
        select(ConstructionReportDB)
        .options(selectinload(ConstructionReportDB.project))
        .where(and_(*base_filter))
        .order_by(desc(ConstructionReportDB.created_at))
    )
    reports_result = await db.execute(reports_query)
    reports = reports_result.scalars().all()

    # Calculate KPIs
    total_jobs = len(reports)
    attention_jobs = 0
    critical_jobs = 0

    # Get analytics for reports
    analytics_query = (
        select(ReportAnalytics)
        .where(ReportAnalytics.report_id.in_([r.id for r in reports]))
    )
    analytics_result = await db.execute(analytics_query)
    analytics_map = {a.report_id: a for a in analytics_result.scalars().all()}

    for report in reports:
        analytics = analytics_map.get(report.id)
        if analytics:
            if analytics.health_status == 'critical':
                critical_jobs += 1
            elif analytics.health_status == 'attention':
                attention_jobs += 1
        elif report.status == 'failed':
            critical_jobs += 1
        elif report.status in ('pending', 'processing'):
            attention_jobs += 1

    kpi = KPIResponse(
        total_jobs=total_jobs,
        attention_jobs=attention_jobs,
        critical_jobs=critical_jobs
    )

    # Calendar events
    calendar_events = []
    for report in reports[:50]:  # Limit to 50
        analytics = analytics_map.get(report.id)
        health = analytics.health_status if analytics else 'stable'
        if report.status == 'failed':
            health = 'critical'

        event_date = report.meeting_date or report.created_at
        calendar_events.append(CalendarEventResponse(
            id=report.id,
            title=report.title or f"Отчёт {report.job_id[:8]}",
            date=event_date.date().isoformat() if event_date else datetime.now().date().isoformat(),
            status=health,
            project_id=report.project_id or 0,
            project_code=report.project.project_code if report.project else "",
            project_name=report.project.name if report.project else "Без проекта"
        ))

    # Attention items (problems)
    problems_query = (
        select(ReportProblem)
        .join(ReportAnalytics)
        .join(ConstructionReportDB)
        .where(
            and_(
                ConstructionReportDB.project_id.in_(project_ids),
                ReportProblem.status == 'new'
            )
        )
        .order_by(
            case((ReportProblem.severity == 'critical', 0), else_=1),
            desc(ReportProblem.created_at)
        )
        .limit(20)
    )
    problems_result = await db.execute(problems_query)
    problems = problems_result.scalars().all()

    attention_items = []
    for problem in problems:
        analytics = problem.analytics
        report = analytics.report if analytics else None
        project_name = report.project.name if report and report.project else "Без проекта"
        source_file = report.title or report.audio_file_path or "Неизвестный файл" if report else "Неизвестный файл"

        attention_items.append(AttentionItemResponse(
            id=problem.id,
            analytics_id=problem.analytics_id,
            problem_text=problem.problem_text,
            status=problem.status,
            severity=problem.severity,
            source_file=source_file,
            project_name=project_name,
            created_at=problem.created_at
        ))

    # Activity feed (recent reports)
    activity_feed = []
    for report in reports[:10]:
        analytics = analytics_map.get(report.id)
        health = analytics.health_status if analytics else 'stable'
        if report.status == 'failed':
            health = 'critical'

        activity_feed.append(ActivityFeedItemResponse(
            id=report.id,
            title=report.title or f"Отчёт {report.job_id[:8]}",
            project_name=report.project.name if report.project else "Без проекта",
            status=health,
            created_at=report.created_at
        ))

    # Projects health
    projects_query = (
        select(ConstructionProject)
        .where(ConstructionProject.id.in_(project_ids))
    )
    projects_result = await db.execute(projects_query)
    projects = projects_result.scalars().all()

    projects_health = []
    for proj in projects:
        # Count reports and issues for this project
        proj_reports = [r for r in reports if r.project_id == proj.id]
        total_reports = len(proj_reports)

        # Determine overall health
        proj_critical = sum(1 for r in proj_reports if analytics_map.get(r.id, None) and analytics_map[r.id].health_status == 'critical')
        proj_attention = sum(1 for r in proj_reports if analytics_map.get(r.id, None) and analytics_map[r.id].health_status == 'attention')

        if proj_critical > 0:
            health = 'critical'
        elif proj_attention > 0:
            health = 'attention'
        else:
            health = 'stable'

        # Count open issues
        open_issues = sum(
            len([p for p in analytics_map[r.id].problems if p.status == 'new'])
            for r in proj_reports
            if r.id in analytics_map and hasattr(analytics_map[r.id], 'problems')
        ) if analytics_map else 0

        projects_health.append(ProjectHealthResponse(
            id=proj.id,
            name=proj.name,
            project_code=proj.project_code,
            health=health,
            total_reports=total_reports,
            open_issues=open_issues
        ))

    # Pulse chart (last 7 days)
    pulse_chart = PulseChartResponse(labels=[], critical=[], attention=[], stable=[])
    today = datetime.now().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        pulse_chart.labels.append(day.strftime('%d.%m'))

        # Count reports by health for this day
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())

        day_reports = [r for r in reports if day_start <= r.created_at.replace(tzinfo=None) <= day_end]

        critical_count = sum(1 for r in day_reports if analytics_map.get(r.id) and analytics_map[r.id].health_status == 'critical')
        attention_count = sum(1 for r in day_reports if analytics_map.get(r.id) and analytics_map[r.id].health_status == 'attention')
        stable_count = len(day_reports) - critical_count - attention_count

        pulse_chart.critical.append(critical_count)
        pulse_chart.attention.append(attention_count)
        pulse_chart.stable.append(stable_count)

    return DashboardViewResponse(
        kpi=kpi,
        calendar_events=calendar_events,
        attention_items=attention_items,
        activity_feed=activity_feed,
        projects_health=projects_health,
        pulse_chart=pulse_chart
    )


# =============================================================================
# Analytics Detail Endpoint
# =============================================================================

@router.get(
    "/analytics/{analytics_id}",
    response_model=AnalyticsDetailResponse,
    summary="Get analytics detail",
    description="Returns detailed analytics data for a specific report."
)
async def get_analytics_detail(
    analytics_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalyticsDetailResponse:
    """Get detailed analytics for a report."""

    # Get analytics with report and project
    query = (
        select(ReportAnalytics)
        .options(
            selectinload(ReportAnalytics.report).selectinload(ConstructionReportDB.project),
            selectinload(ReportAnalytics.problems)
        )
        .where(ReportAnalytics.id == analytics_id)
    )
    result = await db.execute(query)
    analytics = result.scalar_one_or_none()

    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analytics with id {analytics_id} not found"
        )

    # Check access
    if analytics.report and analytics.report.project:
        project_ids = await get_user_project_ids(db, current_user)
        if analytics.report.project_id not in project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this analytics"
            )

    # Build dynamic indicators (Autoprotocol format)
    key_indicators = []
    if analytics.key_indicators:
        for indicator in analytics.key_indicators:
            key_indicators.append(KeyIndicator(
                indicator_name=indicator.get('indicator_name', indicator.get('label', '')),
                status=indicator.get('status', indicator.get('value', '')),
                comment=indicator.get('comment', '')
            ))

    # Build challenges
    challenges = []
    if analytics.challenges:
        for challenge in analytics.challenges:
            challenges.append(Challenge(
                text=challenge.get('text', ''),
                recommendation=challenge.get('recommendation', '')
            ))

    # Build achievements
    achievements = analytics.achievements or []

    # Report files
    report = analytics.report
    report_files = ReportFiles()
    has_main_report = False
    has_detailed_report = False
    has_transcript = False
    has_tasks = False
    filename = ""

    if report:
        if report.report_path:
            report_files.main = report.report_path
            has_main_report = Path(report.report_path).exists() if report.report_path else False
        # Manager brief is stored in DB but not exposed for download
        has_detailed_report = False
        if report.transcript_path:
            report_files.transcript = report.transcript_path
            has_transcript = Path(report.transcript_path).exists() if report.transcript_path else False
        if report.tasks_path:
            report_files.tasks = report.tasks_path
            has_tasks = Path(report.tasks_path).exists() if report.tasks_path else False
        # Original filename
        filename = report.title or report.audio_file_path or f"Отчёт {report.job_id[:8]}"

    return AnalyticsDetailResponse(
        id=analytics.id,
        summary=analytics.summary or "",
        status=analytics.health_status,
        key_indicators=key_indicators,
        challenges=challenges,
        achievements=achievements,
        toxicity_level=analytics.toxicity_level or 0.0,
        toxicity_details=analytics.toxicity_details or "",
        report_files=report_files,
        has_main_report=has_main_report,
        has_detailed_report=has_detailed_report,
        has_transcript=has_transcript,
        has_tasks=has_tasks,
        filename=filename
    )


# =============================================================================
# Problem Status Update Endpoint
# =============================================================================

@router.post(
    "/problem/status",
    response_model=dict,
    summary="Update problem status",
    description="Mark a problem as resolved or reopen it."
)
async def update_problem_status(
    data: ProblemStatusUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Update problem status."""

    # Get problem
    query = (
        select(ReportProblem)
        .options(
            selectinload(ReportProblem.analytics)
            .selectinload(ReportAnalytics.report)
        )
        .where(ReportProblem.id == data.problem_id)
    )
    result = await db.execute(query)
    problem = result.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id {data.problem_id} not found"
        )

    # Check access
    if problem.analytics and problem.analytics.report:
        project_ids = await get_user_project_ids(db, current_user)
        project_id = problem.analytics.report.project_id
        if project_id and project_id not in project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this problem"
            )

    # Update status
    problem.status = data.status
    if data.status == 'done':
        problem.resolved_by_id = current_user.id
        problem.resolved_at = datetime.utcnow()
    else:
        problem.resolved_by_id = None
        problem.resolved_at = None

    await db.commit()

    return {"success": True, "message": f"Problem status updated to {data.status}"}


# =============================================================================
# Report Download Endpoint
# =============================================================================

@router.get(
    "/analytics/{analytics_id}/report/{report_type}",
    summary="Download analytics report",
    description="Download report file by type."
)
async def download_analytics_report(
    analytics_id: int,
    report_type: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Download report file for analytics."""

    if report_type not in ('main', 'detailed', 'transcript', 'tasks'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="report_type must be 'main', 'detailed', 'transcript', or 'tasks'"
        )
    if report_type == "detailed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detailed report is not available"
        )

    # Get analytics
    query = (
        select(ReportAnalytics)
        .options(selectinload(ReportAnalytics.report))
        .where(ReportAnalytics.id == analytics_id)
    )
    result = await db.execute(query)
    analytics = result.scalar_one_or_none()

    if not analytics or not analytics.report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analytics with id {analytics_id} not found"
        )

    # Check access
    if analytics.report.project_id:
        project_ids = await get_user_project_ids(db, current_user)
        if analytics.report.project_id not in project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this report"
            )

    # Get file path
    report = analytics.report
    file_path_str = {
        "main": report.report_path,
        "transcript": report.transcript_path,
        "tasks": report.tasks_path,
    }.get(report_type)

    if not file_path_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {report_type} file available"
        )

    # Validate file path is within DATA_DIR (prevents path traversal)
    path = validate_file_path(
        file_path=file_path_str,
        allowed_dir=DATA_DIR,
        must_exist=True
    )

    # Return file
    filename = path.name
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if path.suffix == '.txt':
        media_type = "text/plain"
    elif path.suffix == '.pdf':
        media_type = "application/pdf"

    return FileResponse(
        path=str(path),
        filename=filename,
        media_type=media_type
    )


@router.get(
    "/analytics/{analytics_id}/report/all",
    summary="Download all analytics files",
    description="Download all available report files as a zip archive."
)
async def download_analytics_report_all(
    analytics_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Download all available files for analytics as a zip archive."""
    import zipfile
    import tempfile

    # Get analytics
    query = (
        select(ReportAnalytics)
        .options(selectinload(ReportAnalytics.report))
        .where(ReportAnalytics.id == analytics_id)
    )
    result = await db.execute(query)
    analytics = result.scalar_one_or_none()

    if not analytics or not analytics.report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analytics with id {analytics_id} not found"
        )

    # Check access
    if analytics.report.project_id:
        project_ids = await get_user_project_ids(db, current_user)
        if analytics.report.project_id not in project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this report"
            )

    report = analytics.report
    candidates = {
        "report.docx": report.report_path,
        "transcript": report.transcript_path,
        "tasks.xlsx": report.tasks_path,
    }

    files = []
    for name, path_str in candidates.items():
        if not path_str:
            continue
        path = validate_file_path(
            file_path=path_str,
            allowed_dir=DATA_DIR,
            must_exist=True
        )
        files.append((name, path))

    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files available to download"
        )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in files:
            arcname = name if name.endswith(path.suffix) else f"{name}{path.suffix}"
            zf.write(path, arcname=arcname)

    filename = f"analytics_{analytics_id}_files.zip"
    return FileResponse(
        path=tmp.name,
        filename=filename,
        media_type="application/zip"
    )
