"""Recommendation orchestration service."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache

from app.core.risk import evaluate_risk
from app.core.scoring import ScoredCrop, score_crops, score_systems
from app.models.mission import ChangeEvent, MissionConstraints, MissionProfile, downgrade_constraint
from app.models.response import (
    CropRecommendation,
    RecommendationResponse,
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

        crop_recommendations = [
            CropRecommendation(
                name=item.crop.name,
                score=round(item.score, 3),
                reason=self.explainer.build_crop_reason(item, mission, selected_system),
                selected_system=selected_system.name,
            )
            for item in top_ranked_crops
        ]

        resource_plan = self.resource_planner.build_plan(top_ranked_crops, selected_system)
        risk_analysis = evaluate_risk(mission, selected_system, top_ranked_crops)
        explanation = self.explainer.build_overall_explanation(
            mission=mission,
            selected_system=selected_system,
            top_crop=top_ranked_crops[0],
            crop_reason=crop_recommendations[0].reason,
            risk_analysis=risk_analysis,
        )

        return RecommendationResponse(
            mission_profile=mission,
            top_crops=crop_recommendations,
            recommended_system=selected_system.name,
            resource_plan=resource_plan,
            risk_analysis=risk_analysis,
            explanation=explanation,
        )

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        updated_mission = request.mission_profile
        temporary_penalties: dict[str, float] | None = None
        weight_adjustments: dict[str, float] | None = None

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
            if request.affected_crop:
                temporary_penalties = {request.affected_crop.lower(): 0.20}
            else:
                weight_adjustments = {"growth_time": 0.10, "risk": 0.10}

        # TODO: Extend this path with persistent mission state and event history if the runtime mode expands.
        updated_recommendation = self.recommend(
            updated_mission,
            temporary_penalties=temporary_penalties,
            weight_adjustments=weight_adjustments,
        )

        adaptation_reason = self.explainer.build_adaptation_reason(
            change_event=request.change_event,
            updated_recommendation=updated_recommendation,
            previous_recommendation=request.previous_recommendation,
            affected_crop=request.affected_crop,
        )

        return SimulationResponse(
            change_event=request.change_event,
            updated_mission_profile=updated_mission,
            updated_recommendation=updated_recommendation,
            adaptation_reason=adaptation_reason,
        )

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

