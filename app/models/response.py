"""API response and simulation models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.mission import ChangeEvent, MissionProfile


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class MissionStatus(StrEnum):
    NOMINAL = "NOMINAL"
    WATCH = "WATCH"
    CRITICAL = "CRITICAL"


class MetricBreakdown(BaseModel):
    """Normalized crop metric view for UI presentation."""

    model_config = ConfigDict(extra="forbid")

    calorie: float
    water: float
    energy: float
    growth_time: float
    risk: float
    maintenance: float


class CropRecommendation(BaseModel):
    """Single ranked crop recommendation."""

    model_config = ConfigDict(extra="forbid")

    name: str
    score: float
    reason: str
    selected_system: str
    strengths: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    metric_breakdown: MetricBreakdown
    compatibility_score: float


class ResourcePlan(BaseModel):
    """Categorized resource allocation summary."""

    model_config = ConfigDict(extra="forbid")

    water_level: str
    energy_level: str
    area_usage: str
    water_score: float
    energy_score: float
    area_score: float
    maintenance_score: float
    calorie_score: float


class RiskAnalysis(BaseModel):
    """Mission-level agriculture risk summary."""

    model_config = ConfigDict(extra="forbid")

    level: RiskLevel
    score: float
    factors: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    """Main response body returned by the recommendation engine."""

    model_config = ConfigDict(extra="forbid")

    mission_profile: MissionProfile
    top_crops: list[CropRecommendation]
    recommended_system: str
    system_reason: str
    system_reasoning: str
    why_this_system: str
    tradeoff_summary: str
    resource_plan: ResourcePlan
    risk_analysis: RiskAnalysis
    mission_status: MissionStatus
    executive_summary: str
    operational_note: str
    explanation: str


class RiskDelta(StrEnum):
    INCREASED = "increased"
    DECREASED = "decreased"
    UNCHANGED = "unchanged"


class SimulationRequest(BaseModel):
    """Request body for lightweight runtime adaptation simulation."""

    model_config = ConfigDict(extra="forbid")

    mission_profile: MissionProfile
    change_event: ChangeEvent
    affected_crop: str | None = None
    previous_recommendation: RecommendationResponse | None = None


class SimulationResponse(BaseModel):
    """Response body for simulated runtime updates."""

    model_config = ConfigDict(extra="forbid")

    change_event: ChangeEvent
    changed_fields: list[str] = Field(default_factory=list)
    previous_top_crop: str | None = None
    new_top_crop: str | None = None
    ranking_diff: dict[str, int] = Field(default_factory=dict)
    system_changed: bool
    previous_system: str | None = None
    new_system: str | None = None
    risk_delta: RiskDelta
    risk_score_delta: float
    previous_mission_status: MissionStatus
    new_mission_status: MissionStatus
    updated_mission_profile: MissionProfile
    updated_recommendation: RecommendationResponse
    adaptation_summary: str
    reason: str
    adaptation_reason: str


class HealthResponse(BaseModel):
    """Basic health response for demos and smoke tests."""

    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
