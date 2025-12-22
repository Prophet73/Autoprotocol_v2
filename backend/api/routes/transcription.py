"""Transcription API routes with Redis-backed job storage."""
import os
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from ..schemas import (
    JobResponse,
    JobStatusResponse,
    JobResultResponse,
)
from ...core.storage import get_job_store, JobStore
from ...core.storage.job_store import JobData
from ...core.transcription.models import TranscriptionRequest, JobStatus
from ...tasks.transcription import process_transcription_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["transcription"])

# Storage paths - use DATA_DIR env or default to /data (Docker)
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"


def get_store() -> JobStore:
    """Get job store instance."""
    return get_job_store()


@router.post("", response_model=JobResponse)
async def create_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio or video file"),
    languages: str = Form(default="ru", description="Comma-separated languages"),
    skip_diarization: bool = Form(default=False),
    skip_translation: bool = Form(default=False),
    skip_emotions: bool = Form(default=False),
    # Domain artifact options (ДПУ)
    generate_transcript: bool = Form(default=True, description="Generate transcript.docx"),
    generate_tasks: bool = Form(default=False, description="Generate tasks.xlsx via LLM"),
    generate_report: bool = Form(default=False, description="Generate report.docx via LLM"),
    generate_analysis: bool = Form(default=False, description="Generate analysis.docx via LLM"),
):
    """
    Upload file and start transcription job.

    Returns job_id to track progress.
    """
    store = get_store()

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Parse languages
    lang_list = [lang.strip() for lang in languages.split(",") if lang.strip()]
    if not lang_list:
        lang_list = ["ru"]

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
    job_data = JobData(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=now,
        updated_at=now,
        input_file=str(input_file),
        languages=lang_list,
        skip_diarization=skip_diarization,
        skip_translation=skip_translation,
        skip_emotions=skip_emotions,
        generate_transcript=generate_transcript,
        generate_tasks=generate_tasks,
        generate_report=generate_report,
        generate_analysis=generate_analysis,
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
        )

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=now,
        message="Job queued for processing",
    )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job processing status."""
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


@router.get("/{job_id}", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """Get completed job result."""
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


@router.get("/{job_id}/download/{file_type}")
async def download_result(job_id: str, file_type: str):
    """
    Download result file.

    file_type: transcript, tasks, report, analysis, docx, txt, json
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


@router.get("")
async def list_jobs(limit: int = 50):
    """List recent jobs."""
    store = get_store()
    jobs = store.list_jobs(limit=limit)

    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "source_file": Path(job.input_file).name,
                "progress_percent": job.progress_percent,
                "message": job.message,
            }
            for job in jobs
        ]
    }


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending or processing job."""
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

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        store.fail(job_id, str(e))
