"""Transcription API routes."""
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from ..schemas import (
    TranscribeRequest,
    JobResponse,
    JobStatusResponse,
    JobResultResponse,
    ErrorResponse,
)
from ...core.transcription.models import JobStatus, TranscriptionRequest
from ...tasks.transcription import process_transcription_task

router = APIRouter(prefix="/transcribe", tags=["transcription"])

# In-memory job storage (replace with Redis in production)
jobs = {}

# Storage paths
UPLOAD_DIR = Path("/data/uploads")
OUTPUT_DIR = Path("/data/output")


@router.post("", response_model=JobResponse)
async def create_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio or video file"),
    languages: str = Form(default="ru", description="Comma-separated languages"),
    skip_diarization: bool = Form(default=False),
    skip_translation: bool = Form(default=False),
    skip_emotions: bool = Form(default=False),
):
    """
    Upload file and start transcription job.

    Returns job_id to track progress.
    """
    # Generate job ID
    job_id = str(uuid.uuid4())

    # Parse languages
    lang_list = [l.strip() for l in languages.split(",") if l.strip()]
    if not lang_list:
        lang_list = ["ru"]

    # Create upload directory
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    input_file = job_dir / file.filename
    with open(input_file, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create job record
    now = datetime.now()
    jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "created_at": now,
        "updated_at": now,
        "input_file": str(input_file),
        "languages": lang_list,
        "skip_diarization": skip_diarization,
        "skip_translation": skip_translation,
        "skip_emotions": skip_emotions,
        "current_stage": None,
        "progress_percent": 0,
        "message": "Job queued",
        "output_files": None,
        "error": None,
    }

    # Queue task (Celery or background task)
    try:
        # Try Celery first
        process_transcription_task.delay(
            job_id=job_id,
            input_file=str(input_file),
            output_dir=str(OUTPUT_DIR / job_id),
            languages=lang_list,
            skip_diarization=skip_diarization,
            skip_translation=skip_translation,
            skip_emotions=skip_emotions,
        )
    except Exception:
        # Fallback to background task
        background_tasks.add_task(
            run_transcription_background,
            job_id=job_id,
            input_file=input_file,
            output_dir=OUTPUT_DIR / job_id,
            languages=lang_list,
            skip_diarization=skip_diarization,
            skip_translation=skip_translation,
            skip_emotions=skip_emotions,
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
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        current_stage=job.get("current_stage"),
        progress_percent=job.get("progress_percent", 0),
        message=job.get("message"),
        created_at=job["created_at"],
        updated_at=job.get("updated_at"),
        completed_at=job.get("completed_at"),
        error=job.get("error"),
    )


@router.get("/{job_id}", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """Get completed job result."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] == JobStatus.PENDING:
        raise HTTPException(status_code=202, detail="Job is pending")

    if job["status"] == JobStatus.PROCESSING:
        raise HTTPException(status_code=202, detail="Job is still processing")

    if job["status"] == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=job.get("error", "Job failed"))

    return JobResultResponse(
        job_id=job_id,
        status=job["status"],
        source_file=Path(job["input_file"]).name,
        processing_time_seconds=job.get("processing_time", 0),
        segment_count=job.get("segment_count", 0),
        language_distribution=job.get("language_distribution", {}),
        output_files=job.get("output_files", {}),
        completed_at=job.get("completed_at", datetime.now()),
    )


@router.get("/{job_id}/download/{file_type}")
async def download_result(job_id: str, file_type: str):
    """
    Download result file.

    file_type: docx, txt, json
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    output_files = job.get("output_files", {})
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


async def run_transcription_background(
    job_id: str,
    input_file: Path,
    output_dir: Path,
    languages: list,
    skip_diarization: bool,
    skip_translation: bool,
    skip_emotions: bool,
):
    """Background task for transcription (fallback when Celery unavailable)."""
    from ...core.transcription.pipeline import TranscriptionPipeline
    from ...core.transcription.models import TranscriptionRequest

    def progress_callback(stage: str, percent: int, message: str):
        if job_id in jobs:
            jobs[job_id]["current_stage"] = stage
            jobs[job_id]["progress_percent"] = percent
            jobs[job_id]["message"] = message
            jobs[job_id]["updated_at"] = datetime.now()

    try:
        jobs[job_id]["status"] = JobStatus.PROCESSING
        jobs[job_id]["updated_at"] = datetime.now()

        request = TranscriptionRequest(
            languages=languages,
            skip_diarization=skip_diarization,
            skip_translation=skip_translation,
            skip_emotions=skip_emotions,
        )

        pipeline = TranscriptionPipeline(progress_callback=progress_callback)
        result = pipeline.process(
            input_file=input_file,
            request=request,
            output_dir=output_dir,
        )

        # Update job with results
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["completed_at"] = datetime.now()
        jobs[job_id]["processing_time"] = result.processing_time_seconds
        jobs[job_id]["segment_count"] = result.segment_count
        jobs[job_id]["language_distribution"] = result.language_distribution

        # Find output files
        output_files = {}
        for ext in ["docx", "txt", "json"]:
            files = list(output_dir.glob(f"*.{ext}"))
            if files:
                output_files[ext] = str(files[0])

        jobs[job_id]["output_files"] = output_files
        jobs[job_id]["message"] = "Completed successfully"

    except Exception as e:
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now()
