"""
System statistics service.

Provides aggregated statistics for:
- Users
- Transcriptions
- Storage usage
- Domain breakdown
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import User
from backend.core.storage.job_store import get_job_store, JobData
from backend.core.transcription.models import JobStatus
from .schemas import (
    GlobalStatsResponse,
    UserStats,
    TranscriptionStats,
    StorageStats,
    DomainStats,
    SystemHealthResponse,
)

logger = logging.getLogger(__name__)

# Data directories
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"


class StatsService:
    """Service for system statistics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_stats(self) -> UserStats:
        """Get user statistics."""
        # Total users
        total_result = await self.db.execute(select(func.count(User.id)))
        total = total_result.scalar() or 0

        # Active users
        active_result = await self.db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active = active_result.scalar() or 0

        # Superusers
        super_result = await self.db.execute(
            select(func.count(User.id)).where(User.is_superuser == True)
        )
        superusers = super_result.scalar() or 0

        # By role
        role_result = await self.db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        by_role = {role: count for role, count in role_result.all()}

        # By domain
        domain_result = await self.db.execute(
            select(User.domain, func.count(User.id))
            .where(User.domain.isnot(None))
            .group_by(User.domain)
        )
        by_domain = {domain: count for domain, count in domain_result.all()}

        return UserStats(
            total_users=total,
            active_users=active,
            superusers=superusers,
            by_role=by_role,
            by_domain=by_domain,
        )

    def get_transcription_stats(self) -> TranscriptionStats:
        """Get transcription job statistics from Redis."""
        try:
            job_store = get_job_store()
            jobs = job_store.list_jobs(limit=10000)

            stats = TranscriptionStats()
            for job in jobs:
                stats.total += 1
                if job.status == JobStatus.PENDING:
                    stats.pending += 1
                elif job.status == JobStatus.PROCESSING:
                    stats.processing += 1
                elif job.status == JobStatus.COMPLETED:
                    stats.completed += 1
                elif job.status == JobStatus.FAILED:
                    stats.failed += 1

            return stats
        except Exception as e:
            logger.error(f"Failed to get transcription stats: {e}")
            return TranscriptionStats()

    def get_storage_stats(self) -> StorageStats:
        """Calculate storage usage."""
        try:
            uploads_bytes = self._get_directory_size(UPLOAD_DIR)
            outputs_bytes = self._get_directory_size(OUTPUT_DIR)
            total_bytes = uploads_bytes + outputs_bytes

            return StorageStats(
                total_bytes=total_bytes,
                total_mb=round(total_bytes / (1024 * 1024), 2),
                total_gb=round(total_bytes / (1024 * 1024 * 1024), 3),
                uploads_bytes=uploads_bytes,
                outputs_bytes=outputs_bytes,
            )
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return StorageStats()

    def _get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory recursively."""
        if not path.exists():
            return 0

        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception as e:
            logger.warning(f"Error calculating size for {path}: {e}")

        return total

    def get_domain_stats(self) -> DomainStats:
        """Get transcription count by domain (based on job metadata)."""
        # For now, return zeros as domain is not tracked per job
        # This could be enhanced by adding domain to JobData
        return DomainStats()

    async def get_global_stats(self) -> GlobalStatsResponse:
        """Get all global statistics."""
        user_stats = await self.get_user_stats()
        transcription_stats = self.get_transcription_stats()
        storage_stats = self.get_storage_stats()
        domain_stats = self.get_domain_stats()

        # Check Redis
        try:
            job_store = get_job_store()
            redis_connected = job_store.health_check()
        except Exception as e:
            logger.debug(f"Redis health check failed: {e}")
            redis_connected = False

        # Check GPU
        gpu_available = self._check_gpu()

        return GlobalStatsResponse(
            users=user_stats,
            transcriptions=transcription_stats,
            storage=storage_stats,
            domains=domain_stats,
            redis_connected=redis_connected,
            gpu_available=gpu_available,
            generated_at=datetime.now(),
        )

    def _check_gpu(self) -> bool:
        """Check if GPU is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    async def get_system_health(self) -> SystemHealthResponse:
        """Get system health status."""
        import psutil

        # Redis check
        try:
            job_store = get_job_store()
            redis_ok = job_store.health_check()
        except Exception as e:
            logger.debug(f"Redis health check failed: {e}")
            redis_ok = False

        # Database check
        try:
            await self.db.execute(select(1))
            db_ok = True
        except Exception as e:
            logger.debug(f"Database health check failed: {e}")
            db_ok = False

        # GPU check
        gpu_ok = self._check_gpu()

        # Celery check
        celery_ok = self._check_celery()

        # System resources
        disk = psutil.disk_usage("/")
        memory = psutil.virtual_memory()

        # Overall status
        all_ok = redis_ok and db_ok
        status = "healthy" if all_ok else "degraded"

        return SystemHealthResponse(
            status=status,
            redis=redis_ok,
            database=db_ok,
            gpu=gpu_ok,
            celery=celery_ok,
            disk_usage_percent=disk.percent,
            memory_usage_percent=memory.percent,
        )

    def _check_celery(self) -> bool:
        """Check if Celery is reachable."""
        try:
            from backend.tasks.celery_app import celery_app
            # Ping the broker
            celery_app.control.ping(timeout=1.0)
            return True
        except Exception as e:
            logger.debug(f"Celery health check failed: {e}")
            return False
