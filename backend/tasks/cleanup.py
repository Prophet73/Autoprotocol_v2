"""
Cleanup tasks for audio file retention policy.

Provides periodic cleanup of old audio files while preserving
text reports and transcripts.
"""
import os
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


from backend.tasks.celery_app import celery_app
from backend.shared.database import get_db_context
from backend.admin.settings.service import SettingsService

logger = logging.getLogger(__name__)


from backend.shared.async_utils import run_async


# Storage paths
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"

# Audio file extensions to clean up
AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma",
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv",
}


@celery_app.task(name="cleanup.cleanup_old_audio_files")
def cleanup_old_audio_files(
    retention_days: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """
    Delete audio/video files older than retention period.

    Keeps text reports, transcripts, and JSON results.

    Args:
        retention_days: Override days to keep (default from SystemSettings)
        dry_run: If True, only report what would be deleted

    Returns:
        Cleanup statistics
    """
    return run_async(_async_cleanup(retention_days, dry_run))


async def _async_cleanup(
    retention_days: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """Async implementation of cleanup."""
    stats = {
        "files_checked": 0,
        "files_deleted": 0,
        "bytes_freed": 0,
        "directories_cleaned": 0,
        "errors": [],
        "dry_run": dry_run,
    }

    # Get retention period from settings if not specified
    if retention_days is None:
        try:
            async with get_db_context() as db:
                service = SettingsService(db)
                from backend.shared.config import AUDIO_RETENTION_DAYS
                retention_str = await service.get_value(
                    "audio_retention_days",
                    default=str(AUDIO_RETENTION_DAYS),
                )
                retention_days = int(retention_str)
        except Exception as e:
            logger.warning(f"Could not get retention setting, using default: {e}")
            from backend.shared.config import AUDIO_RETENTION_DAYS
            retention_days = AUDIO_RETENTION_DAYS

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    logger.info(
        f"Starting cleanup: retention={retention_days} days, "
        f"cutoff={cutoff_date.isoformat()}, dry_run={dry_run}"
    )

    # Cleanup uploads directory
    if UPLOAD_DIR.exists():
        upload_stats = await _cleanup_directory(
            UPLOAD_DIR,
            cutoff_date,
            dry_run,
            cleanup_audio_only=True,
        )
        stats["files_checked"] += upload_stats["checked"]
        stats["files_deleted"] += upload_stats["deleted"]
        stats["bytes_freed"] += upload_stats["bytes"]
        stats["directories_cleaned"] += upload_stats["dirs"]
        stats["errors"].extend(upload_stats["errors"])

    # Cleanup output directory (only audio files, keep reports)
    if OUTPUT_DIR.exists():
        output_stats = await _cleanup_directory(
            OUTPUT_DIR,
            cutoff_date,
            dry_run,
            cleanup_audio_only=True,
        )
        stats["files_checked"] += output_stats["checked"]
        stats["files_deleted"] += output_stats["deleted"]
        stats["bytes_freed"] += output_stats["bytes"]
        stats["directories_cleaned"] += output_stats["dirs"]
        stats["errors"].extend(output_stats["errors"])

    # Convert bytes to MB for readability
    stats["mb_freed"] = round(stats["bytes_freed"] / (1024 * 1024), 2)

    logger.info(
        f"Cleanup complete: deleted {stats['files_deleted']} files, "
        f"freed {stats['mb_freed']} MB"
    )

    return stats


async def _cleanup_directory(
    directory: Path,
    cutoff_date: datetime,
    dry_run: bool,
    cleanup_audio_only: bool = True,
) -> dict:
    """Clean up files in a directory."""
    stats = {
        "checked": 0,
        "deleted": 0,
        "bytes": 0,
        "dirs": 0,
        "errors": [],
    }

    try:
        for job_dir in directory.iterdir():
            if not job_dir.is_dir():
                continue

            # Check directory modification time
            dir_mtime = datetime.fromtimestamp(job_dir.stat().st_mtime, tz=timezone.utc)
            if dir_mtime >= cutoff_date:
                continue  # Skip recent directories

            # Process files in job directory
            for file_path in job_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                stats["checked"] += 1

                # Check if this is an audio/video file
                if cleanup_audio_only:
                    if file_path.suffix.lower() not in AUDIO_EXTENSIONS:
                        continue  # Skip non-audio files

                # Check file age
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                if file_mtime >= cutoff_date:
                    continue

                # Delete or report
                file_size = file_path.stat().st_size
                try:
                    if not dry_run:
                        file_path.unlink()
                        logger.debug(f"Deleted: {file_path}")
                    stats["deleted"] += 1
                    stats["bytes"] += file_size
                except Exception as e:
                    stats["errors"].append(f"Failed to delete {file_path}: {e}")
                    logger.error(f"Failed to delete {file_path}: {e}")

            # Check if directory is now empty (or only has empty subdirs)
            try:
                remaining_files = list(job_dir.rglob("*"))
                remaining_files = [f for f in remaining_files if f.is_file()]

                if not remaining_files and not dry_run:
                    shutil.rmtree(job_dir)
                    stats["dirs"] += 1
                    logger.debug(f"Removed empty directory: {job_dir}")
            except Exception as e:
                stats["errors"].append(f"Failed to remove directory {job_dir}: {e}")

    except Exception as e:
        stats["errors"].append(f"Error processing {directory}: {e}")
        logger.exception(f"Error during cleanup of {directory}")

    return stats


@celery_app.task(name="cleanup.cleanup_old_error_logs")
def cleanup_old_error_logs(retention_days: int = None) -> dict:
    """
    Clean up old error logs from database.
    Reads retention period from DB settings, falls back to 30 days.
    """
    return run_async(_cleanup_error_logs_with_settings(retention_days))


async def _cleanup_error_logs_with_settings(retention_days: int = None) -> dict:
    """Read retention from DB if not specified, then run cleanup."""
    if retention_days is None:
        try:
            async with get_db_context() as db:
                service = SettingsService(db)
                from backend.shared.config import ERROR_LOG_RETENTION_DAYS
                retention_str = await service.get_value(
                    "error_log_retention_days",
                    default=str(ERROR_LOG_RETENTION_DAYS),
                )
                retention_days = int(retention_str)
        except Exception as e:
            logger.warning(f"Could not get error_log_retention setting: {e}")
            from backend.shared.config import ERROR_LOG_RETENTION_DAYS
            retention_days = ERROR_LOG_RETENTION_DAYS
    return await _cleanup_error_logs(retention_days)


async def _cleanup_error_logs(retention_days: int) -> dict:
    """Delete old error logs from database."""
    from backend.admin.logs.service import ErrorLogService

    try:
        async with get_db_context() as db:
            service = ErrorLogService(db)
            deleted = await service.delete_old_logs(days=retention_days)
            return {
                "deleted": deleted,
                "retention_days": retention_days,
                "success": True,
            }
    except Exception as e:
        logger.exception(f"Error cleaning up error logs: {e}")
        return {
            "deleted": 0,
            "retention_days": retention_days,
            "success": False,
            "error": str(e),
        }


@celery_app.task(name="cleanup.cleanup_expired_jobs")
def cleanup_expired_jobs() -> dict:
    """
    Clean up expired jobs from Redis and orphan upload directories.

    Checks both Redis and database to find orphaned directories
    (e.g., from interrupted uploads that never created a job).
    Directories older than 1 day with no matching job are removed.

    Returns:
        Cleanup statistics
    """
    return run_async(_async_cleanup_expired_jobs())


async def _async_cleanup_expired_jobs() -> dict:
    """Async implementation of expired jobs cleanup."""
    from backend.core.storage import get_job_store
    from sqlalchemy import select
    from backend.shared.models import TranscriptionJob

    stats = {
        "jobs_checked": 0,
        "orphaned_dirs_removed": 0,
        "errors": [],
    }

    try:
        # Collect known job IDs from Redis
        store = get_job_store()
        redis_job_ids: set[str] = set()
        prefix = store.KEY_PREFIX
        for key in store.redis.scan_iter(f"{prefix}*", count=100):
            job_id = (
                key.decode().removeprefix(prefix)
                if isinstance(key, bytes)
                else key.removeprefix(prefix)
            )
            redis_job_ids.add(job_id)
        stats["jobs_checked"] = len(redis_job_ids)

        # Collect known job IDs from database
        db_job_ids: set[str] = set()
        try:
            async with get_db_context() as db:
                result = await db.execute(
                    select(TranscriptionJob.job_id)
                )
                db_job_ids = {row[0] for row in result.all()}
        except Exception as e:
            logger.warning(f"Could not query DB for job IDs: {e}")

        known_job_ids = redis_job_ids | db_job_ids
        orphan_cutoff = datetime.now(timezone.utc) - timedelta(days=1)

        # Check for orphaned directories
        for directory in [UPLOAD_DIR, OUTPUT_DIR]:
            if not directory.exists():
                continue

            for job_dir in directory.iterdir():
                if not job_dir.is_dir():
                    continue

                job_id = job_dir.name
                if job_id in known_job_ids:
                    continue

                # Only remove if directory is older than 1 day
                dir_mtime = datetime.fromtimestamp(
                    job_dir.stat().st_mtime, tz=timezone.utc
                )
                if dir_mtime >= orphan_cutoff:
                    continue

                try:
                    shutil.rmtree(job_dir)
                    stats["orphaned_dirs_removed"] += 1
                    logger.info(f"Removed orphaned directory: {job_dir}")
                except Exception as e:
                    stats["errors"].append(f"Failed to remove {job_dir}: {e}")

    except Exception as e:
        stats["errors"].append(f"Error during orphan cleanup: {e}")
        logger.exception("Error during orphan cleanup")

    return stats


@celery_app.task(name="cleanup.recover_stuck_jobs")
def recover_stuck_jobs(
    stale_threshold_minutes: int = int(os.getenv("STUCK_JOB_THRESHOLD_MINUTES", "30")),
    dry_run: bool = False,
) -> dict:
    """
    Find and recover jobs stuck in 'processing' state.

    Jobs get stuck when worker crashes/restarts mid-processing.
    This task marks them as 'failed' so users can retry.

    Args:
        stale_threshold_minutes: Minutes since last update to consider stuck
        dry_run: If True, only report what would be recovered

    Returns:
        Recovery statistics
    """
    from backend.core.storage import get_job_store

    try:
        store = get_job_store()
        return store.recover_stuck_jobs(
            stale_threshold_minutes=stale_threshold_minutes,
            dry_run=dry_run,
        )
    except Exception as e:
        logger.exception(f"Error during stuck job recovery: {e}")
        return {
            "recovered": 0,
            "jobs": [],
            "errors": [str(e)],
            "dry_run": dry_run,
        }


@celery_app.task(name="cleanup.check_system_health")
def check_system_health_task() -> dict:
    """
    System watchdog: check for recent failures and send admin alerts.

    Queries ErrorLog and TranscriptionJob for failures in the last 15 minutes.
    Sends an admin email if thresholds are exceeded.
    """
    return run_async(_async_check_system_health())


async def _async_check_system_health() -> dict:
    """Async implementation of system health check."""
    from backend.admin.logs.service import ErrorLogService
    from backend.shared.models import TranscriptionJob, ErrorLog
    from sqlalchemy import select, func

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=15)

    failed_jobs_count = 0
    critical_errors = []
    recent_error_count = 0

    # Critical error patterns (Gemini quota, CUDA OOM)
    CRITICAL_PATTERNS = [
        "ResourceExhausted",
        "429",
        "CUDA out of memory",
        "OutOfMemoryError",
        "quota",
    ]

    try:
        async with get_db_context() as db:
            # Count failed jobs in last 15 minutes
            result = await db.execute(
                select(func.count(TranscriptionJob.id))
                .where(TranscriptionJob.status == "failed")
                .where(TranscriptionJob.updated_at >= window_start)
            )
            failed_jobs_count = result.scalar() or 0

            # Get recent error logs
            result = await db.execute(
                select(ErrorLog)
                .where(ErrorLog.timestamp >= window_start)
                .order_by(ErrorLog.timestamp.desc())
                .limit(50)
            )
            recent_errors = result.scalars().all()
            recent_error_count = len(recent_errors)

            # Check for critical patterns
            for err in recent_errors:
                detail = (err.error_detail or "") + (err.error_type or "")
                for pattern in CRITICAL_PATTERNS:
                    if pattern.lower() in detail.lower():
                        critical_errors.append({
                            "type": err.error_type,
                            "endpoint": err.endpoint,
                            "detail": (err.error_detail or "")[:200],
                            "timestamp": err.timestamp.isoformat() if err.timestamp else "",
                        })
                        break

            # Aggregate most frequent error types
            type_result = await db.execute(
                select(ErrorLog.error_type, func.count(ErrorLog.id).label("cnt"))
                .where(ErrorLog.timestamp >= window_start)
                .group_by(ErrorLog.error_type)
                .order_by(func.count(ErrorLog.id).desc())
                .limit(5)
            )
            top_error_types = {row[0]: row[1] for row in type_result.all()}

    except Exception as e:
        logger.exception(f"Watchdog DB query failed: {e}")
        return {"success": False, "error": str(e)}

    # Decide whether to alert
    should_alert = failed_jobs_count > 3 or len(critical_errors) > 0

    stats = {
        "failed_jobs_15min": failed_jobs_count,
        "error_logs_15min": recent_error_count,
        "critical_errors": len(critical_errors),
        "alerted": should_alert,
    }

    if should_alert:
        # Build alert message
        lines = []
        lines.append(f"<h2 style='margin:0 0 15px;color:#dc3545;'>Обнаружены проблемы</h2>")
        lines.append(f"<p><strong>Упавших задач за 15 мин:</strong> {failed_jobs_count}</p>")
        lines.append(f"<p><strong>Ошибок в логах за 15 мин:</strong> {recent_error_count}</p>")

        if critical_errors:
            lines.append("<h3 style='color:#dc3545;margin-top:20px;'>Критические ошибки:</h3>")
            lines.append("<ul>")
            for ce in critical_errors[:10]:
                lines.append(
                    f"<li><strong>{ce['type']}</strong> в <code>{ce['endpoint']}</code>"
                    f"<br><span style='color:#666;font-size:12px;'>{ce['detail']}</span></li>"
                )
            lines.append("</ul>")

        if top_error_types:
            lines.append("<h3 style='margin-top:20px;'>Частые типы ошибок:</h3>")
            lines.append("<ul>")
            for etype, count in top_error_types.items():
                lines.append(f"<li>{etype}: <strong>{count}</strong></li>")
            lines.append("</ul>")

        message = "\n".join(lines)

        try:
            from backend.core.email.service import email_service
            email_service.send_admin_alert(
                subject=f"⚠️ Watchdog: {failed_jobs_count} упавших задач, {len(critical_errors)} критических ошибок",
                message=message,
            )
        except Exception as e:
            logger.error(f"Watchdog alert email failed: {e}")
            stats["alert_error"] = str(e)

    logger.info(f"Watchdog check: {stats}")
    return stats


# Beat schedule is defined in celery_app.py (single source of truth)
