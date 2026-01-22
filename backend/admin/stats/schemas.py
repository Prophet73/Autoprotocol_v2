"""
Schemas for comprehensive system statistics.

Supports:
- Global overview stats
- Domain-specific stats
- Meeting type breakdowns
- User activity stats
- Cost analytics (Gemini tokens)
- Time-based analytics
"""
from datetime import datetime, date
from typing import Dict, List, Optional
from pydantic import BaseModel

from backend.domains.base_schemas import DOMAIN_MEETING_TYPES


# =============================================================================
# Gemini Pricing (per million tokens)
# =============================================================================

class GeminiPricing:
    """Gemini API pricing constants (USD per million tokens)."""
    # Flash 2.0 (default model)
    FLASH_2_INPUT = 0.10  # $0.10 per 1M input tokens
    FLASH_2_OUTPUT = 0.40  # $0.40 per 1M output tokens

    # Flash 2.5
    FLASH_25_INPUT = 0.30
    FLASH_25_OUTPUT = 2.50

    # Current model in use
    INPUT_PRICE = FLASH_2_INPUT
    OUTPUT_PRICE = FLASH_2_OUTPUT

    @classmethod
    def calculate_cost(cls, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost in USD."""
        input_cost = (input_tokens / 1_000_000) * cls.INPUT_PRICE
        output_cost = (output_tokens / 1_000_000) * cls.OUTPUT_PRICE
        return round(input_cost + output_cost, 4)


# =============================================================================
# Filter Schemas
# =============================================================================

class StatsFilters(BaseModel):
    """Common filters for stats queries."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    domain: Optional[str] = None
    meeting_type: Optional[str] = None
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    status: Optional[str] = None


# =============================================================================
# KPI Schemas
# =============================================================================

class KPIStats(BaseModel):
    """Key Performance Indicators."""
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    pending_jobs: int = 0
    processing_jobs: int = 0
    success_rate: float = 0.0  # percentage

    total_processing_hours: float = 0.0
    avg_processing_minutes: float = 0.0
    total_audio_hours: float = 0.0

    total_cost_usd: float = 0.0
    avg_cost_per_job: float = 0.0


# =============================================================================
# Domain Stats
# =============================================================================

class MeetingTypeStats(BaseModel):
    """Stats for a single meeting type."""
    meeting_type: str
    name: str
    count: int = 0
    completed: int = 0
    failed: int = 0
    success_rate: float = 0.0
    total_processing_seconds: float = 0.0
    total_audio_seconds: float = 0.0


class DomainStats(BaseModel):
    """Stats for a single domain."""
    domain: str
    display_name: str
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    success_rate: float = 0.0
    total_processing_hours: float = 0.0
    total_audio_hours: float = 0.0
    total_cost_usd: float = 0.0
    meeting_types: List[MeetingTypeStats] = []


class DomainsBreakdown(BaseModel):
    """Stats breakdown by all domains."""
    domains: List[DomainStats] = []

    @classmethod
    def get_domain_names(cls) -> List[str]:
        """Get list of available domains from config."""
        return list(DOMAIN_MEETING_TYPES.keys())


# =============================================================================
# Project Stats (for Construction domain)
# =============================================================================

class ProjectStats(BaseModel):
    """Stats for a single project."""
    project_id: int
    project_name: str
    project_code: str
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    success_rate: float = 0.0
    total_processing_hours: float = 0.0
    total_audio_hours: float = 0.0
    last_activity: Optional[datetime] = None


class ProjectsBreakdown(BaseModel):
    """Stats breakdown by projects."""
    projects: List[ProjectStats] = []
    total_projects: int = 0


# =============================================================================
# User Stats
# =============================================================================

class UserActivityStats(BaseModel):
    """Activity stats for a single user."""
    user_id: int
    email: str
    full_name: Optional[str] = None
    role: str
    total_jobs: int = 0
    completed_jobs: int = 0
    domains_used: List[str] = []
    last_activity: Optional[datetime] = None


class UsersStats(BaseModel):
    """User statistics."""
    total_users: int = 0
    active_users: int = 0  # users with at least 1 job
    by_role: Dict[str, int] = {}
    by_domain: Dict[str, int] = {}
    top_users: List[UserActivityStats] = []


# =============================================================================
# Cost Stats
# =============================================================================

class CostStats(BaseModel):
    """AI cost statistics."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_cost_per_job: float = 0.0
    by_domain: Dict[str, float] = {}  # cost per domain

    # Pricing info
    input_price_per_million: float = GeminiPricing.INPUT_PRICE
    output_price_per_million: float = GeminiPricing.OUTPUT_PRICE


# =============================================================================
# Timeline Stats
# =============================================================================

class TimelinePoint(BaseModel):
    """Single point on timeline."""
    date: str  # YYYY-MM-DD
    jobs: int = 0
    completed: int = 0
    failed: int = 0


class TimelineStats(BaseModel):
    """Time-based statistics."""
    points: List[TimelinePoint] = []
    period: str = "daily"  # daily, weekly, monthly
    total_days: int = 0


# =============================================================================
# Error Stats
# =============================================================================

class ErrorStats(BaseModel):
    """Error statistics."""
    total_errors: int = 0
    error_rate: float = 0.0
    by_stage: Dict[str, int] = {}  # errors per processing stage
    by_domain: Dict[str, int] = {}  # errors per domain
    recent_errors: List[Dict] = []  # last N errors with details


# =============================================================================
# Artifacts Stats
# =============================================================================

class ArtifactsStats(BaseModel):
    """Statistics about generated artifacts."""
    transcripts_generated: int = 0
    tasks_generated: int = 0
    reports_generated: int = 0
    analysis_generated: int = 0

    # Percentage of jobs with each artifact
    transcript_rate: float = 0.0
    tasks_rate: float = 0.0
    report_rate: float = 0.0
    analysis_rate: float = 0.0


# =============================================================================
# Main Response Schemas
# =============================================================================

class OverviewStatsResponse(BaseModel):
    """Global overview statistics response."""
    kpi: KPIStats
    domains: DomainsBreakdown
    timeline: TimelineStats
    artifacts: ArtifactsStats
    filters_applied: StatsFilters
    generated_at: datetime


class DomainStatsResponse(BaseModel):
    """Domain-specific statistics response."""
    domain: DomainStats
    projects: Optional[ProjectsBreakdown] = None  # Only for construction
    timeline: TimelineStats
    errors: ErrorStats
    filters_applied: StatsFilters
    generated_at: datetime


class UsersStatsResponse(BaseModel):
    """User statistics response."""
    users: UsersStats
    timeline: TimelineStats
    filters_applied: StatsFilters
    generated_at: datetime


class CostStatsResponse(BaseModel):
    """Cost statistics response."""
    costs: CostStats
    timeline: List[Dict] = []  # cost over time
    filters_applied: StatsFilters
    generated_at: datetime


class FullDashboardResponse(BaseModel):
    """Complete dashboard with all stats."""
    overview: KPIStats
    domains: DomainsBreakdown
    users: UsersStats
    costs: CostStats
    timeline: TimelineStats
    artifacts: ArtifactsStats
    errors: ErrorStats
    filters_applied: StatsFilters
    generated_at: datetime


# =============================================================================
# Legacy schemas (for backwards compatibility)
# =============================================================================

class TranscriptionStats(BaseModel):
    """Transcription job statistics by status."""
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    total: int = 0


class StorageStats(BaseModel):
    """Storage usage statistics."""
    total_bytes: int = 0
    total_mb: float = 0.0
    total_gb: float = 0.0
    uploads_bytes: int = 0
    outputs_bytes: int = 0


class UserStatsLegacy(BaseModel):
    """User statistics (legacy)."""
    total_users: int = 0
    active_users: int = 0
    superusers: int = 0
    by_role: Dict[str, int] = {}
    by_domain: Dict[str, int] = {}


class DomainStatsLegacy(BaseModel):
    """Statistics by domain (legacy)."""
    construction: int = 0
    hr: int = 0
    it: int = 0
    general: int = 0


class GlobalStatsResponse(BaseModel):
    """Global system statistics response (legacy)."""
    users: UserStatsLegacy
    transcriptions: TranscriptionStats
    storage: StorageStats
    domains: DomainStatsLegacy
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
