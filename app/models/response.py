"""API response and simulation models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.mission import ChangeEvent, MissionProfile


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class CropRecommendation(BaseModel):
    """Single ranked crop recommendation."""

    model_config = ConfigDict(extra="forbid")

    name: str
    score: float
    reason: str
    selected_system: str


class ResourcePlan(BaseModel):
    """Categorized resource allocation summary."""

    model_config = ConfigDict(extra="forbid")

    water_level: str
    energy_level: str
    area_usage: str


class RiskAnalysis(BaseModel):
    """Mission-level agriculture risk summary."""

    model_config = ConfigDict(extra="forbid")

    level: RiskLevel
    factors: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    """Main response body returned by the recommendation engine."""

    model_config = ConfigDict(extra="forbid")

    mission_profile: MissionProfile
    top_crops: list[CropRecommendation]
    recommended_system: str
    resource_plan: ResourcePlan
    risk_analysis: RiskAnalysis
    explanation: str


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
    updated_mission_profile: MissionProfile
    updated_recommendation: RecommendationResponse
    adaptation_reason: str


class HealthResponse(BaseModel):
    """Basic health response for demos and smoke tests."""

    model_config = ConfigDict(extra="forbid")

    status: str
    service: str

