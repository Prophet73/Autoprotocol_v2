"""
Job state storage using Redis.

Provides persistent job state management that survives API restarts
and supports multiple API replicas.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List

from redis import Redis
from pydantic import BaseModel

from backend.shared.config import JOB_TTL_HOURS
from ..transcription.models import JobStatus

logger = logging.getLogger(__name__)


class JobData(BaseModel):
    """Job data model."""
    job_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    # Input
    input_file: str
    languages: List[str] = ["ru"]

    # Project linkage (for construction domain)
    project_id: Optional[int] = None
    project_code: Optional[str] = None
    tenant_id: Optional[int] = None
    domain_type: Optional[str] = None  # 'construction', 'hr', etc.

    # User identity
    uploader_id: Optional[int] = None  # User ID for authenticated users

    # Meeting info (for non-construction domains)
    meeting_type: Optional[str] = None
    meeting_date: Optional[str] = None

    # Processing options
    skip_diarization: bool = False
    skip_translation: bool = False
    skip_emotions: bool = False

    # Artifact generation options
    generate_transcript: bool = True
    generate_tasks: bool = False
    generate_report: bool = False
    generate_risk_brief: bool = False
    generate_summary: bool = False

    # Email notification
    notify_emails: List[str] = []

    # Progress
    current_stage: Optional[str] = None
    progress_percent: int = 0
    message: str = "Задача добавлена в очередь"

    # Retry tracking
    retry_count: int = 0
    max_retries: int = 3
    last_failed_stage: Optional[str] = None

    # Warnings (non-fatal errors shown to user)
    warnings: List[str] = []

    # Results
    output_files: Optional[Dict[str, str]] = None
    processing_time: Optional[float] = None
    segment_count: Optional[int] = None
    language_distribution: Optional[Dict[str, int]] = None
    error: Optional[str] = None

    # Structured report data (domain-specific, e.g. NOTECH protocol)
    meeting_report: Optional[Dict] = None

    class Config:
        use_enum_values = True


class JobStore:
    """
    Redis-backed job state storage.

    Features:
    - Persistent storage (survives restarts)
    - Supports multiple API replicas
    - TTL for automatic cleanup of old jobs
    - Atomic operations for thread safety
    """

    # Redis key prefix
    KEY_PREFIX = "whisperx:job:"
    # Default TTL: from shared config
    DEFAULT_TTL = JOB_TTL_HOURS * 3600

    def __init__(self, redis_url: str = None, ttl: int = None):
        """
        Initialize JobStore.

        Args:
            redis_url: Redis connection URL (defaults to env REDIS_URL)
            ttl: Time-to-live for job records in seconds
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        if ttl is not None:
            self.ttl = ttl
        else:
            from backend.admin.settings.service import get_setting_value
            hours = int(get_setting_value("job_ttl_hours", str(JOB_TTL_HOURS)))
            self.ttl = hours * 3600
        self._redis: Optional[Redis] = None

    @property
    def redis(self) -> Redis:
        """Lazy Redis connection."""
        if self._redis is None:
            self._redis = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._redis

    def _key(self, job_id: str) -> str:
        """Generate Redis key for job."""
        return f"{self.KEY_PREFIX}{job_id}"

    def create(self, job_data: JobData) -> JobData:
        """
        Create new job record.

        Args:
            job_data: Job data to store

        Returns:
            Stored job data
        """
        key = self._key(job_data.job_id)
        data = job_data.model_dump_json()

        self.redis.setex(key, self.ttl, data)
        logger.info(f"Created job: {job_data.job_id}")

        return job_data

    def get(self, job_id: str) -> Optional[JobData]:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job data or None if not found
        """
        key = self._key(job_id)
        data = self.redis.get(key)

        if data is None:
            return None

        return JobData.model_validate_json(data)

    def update(self, job_id: str, **updates) -> Optional[JobData]:
        """
        Update job fields with optimistic locking (WATCH/MULTI/EXEC).

        Args:
            job_id: Job identifier
            **updates: Fields to update

        Returns:
            Updated job data or None if not found
        """
        key = self._key(job_id)
        max_retries = 3

        for attempt in range(max_retries):
            try:
                with self.redis.pipeline() as pipe:
                    pipe.watch(key)
                    data = pipe.get(key)
                    if data is None:
                        logger.warning(f"Job not found for update: {job_id}")
                        return None

                    job = JobData.model_validate_json(data)

                    # Apply updates
                    updates["updated_at"] = datetime.now(timezone.utc)
                    for field, value in updates.items():
                        if hasattr(job, field):
                            setattr(job, field, value)

                    # Atomic write
                    pipe.multi()
                    pipe.setex(key, self.ttl, job.model_dump_json())
                    pipe.execute()
                    return job
            except Exception:
                if attempt == max_retries - 1:
                    raise
                continue

        return None

    def update_progress(
        self,
        job_id: str,
        stage: str,
        percent: int,
        message: str
    ) -> Optional[JobData]:
        """
        Update job progress.

        Args:
            job_id: Job identifier
            stage: Current processing stage
            percent: Progress percentage (0-100)
            message: Status message

        Returns:
            Updated job data
        """
        return self.update(
            job_id,
            status=JobStatus.PROCESSING,
            current_stage=stage,
            progress_percent=percent,
            message=message,
        )

    def add_warning(self, job_id: str, warning: str) -> Optional[JobData]:
        """
        Add a warning message to the job.

        Args:
            job_id: Job identifier
            warning: Warning message

        Returns:
            Updated job data or None if not found
        """
        job = self.get(job_id)
        if job is None:
            return None
        job.warnings.append(warning)
        key = self._key(job_id)
        self.redis.setex(key, self.ttl, job.model_dump_json())
        return job

    def complete(
        self,
        job_id: str,
        output_files: Dict[str, str],
        processing_time: float,
        segment_count: int,
        language_distribution: Dict[str, int],
    ) -> Optional[JobData]:
        """
        Mark job as completed.

        Args:
            job_id: Job identifier
            output_files: Map of file type to path
            processing_time: Total processing time in seconds
            segment_count: Number of segments
            language_distribution: Count by language

        Returns:
            Updated job data
        """
        return self.update(
            job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            output_files=output_files,
            processing_time=processing_time,
            segment_count=segment_count,
            language_distribution=language_distribution,
            progress_percent=100,
            message="Обработка завершена",
        )

    def fail(self, job_id: str, error: str) -> Optional[JobData]:
        """
        Mark job as failed.

        Args:
            job_id: Job identifier
            error: Error message

        Returns:
            Updated job data
        """
        return self.update(
            job_id,
            status=JobStatus.FAILED,
            error=error,
            message=f"Ошибка: {error}",
        )

    def delete(self, job_id: str) -> bool:
        """
        Delete job record.

        Args:
            job_id: Job identifier

        Returns:
            True if deleted, False if not found
        """
        key = self._key(job_id)
        result = self.redis.delete(key)
        return result > 0

    def list_jobs(self, limit: int = 100) -> List[JobData]:
        """
        List recent jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of job data, sorted by creation time (newest first)
        """
        pattern = f"{self.KEY_PREFIX}*"
        keys = list(self.redis.scan_iter(pattern, count=limit))[:limit]

        jobs = []
        for key in keys:
            data = self.redis.get(key)
            if data:
                try:
                    jobs.append(JobData.model_validate_json(data))
                except Exception as e:
                    logger.warning(f"Failed to parse job data: {e}")

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs

    def health_check(self) -> bool:
        """
        Check Redis connection.

        Returns:
            True if connected
        """
        try:
            return self.redis.ping()
        except Exception as e:
            logger.debug(f"Redis ping failed: {e}")
            return False

    def recover_stuck_jobs(
        self,
        stale_threshold_minutes: int = 10,
        dry_run: bool = False,
    ) -> Dict[str, any]:
        """
        Find and recover jobs stuck in 'processing' or 'pending' state.

        Jobs are considered stuck if:
        - status == 'processing' and updated_at older than stale_threshold_minutes
        - status == 'pending' and updated_at older than stale_threshold_minutes * 2
          (longer threshold because pending jobs may legitimately wait in queue)

        Recovery strategy:
        - If retry_count < max_retries: requeue the job
        - If retry_count >= max_retries: mark as failed

        Args:
            stale_threshold_minutes: Minutes since last update to consider stuck
            dry_run: If True, only report what would be recovered

        Returns:
            Recovery statistics: {requeued: int, failed: int, jobs: list, errors: list}
        """
        from datetime import timedelta

        stats = {
            "requeued": 0,
            "failed": 0,
            "jobs": [],
            "errors": [],
            "dry_run": dry_run,
            "threshold_minutes": stale_threshold_minutes,
        }

        processing_cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_threshold_minutes)
        pending_cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_threshold_minutes * 2)
        logger.info(
            f"Recovering stuck jobs: threshold={stale_threshold_minutes}min, "
            f"processing_cutoff={processing_cutoff.isoformat()}, "
            f"pending_cutoff={pending_cutoff.isoformat()}, dry_run={dry_run}"
        )

        try:
            # Scan all jobs
            pattern = f"{self.KEY_PREFIX}*"
            for key in self.redis.scan_iter(pattern):
                try:
                    data = self.redis.get(key)
                    if not data:
                        continue

                    job = JobData.model_validate_json(data)

                    # Check if stuck based on status
                    if job.status == JobStatus.PROCESSING:
                        if job.updated_at >= processing_cutoff:
                            continue  # Recently updated, still working
                    elif job.status == JobStatus.PENDING:
                        if job.updated_at >= pending_cutoff:
                            continue  # May still be waiting in queue
                    else:
                        continue  # Not a recoverable status

                    # Found stuck job
                    age_minutes = int((datetime.now(timezone.utc) - job.updated_at).total_seconds() / 60)
                    job_info = {
                        "job_id": job.job_id,
                        "status": job.status,
                        "stage": job.current_stage,
                        "progress": job.progress_percent,
                        "updated_at": job.updated_at.isoformat(),
                        "age_minutes": age_minutes,
                        "retry_count": job.retry_count,
                        "action": None,
                    }

                    if not dry_run:
                        # Check retry count
                        if job.retry_count < job.max_retries:
                            # Requeue the job
                            job_info["action"] = "requeued"
                            self._requeue_job(job)
                            stats["requeued"] += 1
                            logger.warning(
                                f"Requeued stuck job {job.job_id}: "
                                f"status={job.status}, stage={job.current_stage}, "
                                f"age={age_minutes}min, "
                                f"retry={job.retry_count + 1}/{job.max_retries}"
                            )
                        else:
                            # Max retries exceeded - fail permanently
                            job_info["action"] = "failed"
                            self.fail(
                                job.job_id,
                                error=f"Превышено кол-во попыток ({job.max_retries}). "
                                      f"Последний сбой на этапе '{job.current_stage}'. "
                                      "Загрузите файл повторно или обратитесь в поддержку."
                            )
                            stats["failed"] += 1
                            logger.error(
                                f"Job {job.job_id} failed permanently after {job.max_retries} retries"
                            )

                    stats["jobs"].append(job_info)

                except Exception as e:
                    stats["errors"].append(f"Error processing {key}: {e}")
                    logger.error(f"Error checking job {key}: {e}")

        except Exception as e:
            stats["errors"].append(f"Scan error: {e}")
            logger.exception("Error during stuck job recovery scan")

        logger.info(
            f"Stuck job recovery complete: requeued={stats['requeued']}, "
            f"failed={stats['failed']}, dry_run={dry_run}"
        )

        return stats

    # Stages where the GPU pipeline is already done and only LLM work remains
    LLM_STAGES = frozenset({
        "llm_generators", "llm_generation", "domain_generators",
        "domain_report", "report_generation", "retry_reports",
    })

    def _requeue_job(self, job: JobData) -> None:
        """
        Requeue a stuck job for retry.

        Updates job state and sends new Celery task.
        Routes intelligently:
        - If stuck in an LLM stage and pipeline_result.json exists → replay LLM only
        - Text files → transcription_llm queue
        - Audio/video → transcription_gpu queue
        """
        from pathlib import Path
        from backend.tasks.transcription import (
            process_transcription_task, process_text_task, process_llm_generators,
        )

        DATA_DIR = os.getenv("DATA_DIR", "/data")
        output_dir = str(Path(DATA_DIR) / "output" / job.job_id)

        # Update job state for retry
        self.update(
            job.job_id,
            status=JobStatus.PENDING,
            retry_count=job.retry_count + 1,
            last_failed_stage=job.current_stage,
            current_stage=None,
            progress_percent=0,
            message=f"Retrying (attempt {job.retry_count + 1}/{job.max_retries})...",
            error=None,
        )

        # Build artifact options from job data
        artifact_options = {
            "generate_transcript": job.generate_transcript,
            "generate_tasks": job.generate_tasks,
            "generate_report": job.generate_report,
            "generate_risk_brief": job.generate_risk_brief,
            "generate_summary": job.generate_summary,
            "notify_emails": job.notify_emails,
        }

        input_file = job.input_file
        is_text_file = input_file.lower().endswith(('.docx', '.txt', '.doc'))

        # Smart LLM-phase recovery: if GPU work is done, only re-run LLM generators
        pipeline_result_path = Path(output_dir) / "pipeline_result.json"
        if (
            job.current_stage in self.LLM_STAGES
            and not is_text_file
            and pipeline_result_path.exists()
        ):
            process_llm_generators(
                job_id=job.job_id,
                output_dir=output_dir,
                artifact_options=artifact_options,
                domain_type=job.domain_type,
                project_id=job.project_id,
                uploader_id=job.uploader_id,
            )
            logger.info(
                f"Requeued job {job.job_id} for LLM-only retry "
                f"(stuck at stage '{job.current_stage}')"
            )
        elif is_text_file:
            process_text_task.apply_async(
                kwargs={
                    "job_id": job.job_id,
                    "input_file": input_file,
                    "output_dir": output_dir,
                    "project_id": job.project_id,
                    "domain_type": job.domain_type,
                    "uploader_id": job.uploader_id,
                    "artifact_options": artifact_options,
                },
                queue="transcription_llm",
            )
            logger.info(f"Requeued job {job.job_id} as text task")
        else:
            process_transcription_task.apply_async(
                kwargs={
                    "job_id": job.job_id,
                    "input_file": input_file,
                    "output_dir": output_dir,
                    "languages": job.languages,
                    "skip_diarization": job.skip_diarization,
                    "skip_translation": job.skip_translation,
                    "skip_emotions": job.skip_emotions,
                    "artifact_options": artifact_options,
                    "project_id": job.project_id,
                    "domain_type": job.domain_type,
                    "uploader_id": job.uploader_id,
                },
                queue="transcription_gpu",
            )
            logger.info(f"Requeued job {job.job_id} as transcription task")


# Global instance (singleton pattern)
_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    """
    Get global JobStore instance.

    Returns:
        JobStore singleton
    """
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store
