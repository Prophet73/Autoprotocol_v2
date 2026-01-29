"""
Admin Jobs Router - управление очередью задач.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.auth.dependencies import require_admin
from backend.core.storage import get_job_store
from backend.shared.database import get_db
from backend.shared.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Админ - Задачи"])


@router.get("", summary="Список всех задач")
async def list_all_jobs(
    limit: int = 100,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список всех задач из Redis (для админов).
    Включает информацию о пользователе-загрузчике.
    """
    store = get_job_store()
    all_jobs = store.list_jobs(limit=limit)

    # Get user emails for uploader_ids
    user_emails = {}
    uploader_ids = set(
        job.uploader_id for job in all_jobs
        if hasattr(job, 'uploader_id') and job.uploader_id
    )

    if uploader_ids:
        result = await db.execute(
            select(User.id, User.email).where(User.id.in_(uploader_ids))
        )
        user_emails = {row.id: row.email for row in result.fetchall()}

    jobs_data = []
    for job in all_jobs:
        uploader_id = getattr(job, 'uploader_id', None)
        uploader_email = user_emails.get(uploader_id) if uploader_id else None

        jobs_data.append({
            "job_id": job.job_id,
            "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "source_file": Path(job.input_file).name if job.input_file else None,
            "progress_percent": job.progress_percent or 0,
            "current_stage": job.current_stage,
            "message": job.message,
            "project_code": getattr(job, 'project_code', None),
            "uploader_email": uploader_email,
            "error": job.error,
        })

    return {"jobs": jobs_data}


@router.delete("/{job_id}", summary="Отменить задачу")
async def cancel_job(
    job_id: str,
    _: User = Depends(require_admin),
):
    """
    Принудительно отменить задачу (для админов).
    """
    from backend.core.transcription.models import JobStatus

    store = get_job_store()
    job = store.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )

    # Mark as failed with cancellation message
    store.fail(job_id, "Cancelled by admin")

    # Try to revoke Celery task
    try:
        from backend.tasks.celery_app import celery_app

        celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
        logger.info(f"Job {job_id} cancelled by admin and task revoked")
    except Exception as e:
        logger.warning(f"Could not revoke Celery task: {e}")

    return {"success": True, "message": "Job cancelled by admin"}
