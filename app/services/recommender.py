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
        system_reason = self.explainer.build_system_reason(mission, selected_system)
        explanation = self.explainer.build_overall_explanation(
            mission=mission,
            selected_system=selected_system,
            top_crop=top_ranked_crops[0],
            crop_recommendation=crop_recommendations[0],
            risk_analysis=risk_analysis,
            system_reason=system_reason,
        )

        return RecommendationResponse(
            mission_profile=mission,
            top_crops=crop_recommendations,
            recommended_system=selected_system.name,
            system_reason=system_reason,
            resource_plan=resource_plan,
            risk_analysis=risk_analysis,
            explanation=explanation,
        )

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        baseline_recommendation = request.previous_recommendation or self.recommend(request.mission_profile)
        updated_mission = request.mission_profile
        changed_fields: list[str] = []
        temporary_penalties: dict[str, float] | None = None
        weight_adjustments: dict[str, float] | None = None
        penalty_applied = False

        if request.change_event is ChangeEvent.WATER_DROP:
            updated_mission = self._update_constraints(
                request.mission_profile,
                water=downgrade_constraint(request.mission_profile.constraints.water),
            )
            changed_fields.append("constraints.water")
        elif request.change_event is ChangeEvent.ENERGY_DROP:
            updated_mission = self._update_constraints(
                request.mission_profile,
                energy=downgrade_constraint(request.mission_profile.constraints.energy),
            )
            changed_fields.append("constraints.energy")
        elif request.change_event is ChangeEvent.YIELD_DROP:
            crop_lookup = {crop.name.lower() for crop in self.provider.get_crops()}
            if request.affected_crop and request.affected_crop.lower() in crop_lookup:
                affected_crop = request.affected_crop.lower()
                temporary_penalties = {affected_crop: 0.35}
                changed_fields.append(f"yield_penalty.{affected_crop}")
                penalty_applied = True
            else:
                weight_adjustments = {"growth_time": 0.08, "risk": 0.08}
                changed_fields.append("crop_ranking")

        updated_recommendation = self.recommend(
            updated_mission,
            temporary_penalties=temporary_penalties,
            weight_adjustments=weight_adjustments,
        )

        previous_top_crop = baseline_recommendation.top_crops[0].name if baseline_recommendation.top_crops else None
        new_top_crop = updated_recommendation.top_crops[0].name if updated_recommendation.top_crops else None
        system_changed = baseline_recommendation.recommended_system != updated_recommendation.recommended_system
        risk_delta = self._compute_risk_delta(
            baseline_recommendation.risk_analysis.score,
            updated_recommendation.risk_analysis.score,
        )
        reason = self.explainer.build_simulation_reason(
            change_event=request.change_event,
            previous_recommendation=baseline_recommendation,
            updated_recommendation=updated_recommendation,
            risk_delta=risk_delta,
            system_changed=system_changed,
            affected_crop=request.affected_crop,
            penalty_applied=penalty_applied,
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
            updated_mission_profile=updated_mission,
            updated_recommendation=updated_recommendation,
            reason=reason,
            adaptation_reason=reason,
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


@lru_cache
def get_default_engine() -> RecommendationEngine:
    """Return the shared default engine for the local app instance."""

    return RecommendationEngine(provider=JSONDataProvider())
