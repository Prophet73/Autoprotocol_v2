"""Transcription Celery tasks."""
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="transcription.process",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
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
) -> dict:
    """
    Celery task for transcription processing.

    Args:
        job_id: Unique job identifier
        input_file: Path to input file
        output_dir: Path to output directory
        languages: List of languages to transcribe
        skip_diarization: Skip speaker identification
        skip_translation: Skip translation
        skip_emotions: Skip emotion analysis

    Returns:
        Dict with processing results
    """
    from ..core.transcription.pipeline import TranscriptionPipeline
    from ..core.transcription.models import TranscriptionRequest

    logger.info(f"Starting transcription job: {job_id}")
    logger.info(f"Input: {input_file}")
    logger.info(f"Languages: {languages}")

    def progress_callback(stage: str, percent: int, message: str):
        """Update task state with progress."""
        self.update_state(
            state="PROGRESS",
            meta={
                "current_stage": stage,
                "progress_percent": percent,
                "message": message,
            }
        )

    try:
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

        # Run pipeline
        pipeline = TranscriptionPipeline(progress_callback=progress_callback)
        result = pipeline.process(
            input_file=Path(input_file),
            request=request,
            output_dir=output_path,
        )

        # Find output files
        output_files = {}
        for ext in ["docx", "txt", "json"]:
            files = list(output_path.glob(f"*.{ext}"))
            if files:
                output_files[ext] = str(files[0])

        logger.info(f"Job {job_id} completed successfully")

        return {
            "job_id": job_id,
            "status": "completed",
            "processing_time_seconds": result.processing_time_seconds,
            "segment_count": result.segment_count,
            "language_distribution": result.language_distribution,
            "output_files": output_files,
            "completed_at": datetime.now().isoformat(),
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Job {job_id} exceeded time limit")
        return {
            "job_id": job_id,
            "status": "failed",
            "error": "Task exceeded time limit",
        }

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        raise  # Will trigger retry


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
