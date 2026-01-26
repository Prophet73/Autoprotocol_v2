"""
API маршруты транскрипции с хранением задач в Redis.

Эндпоинты:
- POST /transcribe — загрузка файла и запуск транскрипции
- GET /transcribe/{job_id}/status — статус обработки
- GET /transcribe/{job_id} — результат обработки
- GET /transcribe/{job_id}/download/{file_type} — скачивание файлов
- GET /transcribe — список задач
- DELETE /transcribe/{job_id} — отмена задачи
"""
import os
import re
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Header, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import (
    JobResponse,
    JobStatusResponse,
    JobResultResponse,
)
from ...core.storage import get_job_store, JobStore
from ...core.utils.file_security import validate_file_path
from ...core.storage.job_store import JobData
from ...core.transcription.models import JobStatus
from ...tasks.transcription import process_transcription_task, _sync_job_to_db, _update_job_in_db, _save_domain_report
from ...core.utils.text_extraction import is_text_file, extract_text_from_file
from ...shared.database import get_db
from ...domains.construction.project_service import ProjectService
from ...core.auth.dependencies import get_optional_user
from ...shared.models import User, TranscriptionJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["Транскрипция"])


def _extract_media_creation_date(file_path: Path) -> Optional[str]:
    """
    Extract creation date from media file metadata using FFprobe.

    Returns date in YYYY-MM-DD format or None if not found.
    """
    import subprocess
    import json

    try:
        # Run ffprobe to get metadata
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path)
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        tags = data.get("format", {}).get("tags", {})

        # Try various date fields (case-insensitive)
        date_fields = ["creation_time", "date", "DATE", "Creation Time", "CREATION_TIME"]
        for field in date_fields:
            if field in tags:
                date_str = tags[field]
                # Parse ISO format: 2025-12-17T16:35:23.000000Z
                try:
                    if "T" in date_str:
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    return dt.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    continue

        return None
    except Exception as e:
        logger.debug(f"Could not extract media creation date: {e}")
        return None

# Email validation regex (RFC 5322 simplified)
_EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)


def validate_email_list(emails_str: Optional[str]) -> list[str]:
    """
    Validate and parse comma-separated email list.

    Args:
        emails_str: Comma-separated email addresses.

    Returns:
        List of validated email addresses.

    Raises:
        HTTPException 400: If any email is invalid.
    """
    if not emails_str:
        return []

    emails = []
    for email in emails_str.split(","):
        email = email.strip()
        if not email:
            continue

        if not _EMAIL_REGEX.match(email):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid email format: {email}"
            )

        # Additional security: prevent email header injection
        if '\n' in email or '\r' in email:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid characters in email: {email}"
            )

        emails.append(email)

    return emails

# Storage paths - use DATA_DIR env or default to /data (Docker)
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"


def get_store() -> JobStore:
    """Get job store instance."""
    return get_job_store()


# =============================================================================
# Helper functions to reduce code duplication
# =============================================================================

def _create_progress_callback(store: JobStore, job_id: str):
    """Create a progress callback function for job updates."""
    def progress_callback(stage: str, percent: int, message: str):
        store.update_progress(job_id, stage, percent, message)
    return progress_callback


def _start_job_processing(store: JobStore, job_id: str):
    """Mark job as processing in store and database."""
    store.update(job_id, status=JobStatus.PROCESSING)
    _update_job_in_db(job_id=job_id, status="processing")


def _complete_job(
    store: JobStore,
    job_id: str,
    output_files: dict,
    processing_time: float = 0,
    segment_count: int = 0,
    speaker_count: int = None,
    language_distribution: dict = None,
    audio_duration_seconds: float = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    all_output_files: dict = None,
):
    """Mark job as completed in store and database.

    Args:
        output_files: Files available for user download (shown in UI).
        all_output_files: All generated files for artifacts tracking.
                          Defaults to output_files if not specified.
    """
    artifacts_source = all_output_files if all_output_files is not None else output_files
    store.complete(
        job_id=job_id,
        output_files=output_files,
        processing_time=processing_time,
        segment_count=segment_count,
        language_distribution=language_distribution or {},
    )
    _update_job_in_db(
        job_id=job_id,
        status="completed",
        processing_time_seconds=processing_time,
        audio_duration_seconds=audio_duration_seconds,
        segment_count=segment_count,
        speaker_count=speaker_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        artifacts={
            "transcript": "transcript" in artifacts_source,
            "tasks": "tasks" in artifacts_source,
            "report": "report" in artifacts_source,
            "analysis": "analysis" in artifacts_source,
        },
    )


def _fail_job(store: JobStore, job_id: str, error: Exception, stage: str = "processing"):
    """Mark job as failed in store and database."""
    logger.exception(f"Job {job_id} failed: {error}")
    store.fail(job_id, str(error))
    _update_job_in_db(
        job_id=job_id,
        status="failed",
        error_message=str(error)[:500],
        error_stage=stage,
    )


def _send_notification_email(store: JobStore, job_id: str, notify_emails: list, output_files: dict):
    """Send email notification if emails are provided."""
    if not notify_emails:
        return
    try:
        from ...core.email.service import send_report_email
        job_data = store.get(job_id)
        project_name = getattr(job_data, 'project_code', None)
        send_report_email(
            recipients=notify_emails,
            job_id=job_id,
            project_name=project_name,
            output_files=output_files,
        )
        logger.info(f"Email notification sent to {notify_emails}")
    except Exception as e:
        logger.error(f"Email notification failed (non-fatal): {e}")


@router.post(
    "",
    response_model=JobResponse,
    summary="Загрузить файл и начать транскрипцию",
    description="Загружает аудио/видео файл и запускает процесс транскрипции. Возвращает job_id для отслеживания прогресса.",
)
async def create_transcription(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    file: UploadFile = File(..., description="Аудио или видео файл (WAV, MP3, MP4, MKV и др.)"),
    languages: str = Form(default="ru", description="Языки через запятую (ru, zh, en). Пример: ru,zh"),
    skip_diarization: bool = Form(default=False, description="Пропустить определение спикеров"),
    skip_translation: bool = Form(default=False, description="Пропустить перевод на русский"),
    skip_emotions: bool = Form(default=False, description="Пропустить анализ эмоций"),
    # Project linkage (for construction domain)
    project_code: Optional[str] = Form(default=None, description="4-значный код проекта для анонимной загрузки"),
    # Meeting type (for HR/IT domains)
    meeting_type: Optional[str] = Form(default=None, description="Тип встречи (recruitment, standup, и т.д.)"),
    # Meeting date (optional)
    meeting_date: Optional[str] = Form(default=None, description="Дата встречи (YYYY-MM-DD)"),
    # Guest ID for anonymous users (from X-Guest-ID header)
    x_guest_id: Optional[str] = Header(default=None, alias="X-Guest-ID", description="UUID гостя для анонимной загрузки"),
    # Domain artifact options (ДПУ)
    generate_transcript: bool = Form(default=True, description="Создать транскрипт (transcript.docx)"),
    generate_tasks: bool = Form(default=False, description="Извлечь задачи через LLM (tasks.xlsx)"),
    generate_report: bool = Form(default=False, description="Создать отчёт через LLM (report.docx)"),
    generate_analysis: bool = Form(default=False, description="Генерировать менеджерский бриф для дашборда"),
    generate_risk_brief: bool = Form(default=False, description="Создать риск-бриф (risk_brief.pdf)"),
    # Email notification
    notify_emails: Optional[str] = Form(default=None, description="Email адреса для уведомления (через запятую)"),
    # Meeting participants (person IDs, comma-separated)
    participant_ids: Optional[str] = Form(default=None, description="ID участников совещания через запятую"),
):
    """
    ## Загрузка файла и запуск транскрипции

    Поддерживаемые форматы:
    - **Аудио**: WAV, MP3, FLAC, OGG, M4A
    - **Видео**: MP4, MKV, AVI, MOV, WEBM

    ### Языки
    Укажите языки через запятую. Система выберет лучший вариант для каждого сегмента:
    - `ru` — русский
    - `zh` — китайский
    - `en` — английский

    ### Этапы обработки
    1. Извлечение аудио (FFmpeg)
    2. Голосовая активность (VAD)
    3. Транскрипция (WhisperX)
    4. Диаризация (pyannote)
    5. Перевод (Gemini AI)
    6. Анализ эмоций
    7. Генерация отчётов

    Возвращает `job_id` для отслеживания прогресса.
    """
    store = get_store()

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Parse languages
    lang_list = [lang.strip() for lang in languages.split(",") if lang.strip()]
    if not lang_list:
        lang_list = ["ru"]

    # Validate project code if provided
    project_id = None
    tenant_id = None
    domain_type = None
    project_name = None  # For risk brief header
    if project_code:
        project_service = ProjectService(db)
        validation = await project_service.validate_code(project_code)
        if not validation.valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid project code: {validation.message}"
            )
        project_id = validation.project_id
        tenant_id = validation.tenant_id
        domain_type = getattr(validation, 'domain_type', 'construction')
        project_name = getattr(validation, 'project_name', None)
        logger.info(f"Job linked to project {project_id} ({project_name}) via code {project_code}")

    # Determine uploader identity
    uploader_id = current_user.id if current_user else None
    # Use guest_uid only for anonymous users
    guest_uid = x_guest_id if not current_user else None

    # Create directories
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    job_upload_dir = UPLOAD_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)

    input_file = job_upload_dir / file.filename
    with open(input_file, "wb") as f:
        shutil.copyfileobj(file.file, f)

    logger.info(f"File uploaded: {input_file}")

    # Manager brief is always generated for construction domain
    generate_analysis_effective = (domain_type or "construction") == "construction"

    # Create job record in Redis
    now = datetime.now()
    # Parse and validate notify emails
    notify_emails_list = validate_email_list(notify_emails)

    # Parse participant IDs
    participant_ids_list = []
    if participant_ids:
        try:
            participant_ids_list = [int(pid.strip()) for pid in participant_ids.split(",") if pid.strip()]
            logger.info(f"[DEBUG] Parsed participant_ids: {participant_ids} -> {participant_ids_list}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid participant_ids format")
    else:
        logger.info("[DEBUG] No participant_ids provided in form data")

    job_data = JobData(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=now,
        updated_at=now,
        input_file=str(input_file),
        languages=lang_list,
        project_id=project_id,
        project_code=project_code,
        tenant_id=tenant_id,
        domain_type=domain_type,
        guest_uid=guest_uid,
        uploader_id=uploader_id,
        skip_diarization=skip_diarization,
        skip_translation=skip_translation,
        skip_emotions=skip_emotions,
        generate_transcript=generate_transcript,
        generate_tasks=generate_tasks,
        generate_report=generate_report,
        generate_analysis=generate_analysis_effective,
        generate_risk_brief=generate_risk_brief,
        notify_emails=notify_emails_list,
    )

    store.create(job_data)

    # Create TranscriptionJob record in PostgreSQL for stats tracking
    try:
        file_size = input_file.stat().st_size if input_file.exists() else None
        _sync_job_to_db(
            job_id=job_id,
            domain=domain_type or "construction",
            meeting_type=meeting_type,
            user_id=uploader_id,
            guest_uid=guest_uid,
            project_id=project_id,
            source_filename=file.filename,
            source_size_bytes=file_size,
            status="pending",
        )
    except Exception as e:
        logger.warning(f"Failed to sync job to DB (non-fatal): {e}")

    # Auto-fill meeting date from file metadata if not provided
    effective_meeting_date = meeting_date
    if not effective_meeting_date:
        # Try to extract from media file internal metadata (creation_time)
        effective_meeting_date = _extract_media_creation_date(input_file)
        if effective_meeting_date:
            logger.info(f"Auto-filled meeting date from media metadata: {effective_meeting_date}")
        else:
            # Fallback: use current date (file mtime is upload time, not original)
            effective_meeting_date = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"Using current date as meeting date: {effective_meeting_date}")

    # Artifact options for task
    artifact_options = {
        "generate_transcript": generate_transcript,
        "generate_tasks": generate_tasks,
        "generate_report": generate_report,
        "generate_analysis": generate_analysis_effective,
        "generate_risk_brief": generate_risk_brief,
        "meeting_type": meeting_type,
        "meeting_date": effective_meeting_date,
        "participant_ids": participant_ids_list,
        "project_name": project_name,  # For risk brief header
        "project_code": project_code,  # For risk brief header
    }
    logger.info(f"[DEBUG] artifact_options participant_ids: {artifact_options.get('participant_ids')}")

    # Check if this is a text file (direct report generation without transcription)
    if is_text_file(file.filename):
        logger.info(f"Text file detected: {file.filename}, using direct report generation")
        # Run direct report generation in background (no GPU needed)
        background_tasks.add_task(
            run_text_report_generation,
            job_id=job_id,
            input_file=input_file,
            output_dir=OUTPUT_DIR / job_id,
            artifact_options=artifact_options,
            domain_type=domain_type,
            project_id=project_id,
            guest_uid=guest_uid,
            uploader_id=uploader_id,
            notify_emails=notify_emails_list,
        )
        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            message="Text file queued for report generation",
        )

    # Queue Celery task for audio/video files
    try:
        process_transcription_task.delay(
            job_id=job_id,
            input_file=str(input_file),
            output_dir=str(OUTPUT_DIR / job_id),
            languages=lang_list,
            skip_diarization=skip_diarization,
            skip_translation=skip_translation,
            skip_emotions=skip_emotions,
            artifact_options=artifact_options,
            # Domain-specific parameters
            project_id=project_id,
            domain_type=domain_type,
            meeting_type=meeting_type,
            guest_uid=guest_uid,
            uploader_id=uploader_id,
            # Email notification
            notify_emails=notify_emails_list,
        )
        logger.info(f"Job {job_id} queued to Celery")
    except Exception as e:
        logger.warning(f"Celery unavailable, using background task: {e}")
        # Fallback to background task (for development without Celery)
        background_tasks.add_task(
            run_transcription_background,
            job_id=job_id,
            input_file=input_file,
            output_dir=OUTPUT_DIR / job_id,
            languages=lang_list,
            skip_diarization=skip_diarization,
            skip_translation=skip_translation,
            skip_emotions=skip_emotions,
            artifact_options=artifact_options,
            # Domain linkage
            project_id=project_id,
            domain_type=domain_type,
            guest_uid=guest_uid,
            uploader_id=uploader_id,
            notify_emails=notify_emails_list,
        )

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=now,
        message="Job queued for processing",
    )


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Получить статус задачи",
    description="Возвращает текущий статус обработки, этап и процент выполнения.",
)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    ## Статус задачи

    Возвращает:
    - **status** — статус (pending, processing, completed, failed)
    - **current_stage** — текущий этап обработки
    - **progress_percent** — процент выполнения (0-100)
    - **message** — описание текущего действия
    """
    store = get_store()
    job = store.get(job_id)

    result = await db.execute(
        select(TranscriptionJob).where(TranscriptionJob.job_id == job_id)
    )
    db_job = result.scalar_one_or_none()

    if job is None and db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if db_job and job and job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
        if db_job.status == "completed":
            store.update(
                job_id,
                status=JobStatus.COMPLETED,
                current_stage="completed",
                progress_percent=100,
                message="Completed successfully",
                completed_at=db_job.completed_at or datetime.now(),
            )
        elif db_job.status == "failed":
            store.update(
                job_id,
                status=JobStatus.FAILED,
                current_stage="failed",
                progress_percent=job.progress_percent or 0,
                message=f"Failed: {db_job.error_message}" if db_job.error_message else "Failed",
                error=db_job.error_message,
                completed_at=db_job.completed_at or datetime.now(),
            )
        job = store.get(job_id)

    if job is None and db_job:
        status = db_job.status
        current_stage = (
            "completed" if status == "completed"
            else "failed" if status == "failed"
            else "processing"
        )
        progress_percent = 100 if status == "completed" else 0
        message = (
            "Completed successfully" if status == "completed"
            else db_job.error_message if status == "failed"
            else "Processing..."
        )
        updated_at = db_job.completed_at or db_job.started_at or db_job.created_at

        return JobStatusResponse(
            job_id=db_job.job_id,
            status=status,
            current_stage=current_stage,
            progress_percent=progress_percent,
            message=message,
            created_at=db_job.created_at,
            updated_at=updated_at,
            completed_at=db_job.completed_at,
            error=db_job.error_message,
        )

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        message=job.message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@router.get(
    "/{job_id}",
    response_model=JobResultResponse,
    summary="Получить результат задачи",
    description="Возвращает результат завершённой задачи: статистику, список файлов и метаданные.",
)
async def get_job_result(job_id: str):
    """
    ## Результат задачи

    Доступен только для завершённых задач (status=completed).

    Возвращает:
    - **segment_count** — количество сегментов
    - **language_distribution** — распределение по языкам
    - **output_files** — словарь доступных файлов для скачивания
    - **processing_time_seconds** — время обработки
    """
    store = get_store()
    job = store.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.PENDING:
        raise HTTPException(status_code=202, detail="Job is pending")

    if job.status == JobStatus.PROCESSING:
        raise HTTPException(status_code=202, detail="Job is still processing")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=job.error or "Job failed")

    return JobResultResponse(
        job_id=job.job_id,
        status=job.status,
        source_file=Path(job.input_file).name,
        processing_time_seconds=job.processing_time or 0,
        segment_count=job.segment_count or 0,
        language_distribution=job.language_distribution or {},
        output_files=job.output_files or {},
        completed_at=job.completed_at or datetime.now(),
    )


@router.get(
    "/{job_id}/download/{file_type}",
    summary="Скачать файл результата",
    description="Скачивание результирующего файла по типу.",
)
async def download_result(job_id: str, file_type: str):
    """
    ## Скачивание файла

    Типы файлов (file_type):
    - **transcript** — транскрипт (DOCX)
    - **tasks** — задачи (XLSX)
    - **report** — отчёт (DOCX)
    - **analysis** — менеджерский бриф (DOCX)
    - **risk_brief** — риск-бриф (PDF)
    - **protocol_docx** — протокол Word
    - **protocol_txt** — протокол текст
    - **result_json** — сырые данные JSON
    """
    if file_type == "all":
        return await download_all_results(job_id)

    store = get_store()
    job = store.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    output_files = job.output_files or {}
    if file_type == "analysis" and "analysis" not in output_files and "risk_brief" in output_files:
        file_type = "risk_brief"
    if file_type not in output_files:
        raise HTTPException(status_code=404, detail=f"File type '{file_type}' not found")

    # Validate file path is within OUTPUT_DIR (prevents path traversal)
    file_path = validate_file_path(
        file_path=output_files[file_type],
        allowed_dir=OUTPUT_DIR,
        must_exist=True
    )

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.get(
    "/{job_id}/download/all",
    summary="Скачать все файлы результата",
    description="Скачивание всех доступных файлов одним архивом.",
)
async def download_all_results(job_id: str):
    """Download all available files for a job as a zip archive."""
    import zipfile
    import tempfile

    store = get_store()
    job = store.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    output_files = job.output_files or {}
    if not output_files:
        raise HTTPException(status_code=404, detail="No files available to download")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_type, file_path_str in output_files.items():
            file_path = validate_file_path(
                file_path=file_path_str,
                allowed_dir=OUTPUT_DIR,
                must_exist=True
            )
            zf.write(file_path, arcname=file_path.name)

    filename = f"{job_id}_files.zip"
    return FileResponse(
        path=tmp.name,
        filename=filename,
        media_type="application/zip",
    )


@router.get(
    "",
    summary="Список задач",
    description="Возвращает список последних задач с базовой информацией.",
)
async def list_jobs(
    limit: int = Query(default=50, le=100, description="Максимальное количество задач"),
    x_guest_id: Optional[str] = Header(default=None, alias="X-Guest-ID", description="UUID гостя для фильтрации"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ## История задач

    Возвращает список последних задач, отсортированных по дате создания.

    **Фильтрация:**
    - Авторизованные пользователи видят свои задачи
    - Гости (с X-Guest-ID) видят только свои задачи
    - Без идентификации — пустой список

    Параметры:
    - **limit** — максимальное количество (по умолчанию 50)
    """
    store = get_store()

    # Authenticated users: read history from PostgreSQL
    if current_user:
        result = await db.execute(
            select(TranscriptionJob)
            .where(TranscriptionJob.user_id == current_user.id)
            .order_by(desc(TranscriptionJob.created_at))
            .limit(limit)
        )
        jobs = result.scalars().all()

        response_jobs = []
        for job in jobs:
            job_state = store.get(job.job_id)
            status_value = job.status
            progress_percent = 100 if job.status == "completed" else 0
            message = None
            project_code = None

            if job_state:
                status_value = job_state.status.value if hasattr(job_state.status, "value") else job_state.status
                progress_percent = job_state.progress_percent
                message = job_state.message
                project_code = getattr(job_state, "project_code", None)
                if status_value != job.status:
                    _update_job_in_db(job_id=job.job_id, status=status_value)
            elif job.status == "failed":
                message = job.error_message

            response_jobs.append({
                "job_id": job.job_id,
                "status": status_value,
                "created_at": job.created_at.isoformat(),
                "source_file": job.source_filename or "",
                "progress_percent": progress_percent,
                "message": message,
                "project_code": project_code,
            })

        return {"jobs": response_jobs}

    # Guests: prefer DB history (if guest_uid is stored), fallback to Redis by guest ID
    if x_guest_id:
        result = await db.execute(
            select(TranscriptionJob)
            .where(TranscriptionJob.guest_uid == x_guest_id)
            .order_by(desc(TranscriptionJob.created_at))
            .limit(limit)
        )
        jobs = result.scalars().all()

        if jobs:
            response_jobs = []
            for job in jobs:
                job_state = store.get(job.job_id)
                status_value = job.status
                progress_percent = 100 if job.status == "completed" else 0
                message = None

                if job_state:
                    status_value = job_state.status.value if hasattr(job_state.status, "value") else job_state.status
                    progress_percent = job_state.progress_percent
                    message = job_state.message
                    if status_value != job.status:
                        _update_job_in_db(job_id=job.job_id, status=status_value)
                elif job.status == "failed":
                    message = job.error_message

                response_jobs.append({
                    "job_id": job.job_id,
                    "status": status_value,
                    "created_at": job.created_at.isoformat(),
                    "source_file": job.source_filename or "",
                    "progress_percent": progress_percent,
                    "message": message,
                    "project_code": None,
                })

            return {"jobs": response_jobs}

    all_jobs = store.list_jobs(limit=limit * 2)  # Fetch more to filter
    jobs = [
        job for job in all_jobs
        if x_guest_id and getattr(job, 'guest_uid', None) == x_guest_id
    ][:limit] if x_guest_id else []

    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "source_file": Path(job.input_file).name,
                "progress_percent": job.progress_percent,
                "message": job.message,
                "project_code": getattr(job, 'project_code', None),
            }
            for job in jobs
        ]
    }


@router.delete(
    "/{job_id}",
    summary="Отменить задачу",
    description="Отменяет задачу в статусе pending или processing.",
)
async def cancel_job(job_id: str):
    """
    ## Отмена задачи

    Отменяет выполнение задачи. Работает только для задач в статусе:
    - **pending** — ожидает в очереди
    - **processing** — выполняется

    Завершённые или уже отменённые задачи отменить нельзя.
    """
    store = get_store()
    job = store.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )

    # Mark as failed with cancellation message
    store.fail(job_id, "Cancelled by user")

    # Try to revoke Celery task
    try:
        from ...tasks.celery_app import celery_app

        # Revoke the task
        celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
        logger.info(f"Job {job_id} cancelled and task revoked")
    except Exception as e:
        logger.warning(f"Could not revoke Celery task: {e}")

    return {"success": True, "message": "Job cancelled"}


async def run_transcription_background(
    job_id: str,
    input_file: Path,
    output_dir: Path,
    languages: list,
    skip_diarization: bool,
    skip_translation: bool,
    skip_emotions: bool,
    artifact_options: dict = None,
    project_id: Optional[int] = None,
    domain_type: Optional[str] = None,
    guest_uid: Optional[str] = None,
    uploader_id: Optional[int] = None,
    notify_emails: list = None,
):
    """Background task for transcription (fallback when Celery unavailable)."""
    from ...core.transcription.pipeline import TranscriptionPipeline
    from ...core.transcription.models import TranscriptionRequest

    store = get_store()
    artifact_options = artifact_options or {}
    progress_callback = _create_progress_callback(store, job_id)

    try:
        _start_job_processing(store, job_id)

        request = TranscriptionRequest(
            languages=languages,
            skip_diarization=skip_diarization,
            skip_translation=skip_translation,
            skip_emotions=skip_emotions,
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        pipeline = TranscriptionPipeline(progress_callback=progress_callback)
        result = pipeline.process(
            input_file=input_file,
            request=request,
            output_dir=output_dir,
        )

        # Run domain generators (same logic as Celery task)
        from ...tasks.transcription import _run_domain_generators, _save_domain_report

        output_files = {}
        generated_artifacts = _run_domain_generators(
            result=result,
            output_path=output_dir,
            artifact_options=artifact_options,
            progress_callback=progress_callback,
        )
        output_files.update(generated_artifacts)

        # Save domain report to database if project is linked
        if domain_type and project_id:
            progress_callback("domain_report", 99, "Сохранение в базу данных...")
            try:
                _save_domain_report(
                    job_id=job_id,
                    result=result,
                    project_id=project_id,
                    domain_type=domain_type,
                    output_files=output_files,
                    guest_uid=guest_uid,
                    uploader_id=uploader_id,
                )
            except Exception as e:
                logger.error(f"Domain report save failed (non-fatal): {e}")

        # Find additional pipeline output files
        artifact_patterns = {
            "protocol_docx": "protocol*.docx",
            "protocol_txt": "protocol*.txt",
            "result_json": "result*.json",
        }

        for artifact_type, pattern in artifact_patterns.items():
            if artifact_type not in output_files:
                files = list(output_dir.glob(pattern))
                if files:
                    output_files[artifact_type] = str(files[0])

        # Mark completed
        _complete_job(
            store=store,
            job_id=job_id,
            output_files=output_files,
            processing_time=result.processing_time_seconds,
            segment_count=result.segment_count,
            speaker_count=getattr(result, "speaker_count", None),
            language_distribution=result.language_distribution,
            audio_duration_seconds=getattr(result, "audio_duration_seconds", None),
            input_tokens=getattr(result, "input_tokens", 0),
            output_tokens=getattr(result, "output_tokens", 0),
        )
        logger.info(f"Job {job_id} completed successfully")

        _send_notification_email(store, job_id, notify_emails, output_files)

    except Exception as e:
        _fail_job(store, job_id, e, "processing")


async def run_text_report_generation(
    job_id: str,
    input_file: Path,
    output_dir: Path,
    artifact_options: dict = None,
    domain_type: str = None,
    project_id: Optional[int] = None,
    guest_uid: Optional[str] = None,
    uploader_id: Optional[int] = None,
    notify_emails: list = None,
):
    """
    Background task for generating reports from text files (.txt, .docx).
    Bypasses transcription pipeline - directly generates LLM-based reports.
    """
    import os
    from datetime import datetime
    from dataclasses import dataclass, field
    from typing import Dict, List

    store = get_store()
    artifact_options = artifact_options or {}
    progress_callback = _create_progress_callback(store, job_id)

    try:
        _start_job_processing(store, job_id)
        progress_callback("text_extraction", 10, "Извлечение текста из файла...")

        # Extract text from file
        text_content = extract_text_from_file(input_file)
        if not text_content:
            raise ValueError(f"Failed to extract text from {input_file}")

        logger.info(f"Extracted {len(text_content)} characters from {input_file.name}")
        progress_callback("text_extraction", 20, f"Извлечено {len(text_content)} символов")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a minimal "fake" TranscriptionResult for generators
        @dataclass
        class MinimalSegment:
            text: str
            speaker: str = "Speaker"
            start: float = 0.0
            end: float = 0.0
            language: str = "ru"
            translated_text: str = ""

            @property
            def start_formatted(self) -> str:
                """Format start time as MM:SS."""
                mins = int(self.start // 60)
                secs = int(self.start % 60)
                return f"{mins:02d}:{secs:02d}"

        @dataclass
        class MinimalMetadata:
            source_file: str = ""
            duration: float = 0.0

            @property
            def duration_formatted(self) -> str:
                mins = int(self.duration // 60)
                secs = int(self.duration % 60)
                return f"{mins:02d}:{secs:02d}"

        @dataclass
        class MinimalSpeaker:
            speaker_id: str
            total_time_formatted: str = "00:00"
            dominant_emotion: Optional[object] = None

        @dataclass
        class MinimalResult:
            source_file: str = ""
            segments: List[MinimalSegment] = field(default_factory=list)
            processing_time_seconds: float = 0.0
            segment_count: int = 0
            language_distribution: Dict[str, int] = field(default_factory=dict)
            speakers: Dict[str, MinimalSpeaker] = field(default_factory=dict)

            @property
            def metadata(self) -> MinimalMetadata:
                return MinimalMetadata(source_file=self.source_file, duration=0.0)

            @property
            def speaker_count(self) -> int:
                return len(self.speakers)

            def get_full_text(self) -> str:
                return "\n".join(seg.text for seg in self.segments)

            @property
            def speakers_list(self) -> list:
                """Get speakers as list for iteration."""
                return list(self.speakers.values())

            def to_plain_text(self) -> str:
                """Convert to plain text for LLM analysis."""
                lines = []
                for seg in self.segments:
                    lines.append(f"[{seg.start_formatted}] {seg.speaker}: {seg.text}")
                return "\n".join(lines)

        # Split text into paragraphs as "segments"
        paragraphs = [p.strip() for p in text_content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text_content]

        segments = [MinimalSegment(text=p, speaker="Speaker 1") for p in paragraphs]
        result = MinimalResult(
            source_file=input_file.name,
            segments=segments,
            segment_count=len(segments),
            language_distribution={"ru": len(segments)},
            speakers={"Speaker 1": MinimalSpeaker(speaker_id="Speaker 1")},
        )

        # Check if Gemini is configured
        has_gemini = bool(os.getenv("GOOGLE_API_KEY"))
        output_files = {}

        if not has_gemini:
            raise ValueError("GOOGLE_API_KEY not configured - cannot generate LLM reports")

        progress_callback("llm_generation", 30, "Генерация документов...")

        # Import generators based on domain
        domain = domain_type or "construction"
        ai_analysis = None  # Will be populated if generate_analysis is called (construction only)

        if domain == "construction":
            from ...domains.construction.generators import (
                get_basic_report,
                generate_tasks,
                generate_report,
                generate_analysis,
                generate_risk_brief,
            )

            # Fetch participants once for all generators
            participant_ids = artifact_options.get("participant_ids", [])
            participants = None
            if participant_ids:
                try:
                    from ...tasks.transcription import _fetch_participants_for_risk_brief_async
                    participants = await _fetch_participants_for_risk_brief_async(participant_ids)
                    logger.info(f"Fetched {len(participants)} participant groups for generators")
                except Exception as e:
                    logger.warning(f"Failed to fetch participants: {e}")

            # Generate BasicReport ONCE for both tasks.xlsx and report.docx
            basic_report = None
            needs_basic_report = (
                artifact_options.get("generate_tasks", False) or
                artifact_options.get("generate_report", False)
            )
            if needs_basic_report:
                progress_callback("llm_generation", 40, "Анализ совещания через LLM...")
                try:
                    basic_report = get_basic_report(
                        result,
                        meeting_date=artifact_options.get("meeting_date"),
                    )
                    logger.info(f"BasicReport generated: {len(basic_report.tasks)} tasks")
                except Exception as e:
                    logger.error(f"BasicReport generation failed: {e}")

            # Generate tasks - uses pre-generated BasicReport
            if artifact_options.get("generate_tasks", False) and basic_report:
                progress_callback("llm_generation", 50, "Формирование списка задач...")
                try:
                    tasks_path = generate_tasks(
                        result, output_dir,
                        basic_report=basic_report,
                        participants=participants,
                    )
                    output_files["tasks"] = str(tasks_path)
                    logger.info(f"Generated tasks: {tasks_path}")
                except Exception as e:
                    logger.error(f"Tasks generation failed: {e}")

            # Generate report - uses pre-generated BasicReport
            if artifact_options.get("generate_report", False) and basic_report:
                progress_callback("llm_generation", 70, "Формирование отчёта...")
                try:
                    report_path = generate_report(
                        result, output_dir,
                        basic_report=basic_report,
                        meeting_date=artifact_options.get("meeting_date"),
                        participants=participants,
                    )
                    output_files["report"] = str(report_path)
                    logger.info(f"Generated report: {report_path}")
                except Exception as e:
                    logger.error(f"Report generation failed: {e}")

            # Generate manager brief - for dashboard only, no file
            if artifact_options.get("generate_analysis", False):
                # Silent generation - no progress message for user, no file output
                try:
                    ai_analysis = generate_analysis(result)
                    logger.info("Generated manager brief (AIAnalysis for dashboard)")
                except Exception as e:
                    logger.error(f"Manager brief generation failed: {e}")

            # Generate risk brief (optional) - reuses participants fetched above
            if artifact_options.get("generate_risk_brief", False):
                progress_callback("llm_generation", 95, "Формирование риск-брифа...")
                try:
                    risk_brief_path = generate_risk_brief(
                        result,
                        output_dir,
                        meeting_date=artifact_options.get("meeting_date"),
                        project_name=artifact_options.get("project_name"),
                        project_code=artifact_options.get("project_code"),
                        participants=participants,
                    )
                    output_files["risk_brief"] = str(risk_brief_path)
                    logger.info(f"Generated risk brief: {risk_brief_path}")
                except Exception as e:
                    logger.error(f"Risk brief generation failed: {e}")

        # Save original text as transcript
        if artifact_options.get("generate_transcript", True):
            transcript_path = output_dir / f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            output_files["transcript"] = str(transcript_path)

        # Save domain report to database if project is linked
        if domain_type and project_id:
            progress_callback("domain_report", 98, "Saving report to database...")
            try:
                _save_domain_report(
                    job_id=job_id,
                    result=result,
                    project_id=project_id,
                    domain_type=domain_type,
                    output_files=output_files,
                    guest_uid=guest_uid,
                    uploader_id=uploader_id,
                    ai_analysis=ai_analysis if domain == "construction" else None,
                )
            except Exception as e:
                logger.error(f"Domain report save failed (non-fatal): {e}")

        # No need to filter - analysis is no longer a file
        public_output_files = output_files

        # Mark completed
        _complete_job(
            store=store,
            job_id=job_id,
            output_files=public_output_files,
            segment_count=len(segments),
            speaker_count=result.speaker_count,
            language_distribution={"ru": len(segments)},
            all_output_files=output_files,  # Track all artifacts including analysis
        )
        logger.info(f"Text report job {job_id} completed successfully")

        _send_notification_email(store, job_id, notify_emails, public_output_files)

    except Exception as e:
        _fail_job(store, job_id, e, "text_generation")
