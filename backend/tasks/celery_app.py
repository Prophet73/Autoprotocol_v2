"""Celery application configuration."""
import os
from celery import Celery

# Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "whisperx_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.tasks.transcription"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "transcription.*": {"queue": "transcription"},
    },

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time (GPU constraint)
    worker_concurrency=1,  # Single worker per GPU

    # Task time limits
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=7200,  # 2 hour hard limit

    # Result backend
    result_expires=86400,  # Results expire after 24 hours

    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,
)
