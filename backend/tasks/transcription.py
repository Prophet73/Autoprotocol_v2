"""Transcription Celery tasks with Redis job storage."""
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .celery_app import celery_app

logger = logging.getLogger(__name__)


def _check_gemini_configured():
    """Check if Gemini API is configured via GOOGLE_API_KEY env var."""
    return bool(os.getenv("GOOGLE_API_KEY"))


def get_job_store():
    """Get job store - lazy import to avoid circular deps."""
    from ..core.storage import get_job_store
    return get_job_store()


def _run_domain_generators(
    result,
    output_path: Path,
    artifact_options: Dict,
    progress_callback,
) -> Dict[str, str]:
    """
    Run domain-specific generators based on artifact_options.

    Args:
        result: TranscriptionResult from pipeline
        output_path: Output directory
        artifact_options: Dict with flags (generate_transcript, generate_tasks, etc.)
        progress_callback: Progress callback function

    Returns:
        Dict mapping artifact type to file path
    """
    from ..domains.construction.generators import (
        generate_transcript,
        generate_tasks,
        generate_report,
        generate_analysis,
    )

    output_files = {}

    # Check if Gemini is configured for LLM-based generators
    has_gemini = _check_gemini_configured()

    # 1. Transcript (no LLM required)
    if artifact_options.get("generate_transcript", True):
        progress_callback("domain_generators", 92, "Generating transcript.docx...")
        try:
            transcript_path = generate_transcript(result, output_path)
            output_files["transcript"] = str(transcript_path)
            logger.info(f"Generated transcript: {transcript_path}")
        except Exception as e:
            logger.error(f"Transcript generation failed: {e}")

    # LLM-based generators (require Gemini via GOOGLE_API_KEY)
    if has_gemini:
        # 2. Tasks Excel
        if artifact_options.get("generate_tasks", False):
            progress_callback("domain_generators", 94, "Generating tasks.xlsx (AI)...")
            try:
                tasks_path = generate_tasks(result, output_path)
                output_files["tasks"] = str(tasks_path)
                logger.info(f"Generated tasks: {tasks_path}")
            except Exception as e:
                logger.error(f"Tasks generation failed: {e}")

        # 3. Report Word
        if artifact_options.get("generate_report", False):
            progress_callback("domain_generators", 96, "Generating report.docx (AI)...")
            try:
                report_path = generate_report(result, output_path)
                output_files["report"] = str(report_path)
                logger.info(f"Generated report: {report_path}")
            except Exception as e:
                logger.error(f"Report generation failed: {e}")

        # 4. AI Analysis
        if artifact_options.get("generate_analysis", False):
            progress_callback("domain_generators", 98, "Generating analysis.docx (AI)...")
            try:
                analysis_path = generate_analysis(result, output_path)
                output_files["analysis"] = str(analysis_path)
                logger.info(f"Generated analysis: {analysis_path}")
            except Exception as e:
                logger.error(f"Analysis generation failed: {e}")
    else:
        # Log warning if LLM generators were requested but Gemini not configured
        llm_requested = any([
            artifact_options.get("generate_tasks", False),
            artifact_options.get("generate_report", False),
            artifact_options.get("generate_analysis", False),
        ])
        if llm_requested:
            logger.warning(
                "LLM generators requested but GOOGLE_API_KEY not set. "
                "Skipping tasks.xlsx, report.docx, analysis.docx"
            )

    return output_files


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
    artifact_options: Optional[dict] = None,
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

        # Run domain generators based on artifact_options
        output_files = {}
        generated_artifacts = _run_domain_generators(
            result=result,
            output_path=output_path,
            artifact_options=artifact_options,
            progress_callback=progress_callback,
        )
        output_files.update(generated_artifacts)

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

        # Mark completed in Redis
        store.complete(
            job_id=job_id,
            output_files=output_files,
            processing_time=result.processing_time_seconds,
            segment_count=result.segment_count,
            language_distribution=result.language_distribution,
        )

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
        error_msg = "Task exceeded time limit"
        logger.error(f"Job {job_id}: {error_msg}")
        store.fail(job_id, error_msg)
        return {
            "job_id": job_id,
            "status": "failed",
            "error": error_msg,
        }

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        store.fail(job_id, str(e))
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
