"""
API роуты дашборда менеджера.

Эндпоинты для:
- Дашборд с KPI, календарём, проблемами, лентой активности
- Детальная аналитика отчёта
- Управление статусами проблем
- Скачивание отчётов
"""
import os
from datetime import datetime, timedelta, timezone
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

# Базовая директория данных для валидации путей к файлам
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
from backend.shared.models import User, user_project_access
from backend.core.auth.dependencies import CurrentUser
# Импорт напрямую из моделей чтобы избежать тяжёлой цепочки зависимостей
from backend.domains.construction.models import (
    ConstructionProject,
    ConstructionReportDB,
    ReportAnalytics,
    ReportProblem,
)


router = APIRouter(tags=["Дашборд менеджера"])


# =============================================================================
# Схемы
# =============================================================================

class KPIResponse(BaseModel):
    """Ключевые показатели эффективности."""
    total_jobs: int = 0
    attention_jobs: int = 0
    critical_jobs: int = 0


class CalendarEventResponse(BaseModel):
    """Событие календаря для отображения."""
    id: int  # report_id
    analytics_id: Optional[int] = None  # analytics_id для модалки
    title: str
    date: str  # ISO date string
    status: str  # critical, attention, stable
    project_id: int
    project_code: str
    project_name: str


class AttentionItemResponse(BaseModel):
    """Элемент требующий внимания (проблема) для отображения."""
    id: int
    analytics_id: int
    problem_text: str
    status: str  # new, done
    severity: str  # critical, attention
    source_file: str
    project_name: str
    created_at: datetime


class ActivityFeedItemResponse(BaseModel):
    """Элемент ленты активности."""
    id: int
    title: str
    project_name: str
    status: str  # critical, attention, stable
    created_at: datetime


class ProjectHealthResponse(BaseModel):
    """Сводка здоровья проекта."""
    id: int
    name: str
    project_code: str
    health: str  # critical, attention, stable
    total_reports: int = 0
    open_issues: int = 0


class PulseChartResponse(BaseModel):
    """Данные пульс-графика для стековой диаграммы."""
    labels: List[str] = []
    critical: List[int] = []
    attention: List[int] = []
    stable: List[int] = []


class DashboardViewResponse(BaseModel):
    """Полный ответ представления дашборда."""
    kpi: KPIResponse
    calendar_events: List[CalendarEventResponse] = []
    attention_items: List[AttentionItemResponse] = []
    activity_feed: List[ActivityFeedItemResponse] = []
    projects_health: List[ProjectHealthResponse] = []
    pulse_chart: PulseChartResponse


class KeyIndicator(BaseModel):
    """Динамический индикатор для детальной аналитики (формат Autoprotocol)."""
    indicator_name: str
    status: str  # "Критический", "Есть риски", "В норме"
    comment: str


class Challenge(BaseModel):
    """Проблема/вызов с рекомендацией."""
    text: str
    recommendation: str


class ReportFiles(BaseModel):
    """Пути к файлам отчёта."""
    main: Optional[str] = None
    detailed: Optional[str] = None
    transcript: Optional[str] = None
    tasks: Optional[str] = None
    risk_brief: Optional[str] = None
    summary: Optional[str] = None


class ParticipantGroup(BaseModel):
    """Группа участников по организации."""
    org_name: str
    persons: List[str]


class AnalyticsDetailResponse(BaseModel):
    """Ответ с детальной аналитикой."""
    id: int
    summary: str = ""
    status: str = "stable"  # critical, attention, stable
    key_indicators: List[KeyIndicator] = []
    challenges: List[Challenge] = []
    achievements: List[str] = []
    toxicity_level: float = 0.0
    toxicity_details: str = ""
    report_files: ReportFiles
    # Флаги для кнопок скачивания (формат Autoprotocol)
    has_main_report: bool = False
    has_detailed_report: bool = False
    has_transcript: bool = False
    has_tasks: bool = False
    has_risk_brief: bool = False
    has_summary: bool = False
    filename: str = ""  # Оригинальное имя файла для отображения
    # JSON данные для интерактивного отображения
    risk_brief_json: Optional[dict] = None  # RiskBrief JSON для аккордеонов
    basic_report_json: Optional[dict] = None  # BasicReport JSON (meeting_summary, expert_analysis, tasks)
    # Участники совещания (сгруппированные по организациям)
    participants: List[ParticipantGroup] = []


class ProblemStatusUpdate(BaseModel):
    """Запрос на обновление статуса проблемы."""
    problem_id: int
    status: str = Field(..., pattern="^(new|done)$")


# =============================================================================
# Вспомогательные функции
# =============================================================================

async def get_user_project_ids(db: AsyncSession, user: User) -> List[int]:
    """
    Получить ID проектов доступных пользователю через user_project_access.

    ВСЕ пользователи (включая суперпользователей) должны иметь явный доступ.
    Это предотвращает загромождение дашборда всеми проектами.

    Пользователь видит проекты где:
    1. Он назначен менеджером (manager_id)
    2. У него есть явный доступ через таблицу user_project_access
    """
    access_subquery = (
        select(user_project_access.c.project_id)
        .where(user_project_access.c.user_id == user.id)
    )
    result = await db.execute(
        select(ConstructionProject.id)
        .where(
            or_(
                ConstructionProject.manager_id == user.id,
                ConstructionProject.id.in_(access_subquery)
            )
        )
    )
    return [row[0] for row in result.fetchall()]


# =============================================================================
# Эндпоинт дашборда
# =============================================================================

@router.get(
    "/dashboard-view",
    response_model=DashboardViewResponse,
    summary="Получить дашборд",
    description="Возвращает полные данные дашборда: KPI, календарь, проблемы, лента активности и здоровье проектов."
)
async def get_dashboard_view(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: Optional[int] = Query(None, description="Фильтр по ID проекта"),
    start_date: Optional[str] = Query(None, description="Фильтр по начальной дате (ISO формат)"),
    end_date: Optional[str] = Query(None, description="Фильтр по конечной дате (ISO формат)"),
) -> DashboardViewResponse:
    """Получить полные данные дашборда."""

    # Получить доступные ID проектов
    project_ids = await get_user_project_ids(db, current_user)
    if not project_ids:
        return DashboardViewResponse(
            kpi=KPIResponse(),
            pulse_chart=PulseChartResponse()
        )

    # Фильтровать по конкретному проекту если запрошено
    if project_id and project_id in project_ids:
        project_ids = [project_id]
    elif project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )

    # Парсинг фильтров дат
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

    # Построение базового запроса для отчётов
    base_filter = [ConstructionReportDB.project_id.in_(project_ids)]
    if date_from:
        base_filter.append(ConstructionReportDB.created_at >= date_from)
    if date_to:
        base_filter.append(ConstructionReportDB.created_at <= date_to)

    # Получение отчётов с аналитикой
    reports_query = (
        select(ConstructionReportDB)
        .options(selectinload(ConstructionReportDB.project))
        .where(and_(*base_filter))
        .order_by(desc(ConstructionReportDB.created_at))
    )
    reports_result = await db.execute(reports_query)
    reports = reports_result.scalars().all()

    # Расчёт KPI
    total_jobs = len(reports)
    attention_jobs = 0
    critical_jobs = 0

    # Получение аналитики для отчётов
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

    # События календаря
    calendar_events = []
    for report in reports[:50]:  # Limit to 50
        analytics = analytics_map.get(report.id)
        health = analytics.health_status if analytics else 'stable'
        if report.status == 'failed':
            health = 'critical'

        event_date = report.meeting_date or report.created_at
        calendar_events.append(CalendarEventResponse(
            id=report.id,
            analytics_id=analytics.id if analytics else None,
            title=report.title or f"Отчёт {report.job_id[:8]}",
            date=event_date.date().isoformat() if event_date else datetime.now(timezone.utc).date().isoformat(),
            status=health,
            project_id=report.project_id or 0,
            project_code=report.project.project_code if report.project else "",
            project_name=report.project.name if report.project else "Без проекта"
        ))

    # Проблемы требующие внимания (включая выполненные - они отображаются внизу списка)
    problems_query = (
        select(ReportProblem)
        .join(ReportAnalytics)
        .join(ConstructionReportDB)
        .where(ConstructionReportDB.project_id.in_(project_ids))
        .order_by(
            case((ReportProblem.status == 'new', 0), else_=1),  # new сначала, done внизу
            case((ReportProblem.severity == 'critical', 0), else_=1),
            desc(ReportProblem.created_at)
        )
        .limit(30)
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

    # Лента активности (последние отчёты)
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

    # Здоровье проектов
    projects_query = (
        select(ConstructionProject)
        .where(ConstructionProject.id.in_(project_ids))
    )
    projects_result = await db.execute(projects_query)
    projects = projects_result.scalars().all()

    projects_health = []
    for proj in projects:
        # Подсчёт отчётов и проблем для этого проекта
        proj_reports = [r for r in reports if r.project_id == proj.id]
        total_reports = len(proj_reports)

        # Определение общего здоровья
        proj_critical = sum(1 for r in proj_reports if analytics_map.get(r.id, None) and analytics_map[r.id].health_status == 'critical')
        proj_attention = sum(1 for r in proj_reports if analytics_map.get(r.id, None) and analytics_map[r.id].health_status == 'attention')

        if proj_critical > 0:
            health = 'critical'
        elif proj_attention > 0:
            health = 'attention'
        else:
            health = 'stable'

        # Подсчёт открытых проблем
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

    # Пульс-график (последние 7 дней)
    pulse_chart = PulseChartResponse(labels=[], critical=[], attention=[], stable=[])
    today = datetime.now(timezone.utc).date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        pulse_chart.labels.append(day.strftime('%d.%m'))

        # Подсчёт отчётов по здоровью за этот день
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        day_end = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)

        day_reports = [r for r in reports if day_start <= r.created_at <= day_end]

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
# Эндпоинт детальной аналитики
# =============================================================================

@router.get(
    "/analytics/{analytics_id}",
    response_model=AnalyticsDetailResponse,
    summary="Получить детали аналитики",
    description="Возвращает детальные данные аналитики для конкретного отчёта."
)
async def get_analytics_detail(
    analytics_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalyticsDetailResponse:
    """Получить детальную аналитику для отчёта."""

    # Получение аналитики с отчётом и проектом
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

    # Проверка доступа
    if analytics.report and analytics.report.project:
        project_ids = await get_user_project_ids(db, current_user)
        if analytics.report.project_id not in project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this analytics"
            )

    # Построение динамических индикаторов (формат Autoprotocol)
    key_indicators = []
    if analytics.key_indicators:
        for indicator in analytics.key_indicators:
            key_indicators.append(KeyIndicator(
                indicator_name=indicator.get('indicator_name', indicator.get('label', '')),
                status=indicator.get('status', indicator.get('value', '')),
                comment=indicator.get('comment', '')
            ))

    # Построение вызовов/проблем
    challenges = []
    if analytics.challenges:
        for challenge in analytics.challenges:
            challenges.append(Challenge(
                text=challenge.get('text', ''),
                recommendation=challenge.get('recommendation', '')
            ))

    # Построение достижений
    achievements = analytics.achievements or []

    # Файлы отчёта
    report = analytics.report
    report_files = ReportFiles()
    has_main_report = False
    has_detailed_report = False
    has_transcript = False
    has_tasks = False
    has_risk_brief = False
    has_summary = False
    filename = ""

    if report:
        if report.report_path:
            report_files.main = report.report_path
            has_main_report = Path(report.report_path).exists() if report.report_path else False
        # Менеджерский бриф хранится в БД но не доступен для скачивания
        has_detailed_report = False
        if report.transcript_path:
            report_files.transcript = report.transcript_path
            has_transcript = Path(report.transcript_path).exists() if report.transcript_path else False
        if report.tasks_path:
            report_files.tasks = report.tasks_path
            has_tasks = Path(report.tasks_path).exists() if report.tasks_path else False
        if report.risk_brief_path:
            report_files.risk_brief = report.risk_brief_path
            has_risk_brief = Path(report.risk_brief_path).exists() if report.risk_brief_path else False
        if getattr(report, 'summary_path', None):
            report_files.summary = report.summary_path
            has_summary = Path(report.summary_path).exists() if report.summary_path else False
        # Оригинальное имя файла
        filename = report.title or report.audio_file_path or f"Отчёт {report.job_id[:8]}"

    # Получить risk_brief_json для интерактивного отображения
    risk_brief_json = None
    if report and report.risk_brief_json:
        risk_brief_json = report.risk_brief_json

    # Получить basic_report_json (meeting_summary, expert_analysis, tasks)
    basic_report_json = None
    if report and report.basic_report_json:
        basic_report_json = report.basic_report_json

    # Получить участников совещания
    # Источник 1: participant_ids в БД -> fetch из Person table
    # Источник 2: risk_brief_json.participants (сохраняются при генерации)
    participants = []

    # Try from participant_ids first (fresh data from DB)
    if report and report.participant_ids:
        try:
            from ...tasks.transcription import _fetch_participants_for_risk_brief_async
            raw_participants = await _fetch_participants_for_risk_brief_async(report.participant_ids)
            for group in raw_participants:
                # Map from function's keys to ParticipantGroup schema
                # Function returns: {"organization": ..., "role": ..., "people": [...]}
                # Schema expects: {"org_name": ..., "persons": [...]}
                role = group.get("role", "")
                org = group.get("organization", "Без организации")
                org_name = f"{org} ({role})" if role else org
                participants.append(ParticipantGroup(
                    org_name=org_name,
                    persons=group.get("people", [])
                ))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to fetch participants from IDs: {e}")

    # Fallback: try from risk_brief_json.participants (stored during generation)
    if not participants and risk_brief_json and risk_brief_json.get("participants"):
        try:
            for group in risk_brief_json["participants"]:
                role = group.get("role", "")
                org = group.get("organization", "Без организации")
                org_name = f"{org} ({role})" if role else org
                participants.append(ParticipantGroup(
                    org_name=org_name,
                    persons=group.get("people", [])
                ))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to parse participants from risk_brief_json: {e}")

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
        has_risk_brief=has_risk_brief,
        has_summary=has_summary,
        filename=filename,
        risk_brief_json=risk_brief_json,
        basic_report_json=basic_report_json,
        participants=participants,
    )


# =============================================================================
# Эндпоинт обновления статуса проблемы
# =============================================================================

@router.post(
    "/problem/status",
    response_model=dict,
    summary="Обновить статус проблемы",
    description="Пометить проблему как решённую или переоткрыть её."
)
async def update_problem_status(
    data: ProblemStatusUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Обновить статус проблемы."""

    # Получение проблемы
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

    # Проверка доступа
    if problem.analytics and problem.analytics.report:
        project_ids = await get_user_project_ids(db, current_user)
        project_id = problem.analytics.report.project_id
        if project_id and project_id not in project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this problem"
            )

    # Обновление статуса
    problem.status = data.status
    if data.status == 'done':
        problem.resolved_by_id = current_user.id
        problem.resolved_at = datetime.now(timezone.utc)
    else:
        problem.resolved_by_id = None
        problem.resolved_at = None

    await db.commit()
    await db.refresh(problem)

    return {"success": True, "message": f"Problem status updated to {data.status}"}


# =============================================================================
# Эндпоинт скачивания отчётов
# =============================================================================

# NOTE: /report/all MUST be registered before /report/{report_type}
# to prevent FastAPI from matching "all" as a report_type parameter.

@router.get(
    "/analytics/{analytics_id}/report/all",
    summary="Скачать все файлы аналитики",
    description="Скачать все доступные файлы отчёта в zip архиве."
)
async def download_analytics_report_all(
    analytics_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Скачать все доступные файлы аналитики в zip архиве."""
    import zipfile
    import tempfile

    # Получение аналитики
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

    # Проверка доступа
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
        "tasks.xlsx": report.tasks_path,
        "risk_brief.pdf": report.risk_brief_path,
        "summary.docx": getattr(report, 'summary_path', None),
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
    from starlette.background import BackgroundTask
    return FileResponse(
        path=tmp.name,
        filename=filename,
        media_type="application/zip",
        background=BackgroundTask(lambda: os.unlink(tmp.name)),
    )


@router.get(
    "/analytics/{analytics_id}/report/{report_type}",
    summary="Скачать отчёт аналитики",
    description="Скачать файл отчёта по типу."
)
async def download_analytics_report(
    analytics_id: int,
    report_type: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Скачать файл отчёта для аналитики."""

    if report_type not in ('main', 'detailed', 'transcript', 'tasks', 'risk_brief', 'summary'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="report_type must be 'main', 'detailed', 'transcript', 'tasks', 'risk_brief', or 'summary'"
        )
    if report_type == "detailed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detailed report is not available"
        )

    # Получение аналитики
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

    # Проверка доступа
    if analytics.report.project_id:
        project_ids = await get_user_project_ids(db, current_user)
        if analytics.report.project_id not in project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this report"
            )

    # Получение пути к файлу
    report = analytics.report
    file_path_str = {
        "main": report.report_path,
        "transcript": report.transcript_path,
        "tasks": report.tasks_path,
        "risk_brief": report.risk_brief_path,
        "summary": getattr(report, 'summary_path', None),
    }.get(report_type)

    if not file_path_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {report_type} file available"
        )

    # Валидация что путь к файлу внутри DATA_DIR (защита от path traversal)
    path = validate_file_path(
        file_path=file_path_str,
        allowed_dir=DATA_DIR,
        must_exist=True
    )

    # Возврат файла
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


# =============================================================================
# Эндпоинты редактирования артефактов
# =============================================================================

class UpdateRiskBriefRequest(BaseModel):
    """Запрос на обновление риск-брифа."""
    risk_brief_json: dict  # Full RiskBrief JSON


class UpdateTasksRequest(BaseModel):
    """Запрос на обновление задач."""
    basic_report_json: dict  # Full BasicReport JSON (only tasks will be used)


async def _get_analytics_for_update(
    analytics_id: int,
    current_user: CurrentUser,
    db: AsyncSession,
    load_project: bool = False,
) -> tuple:
    """
    Common checks for analytics update endpoints:
    1. Verify manager+ role
    2. Load analytics with report (optionally with project)
    3. Check project access

    Returns (analytics, report) tuple.
    """
    if not current_user.is_superuser and current_user.role not in ('manager', 'admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only manager+ can edit reports"
        )

    report_load = selectinload(ReportAnalytics.report)
    if load_project:
        report_load = report_load.selectinload(ConstructionReportDB.project)

    query = (
        select(ReportAnalytics)
        .options(report_load)
        .where(ReportAnalytics.id == analytics_id)
    )
    result = await db.execute(query)
    analytics = result.scalar_one_or_none()

    if not analytics or not analytics.report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analytics with id {analytics_id} not found"
        )

    if analytics.report.project_id:
        project_ids = await get_user_project_ids(db, current_user)
        if analytics.report.project_id not in project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this report"
            )

    return analytics, analytics.report


@router.patch(
    "/analytics/{analytics_id}/risk_brief",
    response_model=dict,
    summary="Обновить риск-бриф",
    description="Обновить risk_brief_json и перегенерировать PDF. Только для manager+."
)
async def update_risk_brief(
    analytics_id: int,
    data: UpdateRiskBriefRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Обновить риск-бриф и перегенерировать PDF."""
    from backend.domains.construction.schemas import RiskBrief
    from backend.domains.construction.generators.risk_brief import regenerate_risk_brief_pdf

    _analytics, report = await _get_analytics_for_update(
        analytics_id, current_user, db, load_project=True
    )

    try:
        risk_brief = RiskBrief.model_validate(data.risk_brief_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid risk_brief_json: {e}"
        )

    report.risk_brief_json = data.risk_brief_json
    await db.commit()

    if report.risk_brief_path:
        try:
            project = report.project
            regenerate_risk_brief_pdf(
                risk_brief=risk_brief,
                output_path=Path(report.risk_brief_path),
                source_file=report.title or report.audio_file_path or "N/A",
                duration="N/A",
                speakers_count=report.speaker_count or 0,
                meeting_date=report.meeting_date.strftime("%Y-%m-%d") if report.meeting_date else None,
                project_name=project.name if project else None,
                project_code=project.project_code if project else None,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to regenerate risk_brief PDF: {e}")

    return {"success": True, "message": "Risk brief updated"}


@router.patch(
    "/analytics/{analytics_id}/tasks",
    response_model=dict,
    summary="Обновить задачи",
    description="Обновить basic_report_json и перегенерировать XLSX. Только для manager+."
)
async def update_tasks(
    analytics_id: int,
    data: UpdateTasksRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Обновить задачи и перегенерировать XLSX."""
    from backend.domains.construction.schemas import BasicReport
    from backend.domains.construction.generators.tasks import regenerate_tasks_xlsx

    _analytics, report = await _get_analytics_for_update(analytics_id, current_user, db)

    try:
        basic_report = BasicReport.model_validate(data.basic_report_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid basic_report_json: {e}"
        )

    report.basic_report_json = data.basic_report_json
    await db.commit()

    if report.tasks_path:
        try:
            regenerate_tasks_xlsx(
                basic_report=basic_report,
                output_path=Path(report.tasks_path),
                source_file=report.title or report.audio_file_path or "N/A",
                duration="N/A",
                meeting_date=report.meeting_date.strftime("%Y-%m-%d") if report.meeting_date else None,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to regenerate tasks XLSX: {e}")

    return {"success": True, "message": "Tasks updated"}


# =============================================================================
# Подрядчики и участники проекта
# =============================================================================

class PersonResponse(BaseModel):
    """Сотрудник организации."""
    id: int
    full_name: str
    position: Optional[str] = None
    email: Optional[str] = None


class ContractorResponse(BaseModel):
    """Подрядчик (организация с ролью) для проекта."""
    id: int
    organization_id: int
    organization_name: str
    role: str
    role_label: str
    persons: List[PersonResponse] = []


class RoleResponse(BaseModel):
    """Стандартная роль подрядчика."""
    value: str
    label: str


@router.get(
    "/projects/{project_code}/contractors",
    response_model=List[ContractorResponse],
    summary="Получить подрядчиков проекта",
    description="Возвращает список подрядчиков (организаций с сотрудниками) для проекта."
)
async def get_project_contractors(
    project_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[ContractorResponse]:
    """Получить подрядчиков проекта по коду."""
    from backend.domains.construction.project_service import ProjectService

    service = ProjectService(db)

    # Получение проекта по коду
    project = await service.get_project_by_code(project_code)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с кодом {project_code} не найден"
        )

    contractors = await service.get_project_contractors(project.id)
    return [ContractorResponse(**c) for c in contractors]


@router.get(
    "/roles",
    response_model=List[RoleResponse],
    summary="Получить стандартные роли подрядчиков",
    description="Возвращает список стандартных ролей для подрядчиков."
)
async def get_standard_roles(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[RoleResponse]:
    """Получить стандартные роли подрядчиков."""
    from backend.domains.construction.project_service import ProjectService

    service = ProjectService(db)
    roles = await service.get_standard_roles()
    return [RoleResponse(**r) for r in roles]


class CreateContractorRequest(BaseModel):
    """Запрос на создание подрядчика для проекта."""
    organization_name: str
    role: str
    short_name: Optional[str] = None


class CreatePersonRequest(BaseModel):
    """Запрос на добавление сотрудника в организацию."""
    full_name: str
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@router.post(
    "/projects/{project_code}/contractors",
    response_model=ContractorResponse,
    summary="Добавить подрядчика в проект",
    description="Добавить нового подрядчика (организацию с ролью) в проект."
)
async def create_project_contractor(
    project_code: str,
    request: CreateContractorRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContractorResponse:
    """Добавить подрядчика в проект."""
    from backend.domains.construction.project_service import ProjectService

    service = ProjectService(db)

    # Получение проекта по коду
    project = await service.get_project_by_code(project_code)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с кодом {project_code} не найден"
        )

    # Создание подрядчика
    contractor = await service.add_contractor(
        project_id=project.id,
        organization_name=request.organization_name,
        role=request.role,
        short_name=request.short_name,
    )
    await db.commit()

    # Перезагрузка с организацией
    from backend.domains.construction.models import ProjectContractor, Organization, ContractorRole
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select

    result = await db.execute(
        select(ProjectContractor)
        .options(selectinload(ProjectContractor.organization).selectinload(Organization.persons))
        .where(ProjectContractor.id == contractor.id)
    )
    contractor = result.scalar_one()

    role_labels = ContractorRole.labels()
    org = contractor.organization

    return ContractorResponse(
        id=contractor.id,
        organization_id=org.id,
        organization_name=org.short_name or org.name,
        role=contractor.role,
        role_label=role_labels.get(contractor.role, contractor.role),
        persons=[
            PersonResponse(
                id=p.id,
                full_name=p.full_name,
                position=p.position,
                email=p.email,
            )
            for p in org.persons if p.is_active
        ],
    )


@router.post(
    "/organizations/{organization_id}/persons",
    response_model=PersonResponse,
    summary="Добавить сотрудника в организацию",
    description="Добавить нового сотрудника в организацию."
)
async def create_person(
    organization_id: int,
    request: CreatePersonRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PersonResponse:
    """Добавить сотрудника в организацию."""
    from backend.domains.construction.project_service import ProjectService
    from backend.domains.construction.models import Organization

    # Проверка существования организации
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with id {organization_id} not found"
        )

    service = ProjectService(db)
    person = await service.add_person(
        organization_id=organization_id,
        full_name=request.full_name,
        position=request.position,
        email=request.email,
        phone=request.phone,
    )
    await db.commit()

    return PersonResponse(
        id=person.id,
        full_name=person.full_name,
        position=person.position,
        email=person.email,
    )


# =============================================================================
# CRUD endpoints for persons, organizations, contractors
# =============================================================================

class UpdatePersonRequest(BaseModel):
    """Запрос на обновление сотрудника."""
    full_name: Optional[str] = None
    position: Optional[str] = None


class UpdateOrganizationRequest(BaseModel):
    """Запрос на переименование организации."""
    name: Optional[str] = None
    short_name: Optional[str] = None


@router.patch(
    "/persons/{person_id}",
    response_model=PersonResponse,
    summary="Обновить сотрудника",
    description="Обновить ФИО и/или должность сотрудника."
)
async def update_person(
    person_id: int,
    request: UpdatePersonRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PersonResponse:
    """Обновить сотрудника."""
    from backend.domains.construction.project_service import ProjectService

    service = ProjectService(db)
    person = await service.update_person(
        person_id=person_id,
        full_name=request.full_name,
        position=request.position,
    )
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person with id {person_id} not found"
        )

    await db.commit()
    return PersonResponse(
        id=person.id,
        full_name=person.full_name,
        position=person.position,
        email=person.email,
    )


@router.delete(
    "/persons/{person_id}",
    summary="Удалить сотрудника",
    description="Мягкое удаление сотрудника (is_active=False)."
)
async def delete_person(
    person_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Удалить сотрудника (мягкое удаление)."""
    from backend.domains.construction.project_service import ProjectService

    service = ProjectService(db)
    success = await service.delete_person(person_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person with id {person_id} not found"
        )

    await db.commit()
    return {"success": True}


@router.patch(
    "/organizations/{organization_id}",
    summary="Переименовать организацию",
    description="Обновить название организации."
)
async def update_organization(
    organization_id: int,
    request: UpdateOrganizationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Обновить организацию."""
    from backend.domains.construction.project_service import ProjectService

    service = ProjectService(db)
    org = await service.update_organization(
        organization_id=organization_id,
        name=request.name,
        short_name=request.short_name,
    )
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with id {organization_id} not found"
        )

    await db.commit()
    return {"success": True, "name": org.name}


@router.delete(
    "/projects/{project_code}/contractors/{contractor_id}",
    summary="Удалить подрядчика из проекта",
    description="Удалить подрядчика (организацию) из проекта."
)
async def delete_project_contractor(
    project_code: str,
    contractor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Удалить подрядчика из проекта."""
    from backend.domains.construction.project_service import ProjectService

    service = ProjectService(db)
    project = await service.get_project_by_code(project_code)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с кодом {project_code} не найден"
        )

    success = await service.remove_contractor(project.id, contractor_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contractor with id {contractor_id} not found in project"
        )

    await db.commit()
    return {"success": True}
