"""
IT Domain Schemas.

Pydantic models for IT/Development meeting analysis.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.domains.base_schemas import BaseMeetingReport, ActionItem


class ITMeetingType(str, Enum):
    """Types of IT meetings."""
    STANDUP = "standup"
    PLANNING = "planning"
    RETROSPECTIVE = "retrospective"
    INCIDENT_REVIEW = "incident_review"
    ARCHITECTURE = "architecture"
    DEMO = "demo"


# =============================================================================
# Standup Schemas
# =============================================================================

class SprintStatus(str, Enum):
    """Sprint status."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"


class ParticipantStatus(BaseModel):
    """Individual participant status from standup."""
    name: str
    yesterday: List[str] = Field(default_factory=list)
    today: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)


class Blocker(BaseModel):
    """A blocker preventing progress."""
    description: str
    owner: Optional[str] = None
    severity: str = "medium"  # low, medium, high
    needs_escalation: bool = False


class StandupSummary(BaseModel):
    """Summary of a standup meeting."""
    sprint_status: SprintStatus
    participants: List[ParticipantStatus] = Field(default_factory=list)
    team_blockers: List[Blocker] = Field(default_factory=list)
    attention_items: List[str] = Field(default_factory=list)


# =============================================================================
# Planning Schemas
# =============================================================================

class SprintGoal(BaseModel):
    """Sprint goal."""
    description: str
    priority: int = 1


class PlannedTask(BaseModel):
    """Task planned for sprint."""
    title: str
    estimate: Optional[str] = None  # story points or hours
    assignee: Optional[str] = None


class SprintCapacity(BaseModel):
    """Team capacity for sprint."""
    total_points: Optional[int] = None
    total_hours: Optional[int] = None
    team_availability: Optional[str] = None


class PlanningResult(BaseModel):
    """Result of sprint planning."""
    sprint_goals: List[SprintGoal] = Field(default_factory=list)
    planned_tasks: List[PlannedTask] = Field(default_factory=list)
    capacity: Optional[SprintCapacity] = None
    risks: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


# =============================================================================
# Retrospective Schemas
# =============================================================================

class TeamMood(str, Enum):
    """Team mood."""
    ENERGIZED = "energized"
    STABLE = "stable"
    TIRED = "tired"
    FRUSTRATED = "frustrated"


class Improvement(BaseModel):
    """Improvement item from retrospective."""
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None


class RetroResult(BaseModel):
    """Result of retrospective."""
    went_well: List[str] = Field(default_factory=list)
    to_improve: List[str] = Field(default_factory=list)
    action_items: List[Improvement] = Field(default_factory=list)
    team_mood: TeamMood = TeamMood.STABLE
    trends: List[str] = Field(default_factory=list)


# =============================================================================
# Incident Review Schemas
# =============================================================================

class IncidentSeverity(str, Enum):
    """Incident severity."""
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"
    SEV4 = "sev4"


class TimelineEvent(BaseModel):
    """Event in incident timeline."""
    time: str
    description: str
    actor: Optional[str] = None


class IncidentImpact(BaseModel):
    """Incident impact assessment."""
    duration_minutes: Optional[int] = None
    affected_users: Optional[str] = None
    affected_services: List[str] = Field(default_factory=list)
    business_impact: Optional[str] = None


class IncidentActionItem(BaseModel):
    """Action item from incident review."""
    description: str
    category: str  # prevent, detect, mitigate
    owner: Optional[str] = None
    due_date: Optional[str] = None


class IncidentReview(BaseModel):
    """Incident review summary."""
    summary: str
    severity: Optional[IncidentSeverity] = None
    timeline: List[TimelineEvent] = Field(default_factory=list)
    root_cause: Optional[str] = None
    impact: Optional[IncidentImpact] = None
    action_items: List[IncidentActionItem] = Field(default_factory=list)
    lessons_learned: List[str] = Field(default_factory=list)


# =============================================================================
# Architecture Schemas
# =============================================================================

class TechnicalDecision(BaseModel):
    """Technical decision from architecture discussion."""
    topic: str
    decision: str
    rationale: Optional[str] = None
    trade_offs: List[str] = Field(default_factory=list)


class ArchitectureResult(BaseModel):
    """Result of architecture discussion."""
    topic: str
    options_considered: List[str] = Field(default_factory=list)
    decision: Optional[TechnicalDecision] = None
    next_steps: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)


# =============================================================================
# Demo Schemas
# =============================================================================

class DemoFeedback(BaseModel):
    """Feedback from demo."""
    positive: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)


class DemoResult(BaseModel):
    """Result of sprint demo."""
    features_shown: List[str] = Field(default_factory=list)
    feedback: Optional[DemoFeedback] = None
    accepted: List[str] = Field(default_factory=list)
    needs_rework: List[str] = Field(default_factory=list)
    new_requests: List[str] = Field(default_factory=list)
    sprint_achievements: List[str] = Field(default_factory=list)


# =============================================================================
# Main IT Report Schema
# =============================================================================

class ITReport(BaseMeetingReport):
    """
    IT meeting analysis report.

    Contains type-specific results based on meeting type.
    """
    meeting_type: ITMeetingType

    # Type-specific results (only one will be populated)
    standup_summary: Optional[StandupSummary] = None
    planning_result: Optional[PlanningResult] = None
    retro_result: Optional[RetroResult] = None
    incident_review: Optional[IncidentReview] = None
    architecture_result: Optional[ArchitectureResult] = None
    demo_result: Optional[DemoResult] = None
