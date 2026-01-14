"""
Schemas for system statistics endpoints.
"""
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class TranscriptionStats(BaseModel):
    """Transcription job statistics by status."""
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    total: int = 0


class DomainStats(BaseModel):
    """Statistics by domain."""
    construction: int = 0
    hr: int = 0
    it: int = 0
    general: int = 0


class StorageStats(BaseModel):
    """Storage usage statistics."""
    total_bytes: int = 0
    total_mb: float = 0.0
    total_gb: float = 0.0
    uploads_bytes: int = 0
    outputs_bytes: int = 0


class UserStats(BaseModel):
    """User statistics."""
    total_users: int = 0
    active_users: int = 0
    superusers: int = 0
    by_role: Dict[str, int] = {}
    by_domain: Dict[str, int] = {}


class GlobalStatsResponse(BaseModel):
    """Global system statistics response."""
    users: UserStats
    transcriptions: TranscriptionStats
    storage: StorageStats
    domains: DomainStats
    redis_connected: bool = True
    gpu_available: bool = False
    generated_at: datetime


class SystemHealthResponse(BaseModel):
    """System health status."""
    status: str
    redis: bool
    database: bool
    gpu: bool
    celery: bool
    disk_usage_percent: float
    memory_usage_percent: float
