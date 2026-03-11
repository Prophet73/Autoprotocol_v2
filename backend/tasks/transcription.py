"""Transcription Celery tasks with Redis job storage."""
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict

from celery.exceptions import SoftTimeLimitExceeded

from .celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run a coroutine in sync Celery worker context.

    Handles both cases: when event loop exists and when it doesn't.
    """
    try:
        asyncio.get_running_loop()
        # Already in a running loop - run in separate thread with new loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop - use asyncio.run()
        return asyncio.run(coro)


def _check_gemini_configured():
    """Check if Gemini API is configured via GOOGLE_API_KEY env var."""
    return bool(os.getenv("GOOGLE_API_KEY"))


def _needs_llm_generators(artifact_options: Dict) -> bool:
    """Check if any LLM-dependent generators are requested and Gemini is configured."""
    if not _check_gemini_configured():
        return False
    return any([
        artifact_options.get("generate_tasks", False),
        artifact_options.get("generate_report", False),
        artifact_options.get("generate_risk_brief", False),
    ])


def _generate_transcript_artifact(
    result,
    output_path: Path,
    artifact_options: Dict,
    progress_callback,
    domain_type: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate transcript.docx only (no LLM required). Runs on GPU worker.

    Returns:
        Dict mapping artifact type to file path.
    """
    output_files = {}

    domain = domain_type or "construction"

    from ..domains.generator_registry import get_domain_generators
    gens = get_domain_generators(domain)
    if gens:
        generate_transcript = gens.generate_transcript
    else:
        from ..domains.construction.generators import generate_transcript

    if artifact_options.get("generate_transcript", True):
        progress_callback("domain_generators", 92, "Формирование стенограммы...")
        try:
            transcript_path = generate_transcript(
                result, output_path,
                meeting_type=artifact_options.get("meeting_type"),
                meeting_date=artifact_options.get("meeting_date"),
            )
            output_files["transcript"] = str(transcript_path)
            logger.info(f"Generated transcript: {transcript_path}")
        except Exception as e:
            logger.error(f"Transcript generation failed: {e}")

    return output_files


def get_job_store():
    """Get job store - lazy import to avoid circular deps."""
    from ..core.storage import get_job_store
    return get_job_store()


async def _fetch_participants_for_risk_brief_async(participant_ids: List[int]) -> List[dict]:
    """
    Fetch participants from DB and group by organization for risk brief (async version).

    Args:
        participant_ids: List of person IDs

    Returns:
        List of dicts with format:
        [
            {
                "role": "Заказчик",
                "organization": "ООО СтройМонтаж",
                "people": ["Иванов И.И. (директор)", "Петров П.П."]
            },
            ...
        ]
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from ..shared.database import get_celery_session_factory
    from ..domains.construction.models import Person, ProjectContractor

    session_factory = get_celery_session_factory()
    async with session_factory() as db:
        # Fetch persons with their organizations eagerly loaded
        result = await db.execute(
            select(Person)
            .options(selectinload(Person.organization))
            .where(Person.id.in_(participant_ids))
        )
        persons = result.scalars().all()

        # Group by organization
        org_map = {}  # org_id -> {org, persons, role}
        for person in persons:
            if person.organization_id:
                org = person.organization
                if org.id not in org_map:
                    # Try to find role from ProjectContractor
                    contractor_result = await db.execute(
                        select(ProjectContractor).where(
                            ProjectContractor.organization_id == org.id
                        )
                    )
                    contractor = contractor_result.scalar_one_or_none()
                    role = contractor.role if contractor else "Участник"
                    role_label = _get_role_label(role)
                    org_map[org.id] = {
                        "organization": org.name,
                        "role": role_label,
                        "people": []
                    }
                # Format person name with position
                name = person.full_name
                if person.position:
                    name += f" ({person.position})"
                org_map[org.id]["people"].append(name)

        return list(org_map.values())


def _fetch_participants_for_risk_brief(participant_ids: List[int]) -> List[dict]:
    """
    Fetch participants from DB (sync wrapper for Celery worker).
    Use _fetch_participants_for_risk_brief_async for async contexts.
    """
    return asyncio.run(_fetch_participants_for_risk_brief_async(participant_ids))


def _get_role_label(role: str) -> str:
    """Get Russian label for contractor role."""
    role_labels = {
        "customer": "Заказчик",
        "tech_customer": "Технический заказчик",
        "general_contractor": "Генподрядчик",
        "designer": "Проектировщик",
        "subcontractor": "Субподрядчик",
        "supplier": "Поставщик",
        "inspector": "Контролирующий орган",
        "other": "Прочее",
    }
    return role_labels.get(role, role)


def _build_meeting_report(
    domain_type: Optional[str],
    domain_report_json: Optional[str],
    basic_report_json: Optional[str],
) -> Optional[Dict]:
    """
    Convert domain LLM report to MeetingReport format for Redis/frontend.

    MeetingReport: {executive_summary, topics: [{title, problem, decision, risks}], tasks: [{description, responsible, priority}]}
    """
    import json

    # CEO domain: NotechResult → MeetingReport
    if domain_type == "ceo" and domain_report_json:
        try:
            raw = json.loads(domain_report_json)
            # CEOReport wraps meeting_type + result based on type
            # For notech: raw has meeting_summary, key_points, action_items, participants_summary
            # plus notech-specific fields via the LLM output

            # Try to find notech result data
            notech = raw  # flat structure from BaseMeetingReport + CEOReport

            topics = []
            for i, q in enumerate(notech.get("questions", [])):
                topics.append({
                    "id": i,
                    "title": q.get("title", f"Вопрос {i + 1}"),
                    "problem": q.get("description", ""),
                    "decision": q.get("decision"),
                    "risks": q.get("risks", []),
                    "value_points": q.get("value_points", []),
                    "discussion_details": q.get("discussion_details", []),
                    "timecodes": [],
                })

            tasks = []
            for item in notech.get("action_items", []):
                if isinstance(item, str):
                    tasks.append({"description": item})
                elif isinstance(item, dict):
                    tasks.append({
                        "description": item.get("description", str(item)),
                        "responsible": item.get("responsible"),
                        "priority": item.get("priority", "medium"),
                    })

            return {
                "executive_summary": notech.get("meeting_summary") or notech.get("summary", ""),
                "meeting_type": notech.get("meeting_type", "notech"),
                "meeting_topic": notech.get("meeting_topic"),
                "attendees": notech.get("attendees", []),
                "topics": topics,
                "tasks": tasks,
            }
        except Exception as e:
            logger.warning(f"Failed to build meeting_report for CEO: {e}")
            return None

    # Other non-construction domains: generic conversion
    if domain_report_json and domain_type not in ("construction", None):
        try:
            raw = json.loads(domain_report_json)
            tasks = []
            for item in raw.get("action_items", []):
                if isinstance(item, str):
                    tasks.append({"description": item})
                elif isinstance(item, dict):
                    tasks.append({
                        "description": item.get("description", str(item)),
                        "responsible": item.get("responsible"),
                        "priority": item.get("priority", "medium"),
                    })
            return {
                "executive_summary": raw.get("meeting_summary", ""),
                "meeting_type": raw.get("meeting_type", domain_type),
                "topics": [],
                "tasks": tasks,
            }
        except Exception as e:
            logger.warning(f"Failed to build meeting_report for {domain_type}: {e}")
            return None

    return None


def _run_domain_generators(
    result,
    output_path: Path,
    artifact_options: Dict,
    progress_callback,
    domain_type: Optional[str] = None,
    job_id: Optional[str] = None,
) -> tuple[Dict[str, str], Optional[object], Optional[object]]:
    """
    Run LLM-based domain generators (tasks, report, risk_brief).

    Transcript generation is handled separately by _generate_transcript_artifact
    and runs on the GPU worker without LLM dependency.

    Args:
        result: TranscriptionResult from pipeline
        output_path: Output directory
        artifact_options: Dict with flags (generate_tasks, generate_report, etc.)
        progress_callback: Progress callback function
        domain_type: Domain type (construction, hr, it)
        job_id: Job identifier (for adding warnings)

    Returns:
        Tuple of:
        - Dict mapping artifact type to file path
        - BasicReport object or None (for DB storage)
        - RiskBrief object or None (for DB storage)
    """
    output_files = {}
    basic_report_obj = None  # Will store BasicReport for DB
    risk_brief_obj = None  # Will store RiskBrief for DB

    def _add_warning(msg: str):
        """Add a warning to the job store if job_id is available."""
        if job_id:
            try:
                store = get_job_store()
                store.add_warning(job_id, msg)
            except Exception:
                pass

    # Check if Gemini is configured for LLM-based generators
    has_gemini = _check_gemini_configured()

    # Get meeting_type and meeting_date from artifact_options
    meeting_type = artifact_options.get("meeting_type")
    meeting_date = artifact_options.get("meeting_date")

    # Default to construction domain
    domain = domain_type or "construction"

    # Import generators based on domain
    generate_risk_brief = None  # Default - only construction has risk_brief
    get_basic_report = None  # Only construction has shared basic report
    _get_domain_report = None  # Domain-specific LLM report generator
    _MeetingTypeEnum = None  # Meeting type enum for non-construction domains
    _file_prefix = None  # File prefix for non-construction domains

    from ..domains.generator_registry import get_domain_generators
    gens = get_domain_generators(domain)
    if gens:
        generate_tasks = gens.generate_tasks
        generate_report = gens.generate_report
        _get_domain_report = gens.get_llm_report
        _MeetingTypeEnum = gens.meeting_type_enum
        _file_prefix = gens.file_prefix
    else:  # construction (default)
        from ..domains.construction.generators import (
            get_basic_report,  # Shared LLM call for tasks.xlsx and report.docx
            generate_tasks,
            generate_report,
            generate_risk_brief,  # INoT approach - PDF for client
            generate_summary,  # Topic-based synopsis (конспект)
        )

    domain_report_obj = None  # Non-construction: LLM report for meeting_report

    # LLM-based generators (require Gemini via GOOGLE_API_KEY)
    if has_gemini:
        # Fetch participants once for all generators that need them
        participant_ids = artifact_options.get("participant_ids", [])
        participants = None
        if participant_ids:
            try:
                participants = _fetch_participants_for_risk_brief(participant_ids)
                logger.info(f"Fetched participants for generators: {len(participants)} orgs")
            except Exception as e:
                logger.warning(f"Failed to fetch participants: {e}")

        basic_report = None  # Construction domain
        domain_report_obj = None  # Non-construction domains (dct, business, fta, ceo)
        needs_llm_report = (
            artifact_options.get("generate_tasks", False) or
            artifact_options.get("generate_report", False)
        )

        # --- Phase 1: Parallel LLM calls ---
        # Construction: get_basic_report, generate_risk_brief, generate_summary
        # are 3 independent LLM calls that can run concurrently.
        if domain == "construction" or domain is None:
            from concurrent.futures import ThreadPoolExecutor as _LLMPool

            futures = {}
            project_name = artifact_options.get("project_name")
            project_code = artifact_options.get("project_code")

            progress_callback("domain_generators", 93, "AI-генерация отчётов (параллельно)...")

            with _LLMPool(max_workers=3, thread_name_prefix="llm") as pool:
                # 1) BasicReport (needed for tasks + report)
                if needs_llm_report and get_basic_report:
                    futures["basic_report"] = pool.submit(
                        get_basic_report, result, meeting_date=meeting_date,
                        participants=participants,
                    )

                # 2) Risk Brief
                if artifact_options.get("generate_risk_brief", False) and generate_risk_brief:
                    futures["risk_brief"] = pool.submit(
                        generate_risk_brief, result, output_path,
                        meeting_date=meeting_date,
                        project_name=project_name,
                        project_code=project_code,
                        participants=participants,
                    )

                # 3) Summary (конспект)
                if artifact_options.get("generate_summary", False) and generate_summary:
                    futures["summary"] = pool.submit(
                        generate_summary, result, output_path,
                        meeting_date=meeting_date,
                        participants=participants,
                    )

                # Collect results as they complete
                for future_key, future in futures.items():
                    try:
                        result_val = future.result()  # blocks until done
                        if future_key == "basic_report":
                            basic_report = result_val
                            basic_report_obj = basic_report
                            logger.info(f"BasicReport generated: {len(basic_report.tasks)} tasks")
                        elif future_key == "risk_brief":
                            risk_brief_path, risk_brief_data = result_val
                            output_files["risk_brief"] = str(risk_brief_path)
                            risk_brief_obj = risk_brief_data
                            logger.info(f"Generated risk brief: {risk_brief_path}")
                        elif future_key == "summary":
                            output_files["summary"] = str(result_val)
                            logger.info(f"Generated summary: {result_val}")
                    except Exception as e:
                        logger.error(f"{future_key} generation failed: {e}", exc_info=True)
                        if future_key == "basic_report":
                            _add_warning("Не удалось сгенерировать отчёт через AI. Попробуйте повторить генерацию.")
                        elif future_key == "risk_brief":
                            _add_warning("Часть аналитических отчётов не сформирована. Попробуйте повторить генерацию.")
                        elif future_key == "summary":
                            _add_warning("Не удалось сгенерировать конспект. Попробуйте повторить генерацию.")

            logger.info(
                f"Parallel LLM phase complete: "
                f"basic_report={'ok' if basic_report else 'skip/fail'}, "
                f"risk_brief={'ok' if 'risk_brief' in output_files else 'skip/fail'}, "
                f"summary={'ok' if 'summary' in output_files else 'skip/fail'}"
            )
        else:
            # Non-construction domains (dct, business, fta, ceo) - single LLM call
            if needs_llm_report and _get_domain_report:
                progress_callback("domain_generators", 93, f"AI-анализ встречи ({domain})...")
                try:
                    domain_report_obj = _get_domain_report(
                        result, meeting_type=meeting_type, meeting_date=meeting_date,
                    )
                    if domain_report_obj:
                        logger.info(f"{domain} report generated for meeting type: {meeting_type}")
                    else:
                        logger.warning(f"{domain} report returned None (LLM may not be configured)")
                        _add_warning("AI-анализ встречи не сгенерирован")
                except Exception as e:
                    logger.error(f"{domain} report generation failed: {e}", exc_info=True)
                    _add_warning("AI-анализ встречи не сгенерирован. Попробуйте повторить генерацию.")

        # --- Phase 2: File generation (depends on LLM results) ---

        # Tasks Excel
        if artifact_options.get("generate_tasks", False) and generate_tasks:
            if basic_report:
                progress_callback("domain_generators", 96, "Формирование списка задач...")
                try:
                    tasks_path = generate_tasks(
                        result, output_path,
                        basic_report=basic_report,
                        participants=participants,
                        meeting_date=meeting_date,
                    )
                    output_files["tasks"] = str(tasks_path)
                    logger.info(f"Generated tasks: {tasks_path}")
                except Exception as e:
                    logger.error(f"Tasks generation failed: {e}", exc_info=True)
                    _add_warning("Excel-отчёт не сформирован. Попробуйте повторить генерацию.")
            elif domain_report_obj and _MeetingTypeEnum and _file_prefix:
                progress_callback("domain_generators", 96, "Формирование Excel отчёта...")
                try:
                    tasks_path = generate_tasks(
                        _MeetingTypeEnum(meeting_type),
                        domain_report_obj,
                        output_path / f"{_file_prefix}_report_{meeting_type}.xlsx",
                        meeting_date=meeting_date,
                    )
                    output_files["tasks"] = str(tasks_path)
                    logger.info(f"Generated {domain} Excel: {tasks_path}")
                except Exception as e:
                    logger.error(f"{domain} Excel generation failed: {e}", exc_info=True)
                    _add_warning("Excel-отчёт не сформирован. Попробуйте повторить генерацию.")

        # Report Word
        if artifact_options.get("generate_report", False):
            if basic_report:
                progress_callback("domain_generators", 97, "Формирование отчёта...")
                try:
                    report_path = generate_report(
                        result, output_path,
                        basic_report=basic_report,
                        meeting_type=meeting_type,
                        meeting_date=meeting_date,
                        participants=participants,
                    )
                    output_files["report"] = str(report_path)
                    logger.info(f"Generated report: {report_path}")
                except Exception as e:
                    logger.error(f"Report generation failed: {e}", exc_info=True)
                    _add_warning("Word-отчёт не сформирован. Попробуйте повторить генерацию.")
            elif domain_report_obj and _MeetingTypeEnum and _file_prefix:
                progress_callback("domain_generators", 97, "Формирование Word отчёта...")
                try:
                    report_path = generate_report(
                        _MeetingTypeEnum(meeting_type),
                        domain_report_obj,
                        output_path / f"{_file_prefix}_report_{meeting_type}.docx",
                        meeting_date=meeting_date,
                    )
                    output_files["report"] = str(report_path)
                    logger.info(f"Generated {domain} report: {report_path}")
                except Exception as e:
                    logger.error(f"{domain} report generation failed: {e}", exc_info=True)
                    _add_warning("Word-отчёт не сформирован. Попробуйте повторить генерацию.")
    else:
        # Log warning if LLM generators were requested but Gemini not configured
        llm_requested = any([
            artifact_options.get("generate_tasks", False),
            artifact_options.get("generate_report", False),
            artifact_options.get("generate_risk_brief", False),
            artifact_options.get("generate_summary", False),
        ])
        if llm_requested:
            logger.warning(
                "LLM generators requested but GOOGLE_API_KEY not set. "
                "Skipping tasks.xlsx, report.docx, risk_brief.pdf, summary.docx"
            )
            _add_warning("AI-генерация отчётов недоступна. Обратитесь к администратору.")

    return output_files, basic_report_obj, risk_brief_obj, domain_report_obj


def _sync_job_to_db(
    job_id: str,
    domain: str,
    meeting_type: Optional[str],
    user_id: Optional[int],
    project_id: Optional[int],
    source_filename: Optional[str],
    source_size_bytes: Optional[int] = None,
    status: str = "pending",
    is_private: bool = False,
) -> None:
    """
    Create/update TranscriptionJob record in PostgreSQL for stats tracking.

    Called when job is created to sync Redis -> PostgreSQL.
    Uses fresh async session factory to avoid event loop issues.
    """
    from ..shared.database import get_celery_session_factory
    from ..shared.models import TranscriptionJob
    # Import ConstructionProject to ensure SQLAlchemy can resolve FK to construction_projects table
    from ..domains.construction.models import ConstructionProject  # noqa: F401

    async def _async_create():
        session_factory = get_celery_session_factory()
        async with session_factory() as db:
            try:
                # Create new record
                job = TranscriptionJob(
                    job_id=job_id,
                    domain=domain or "construction",
                    meeting_type=meeting_type,
                    status=status,
                    user_id=user_id,
                    project_id=project_id,
                    source_filename=source_filename,
                    source_size_bytes=source_size_bytes,
                    is_private=is_private,
                )
                db.add(job)
                await db.commit()
                logger.info(f"TranscriptionJob record created for {job_id}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to create TranscriptionJob record: {e}")

    _run_async(_async_create())


def _update_job_in_db(
    job_id: str,
    status: str,
    processing_time_seconds: Optional[float] = None,
    audio_duration_seconds: Optional[float] = None,
    segment_count: Optional[int] = None,
    speaker_count: Optional[int] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    flash_input_tokens: int = 0,
    flash_output_tokens: int = 0,
    pro_input_tokens: int = 0,
    pro_output_tokens: int = 0,
    artifacts: Optional[dict] = None,
    error_message: Optional[str] = None,
    error_stage: Optional[str] = None,
) -> None:
    """
    Update TranscriptionJob record in PostgreSQL after processing completes.

    Uses raw asyncpg with a fresh connection per call — avoids both:
    - psycopg2 (not installed in containers)
    - SQLAlchemy async pool "Future attached to different loop" errors in Celery ForkPool
    """
    import asyncpg
    import json
    from ..shared.database import DATABASE_URL

    # Build raw asyncpg DSN from SQLAlchemy URL
    dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    update_data: dict = {
        "status": status,
        "processing_time_seconds": processing_time_seconds,
        "audio_duration_seconds": audio_duration_seconds,
        "segment_count": segment_count,
        "speaker_count": speaker_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "flash_input_tokens": flash_input_tokens,
        "flash_output_tokens": flash_output_tokens,
        "pro_input_tokens": pro_input_tokens,
        "pro_output_tokens": pro_output_tokens,
        "artifacts": json.dumps(artifacts) if artifacts is not None else None,
        "error_message": error_message,
        "error_stage": error_stage,
    }

    if status == "completed":
        update_data["completed_at"] = datetime.now(timezone.utc)
    elif status == "processing":
        update_data["started_at"] = datetime.now(timezone.utc)

    # Remove None values (don't overwrite existing DB fields with None)
    update_data = {k: v for k, v in update_data.items() if v is not None}

    async def _do_update():
        conn = await asyncpg.connect(dsn)
        try:
            keys = list(update_data.keys())
            values = list(update_data.values())
            set_clause = ", ".join(f"{k} = ${i + 1}" for i, k in enumerate(keys))
            values.append(job_id)
            query = f"UPDATE transcription_jobs SET {set_clause} WHERE job_id = ${len(values)}"
            result = await conn.execute(query, *values)
            # result is "UPDATE N" — extract row count
            rows = int(result.split()[-1])
            if rows == 0:
                logger.warning(f"TranscriptionJob {job_id} not found in DB, skipping update")
            else:
                logger.info(f"TranscriptionJob {job_id} updated: {status}")
        finally:
            await conn.close()

    try:
        _run_async(_do_update())
    except Exception as e:
        logger.error(f"Failed to update TranscriptionJob {job_id}: {e}")


def _save_domain_report(
    job_id: str,
    result,
    project_id: int,
    domain_type: str,
    output_files: Optional[Dict[str, str]] = None,
    uploader_id: Optional[int] = None,
    artifact_options: Optional[Dict] = None,
    basic_report: Optional[object] = None,
    risk_brief: Optional[object] = None,
) -> None:
    """
    Save domain-specific report to database after transcription.

    Also saves ReportAnalytics and ReportProblem records from risk_brief data,
    enabling the manager dashboard to show health status, KPIs, and attention items.

    Stores basic_report and risk_brief as JSON for future file regeneration.

    Args:
        job_id: Job identifier
        result: TranscriptionResult from pipeline
        project_id: Project ID
        domain_type: Domain type ('construction', 'hr', etc.)
        uploader_id: User ID for authenticated uploads
        artifact_options: Dict with artifact options including participant_ids
        basic_report: BasicReport object for DB storage
        risk_brief: RiskBrief object for DB storage and dashboard analytics
    """
    from ..shared.database import get_celery_session_factory
    from ..domains.factory import DomainServiceFactory

    artifact_options = artifact_options or {}

    async def _async_save():
        session_factory = get_celery_session_factory()
        async with session_factory() as db:
            try:
                # Log what we're saving
                logger.info(f"Saving domain report for job {job_id}: basic_report={basic_report is not None}, risk_brief={risk_brief is not None}")
                if basic_report is not None:
                    logger.info(f"BasicReport has {len(getattr(basic_report, 'tasks', []))} tasks")

                # Create domain service via factory
                service = DomainServiceFactory.create(domain_type)

                # Generate simple report (no LLM for now)
                report = service.generate_report_simple(
                    result,
                    meeting_date=artifact_options.get("meeting_date")
                )

                # Save to database
                db_report = await service.save_report_to_db(
                    db=db,
                    job_id=job_id,
                    project_id=project_id,
                    report=report,
                    output_files=output_files or {},
                    uploader_id=uploader_id,
                    basic_report=basic_report,
                    risk_brief=risk_brief,
                    participant_ids=artifact_options.get("participant_ids"),
                )

                # Save analytics from risk_brief (enables manager dashboard)
                if risk_brief is not None and domain_type == "construction":
                    try:
                        await service.save_analytics_to_db(
                            db=db,
                            report_id=db_report.id,
                            risk_brief=risk_brief,
                        )
                        logger.info(f"Analytics saved for report {db_report.id}")
                    except Exception as e:
                        logger.error(f"Failed to save analytics (non-fatal): {e}")
                        # Don't fail the whole save if analytics fails

                # Save meeting attendees if provided (construction domain)
                participant_ids = artifact_options.get("participant_ids")
                if participant_ids and domain_type == "construction":
                    try:
                        from ..domains.construction.models import MeetingAttendee

                        for person_id in participant_ids:
                            attendee = MeetingAttendee(
                                report_id=db_report.id,
                                person_id=person_id,
                            )
                            db.add(attendee)
                        logger.info(f"Saved {len(participant_ids)} meeting attendees for report {db_report.id}")
                    except Exception as e:
                        logger.error(f"Failed to save meeting attendees (non-fatal): {e}")
                        # Don't fail the whole save if attendees save fails

                await db.commit()
                logger.info(f"Domain report saved for job {job_id}, project {project_id}")

            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to save domain report for job {job_id}: {e}")
                raise

    # Run async function in sync context
    _run_async(_async_save())


@celery_app.task(
    bind=True,
    name="transcription.process",
)
def process_transcription_task(
    self,
    job_id: str,
    input_file: str,
    output_dir: str,
    languages: List[str],
    skip_diarization: bool = False,
    skip_translation: bool = False,
    skip_emotions: bool = False,
    artifact_options: Optional[dict] = None,
    # Domain linkage parameters
    project_id: Optional[int] = None,
    domain_type: Optional[str] = None,
    meeting_type: Optional[str] = None,
    uploader_id: Optional[int] = None,
    # Email notification
    notify_emails: Optional[List[str]] = None,
) -> dict:
    """
    Celery task for transcription processing.

    Updates job status in Redis throughout processing.

    Args:
        job_id: Unique job identifier
        input_file: Path to input file
        output_dir: Path to output directory
        languages: List of languages to transcribe
        skip_diarization: Skip speaker identification
        skip_translation: Skip translation
        skip_emotions: Skip emotion analysis
        artifact_options: Dict with artifact generation flags

    Returns:
        Dict with processing results
    """
    from ..core.transcription.pipeline import TranscriptionPipeline
    from ..core.transcription.models import TranscriptionRequest
    from ..core.storage.job_store import JobStatus

    store = get_job_store()
    artifact_options = artifact_options or {}

    # Reset token tracker for this job
    from backend.core.llm.token_tracker import reset_tracker
    reset_tracker()

    logger.info(f"Starting transcription job: {job_id}")
    logger.info(f"Input: {input_file}")
    logger.info(f"Languages: {languages}")

    def progress_callback(stage: str, percent: int, message: str):
        """Update job progress in Redis."""
        store.update_progress(job_id, stage, percent, message)
        # Also update Celery task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current_stage": stage,
                "progress_percent": percent,
                "message": message,
            }
        )

    try:
        # Mark as processing
        store.update(job_id, status=JobStatus.PROCESSING)
        _update_job_in_db(job_id=job_id, status="processing")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create request
        request = TranscriptionRequest(
            languages=languages,
            skip_diarization=skip_diarization,
            skip_translation=skip_translation,
            skip_emotions=skip_emotions,
        )

        # Run pipeline (technical processing)
        pipeline = TranscriptionPipeline(progress_callback=progress_callback)
        result = pipeline.process(
            input_file=Path(input_file),
            request=request,
            output_dir=output_path,
        )

        # Save pipeline result to disk for LLM task
        result_json_path = output_path / "pipeline_result.json"
        result_json_path.write_text(result.model_dump_json())
        logger.info(f"Pipeline result saved: {result_json_path}")

        # Generate transcript (no LLM needed)
        output_files = _generate_transcript_artifact(
            result=result,
            output_path=output_path,
            artifact_options=artifact_options,
            progress_callback=progress_callback,
            domain_type=domain_type,
        )

        # Find any additional output files from pipeline
        artifact_patterns = {
            "protocol_docx": "protocol*.docx",
            "protocol_txt": "protocol*.txt",
            "result_json": "result*.json",
        }
        for artifact_type, pattern in artifact_patterns.items():
            if artifact_type not in output_files:
                files = list(output_path.glob(pattern))
                if files:
                    output_files[artifact_type] = str(files[0])

        # Collect GPU token usage (translation stage uses Gemini)
        from backend.core.llm.token_tracker import get_tracker
        gpu_token_usage = get_tracker().usage.as_dict()

        # Check if LLM generators are needed
        if _needs_llm_generators(artifact_options):
            # Dispatch LLM task to separate worker/queue
            progress_callback("domain_generators", 90, "Запуск AI-генерации отчётов...")
            process_llm_generators(
                job_id=job_id,
                output_dir=output_dir,
                artifact_options=artifact_options,
                domain_type=domain_type,
                project_id=project_id,
                uploader_id=uploader_id,
                notify_emails=notify_emails,
                gpu_output_files=output_files,
                processing_time_seconds=result.processing_time_seconds,
                audio_duration_seconds=result.total_duration or None,
                segment_count=result.segment_count,
                speaker_count=getattr(result, 'speaker_count', None),
                language_distribution=result.language_distribution,
                gpu_token_usage=gpu_token_usage,
            )
            logger.info(f"LLM generators dispatched for job {job_id}")
            return {
                "job_id": job_id,
                "status": "processing",
                "message": "Генерация отчётов через AI...",
            }

        # No LLM generators needed — complete job directly
        if domain_type and project_id:
            progress_callback("domain_report", 99, "Сохранение в базу данных...")
            try:
                _save_domain_report(
                    job_id=job_id,
                    result=result,
                    project_id=project_id,
                    domain_type=domain_type,
                    output_files=output_files,
                    uploader_id=uploader_id,
                    artifact_options=artifact_options,
                )
            except Exception as e:
                logger.error(f"Domain report save failed (non-fatal): {e}")

        store.complete(
            job_id=job_id,
            output_files=output_files,
            processing_time=result.processing_time_seconds,
            segment_count=result.segment_count,
            language_distribution=result.language_distribution,
        )

        _update_job_in_db(
            job_id=job_id,
            status="completed",
            processing_time_seconds=result.processing_time_seconds,
            audio_duration_seconds=result.total_duration or None,
            segment_count=result.segment_count,
            speaker_count=getattr(result, 'speaker_count', None),
            **gpu_token_usage,
            artifacts={
                "transcript": "transcript" in output_files,
                "tasks": False,
                "report": False,
                "risk_brief": False,
            },
        )

        logger.info(f"Job {job_id} completed successfully (transcript only)")

        # Send email notification if emails are provided
        if notify_emails:
            progress_callback("email_notification", 100, "Отправка уведомления на почту...")
            email_sent = False
            try:
                from ..core.email.service import send_report_email
                job_data = store.get(job_id)
                project_name = getattr(job_data, 'project_code', None)
                email_sent = send_report_email(
                    recipients=notify_emails,
                    job_id=job_id,
                    project_name=project_name,
                    output_files=output_files,
                )
            except Exception as e:
                logger.error(f"Email notification failed (non-fatal): {e}")
            finally:
                store.update(
                    job_id,
                    status=JobStatus.COMPLETED,
                    current_stage="completed",
                    progress_percent=100,
                    message="Completed successfully" if email_sent else "Completed; email notification failed",
                    completed_at=datetime.now(timezone.utc),
                )

        return {
            "job_id": job_id,
            "status": "completed",
            "processing_time_seconds": result.processing_time_seconds,
            "segment_count": result.segment_count,
            "language_distribution": result.language_distribution,
            "output_files": output_files,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    except SoftTimeLimitExceeded as e:
        error_msg = "Превышено время обработки"
        logger.error(f"Job {job_id}: {error_msg}")
        store.fail(job_id, error_msg)
        _update_job_in_db(job_id=job_id, status="failed", error_message=error_msg, error_stage="timeout")
        from backend.admin.logs.service import log_celery_error
        log_celery_error("transcription.process", e, user_id=uploader_id, context=f"job_id={job_id}")
        return {
            "job_id": job_id,
            "status": "failed",
            "error": error_msg,
        }

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        store.fail(job_id, str(e))
        _update_job_in_db(job_id=job_id, status="failed", error_message=str(e)[:500], error_stage="pipeline")
        from backend.admin.logs.service import log_celery_error
        log_celery_error("transcription.process", e, user_id=uploader_id, context=f"job_id={job_id}")
        raise


def process_llm_generators(
    job_id: str,
    output_dir: str,
    artifact_options: dict,
    domain_type: str = None,
    project_id: int = None,
    uploader_id: int = None,
    notify_emails: list = None,
    gpu_output_files: dict = None,
    processing_time_seconds: float = None,
    audio_duration_seconds: float = None,
    segment_count: int = None,
    speaker_count: int = None,
    language_distribution: dict = None,
    gpu_token_usage: dict = None,
) -> None:
    """
    Dispatch LLM report generation as a Celery chain of 3 independent tasks:

    1. generate_llm_reports_task — LLM calls, returns JSON with paths and serialized models
    2. save_reports_to_db_task — saves to DB, marks job completed
    3. send_email_notification_task — sends email notifications

    Each task retries independently. Email failure does NOT re-trigger LLM generation.
    """
    from celery import chain

    shared_kwargs = {
        "job_id": job_id,
        "output_dir": output_dir,
        "domain_type": domain_type,
    }

    chain(
        generate_llm_reports_task.s(
            **shared_kwargs,
            artifact_options=artifact_options,
        ),
        save_reports_to_db_task.s(
            **shared_kwargs,
            artifact_options=artifact_options,
            project_id=project_id,
            uploader_id=uploader_id,
            gpu_output_files=gpu_output_files or {},
            gpu_token_usage=gpu_token_usage or {},
            processing_time_seconds=processing_time_seconds,
            audio_duration_seconds=audio_duration_seconds,
            segment_count=segment_count,
            speaker_count=speaker_count,
            language_distribution=language_distribution,
        ),
        send_email_notification_task.s(
            job_id=job_id,
            notify_emails=notify_emails,
        ),
    ).apply_async()


@celery_app.task(
    bind=True,
    name="transcription.generate_reports",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def generate_llm_reports_task(
    self,
    job_id: str,
    output_dir: str,
    artifact_options: dict,
    domain_type: str = None,
) -> dict:
    """
    Step 1/3: Run LLM generators (tasks, report, risk_brief).

    Loads pipeline result from disk, calls LLM, returns serialized results.
    Safe to retry — no GPU work is repeated, no DB writes, no emails.
    """
    from ..core.transcription.models import TranscriptionResult
    from backend.core.llm.token_tracker import reset_tracker, get_tracker

    store = get_job_store()
    reset_tracker()

    logger.info(f"[Step 1/3] Starting LLM generators for job: {job_id}")

    def progress_callback(stage: str, percent: int, message: str):
        store.update_progress(job_id, stage, percent, message)
        self.update_state(
            state="PROGRESS",
            meta={"current_stage": stage, "progress_percent": percent, "message": message},
        )

    try:
        output_path = Path(output_dir)
        result_json_path = output_path / "pipeline_result.json"
        result = TranscriptionResult.model_validate_json(result_json_path.read_text())
        logger.info(f"Loaded pipeline result from {result_json_path}")

        progress_callback("llm_generators", 93, "AI-генерация отчётов...")
        generated_artifacts, basic_report_obj, risk_brief_obj, domain_report_obj = _run_domain_generators(
            result=result,
            output_path=output_path,
            artifact_options=artifact_options,
            progress_callback=progress_callback,
            domain_type=domain_type,
            job_id=job_id,
        )

        llm_token_usage = get_tracker().usage.as_dict()

        logger.info(f"[Step 1/3] LLM generators completed for job: {job_id}")
        return {
            "generated_artifacts": generated_artifacts,
            "basic_report_json": basic_report_obj.model_dump_json() if basic_report_obj else None,
            "risk_brief_json": risk_brief_obj.model_dump_json() if risk_brief_obj else None,
            "domain_report_json": domain_report_obj.model_dump_json() if domain_report_obj else None,
            "llm_token_usage": llm_token_usage,
        }

    except Exception as e:
        logger.exception(f"LLM generators failed for job {job_id}: {e}")
        if self.request.retries >= 2:
            store.fail(job_id, f"Ошибка генерации отчётов: {str(e)[:200]}")
            _update_job_in_db(
                job_id=job_id,
                status="failed",
                error_message=f"LLM generators: {str(e)[:300]}",
                error_stage="llm_generators",
            )
            from backend.admin.logs.service import log_celery_error
            log_celery_error("transcription.generate_reports", e, context=f"job_id={job_id}")
        raise


@celery_app.task(
    bind=True,
    name="transcription.save_reports",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def save_reports_to_db_task(
    self,
    llm_result: dict,
    job_id: str,
    output_dir: str,
    artifact_options: dict,
    domain_type: str = None,
    project_id: int = None,
    uploader_id: int = None,
    gpu_output_files: dict = None,
    gpu_token_usage: dict = None,
    processing_time_seconds: float = None,
    audio_duration_seconds: float = None,
    segment_count: int = None,
    speaker_count: int = None,
    language_distribution: dict = None,
) -> dict:
    """
    Step 2/3: Save reports to DB, mark job completed.

    Receives LLM results from step 1. Deserializes Pydantic models,
    saves domain report + analytics, sends critical risk brief alert,
    marks job completed in Redis + PostgreSQL.
    """
    from ..core.transcription.models import TranscriptionResult

    store = get_job_store()
    gpu_output_files = gpu_output_files or {}
    gpu_token_usage = gpu_token_usage or {}

    logger.info(f"[Step 2/3] Saving reports for job: {job_id}")

    def progress_callback(stage: str, percent: int, message: str):
        store.update_progress(job_id, stage, percent, message)
        self.update_state(
            state="PROGRESS",
            meta={"current_stage": stage, "progress_percent": percent, "message": message},
        )

    try:
        generated_artifacts = llm_result.get("generated_artifacts", {})
        basic_report_json = llm_result.get("basic_report_json")
        risk_brief_json = llm_result.get("risk_brief_json")
        llm_token_usage = llm_result.get("llm_token_usage", {})

        # Merge GPU + LLM output files
        output_files = {**gpu_output_files, **generated_artifacts}

        # Deserialize Pydantic models for DB storage
        basic_report_obj = None
        risk_brief_obj = None

        if basic_report_json and domain_type == "construction":
            from ..domains.construction.schemas import BasicReport
            basic_report_obj = BasicReport.model_validate_json(basic_report_json)

        if risk_brief_json and domain_type == "construction":
            from ..domains.construction.schemas import RiskBrief
            risk_brief_obj = RiskBrief.model_validate_json(risk_brief_json)

        # Save domain report to database
        if domain_type and project_id:
            progress_callback("domain_report", 99, "Сохранение в базу данных...")
            output_path = Path(output_dir)
            result_json_path = output_path / "pipeline_result.json"
            result = TranscriptionResult.model_validate_json(result_json_path.read_text())

            try:
                _save_domain_report(
                    job_id=job_id,
                    result=result,
                    project_id=project_id,
                    domain_type=domain_type,
                    output_files=output_files,
                    uploader_id=uploader_id,
                    artifact_options=artifact_options,
                    basic_report=basic_report_obj,
                    risk_brief=risk_brief_obj,
                )

                # Auto-send critical risk brief to project managers
                if risk_brief_obj is not None and domain_type == "construction":
                    try:
                        overall_status = getattr(risk_brief_obj, 'overall_status', None)
                        if hasattr(overall_status, 'value'):
                            status_value = overall_status.value
                        else:
                            status_value = str(overall_status) if overall_status else None

                        if status_value == "critical":
                            from ..core.email.service import email_service
                            project_name = getattr(risk_brief_obj, 'project_name', None)
                            email_service.send_critical_risk_brief_to_managers(
                                project_id=project_id,
                                job_id=job_id,
                                project_name=project_name,
                                risk_brief_status=status_value,
                            )
                            logger.info(f"Critical risk brief notification sent for project {project_id}")
                    except Exception as e:
                        logger.error(f"Critical brief notification failed (non-fatal): {e}")

            except Exception as e:
                logger.error(f"Domain report save failed (non-fatal): {e}")

        # Build meeting_report for Redis (used by CEO dashboard viewer)
        meeting_report_dict = _build_meeting_report(
            domain_type=domain_type,
            domain_report_json=llm_result.get("domain_report_json"),
            basic_report_json=basic_report_json,
        )

        # Mark completed in Redis
        store.complete(
            job_id=job_id,
            output_files=output_files,
            processing_time=processing_time_seconds,
            segment_count=segment_count,
            language_distribution=language_distribution,
        )

        # Store meeting_report separately (complete() doesn't accept it)
        if meeting_report_dict:
            store.update(job_id, meeting_report=meeting_report_dict)

        # Combine GPU + LLM token usage
        combined_tokens = {
            k: gpu_token_usage.get(k, 0) + llm_token_usage.get(k, 0)
            for k in llm_token_usage
        }

        _update_job_in_db(
            job_id=job_id,
            status="completed",
            processing_time_seconds=processing_time_seconds,
            audio_duration_seconds=audio_duration_seconds,
            segment_count=segment_count,
            speaker_count=speaker_count,
            **combined_tokens,
            artifacts={
                "transcript": "transcript" in output_files,
                "tasks": "tasks" in output_files,
                "report": "report" in output_files,
                "risk_brief": "risk_brief" in output_files,
            },
        )

        logger.info(f"[Step 2/3] Reports saved for job: {job_id}")
        return {
            "job_id": job_id,
            "output_files": output_files,
        }

    except Exception as e:
        logger.exception(f"Save reports failed for job {job_id}: {e}")
        if self.request.retries >= 2:
            store.fail(job_id, f"Ошибка сохранения отчётов: {str(e)[:200]}")
            _update_job_in_db(
                job_id=job_id,
                status="failed",
                error_message=f"Save reports: {str(e)[:300]}",
                error_stage="save_reports",
            )
            from backend.admin.logs.service import log_celery_error
            log_celery_error(
                "transcription.save_reports", e,
                user_id=uploader_id, context=f"job_id={job_id}",
            )
        raise


@celery_app.task(
    bind=True,
    name="transcription.send_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def send_email_notification_task(
    self,
    db_result: dict,
    job_id: str,
    notify_emails: list = None,
) -> dict:
    """
    Step 3/3: Send email notifications.

    Receives output_files from step 2. Job is already marked completed —
    email failure is independent and does NOT affect job status.
    """
    from ..core.storage.job_store import JobStatus

    if not notify_emails:
        return {"job_id": job_id, "email_sent": False, "reason": "no_recipients"}

    store = get_job_store()
    output_files = db_result.get("output_files", {})

    logger.info(f"[Step 3/3] Sending email for job: {job_id}")

    store.update_progress(job_id, "email_notification", 100, "Отправка уведомления на почту...")

    email_sent = False
    try:
        from ..core.email.service import send_report_email
        job_data = store.get(job_id)
        project_name = getattr(job_data, 'project_code', None)
        email_sent = send_report_email(
            recipients=notify_emails,
            job_id=job_id,
            project_name=project_name,
            output_files=output_files,
        )
    except Exception as e:
        logger.error(f"Email notification failed for job {job_id}: {e}")
        raise
    finally:
        store.update(
            job_id,
            status=JobStatus.COMPLETED,
            current_stage="completed",
            progress_percent=100,
            message="Completed successfully" if email_sent else "Completed; email notification failed",
            completed_at=datetime.now(timezone.utc),
        )

    logger.info(f"[Step 3/3] Email sent for job: {job_id}")
    return {"job_id": job_id, "email_sent": email_sent}


@celery_app.task(name="transcription.cleanup")
def cleanup_job_files(job_id: str, upload_dir: str, output_dir: str, keep_output: bool = True):
    """
    Cleanup job files after processing.

    Args:
        job_id: Job identifier
        upload_dir: Upload directory to clean
        output_dir: Output directory
        keep_output: Whether to keep output files
    """
    import shutil

    # Remove upload directory
    upload_path = Path(upload_dir) / job_id
    if upload_path.exists():
        shutil.rmtree(upload_path)
        logger.info(f"Cleaned up upload dir: {upload_path}")

    # Optionally remove output
    if not keep_output:
        output_path = Path(output_dir) / job_id
        if output_path.exists():
            shutil.rmtree(output_path)
            logger.info(f"Cleaned up output dir: {output_path}")


@celery_app.task(
    bind=True,
    name="transcription.process_text",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def process_text_task(
    self,
    job_id: str,
    input_file: str,
    output_dir: str,
    artifact_options: dict = None,
    domain_type: str = None,
    project_id: int = None,
    uploader_id: int = None,
    notify_emails: list = None,
    existing_output_files: dict = None,
):
    """
    Celery task for processing text files (docx, txt).
    Generates reports via LLM without transcription.
    """
    import asyncio
    import os
    from pathlib import Path

    logger.info(f"Starting text processing job: {job_id}")
    logger.info(f"Input: {input_file}")

    # Create job record in PostgreSQL for history tracking
    input_path = Path(input_file)
    source_filename = input_path.name
    try:
        source_size_bytes = os.path.getsize(input_file)
    except Exception:
        source_size_bytes = None

    _sync_job_to_db(
        job_id=job_id,
        domain=domain_type or "construction",
        meeting_type=None,
        user_id=uploader_id,
        project_id=project_id,
        source_filename=source_filename,
        source_size_bytes=source_size_bytes,
        status="processing",
    )

    # Import the async function from API routes
    from ..api.routes.transcription import run_text_report_generation

    try:
        # Run async function in event loop
        asyncio.run(
            run_text_report_generation(
                job_id=job_id,
                input_file=Path(input_file),
                output_dir=Path(output_dir),
                artifact_options=artifact_options,
                domain_type=domain_type,
                project_id=project_id,
                uploader_id=uploader_id,
                notify_emails=notify_emails,
                existing_output_files=existing_output_files,
            )
        )
    except Exception as e:
        logger.exception(f"Text processing failed for job {job_id}: {e}")
        if self.request.retries >= 2:
            from backend.admin.logs.service import log_celery_error
            log_celery_error(
                "transcription.process_text", e,
                user_id=uploader_id, context=f"job_id={job_id}",
            )
        raise

    logger.info(f"Text processing job {job_id} completed")
    return {"job_id": job_id, "status": "completed"}
