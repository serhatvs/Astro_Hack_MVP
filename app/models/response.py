"""API response and simulation models."""

from __future__ import annotations

from enum import StrEnum
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.mission_state import MissionState
from app.core.simulation import MissionEvents, MissionStepRequest
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


class SelectedDomainSystem(BaseModel):
    """Selected candidate for one biological domain."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    domain_score: float
    mission_fit_score: float
    risk_score: float
    support_system: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class SelectedSystemBundle(BaseModel):
    """Integrated selection grouped by biological domain."""

    model_config = ConfigDict(extra="forbid")

    crop: SelectedDomainSystem
    algae: SelectedDomainSystem
    microbial: SelectedDomainSystem


class DomainScoreVector(BaseModel):
    """Domain scoring vector exposed to the API."""

    model_config = ConfigDict(extra="forbid")

    domain_score: float
    mission_fit_score: float
    risk_score: float


class DomainScoreBundle(BaseModel):
    """Grouped domain scores for the selected configuration."""

    model_config = ConfigDict(extra="forbid")

    crop: DomainScoreVector
    algae: DomainScoreVector
    microbial: DomainScoreVector


class InteractionScoreBundle(BaseModel):
    """Interaction metrics across selected domains."""

    model_config = ConfigDict(extra="forbid")

    synergy_score: float
    conflict_score: float
    complexity_penalty: float
    resource_overlap: float
    loop_closure_bonus: float


class ScoreBundle(BaseModel):
    """Overall score payload for the integrated configuration."""

    model_config = ConfigDict(extra="forbid")

    domain: DomainScoreBundle
    interaction: InteractionScoreBundle
    integrated: float


class ExplanationBundle(BaseModel):
    """Narrative explanation fields for the selected configuration."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    system_reasoning: str
    tradeoffs: str
    weak_points: str


class UIEnhancedNarrative(BaseModel):
    """UI-ready Gemini or deterministic summary layer."""

    model_config = ConfigDict(extra="forbid")

    crop_note: str = ""
    algae_note: str = ""
    microbial_note: str = ""
    executive_summary: str = ""
    adaptation_summary: str = ""

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any] | None = None,
        defaults: Mapping[str, Any] | None = None,
    ) -> "UIEnhancedNarrative":
        """Create a normalized UI summary payload with stable keys."""

        payload = payload or {}
        defaults = defaults or {}
        return cls(
            crop_note=cls._normalize_text(payload.get("crop_note"), defaults.get("crop_note", "")),
            algae_note=cls._normalize_text(payload.get("algae_note"), defaults.get("algae_note", "")),
            microbial_note=cls._normalize_text(payload.get("microbial_note"), defaults.get("microbial_note", "")),
            executive_summary=cls._normalize_text(
                payload.get("executive_summary"),
                defaults.get("executive_summary", ""),
            ),
            adaptation_summary=cls._normalize_text(
                payload.get("adaptation_summary"),
                defaults.get("adaptation_summary", ""),
            ),
        )

    @staticmethod
    def _normalize_text(value: Any, default: str = "") -> str:
        if not isinstance(value, str):
            return str(default).strip()
        value = value.strip()
        return value if value else str(default).strip()


class LLMAnalysis(BaseModel):
    """Structured LLM critic output."""

    model_config = ConfigDict(extra="forbid")

    reasoning_summary: str
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    alternative: dict[str, Any] = Field(default_factory=dict)
    alternative_configuration: dict[str, Any] = Field(default_factory=dict)
    second_pass: dict[str, Any] = Field(default_factory=dict)
    second_pass_decision: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any] | None = None,
        default_reasoning: str = "Deterministic fallback analysis remains active.",
    ) -> "LLMAnalysis":
        """Create a normalized LLM analysis payload with stable canonical fields."""

        payload = payload or {}
        improvements = cls._normalize_list(
            payload.get("improvements", payload.get("improvement_suggestions")),
        )
        alternative = cls._normalize_dict(
            payload.get("alternative", payload.get("alternative_configuration")),
        )
        second_pass = cls._normalize_dict(
            payload.get("second_pass", payload.get("second_pass_decision")),
        )
        reasoning_summary = payload.get("reasoning_summary")
        if not isinstance(reasoning_summary, str) or not reasoning_summary.strip():
            reasoning_summary = default_reasoning

        return cls(
            reasoning_summary=reasoning_summary.strip(),
            weaknesses=cls._normalize_list(payload.get("weaknesses")),
            improvements=improvements,
            improvement_suggestions=list(improvements),
            alternative=alternative,
            alternative_configuration=dict(alternative),
            second_pass=second_pass,
            second_pass_decision=dict(second_pass),
        )

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _normalize_dict(value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            return {}
        return {str(key): item for key, item in value.items()}


class GeminiNarrative(BaseModel):
    """Combined Gemini output contract used internally and exposed partly via API."""

    model_config = ConfigDict(extra="forbid")

    ui_layer: UIEnhancedNarrative
    debug_layer: LLMAnalysis

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any] | None = None,
        *,
        default_ui: Mapping[str, Any] | None = None,
        default_reasoning: str = "Deterministic fallback analysis remains active.",
    ) -> "GeminiNarrative":
        payload = payload or {}
        ui_payload = payload.get("ui_layer")
        debug_payload = payload.get("debug_layer")

        if not isinstance(ui_payload, Mapping):
            ui_payload = {}
        if not isinstance(debug_payload, Mapping):
            debug_payload = {}

        return cls(
            ui_layer=UIEnhancedNarrative.from_payload(ui_payload, defaults=default_ui),
            debug_layer=LLMAnalysis.from_payload(debug_payload, default_reasoning=default_reasoning),
        )


class RecommendationResponse(BaseModel):
    """Main response body returned by the recommendation engine."""

    model_config = ConfigDict(extra="forbid")

    mission_profile: MissionProfile
    mission_state: MissionState
    selected_system: SelectedSystemBundle
    scores: ScoreBundle
    explanations: ExplanationBundle
    ui_enhanced: UIEnhancedNarrative
    llm_analysis: LLMAnalysis
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


class MissionStepResponse(BaseModel):
    """Stateful mission-step response."""

    model_config = ConfigDict(extra="forbid")

    mission_state: MissionState
    selected_system: SelectedSystemBundle
    scores: ScoreBundle
    explanations: ExplanationBundle
    ui_enhanced: UIEnhancedNarrative
    llm_analysis: LLMAnalysis
    system_changes: list[str] = Field(default_factory=list)
    risk_delta: float
    adaptation_summary: str
    events: MissionEvents | None = None
    request: MissionStepRequest


class HealthResponse(BaseModel):
    """Basic health response for demos and smoke tests."""

    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
