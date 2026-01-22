"""Transcription Celery tasks with Redis job storage."""
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run a coroutine from sync or async contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
    else:
        loop.create_task(coro)


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
    domain_type: Optional[str] = None,
) -> Dict[str, str]:
    """
    Run domain-specific generators based on artifact_options and domain_type.

    Args:
        result: TranscriptionResult from pipeline
        output_path: Output directory
        artifact_options: Dict with flags (generate_transcript, generate_tasks, etc.)
        progress_callback: Progress callback function
        domain_type: Domain type (construction, hr, it)

    Returns:
        Dict mapping artifact type to file path
    """
    output_files = {}

    # Check if Gemini is configured for LLM-based generators
    has_gemini = _check_gemini_configured()

    # Get meeting_type from artifact_options
    meeting_type = artifact_options.get("meeting_type")

    # Default to construction domain
    domain = domain_type or "construction"

    # Import generators based on domain
    generate_analysis = None
    generate_risk_brief = None  # Default - only construction has risk_brief
    if domain == "hr":
        from ..domains.hr.generators import generate_transcript, generate_report
        generate_tasks = None  # HR doesn't have separate tasks generator
    elif domain == "it":
        from ..domains.it.generators import generate_transcript, generate_report
        generate_tasks = None  # IT doesn't have separate tasks generator
    else:  # construction (default)
        from ..domains.construction.generators import (
            generate_transcript,
            generate_tasks,
            generate_report,
            generate_analysis,  # manager brief (DOCX)
            generate_risk_brief,  # INoT approach - PDF for client
        )

    # 1. Transcript (no LLM required)
    if artifact_options.get("generate_transcript", True):
        progress_callback("domain_generators", 92, "Generating transcript.docx...")
        try:
            if meeting_type:
                transcript_path = generate_transcript(result, output_path, meeting_type=meeting_type)
            else:
                transcript_path = generate_transcript(result, output_path)
            output_files["transcript"] = str(transcript_path)
            logger.info(f"Generated transcript: {transcript_path}")
        except Exception as e:
            logger.error(f"Transcript generation failed: {e}")

    # LLM-based generators (require Gemini via GOOGLE_API_KEY)
    if has_gemini:
        # 2. Tasks Excel (construction only)
        if artifact_options.get("generate_tasks", False) and generate_tasks:
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
                if meeting_type:
                    report_path = generate_report(result, output_path, meeting_type=meeting_type)
                else:
                    report_path = generate_report(result, output_path)
                output_files["report"] = str(report_path)
                logger.info(f"Generated report: {report_path}")
            except Exception as e:
                logger.error(f"Report generation failed: {e}")

        # 4. Manager brief (construction only)
        if artifact_options.get("generate_analysis", False) and generate_analysis:
            progress_callback("domain_generators", 98, "Generating manager_brief.docx (AI)...")
            try:
                analysis_path = generate_analysis(result, output_path)
                output_files["analysis"] = str(analysis_path)
                logger.info(f"Generated manager brief: {analysis_path}")
            except Exception as e:
                logger.error(f"Manager brief generation failed: {e}")

        # 5. Risk Brief (construction only) - INoT approach, PDF for client
        if artifact_options.get("generate_risk_brief", False) and generate_risk_brief:
            progress_callback("domain_generators", 99, "Generating risk_brief.pdf (AI/INoT)...")
            try:
                risk_brief_path = generate_risk_brief(result, output_path)
                output_files["risk_brief"] = str(risk_brief_path)
                logger.info(f"Generated risk brief: {risk_brief_path}")
            except Exception as e:
                logger.error(f"Risk brief generation failed: {e}")
    else:
        # Log warning if LLM generators were requested but Gemini not configured
        llm_requested = any([
            artifact_options.get("generate_tasks", False),
            artifact_options.get("generate_report", False),
            artifact_options.get("generate_analysis", False),
            artifact_options.get("generate_risk_brief", False),
        ])
        if llm_requested:
            logger.warning(
                "LLM generators requested but GOOGLE_API_KEY not set. "
                "Skipping tasks.xlsx, report.docx, analysis.docx, risk_brief.pdf"
            )

    return output_files


def _sync_job_to_db(
    job_id: str,
    domain: str,
    meeting_type: Optional[str],
    user_id: Optional[int],
    guest_uid: Optional[str],
    project_id: Optional[int],
    source_filename: Optional[str],
    source_size_bytes: Optional[int] = None,
    status: str = "pending",
) -> None:
    """
    Create/update TranscriptionJob record in PostgreSQL for stats tracking.

    Called when job is created to sync Redis -> PostgreSQL.
    """
    import asyncio
    from ..shared.database import async_session_factory
    from ..shared.models import TranscriptionJob

    async def _async_create():
        async with async_session_factory() as db:
            try:
                # Create new record
                job = TranscriptionJob(
                    job_id=job_id,
                    domain=domain or "construction",
                    meeting_type=meeting_type,
                    status=status,
                    user_id=user_id,
                    guest_uid=guest_uid,
                    project_id=project_id,
                    source_filename=source_filename,
                    source_size_bytes=source_size_bytes,
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
    artifacts: Optional[dict] = None,
    error_message: Optional[str] = None,
    error_stage: Optional[str] = None,
) -> None:
    """
    Update TranscriptionJob record in PostgreSQL after processing completes.
    """
    import asyncio
    from datetime import datetime
    from sqlalchemy import update
    from ..shared.database import async_session_factory
    from ..shared.models import TranscriptionJob

    async def _async_update():
        async with async_session_factory() as db:
            try:
                update_data = {
                    "status": status,
                    "processing_time_seconds": processing_time_seconds,
                    "audio_duration_seconds": audio_duration_seconds,
                    "segment_count": segment_count,
                    "speaker_count": speaker_count,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "artifacts": artifacts,
                    "error_message": error_message,
                    "error_stage": error_stage,
                }

                if status == "completed":
                    update_data["completed_at"] = datetime.now()
                elif status == "processing":
                    update_data["started_at"] = datetime.now()

                # Remove None values
                update_data = {k: v for k, v in update_data.items() if v is not None}

                stmt = update(TranscriptionJob).where(
                    TranscriptionJob.job_id == job_id
                ).values(**update_data)

                await db.execute(stmt)
                await db.commit()
                logger.info(f"TranscriptionJob record updated for {job_id}: {status}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to update TranscriptionJob record: {e}")

    _run_async(_async_update())


def _save_domain_report(
    job_id: str,
    result,
    project_id: int,
    domain_type: str,
    output_files: Optional[Dict[str, str]] = None,
    guest_uid: Optional[str] = None,
    uploader_id: Optional[int] = None,
) -> None:
    """
    Save domain-specific report to database after transcription.

    Args:
        job_id: Job identifier
        result: TranscriptionResult from pipeline
        project_id: Project ID
        domain_type: Domain type ('construction', 'hr', etc.)
        guest_uid: Guest UUID for anonymous uploads
        uploader_id: User ID for authenticated uploads
    """
    import asyncio
    from ..shared.database import async_session_factory
    from ..domains.factory import DomainServiceFactory

    async def _async_save():
        async with async_session_factory() as db:
            try:
                # Create domain service via factory
                service = DomainServiceFactory.create(domain_type)

                # Generate simple report (no LLM for now)
                report = service.generate_report_simple(result)

                # Save to database
                await service.save_report_to_db(
                    db=db,
                    job_id=job_id,
                    project_id=project_id,
                    report=report,
                    output_files=output_files or {},
                    guest_uid=guest_uid,
                    uploader_id=uploader_id,
                )

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
    # Domain linkage parameters
    project_id: Optional[int] = None,
    domain_type: Optional[str] = None,
    meeting_type: Optional[str] = None,
    guest_uid: Optional[str] = None,
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

        # Run domain generators based on artifact_options
        output_files = {}
        generated_artifacts = _run_domain_generators(
            result=result,
            output_path=output_path,
            artifact_options=artifact_options,
            progress_callback=progress_callback,
            domain_type=domain_type,
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

        # Save domain report to database if project is linked
        if domain_type and project_id:
            progress_callback("domain_report", 99, "Saving report to database...")
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
                # Don't fail the whole job if domain report fails

        # Hide manager brief from user-facing downloads
        public_output_files = {k: v for k, v in output_files.items() if k != "analysis"}

        # Mark completed in Redis
        store.complete(
            job_id=job_id,
            output_files=public_output_files,
            processing_time=result.processing_time_seconds,
            segment_count=result.segment_count,
            language_distribution=result.language_distribution,
        )

        # Update TranscriptionJob in PostgreSQL for stats
        _update_job_in_db(
            job_id=job_id,
            status="completed",
            processing_time_seconds=result.processing_time_seconds,
            audio_duration_seconds=getattr(result, 'audio_duration_seconds', None),
            segment_count=result.segment_count,
            speaker_count=getattr(result, 'speaker_count', None),
            input_tokens=getattr(result, 'input_tokens', 0),
            output_tokens=getattr(result, 'output_tokens', 0),
            artifacts={
                "transcript": "transcript" in output_files,
                "tasks": "tasks" in output_files,
                "report": "report" in output_files,
                "analysis": "analysis" in output_files,
            },
        )

        logger.info(f"Job {job_id} completed successfully")

        # Send email notification if emails are provided
        if notify_emails:
            progress_callback("email_notification", 100, "Sending email notification...")
            email_sent = False
            try:
                from ..core.email.service import send_report_email

                # Get project name from job store for email subject
                job_data = store.get(job_id)
                project_name = getattr(job_data, 'project_code', None)

                email_sent = send_report_email(
                    recipients=notify_emails,
                    job_id=job_id,
                    project_name=project_name,
                    output_files=public_output_files,
                )
                if email_sent:
                    logger.info(f"Email notification sent to {notify_emails}")
                else:
                    logger.warning(f"Email notification failed for {notify_emails}")
            except Exception as e:
                logger.error(f"Email notification failed (non-fatal): {e}")
                # Don't fail the job if email fails
            finally:
                store.update(
                    job_id,
                    status=JobStatus.COMPLETED,
                    current_stage="completed",
                    progress_percent=100,
                    message="Completed successfully" if email_sent else "Completed; email notification failed",
                    completed_at=datetime.now(),
                )

        return {
            "job_id": job_id,
            "status": "completed",
            "processing_time_seconds": result.processing_time_seconds,
            "segment_count": result.segment_count,
            "language_distribution": result.language_distribution,
            "output_files": public_output_files,
            "completed_at": datetime.now().isoformat(),
        }

    except SoftTimeLimitExceeded:
        error_msg = "Task exceeded time limit"
        logger.error(f"Job {job_id}: {error_msg}")
        store.fail(job_id, error_msg)
        _update_job_in_db(job_id=job_id, status="failed", error_message=error_msg, error_stage="timeout")
        return {
            "job_id": job_id,
            "status": "failed",
            "error": error_msg,
        }

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        store.fail(job_id, str(e))
        _update_job_in_db(job_id=job_id, status="failed", error_message=str(e)[:500], error_stage="processing")
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
