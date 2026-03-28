"""Recommendation orchestration service."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache

from app.core.risk import evaluate_risk
from app.core.scoring import score_crops, score_systems
from app.models.demo_case import DemoCase
from app.models.mission import ChangeEvent, MissionConstraints, MissionProfile, downgrade_constraint
from app.models.response import (
    CropRecommendation,
    RecommendationResponse,
    RiskDelta,
    SimulationRequest,
    SimulationResponse,
)
from app.services.data_provider import DataProvider, JSONDataProvider
from app.services.explainer import Explainer
from app.services.resource_planner import ResourcePlanner


class RecommendationEngine:
    """Mission-aware recommendation and adaptation engine."""

    def __init__(
        self,
        provider: DataProvider,
        explainer: Explainer | None = None,
        resource_planner: ResourcePlanner | None = None,
    ) -> None:
        self.provider = provider
        self.explainer = explainer or Explainer()
        self.resource_planner = resource_planner or ResourcePlanner()

    def list_demo_cases(self) -> list[DemoCase]:
        """Return named demo mission presets."""

        return self.provider.get_demo_cases()

    def recommend(
        self,
        mission: MissionProfile,
        temporary_penalties: Mapping[str, float] | None = None,
        weight_adjustments: Mapping[str, float] | None = None,
        status_penalty: bool = False,
    ) -> RecommendationResponse:
        crops = self.provider.get_crops()
        systems = self.provider.get_systems()

        ranked_systems = score_systems(systems, mission)
        selected_system = ranked_systems[0].system

        ranked_crops = score_crops(
            crops=crops,
            mission=mission,
            selected_system=selected_system,
            temporary_penalties=temporary_penalties,
            weight_adjustments=weight_adjustments,
        )
        top_ranked_crops = ranked_crops[:3]

        crop_recommendations: list[CropRecommendation] = []
        for item in top_ranked_crops:
            strengths = self.explainer.build_crop_strengths(item, mission)
            crop_recommendations.append(
                CropRecommendation(
                    name=item.crop.name,
                    score=round(item.score, 3),
                    reason=self.explainer.build_crop_reason(item, mission, selected_system, strengths),
                    selected_system=selected_system.name,
                    strengths=strengths,
                    tradeoffs=self.explainer.build_crop_tradeoffs(item, mission),
                    metric_breakdown=self.explainer.build_metric_breakdown(item),
                    compatibility_score=self.explainer.build_compatibility_score(item, mission, selected_system),
                )
            )

        resource_plan = self.resource_planner.build_plan(top_ranked_crops, selected_system)
        risk_analysis = evaluate_risk(mission, selected_system, top_ranked_crops)
        system_reasoning = self.explainer.build_system_reasoning(mission, selected_system)
        why_this_system = self.explainer.build_why_this_system(mission, selected_system)
        mission_status = self.explainer.build_mission_status(
            mission=mission,
            risk_analysis=risk_analysis,
            selected_system=selected_system,
            lead_crop_compatibility_score=crop_recommendations[0].compatibility_score,
            penalty_on_previous_lead_crop=status_penalty,
        )
        executive_summary = self.explainer.build_executive_summary(
            mission=mission,
            top_crop_recommendation=crop_recommendations[0],
            selected_system=selected_system,
            mission_status=mission_status,
            risk_analysis=risk_analysis,
        )
        operational_note = self.explainer.build_operational_note(risk_analysis, selected_system)
        tradeoff_summary = self.explainer.build_tradeoff_summary(selected_system, crop_recommendations[0])
        explanation = self.explainer.build_explanation(executive_summary, operational_note)

        return RecommendationResponse(
            mission_profile=mission,
            top_crops=crop_recommendations,
            recommended_system=selected_system.name,
            system_reason=system_reasoning,
            system_reasoning=system_reasoning,
            why_this_system=why_this_system,
            tradeoff_summary=tradeoff_summary,
            resource_plan=resource_plan,
            risk_analysis=risk_analysis,
            mission_status=mission_status,
            executive_summary=executive_summary,
            operational_note=operational_note,
            explanation=explanation,
        )

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        baseline_recommendation = request.previous_recommendation or self.recommend(request.mission_profile)
        updated_mission = request.mission_profile
        temporary_penalties: dict[str, float] | None = None
        weight_adjustments: dict[str, float] | None = None
        penalty_applied = False
        penalty_on_previous_lead = False

        if request.change_event is ChangeEvent.WATER_DROP:
            updated_mission = self._update_constraints(
                request.mission_profile,
                water=downgrade_constraint(request.mission_profile.constraints.water),
            )
        elif request.change_event is ChangeEvent.ENERGY_DROP:
            updated_mission = self._update_constraints(
                request.mission_profile,
                energy=downgrade_constraint(request.mission_profile.constraints.energy),
            )
        elif request.change_event is ChangeEvent.YIELD_DROP:
            crop_lookup = {crop.name.lower() for crop in self.provider.get_crops()}
            if request.affected_crop and request.affected_crop.lower() in crop_lookup:
                affected_crop = request.affected_crop.lower()
                temporary_penalties = {affected_crop: 0.45}
                penalty_applied = True
                penalty_on_previous_lead = bool(
                    baseline_recommendation.top_crops
                    and baseline_recommendation.top_crops[0].name.lower() == affected_crop
                )
            else:
                weight_adjustments = {"growth_time": 0.08, "risk": 0.08, "closed_loop": 0.05}

        updated_recommendation = self.recommend(
            updated_mission,
            temporary_penalties=temporary_penalties,
            weight_adjustments=weight_adjustments,
            status_penalty=penalty_on_previous_lead,
        )

        previous_top_crop = baseline_recommendation.top_crops[0].name if baseline_recommendation.top_crops else None
        new_top_crop = updated_recommendation.top_crops[0].name if updated_recommendation.top_crops else None
        system_changed = baseline_recommendation.recommended_system != updated_recommendation.recommended_system
        risk_score_delta = round(
            updated_recommendation.risk_analysis.score - baseline_recommendation.risk_analysis.score,
            3,
        )
        risk_delta = self._compute_risk_delta(
            baseline_recommendation.risk_analysis.score,
            updated_recommendation.risk_analysis.score,
        )
        adaptation_summary = self.explainer.build_simulation_reason(
            change_event=request.change_event,
            previous_recommendation=baseline_recommendation,
            updated_recommendation=updated_recommendation,
            risk_delta=risk_delta,
            system_changed=system_changed,
            affected_crop=request.affected_crop,
            penalty_applied=penalty_applied,
            risk_score_delta=risk_score_delta,
        )
        changed_fields = self._build_changed_fields(
            previous_recommendation=baseline_recommendation,
            updated_recommendation=updated_recommendation,
            updated_mission_profile=updated_mission,
        )

        return SimulationResponse(
            change_event=request.change_event,
            changed_fields=changed_fields,
            previous_top_crop=previous_top_crop,
            new_top_crop=new_top_crop,
            ranking_diff=self._compute_ranking_diff(
                baseline_recommendation.top_crops,
                updated_recommendation.top_crops,
                extra_names=[request.affected_crop.lower()] if request.affected_crop else None,
            ),
            system_changed=system_changed,
            previous_system=baseline_recommendation.recommended_system,
            new_system=updated_recommendation.recommended_system,
            risk_delta=risk_delta,
            risk_score_delta=risk_score_delta,
            previous_mission_status=baseline_recommendation.mission_status,
            new_mission_status=updated_recommendation.mission_status,
            updated_mission_profile=updated_mission,
            updated_recommendation=updated_recommendation,
            adaptation_summary=adaptation_summary,
            reason=adaptation_summary,
            adaptation_reason=adaptation_summary,
        )

    def _compute_ranking_diff(
        self,
        previous_top_crops: list[CropRecommendation],
        new_top_crops: list[CropRecommendation],
        extra_names: list[str] | None = None,
    ) -> dict[str, int]:
        previous_ranks = {item.name: index + 1 for index, item in enumerate(previous_top_crops)}
        new_ranks = {item.name: index + 1 for index, item in enumerate(new_top_crops)}
        crop_names = list(dict.fromkeys([*previous_ranks.keys(), *new_ranks.keys(), *(extra_names or [])]))

        ranking_diff: dict[str, int] = {}
        for name in crop_names:
            old_rank = previous_ranks.get(name, 4)
            new_rank = new_ranks.get(name, 4)
            ranking_diff[name] = old_rank - new_rank
        return ranking_diff

    def _compute_risk_delta(self, previous_score: float, updated_score: float) -> RiskDelta:
        delta = updated_score - previous_score
        if delta > 0.05:
            return RiskDelta.INCREASED
        if delta < -0.05:
            return RiskDelta.DECREASED
        return RiskDelta.UNCHANGED

    def _update_constraints(
        self,
        mission: MissionProfile,
        water=None,
        energy=None,
        area=None,
    ) -> MissionProfile:
        constraints = MissionConstraints(
            water=water or mission.constraints.water,
            energy=energy or mission.constraints.energy,
            area=area or mission.constraints.area,
        )
        return mission.model_copy(update={"constraints": constraints})

    def _build_changed_fields(
        self,
        previous_recommendation: RecommendationResponse,
        updated_recommendation: RecommendationResponse,
        updated_mission_profile: MissionProfile,
    ) -> list[str]:
        changed_fields: list[str] = []
        previous_constraints = previous_recommendation.mission_profile.constraints
        updated_constraints = updated_mission_profile.constraints

        if previous_constraints.water is not updated_constraints.water:
            changed_fields.append("constraints.water")
        if previous_constraints.energy is not updated_constraints.energy:
            changed_fields.append("constraints.energy")
        if previous_constraints.area is not updated_constraints.area:
            changed_fields.append("constraints.area")

        previous_ranking = [item.name for item in previous_recommendation.top_crops]
        updated_ranking = [item.name for item in updated_recommendation.top_crops]
        if previous_ranking != updated_ranking:
            changed_fields.append("top_crops")

        if previous_recommendation.recommended_system != updated_recommendation.recommended_system:
            changed_fields.append("recommended_system")

        if abs(previous_recommendation.risk_analysis.score - updated_recommendation.risk_analysis.score) > 0.01:
            changed_fields.append("risk_analysis")

        if previous_recommendation.mission_status != updated_recommendation.mission_status:
            changed_fields.append("mission_status")

        return changed_fields


@lru_cache
def get_default_engine() -> RecommendationEngine:
    """Return the shared default engine for the local app instance."""

    return RecommendationEngine(provider=JSONDataProvider())
