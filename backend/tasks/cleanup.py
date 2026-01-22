"""
Cleanup tasks for audio file retention policy.

Provides periodic cleanup of old audio files while preserving
text reports and transcripts.
"""
import os
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


from backend.tasks.celery_app import celery_app
from backend.shared.database import get_db_context
from backend.admin.settings.service import SettingsService

logger = logging.getLogger(__name__)

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
    import asyncio

    # Run async cleanup in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _async_cleanup(retention_days, dry_run)
        )
    finally:
        loop.close()


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
                retention_str = await service.get_value(
                    "audio_retention_days",
                    default="7"  # Default 7 days
                )
                retention_days = int(retention_str)
        except Exception as e:
            logger.warning(f"Could not get retention setting, using default: {e}")
            retention_days = 7

    cutoff_date = datetime.now() - timedelta(days=retention_days)
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
            dir_mtime = datetime.fromtimestamp(job_dir.stat().st_mtime)
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
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
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
def cleanup_old_error_logs(retention_days: int = 30) -> dict:
    """
    Clean up old error logs from database.

    Args:
        retention_days: Days to keep error logs

    Returns:
        Cleanup statistics
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _cleanup_error_logs(retention_days)
        )
    finally:
        loop.close()


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
    Clean up expired jobs from Redis.

    Jobs are automatically expired by Redis TTL, but this task
    ensures consistency with filesystem cleanup.

    Returns:
        Cleanup statistics
    """
    from backend.core.storage import get_job_store

    stats = {
        "jobs_checked": 0,
        "orphaned_dirs_removed": 0,
        "errors": [],
    }

    try:
        store = get_job_store()
        jobs = store.list_jobs(limit=10000)
        job_ids = {job.job_id for job in jobs}
        stats["jobs_checked"] = len(jobs)

        # Check for orphaned directories
        for directory in [UPLOAD_DIR, OUTPUT_DIR]:
            if not directory.exists():
                continue

            for job_dir in directory.iterdir():
                if not job_dir.is_dir():
                    continue

                job_id = job_dir.name
                if job_id not in job_ids:
                    # Orphaned directory - job no longer exists in Redis
                    try:
                        shutil.rmtree(job_dir)
                        stats["orphaned_dirs_removed"] += 1
                        logger.info(f"Removed orphaned directory: {job_dir}")
                    except Exception as e:
                        stats["errors"].append(f"Failed to remove {job_dir}: {e}")

    except Exception as e:
        stats["errors"].append(f"Error during orphan cleanup: {e}")
        logger.exception(f"Error during orphan cleanup")

    return stats


# Celery Beat schedule (optional - configure in celery_app.py)
CLEANUP_SCHEDULE = {
    "cleanup-audio-files-daily": {
        "task": "cleanup.cleanup_old_audio_files",
        "schedule": 86400.0,  # Every 24 hours
        "args": (),
    },
    "cleanup-error-logs-weekly": {
        "task": "cleanup.cleanup_old_error_logs",
        "schedule": 604800.0,  # Every 7 days
        "args": (30,),  # Keep 30 days
    },
    "cleanup-expired-jobs-hourly": {
        "task": "cleanup.cleanup_expired_jobs",
        "schedule": 3600.0,  # Every hour
        "args": (),
    },
}
