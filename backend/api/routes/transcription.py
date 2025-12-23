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
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Header, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import (
    JobResponse,
    JobStatusResponse,
    JobResultResponse,
)
from ...core.storage import get_job_store, JobStore
from ...core.storage.job_store import JobData
from ...core.transcription.models import TranscriptionRequest, JobStatus
from ...tasks.transcription import process_transcription_task
from ...shared.database import get_db
from ...domains.construction.project_service import ProjectService
from ...core.auth.dependencies import get_optional_user
from ...shared.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["Транскрипция"])

# Storage paths - use DATA_DIR env or default to /data (Docker)
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"


def get_store() -> JobStore:
    """Get job store instance."""
    return get_job_store()


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
    # Guest ID for anonymous users (from X-Guest-ID header)
    x_guest_id: Optional[str] = Header(default=None, alias="X-Guest-ID", description="UUID гостя для анонимной загрузки"),
    # Domain artifact options (ДПУ)
    generate_transcript: bool = Form(default=True, description="Создать транскрипт (transcript.docx)"),
    generate_tasks: bool = Form(default=False, description="Извлечь задачи через LLM (tasks.xlsx)"),
    generate_report: bool = Form(default=False, description="Создать отчёт через LLM (report.docx)"),
    generate_analysis: bool = Form(default=False, description="Создать аналитику через LLM (analysis.docx)"),
    # Email notification
    notify_emails: Optional[str] = Form(default=None, description="Email адреса для уведомления (через запятую)"),
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
        logger.info(f"Job linked to project {project_id} via code {project_code}")

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

    # Create job record in Redis
    now = datetime.now()
    # Parse notify emails
    notify_emails_list = []
    if notify_emails:
        notify_emails_list = [e.strip() for e in notify_emails.split(",") if e.strip() and "@" in e]

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
        generate_analysis=generate_analysis,
        notify_emails=notify_emails_list,
    )

    store.create(job_data)

    # Artifact options for task
    artifact_options = {
        "generate_transcript": generate_transcript,
        "generate_tasks": generate_tasks,
        "generate_report": generate_report,
        "generate_analysis": generate_analysis,
    }

    # Queue Celery task
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
async def get_job_status(job_id: str):
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

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

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
    - **analysis** — аналитика (DOCX)
    - **protocol_docx** — протокол Word
    - **protocol_txt** — протокол текст
    - **result_json** — сырые данные JSON
    """
    store = get_store()
    job = store.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    output_files = job.output_files or {}
    if file_type not in output_files:
        raise HTTPException(status_code=404, detail=f"File type '{file_type}' not found")

    file_path = Path(output_files[file_type])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
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
    all_jobs = store.list_jobs(limit=limit * 2)  # Fetch more to filter

    # Filter based on user/guest identity
    if current_user:
        # Authenticated user - filter by uploader_id
        jobs = [
            job for job in all_jobs
            if getattr(job, 'uploader_id', None) == current_user.id
        ][:limit]
    elif x_guest_id:
        # Guest - filter by guest_uid
        jobs = [
            job for job in all_jobs
            if getattr(job, 'guest_uid', None) == x_guest_id
        ][:limit]
    else:
        # No identity - return empty list
        jobs = []

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
        from celery.result import AsyncResult
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
    notify_emails: list = None,
):
    """Background task for transcription (fallback when Celery unavailable)."""
    from ...core.transcription.pipeline import TranscriptionPipeline
    from ...core.transcription.models import TranscriptionRequest

    store = get_store()
    artifact_options = artifact_options or {}

    def progress_callback(stage: str, percent: int, message: str):
        store.update_progress(job_id, stage, percent, message)

    try:
        store.update(job_id, status=JobStatus.PROCESSING)

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
        from ...tasks.transcription import _run_domain_generators

        output_files = {}
        generated_artifacts = _run_domain_generators(
            result=result,
            output_path=output_dir,
            artifact_options=artifact_options,
            progress_callback=progress_callback,
        )
        output_files.update(generated_artifacts)

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
        store.complete(
            job_id=job_id,
            output_files=output_files,
            processing_time=result.processing_time_seconds,
            segment_count=result.segment_count,
            language_distribution=result.language_distribution,
        )

        logger.info(f"Job {job_id} completed successfully")

        # Send email notification if emails are provided
        if notify_emails:
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

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        store.fail(job_id, str(e))
