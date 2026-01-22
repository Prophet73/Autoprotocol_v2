"""
HR Domain Schemas.

Pydantic models for HR meeting analysis.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.domains.base_schemas import BaseMeetingReport


class HRMeetingType(str, Enum):
    """Types of HR meetings."""
    RECRUITMENT = "recruitment"
    ONE_ON_ONE = "one_on_one"
    PERFORMANCE_REVIEW = "performance_review"
    TEAM_MEETING = "team_meeting"
    ONBOARDING = "onboarding"


# =============================================================================
# Recruitment Schemas
# =============================================================================

class CandidateMatch(str, Enum):
    """How well candidate matches requirements."""
    STRONG_MATCH = "strong_match"
    PARTIAL_MATCH = "partial_match"
    WEAK_MATCH = "weak_match"


class HireRecommendation(str, Enum):
    """Hiring recommendation."""
    HIRE = "hire"
    CONSIDER = "consider"
    REJECT = "reject"


class CandidateAssessment(BaseModel):
    """Assessment of a job candidate."""
    match_level: CandidateMatch
    strengths: List[str] = Field(default_factory=list)
    development_areas: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recommendation: HireRecommendation
    follow_up_questions: List[str] = Field(default_factory=list)


# =============================================================================
# One-on-One Schemas
# =============================================================================

class EmployeeMood(str, Enum):
    """Employee mood assessment."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CONCERNED = "concerned"
    NEGATIVE = "negative"


class AttritionRisk(str, Enum):
    """Risk of employee leaving."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EmployeeFeedback(BaseModel):
    """Feedback from one-on-one meeting."""
    mood: EmployeeMood
    key_topics: List[str] = Field(default_factory=list)
    career_requests: List[str] = Field(default_factory=list)
    training_requests: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    attrition_risk: AttritionRisk
    hr_recommendations: List[str] = Field(default_factory=list)


# =============================================================================
# Performance Review Schemas
# =============================================================================

class PerformanceRating(str, Enum):
    """Performance rating."""
    EXCEEDS = "exceeds"
    MEETS = "meets"
    BELOW = "below"


class PerformanceReview(BaseModel):
    """Performance review assessment."""
    overall_rating: PerformanceRating
    achievements: List[str] = Field(default_factory=list)
    development_areas: List[str] = Field(default_factory=list)
    goals_next_period: List[str] = Field(default_factory=list)
    manager_feedback: Optional[str] = None
    employee_feedback: Optional[str] = None


# =============================================================================
# Team Meeting Schemas
# =============================================================================

class TeamAtmosphere(str, Enum):
    """Team meeting atmosphere."""
    COLLABORATIVE = "collaborative"
    FORMAL = "formal"
    TENSE = "tense"
    CONFLICT = "conflict"


class TeamDynamics(BaseModel):
    """Team dynamics observation."""
    atmosphere: TeamAtmosphere
    leaders: List[str] = Field(default_factory=list)
    silent_participants: List[str] = Field(default_factory=list)
    decision_making_style: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)


# =============================================================================
# Onboarding Schemas
# =============================================================================

class OnboardingStage(str, Enum):
    """Onboarding stage."""
    ORIENTATION = "orientation"
    TRAINING = "training"
    INTEGRATION = "integration"


class NewHireImpression(str, Enum):
    """New hire impression."""
    ENTHUSIASTIC = "enthusiastic"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    OVERWHELMED = "overwhelmed"
    CONFUSED = "confused"


class OnboardingProgress(BaseModel):
    """Onboarding session progress."""
    stage: OnboardingStage
    topics_covered: List[str] = Field(default_factory=list)
    questions_asked: List[str] = Field(default_factory=list)
    gaps_identified: List[str] = Field(default_factory=list)
    new_hire_impression: NewHireImpression


# =============================================================================
# Main HR Report Schema
# =============================================================================

class HRReport(BaseMeetingReport):
    """
    HR meeting analysis report.

    Contains type-specific assessment based on meeting type.
    """
    meeting_type: HRMeetingType

    # Type-specific assessments (only one will be populated)
    candidate_assessment: Optional[CandidateAssessment] = None
    employee_feedback: Optional[EmployeeFeedback] = None
    performance_review: Optional[PerformanceReview] = None
    team_dynamics: Optional[TeamDynamics] = None
    onboarding_progress: Optional[OnboardingProgress] = None
