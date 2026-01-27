"""
Job state storage using Redis.

Provides persistent job state management that survives API restarts
and supports multiple API replicas.
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, List

from redis import Redis
from pydantic import BaseModel

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

    # User/Guest identity
    guest_uid: Optional[str] = None  # UUID for anonymous users
    uploader_id: Optional[int] = None  # User ID for authenticated users

    # Processing options
    skip_diarization: bool = False
    skip_translation: bool = False
    skip_emotions: bool = False

    # Artifact generation options
    generate_transcript: bool = True
    generate_tasks: bool = False
    generate_report: bool = False
    generate_analysis: bool = False
    generate_risk_brief: bool = False

    # Email notification
    notify_emails: List[str] = []

    # Progress
    current_stage: Optional[str] = None
    progress_percent: int = 0
    message: str = "Job queued"

    # Results
    output_files: Optional[Dict[str, str]] = None
    processing_time: Optional[float] = None
    segment_count: Optional[int] = None
    language_distribution: Optional[Dict[str, int]] = None
    error: Optional[str] = None

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
    # Default TTL: 24 hours
    DEFAULT_TTL = 86400

    def __init__(self, redis_url: str = None, ttl: int = None):
        """
        Initialize JobStore.

        Args:
            redis_url: Redis connection URL (defaults to env REDIS_URL)
            ttl: Time-to-live for job records in seconds
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl = ttl or self.DEFAULT_TTL
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
        Update job fields.

        Args:
            job_id: Job identifier
            **updates: Fields to update

        Returns:
            Updated job data or None if not found
        """
        job = self.get(job_id)
        if job is None:
            logger.warning(f"Job not found for update: {job_id}")
            return None

        # Apply updates
        updates["updated_at"] = datetime.now()
        for field, value in updates.items():
            if hasattr(job, field):
                setattr(job, field, value)

        # Save
        key = self._key(job_id)
        self.redis.setex(key, self.ttl, job.model_dump_json())

        return job

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
            completed_at=datetime.now(),
            output_files=output_files,
            processing_time=processing_time,
            segment_count=segment_count,
            language_distribution=language_distribution,
            progress_percent=100,
            message="Completed successfully",
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
            message=f"Failed: {error}",
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
        Find and recover jobs stuck in 'processing' state.

        Jobs are considered stuck if:
        - status == 'processing'
        - updated_at is older than stale_threshold_minutes

        This handles cases where worker crashed/restarted mid-processing.

        Args:
            stale_threshold_minutes: Minutes since last update to consider stuck
            dry_run: If True, only report what would be recovered

        Returns:
            Recovery statistics: {recovered: int, jobs: list, errors: list}
        """
        from datetime import timedelta

        stats = {
            "recovered": 0,
            "jobs": [],
            "errors": [],
            "dry_run": dry_run,
            "threshold_minutes": stale_threshold_minutes,
        }

        cutoff = datetime.now() - timedelta(minutes=stale_threshold_minutes)
        logger.info(
            f"Recovering stuck jobs: threshold={stale_threshold_minutes}min, "
            f"cutoff={cutoff.isoformat()}, dry_run={dry_run}"
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

                    # Check if stuck
                    if job.status != JobStatus.PROCESSING:
                        continue

                    if job.updated_at >= cutoff:
                        continue  # Recently updated, still working

                    # Found stuck job
                    job_info = {
                        "job_id": job.job_id,
                        "stage": job.current_stage,
                        "progress": job.progress_percent,
                        "updated_at": job.updated_at.isoformat(),
                        "age_minutes": int((datetime.now() - job.updated_at).total_seconds() / 60),
                    }
                    stats["jobs"].append(job_info)

                    if not dry_run:
                        # Mark as failed
                        self.fail(
                            job.job_id,
                            error=f"Worker interrupted during '{job.current_stage}' stage. "
                                  f"Job was stuck for {job_info['age_minutes']} minutes. "
                                  "Please retry the task."
                        )
                        logger.warning(
                            f"Recovered stuck job {job.job_id}: "
                            f"stage={job.current_stage}, age={job_info['age_minutes']}min"
                        )

                    stats["recovered"] += 1

                except Exception as e:
                    stats["errors"].append(f"Error processing {key}: {e}")
                    logger.error(f"Error checking job {key}: {e}")

        except Exception as e:
            stats["errors"].append(f"Scan error: {e}")
            logger.exception("Error during stuck job recovery scan")

        logger.info(
            f"Stuck job recovery complete: found={stats['recovered']}, "
            f"dry_run={dry_run}"
        )

        return stats


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
