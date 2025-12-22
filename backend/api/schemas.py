"""API request/response schemas."""
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from ..core.transcription.models import JobStatus


class TranscribeRequest(BaseModel):
    """Request to start transcription."""
    languages: List[str] = Field(
        default=["ru"],
        description="Languages to transcribe (e.g., ['ru', 'zh', 'en'])"
    )
    skip_diarization: bool = Field(default=False, description="Skip speaker identification")
    skip_translation: bool = Field(default=False, description="Skip translation to Russian")
    skip_emotions: bool = Field(default=False, description="Skip emotion analysis")


class JobResponse(BaseModel):
    """Response with job info."""
    job_id: str
    status: JobStatus
    created_at: datetime
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: JobStatus
    current_stage: Optional[str] = None
    progress_percent: int = 0
    message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class JobResultResponse(BaseModel):
    """Job result with output files."""
    job_id: str
    status: JobStatus
    source_file: str
    processing_time_seconds: float
    segment_count: int
    language_distribution: Dict[str, int]
    output_files: Dict[str, str]
    completed_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "v4"
    gpu_available: bool = False
    gpu_name: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
