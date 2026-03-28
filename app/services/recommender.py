"""Recommendation orchestration service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from functools import lru_cache

from fastapi import HTTPException

from app.core.mission_state import (
    ActiveDomainItem,
    ActiveSystemState,
    MissionHistoryEntry,
    MissionResources,
    MissionState,
    MissionStateStore,
    SystemMetricsState,
    constraint_to_resource_margin,
)
from app.core.risk import evaluate_risk
from app.core.scoring import score_crops
from app.core.simulation import (
    SIMULATION_MAX_WEEKS,
    MissionEvents,
    MissionStepRequest,
    advance_state_time,
    apply_resource_events,
)
from app.engine.crop_engine import ALGAE_LIKE_NAMES
from app.engine.integration_engine import IntegrationEngine
from app.llm.reasoning_loop import ReasoningLoop
from app.models.demo_case import DemoCase
from app.models.mission import ChangeEvent, ConstraintLevel, MissionConstraints, MissionProfile, downgrade_constraint
from app.models.response import (
    CropRecommendation,
    DomainScoreBundle,
    DomainScoreVector,
    ExplanationBundle,
    InteractionScoreBundle,
    MissionStatus,
    MissionStepResponse,
    RecommendationResponse,
    RankedCandidatesBundle,
    RankedDomainCandidate,
    RiskDelta,
    ScoreBundle,
    SimulationStartRequest,
    SimulationStartResponse,
    SelectedDomainSystem,
    SelectedSystemBundle,
    SimulationRequest,
    SimulationResponse,
)
from app.services.data_provider import DataProvider, JSONDataProvider
from app.services.explainer import Explainer
from app.services.resource_planner import ResourcePlanner

RISK_DECAY = 0.02
RISK_COLLAPSE_THRESHOLD = 0.85


class RecommendationEngine:
    """Mission-aware recommendation and adaptation engine."""

    def __init__(
        self,
        provider: DataProvider,
        explainer: Explainer | None = None,
        resource_planner: ResourcePlanner | None = None,
        integration_engine: IntegrationEngine | None = None,
        reasoning_loop: ReasoningLoop | None = None,
        state_store: MissionStateStore | None = None,
    ) -> None:
        self.provider = provider
        self.explainer = explainer or Explainer()
        self.resource_planner = resource_planner or ResourcePlanner()
        self.integration_engine = integration_engine or IntegrationEngine(provider)
        self.reasoning_loop = reasoning_loop or ReasoningLoop(provider, integration_engine=self.integration_engine)
        self.state_store = state_store or MissionStateStore()

    def list_demo_cases(self) -> list[DemoCase]:
        """Return named demo mission presets."""

        return self.provider.get_demo_cases()

    def recommend(
        self,
        mission: MissionProfile,
        temporary_penalties: Mapping[str, float] | None = None,
        weight_adjustments: Mapping[str, float] | None = None,
        status_penalty: bool = False,
        existing_state: MissionState | None = None,
        risk_bias: float = 1.0,
        complexity_bias: float = 1.0,
        loop_bias: float = 1.0,
        persist_state: bool = True,
        history_event: str = "initial_recommendation",
        source: str = "recommend",
        previous_state: MissionState | None = None,
        events: Mapping[str, Any] | MissionEvents | None = None,
        deltas: Mapping[str, Any] | None = None,
        allow_refinement: bool | None = None,
        use_llm: bool = True,
    ) -> RecommendationResponse:
        allow_refinement = source == "recommend" if allow_refinement is None else allow_refinement
        mission_fit_bias = 0.03 if weight_adjustments else 0.0

        integrated_result, ranked_candidates, selected_grow_system = self.integration_engine.select_configuration(
            mission=mission,
            temporary_penalties=dict(temporary_penalties or {}),
            mission_fit_bias=mission_fit_bias,
            risk_bias=risk_bias,
            complexity_bias=complexity_bias,
            loop_bias=loop_bias,
        )
        provisional_explanations = self._build_reasoning_context_explanations(
            mission=mission,
            integrated_result=integrated_result,
            grow_system_name=selected_grow_system.name,
        )
        provisional_state_summary = self._build_reasoning_state_summary(
            mission=mission,
            integrated_result=integrated_result,
            existing_state=existing_state,
        )
        integrated_result, ranked_candidates, selected_grow_system, narrative = self.reasoning_loop.run(
            mission=mission,
            result=integrated_result,
            top_crop_rankings=ranked_candidates,
            grow_system=selected_grow_system,
            temporary_penalties=dict(temporary_penalties or {}),
            base_biases={
                "risk_bias": risk_bias,
                "complexity_bias": complexity_bias,
                "loop_bias": loop_bias,
            },
            source=source,
            deterministic_explanations=provisional_explanations,
            mission_state=provisional_state_summary,
            previous_state=previous_state,
            events=events,
            deltas=deltas,
            allow_refinement=allow_refinement,
            use_llm=use_llm,
        )
        return self._compose_recommendation_response(
            mission=mission,
            integrated_result=integrated_result,
            ranked_candidates=ranked_candidates,
            selected_grow_system=selected_grow_system,
            llm_analysis=narrative.debug_layer,
            ui_enhanced=narrative.ui_layer,
            temporary_penalties=temporary_penalties,
            weight_adjustments=weight_adjustments,
            status_penalty=status_penalty,
            existing_state=existing_state,
            persist_state=persist_state,
            history_event=history_event,
        )

    def start_simulation(self, request: SimulationStartRequest) -> SimulationStartResponse:
        """Bootstrap a stateful ecosystem simulation from a user-selected stack."""

        try:
            integrated_result, ranked_candidates, selected_grow_system = (
                self.integration_engine.evaluate_selected_configuration(
                    mission=request.mission_profile,
                    selected_crop_name=request.selected_crop,
                    selected_algae_name=request.selected_algae,
                    selected_microbial_name=request.selected_microbial,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        provisional_explanations = self._build_reasoning_context_explanations(
            mission=request.mission_profile,
            integrated_result=integrated_result,
            grow_system_name=selected_grow_system.name,
        )
        provisional_state_summary = self._build_reasoning_state_summary(
            mission=request.mission_profile,
            integrated_result=integrated_result,
            existing_state=None,
        )
        integrated_result, ranked_candidates, selected_grow_system, narrative = self.reasoning_loop.run(
            mission=request.mission_profile,
            result=integrated_result,
            top_crop_rankings=ranked_candidates,
            grow_system=selected_grow_system,
            temporary_penalties={},
            base_biases={
                "risk_bias": 1.0,
                "complexity_bias": 1.0,
                "loop_bias": 1.0,
            },
            source="simulation_start",
            deterministic_explanations=provisional_explanations,
            mission_state=provisional_state_summary,
            previous_state=None,
            events=None,
            deltas={
                "custom_selection": {
                    "crop": request.selected_crop,
                    "algae": request.selected_algae,
                    "microbial": request.selected_microbial,
                }
            },
            allow_refinement=False,
            use_llm=False,
        )

        recommendation = self._compose_recommendation_response(
            mission=request.mission_profile,
            integrated_result=integrated_result,
            ranked_candidates=ranked_candidates,
            selected_grow_system=selected_grow_system,
            llm_analysis=narrative.debug_layer,
            ui_enhanced=narrative.ui_layer,
            temporary_penalties=None,
            weight_adjustments=None,
            status_penalty=False,
            existing_state=None,
            persist_state=True,
            history_event="simulation_start",
            lead_crop_compatibility_override=self._build_selected_crop_compatibility(
                mission=request.mission_profile,
                integrated_result=integrated_result,
                selected_grow_system=selected_grow_system,
            ),
        )
        return SimulationStartResponse.from_recommendation(recommendation)

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        baseline_recommendation = request.previous_recommendation or self.recommend(
            request.mission_profile,
            source="simulate",
            allow_refinement=False,
            use_llm=False,
        )
        updated_mission = request.mission_profile
        temporary_penalties: dict[str, float] | None = None
        weight_adjustments: dict[str, float] | None = None
        risk_bias = 1.0
        complexity_bias = 1.0
        loop_bias = 1.0
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
        elif request.change_event in {ChangeEvent.YIELD_DROP, ChangeEvent.YIELD_VARIATION}:
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
                risk_bias = 1.08
        elif request.change_event is ChangeEvent.CONTAMINATION:
            risk_bias = 1.18
            complexity_bias = 1.10

        updated_recommendation = self.recommend(
            updated_mission,
            temporary_penalties=temporary_penalties,
            weight_adjustments=weight_adjustments,
            status_penalty=penalty_on_previous_lead,
            risk_bias=risk_bias,
            complexity_bias=complexity_bias,
            loop_bias=loop_bias,
            history_event=f"simulate_{request.change_event.value}",
            source="simulate",
            previous_state=baseline_recommendation.mission_state,
            events={
                "change_event": request.change_event.value,
                "affected_crop": request.affected_crop,
            },
            deltas={
                "updated_constraints": updated_mission.constraints.model_dump(mode="json"),
            },
            allow_refinement=False,
            use_llm=False,
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
        ranking_diff = self._compute_ranking_diff(
            baseline_recommendation.top_crops,
            updated_recommendation.top_crops,
            extra_names=[request.affected_crop.lower()] if request.affected_crop else None,
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
        updated_narrative = self.reasoning_loop.analyze_response(
            updated_recommendation,
            source="simulate",
            previous_recommendation=baseline_recommendation,
            events={
                "change_event": request.change_event.value,
                "affected_crop": request.affected_crop,
            },
            deltas={
                "changed_fields": changed_fields,
                "previous_top_crop": previous_top_crop,
                "new_top_crop": new_top_crop,
                "ranking_diff": ranking_diff,
                "system_changed": system_changed,
                "previous_system": baseline_recommendation.recommended_system,
                "new_system": updated_recommendation.recommended_system,
                "risk_delta": risk_delta.value,
                "risk_score_delta": risk_score_delta,
                "previous_mission_status": baseline_recommendation.mission_status.value,
                "new_mission_status": updated_recommendation.mission_status.value,
                "adaptation_summary": adaptation_summary,
            },
            use_llm=False,
        )
        updated_recommendation = updated_recommendation.model_copy(
            update={
                "llm_analysis": updated_narrative.debug_layer,
                "ui_enhanced": updated_narrative.ui_layer,
            },
        )

        return SimulationResponse(
            change_event=request.change_event,
            changed_fields=changed_fields,
            previous_top_crop=previous_top_crop,
            new_top_crop=new_top_crop,
            ranking_diff=ranking_diff,
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

    def mission_step(self, request: MissionStepRequest) -> MissionStepResponse:
        state = self.state_store.get(request.mission_id)
        if state is None:
            raise HTTPException(status_code=404, detail=f"Mission '{request.mission_id}' was not found.")

        previous_state = state.model_copy(deep=True)
        updated_state = advance_state_time(state, request.time_step)
        weekly_resources = self._apply_weekly_resource_usage(updated_state, request.time_step)
        updated_resources = apply_resource_events(weekly_resources, request.events)
        updated_constraints = MissionConstraints(
            water=self._margin_to_constraint(updated_resources.water),
            energy=self._margin_to_constraint(updated_resources.energy),
            area=self._margin_to_constraint(updated_resources.area),
        )
        updated_state = updated_state.model_copy(
            update={"resources": updated_resources, "constraints": updated_constraints},
            deep=True,
        )
        mission = MissionProfile(
            environment=updated_state.environment,
            duration=updated_state.duration,
            constraints=updated_constraints,
            goal=updated_state.goal,
        )
        event_adjustments = self._derive_event_adjustments(previous_state, request.events)
        weekly_adjustments = self._derive_weekly_adjustments(
            previous_state,
            updated_resources,
            request.events,
            request.time_step,
        )

        response = self.recommend(
            mission=mission,
            temporary_penalties=self._merge_penalties(
                event_adjustments["temporary_penalties"],
                weekly_adjustments["temporary_penalties"],
            ),
            status_penalty=bool(event_adjustments["status_penalty"] or weekly_adjustments["status_penalty"]),
            existing_state=updated_state,
            risk_bias=round(event_adjustments["risk_bias"] * weekly_adjustments["risk_bias"], 3),
            complexity_bias=round(event_adjustments["complexity_bias"] * weekly_adjustments["complexity_bias"], 3),
            loop_bias=round(event_adjustments["loop_bias"] * weekly_adjustments["loop_bias"], 3),
            history_event=self._build_step_event_label(request.events),
            source="mission_step",
            previous_state=previous_state,
            events=request.events,
            deltas={
                "time_step": request.time_step,
                "time_unit": "week",
            },
            allow_refinement=False,
            use_llm=False,
        )
        cumulative_state, cumulative_risk_delta = self._apply_cumulative_risk(
            previous_state=previous_state,
            updated_state=response.mission_state,
            events=request.events,
        )
        mission_status = (
            MissionStatus.CRITICAL
            if cumulative_state.system_metrics.risk_level / 100 >= RISK_COLLAPSE_THRESHOLD
            else response.mission_status
        )
        response = response.model_copy(
            update={
                "mission_state": cumulative_state,
                "mission_status": mission_status,
            },
        )
        self.state_store.save(cumulative_state)

        system_changes = self._build_system_changes(previous_state, response.mission_state)
        risk_delta = cumulative_risk_delta
        adaptation_summary = self._build_mission_step_summary(
            previous_state=previous_state,
            updated_state=response.mission_state,
            events=request.events,
            system_changes=system_changes,
            risk_delta=risk_delta,
            request_time_step=request.time_step,
        )
        step_narrative = self.reasoning_loop.analyze_response(
            response,
            source="mission_step",
            previous_state=previous_state,
            events=request.events,
            deltas={
                "system_changes": system_changes,
                "risk_delta": risk_delta,
                "previous_time": previous_state.time,
                "new_time": response.mission_state.time,
                "adaptation_summary": adaptation_summary,
            },
            use_llm=False,
        )

        return MissionStepResponse(
            mission_state=response.mission_state,
            selected_system=response.selected_system,
            ranked_candidates=response.ranked_candidates,
            scores=response.scores,
            explanations=response.explanations,
            ui_enhanced=step_narrative.ui_layer,
            llm_analysis=step_narrative.debug_layer,
            mission_status=mission_status,
            operational_note=response.operational_note,
            system_changes=system_changes,
            risk_delta=risk_delta,
            adaptation_summary=adaptation_summary,
            events=request.events,
            request=request,
        )

    def _compose_recommendation_response(
        self,
        *,
        mission: MissionProfile,
        integrated_result,
        ranked_candidates,
        selected_grow_system,
        llm_analysis,
        ui_enhanced,
        temporary_penalties: Mapping[str, float] | None,
        weight_adjustments: Mapping[str, float] | None,
        status_penalty: bool,
        existing_state: MissionState | None,
        persist_state: bool,
        history_event: str,
        lead_crop_compatibility_override: float | None = None,
    ) -> RecommendationResponse:
        filtered_crops = [
            crop
            for crop in self.provider.get_crops()
            if crop.name.lower() not in ALGAE_LIKE_NAMES
        ]
        ranked_crops = score_crops(
            crops=filtered_crops,
            mission=mission,
            selected_system=selected_grow_system,
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
                    reason=self.explainer.build_crop_reason(item, mission, selected_grow_system, strengths),
                    selected_system=selected_grow_system.name,
                    strengths=strengths,
                    tradeoffs=self.explainer.build_crop_tradeoffs(item, mission),
                    metric_breakdown=self.explainer.build_metric_breakdown(item),
                    compatibility_score=self.explainer.build_compatibility_score(item, mission, selected_grow_system),
                )
            )

        resource_plan = self.resource_planner.build_plan(top_ranked_crops, selected_grow_system)
        risk_analysis = evaluate_risk(mission, selected_grow_system, top_ranked_crops)

        system_reasoning = self._build_integrated_system_reasoning(
            mission=mission,
            grow_system_name=selected_grow_system.name,
            integrated_result=integrated_result,
        )
        why_this_system = self._build_why_this_system(
            mission=mission,
            grow_system_name=selected_grow_system.name,
            integrated_result=integrated_result,
        )
        lead_crop_compatibility = (
            lead_crop_compatibility_override
            if lead_crop_compatibility_override is not None
            else (crop_recommendations[0].compatibility_score if crop_recommendations else 0.5)
        )
        mission_status = self.explainer.build_mission_status(
            mission=mission,
            risk_analysis=risk_analysis,
            selected_system=selected_grow_system,
            lead_crop_compatibility_score=lead_crop_compatibility,
            penalty_on_previous_lead_crop=status_penalty,
        )
        executive_summary = self._build_executive_summary(
            mission=mission,
            integrated_result=integrated_result,
            grow_system_name=selected_grow_system.name,
            mission_status=mission_status,
        )
        operational_note = self._build_operational_note(
            risk_analysis=risk_analysis,
            integrated_result=integrated_result,
            llm_analysis=llm_analysis,
        )
        tradeoff_summary = self._build_tradeoff_summary(
            integrated_result=integrated_result,
            grow_system_name=selected_grow_system.name,
        )
        weak_points = self._build_weak_points(llm_analysis, risk_analysis)
        explanation = f"{executive_summary} {operational_note}"

        mission_state = self._build_mission_state(
            mission=mission,
            integrated_result=integrated_result,
            risk_score=risk_analysis.score,
            existing_state=existing_state,
            summary=executive_summary,
            history_event=history_event,
        )
        if persist_state:
            self.state_store.save(mission_state)

        return RecommendationResponse(
            mission_profile=mission,
            mission_state=mission_state,
            selected_system=self._build_selected_system(integrated_result),
            ranked_candidates=self._build_ranked_candidates(ranked_candidates),
            scores=self._build_scores(integrated_result),
            explanations=ExplanationBundle(
                executive_summary=executive_summary,
                system_reasoning=system_reasoning,
                tradeoffs=tradeoff_summary,
                weak_points=weak_points,
            ),
            ui_enhanced=ui_enhanced,
            llm_analysis=llm_analysis,
            top_crops=crop_recommendations,
            recommended_system=selected_grow_system.name,
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

    def _build_selected_crop_compatibility(
        self,
        *,
        mission: MissionProfile,
        integrated_result,
        selected_grow_system,
    ) -> float:
        crop = integrated_result.crop.candidate
        system_fit = crop.system_fit_score(selected_grow_system.name, fallback=0.72)
        environment_fit = crop.environment_fit_score(mission.environment, fallback=0.72)
        closed_loop_fit = (
            crop.nutrient_density
            + crop.oxygen_contribution
            + crop.co2_utilization
            + crop.waste_recycling_synergy
            + crop.crew_acceptance
        ) / 500
        stability_fit = 1 - integrated_result.crop.risk_score
        return round(
            min(
                1.0,
                (0.45 * system_fit)
                + (0.20 * environment_fit)
                + (0.20 * closed_loop_fit)
                + (0.15 * stability_fit),
            ),
            3,
        )

    def _build_reasoning_context_explanations(
        self,
        mission: MissionProfile,
        integrated_result,
        grow_system_name: str,
    ) -> dict[str, Any]:
        return {
            "executive_summary": (
                f"{self.explainer.format_environment(mission.environment)} mission pre-analysis selected "
                f"{integrated_result.crop.candidate.name.title()} as the primary food layer with {grow_system_name.title()}."
            ),
            "system_reasoning": self._build_integrated_system_reasoning(
                mission=mission,
                grow_system_name=grow_system_name,
                integrated_result=integrated_result,
            ),
            "why_this_system": self._build_why_this_system(
                mission=mission,
                grow_system_name=grow_system_name,
                integrated_result=integrated_result,
            ),
            "tradeoffs": self._build_tradeoff_summary(
                integrated_result=integrated_result,
                grow_system_name=grow_system_name,
            ),
        }

    def _build_reasoning_state_summary(
        self,
        mission: MissionProfile,
        integrated_result,
        existing_state: MissionState | None,
    ) -> dict[str, Any]:
        resources = (
            existing_state.resources.model_dump(mode="json")
            if existing_state is not None
            else self._resources_from_constraints(mission.constraints).model_dump(mode="json")
        )
        history = (
            [entry.model_dump(mode="json") for entry in existing_state.history[-5:]]
            if existing_state is not None
            else []
        )
        risk_score = self._estimate_integrated_risk(integrated_result)
        return {
            "mission_id": existing_state.mission_id if existing_state is not None else None,
            "time": existing_state.time if existing_state is not None else 0,
            "resources": resources,
            "active_system": {
                "crops": [
                    {
                        "name": integrated_result.crop.candidate.name,
                        "type": "crop",
                        "score": integrated_result.crop.combined_score,
                        "support_system": integrated_result.grow_system_name,
                    }
                ],
                "algae": [
                    {
                        "name": integrated_result.algae.candidate.name,
                        "type": "algae",
                        "score": integrated_result.algae.combined_score,
                    }
                ],
                "microbial": [
                    {
                        "name": integrated_result.microbial.candidate.name,
                        "type": "microbial",
                        "score": integrated_result.microbial.combined_score,
                    }
                ],
            },
            "system_metrics": self._build_system_metrics(
                integrated_result=integrated_result,
                risk_score=risk_score,
            ).model_dump(mode="json"),
            "history": history,
        }

    def _estimate_integrated_risk(self, integrated_result) -> float:
        return round(
            (
                integrated_result.crop.risk_score
                + integrated_result.algae.risk_score
                + integrated_result.microbial.risk_score
                + integrated_result.interaction.conflict_score
            )
            / 4,
            3,
        )

    def _build_selected_system(self, integrated_result) -> SelectedSystemBundle:
        return SelectedSystemBundle(
            crop=SelectedDomainSystem(
                name=integrated_result.crop.candidate.name,
                type="crop",
                domain_score=integrated_result.crop.domain_score,
                mission_fit_score=integrated_result.crop.mission_fit_score,
                risk_score=integrated_result.crop.risk_score,
                support_system=integrated_result.grow_system_name,
                metrics=integrated_result.crop.metrics,
                notes=integrated_result.crop.notes,
            ),
            algae=SelectedDomainSystem(
                name=integrated_result.algae.candidate.name,
                type="algae",
                domain_score=integrated_result.algae.domain_score,
                mission_fit_score=integrated_result.algae.mission_fit_score,
                risk_score=integrated_result.algae.risk_score,
                metrics=integrated_result.algae.metrics,
                notes=integrated_result.algae.notes,
            ),
            microbial=SelectedDomainSystem(
                name=integrated_result.microbial.candidate.name,
                type="microbial",
                domain_score=integrated_result.microbial.domain_score,
                mission_fit_score=integrated_result.microbial.mission_fit_score,
                risk_score=integrated_result.microbial.risk_score,
                metrics=integrated_result.microbial.metrics,
                notes=integrated_result.microbial.notes,
            ),
        )

    def _build_ranked_candidates(self, ranked_candidates) -> RankedCandidatesBundle:
        return RankedCandidatesBundle(
            crop=self._serialize_ranked_domain(ranked_candidates.crop, "crop"),
            algae=self._serialize_ranked_domain(ranked_candidates.algae, "algae"),
            microbial=self._serialize_ranked_domain(ranked_candidates.microbial, "microbial"),
        )

    def _serialize_ranked_domain(self, evaluations: list[Any], domain_type: str) -> list[RankedDomainCandidate]:
        ranked_items: list[RankedDomainCandidate] = []
        for index, evaluation in enumerate(evaluations, start=1):
            notes = [str(note).strip() for note in getattr(evaluation, "notes", []) if str(note).strip()]
            summary = ". ".join(note.rstrip(".") for note in notes[:2]).strip()
            if summary:
                summary += "."
            ranked_items.append(
                RankedDomainCandidate(
                    name=evaluation.candidate.name,
                    type=domain_type,
                    rank=index,
                    domain_score=round(evaluation.domain_score, 3),
                    mission_fit_score=round(evaluation.mission_fit_score, 3),
                    risk_score=round(evaluation.risk_score, 3),
                    combined_score=round(evaluation.combined_score, 3),
                    support_system=evaluation.support_system,
                    summary=summary,
                    notes=notes,
                )
            )
        return ranked_items

    def _build_scores(self, integrated_result) -> ScoreBundle:
        return ScoreBundle(
            domain=DomainScoreBundle(
                crop=DomainScoreVector(
                    domain_score=integrated_result.crop.domain_score,
                    mission_fit_score=integrated_result.crop.mission_fit_score,
                    risk_score=integrated_result.crop.risk_score,
                ),
                algae=DomainScoreVector(
                    domain_score=integrated_result.algae.domain_score,
                    mission_fit_score=integrated_result.algae.mission_fit_score,
                    risk_score=integrated_result.algae.risk_score,
                ),
                microbial=DomainScoreVector(
                    domain_score=integrated_result.microbial.domain_score,
                    mission_fit_score=integrated_result.microbial.mission_fit_score,
                    risk_score=integrated_result.microbial.risk_score,
                ),
            ),
            interaction=InteractionScoreBundle(
                synergy_score=integrated_result.interaction.synergy_score,
                conflict_score=integrated_result.interaction.conflict_score,
                complexity_penalty=integrated_result.interaction.complexity_penalty,
                resource_overlap=integrated_result.interaction.resource_overlap,
                loop_closure_bonus=integrated_result.interaction.loop_closure_bonus,
            ),
            integrated=round(integrated_result.integrated_score, 3),
        )

    def _build_mission_state(
        self,
        mission: MissionProfile,
        integrated_result,
        risk_score: float,
        existing_state: MissionState | None,
        summary: str,
        history_event: str,
    ) -> MissionState:
        resources = (
            existing_state.resources.model_copy(deep=True)
            if existing_state is not None
            else self._resources_from_constraints(mission.constraints)
        )
        history = list(existing_state.history) if existing_state is not None else []
        mission_id = existing_state.mission_id if existing_state is not None else self.state_store.new_id()
        time = existing_state.time if existing_state is not None else 0
        system_metrics = self._build_system_metrics(integrated_result, risk_score)

        history.append(
            MissionHistoryEntry(
                time=time,
                event=history_event,
                summary=summary,
                selected_crop=integrated_result.crop.candidate.name,
                selected_algae=integrated_result.algae.candidate.name,
                selected_microbial=integrated_result.microbial.candidate.name,
                risk_level=system_metrics.risk_level,
            )
        )

        return MissionState(
            mission_id=mission_id,
            environment=mission.environment,
            duration=mission.duration,
            goal=mission.goal,
            constraints=mission.constraints,
            time=time,
            resources=resources,
            active_system=ActiveSystemState(
                crops=[
                    ActiveDomainItem(
                        name=integrated_result.crop.candidate.name,
                        type="crop",
                        score=integrated_result.crop.combined_score,
                        support_system=integrated_result.grow_system_name,
                    )
                ],
                algae=[
                    ActiveDomainItem(
                        name=integrated_result.algae.candidate.name,
                        type="algae",
                        score=integrated_result.algae.combined_score,
                    )
                ],
                microbial=[
                    ActiveDomainItem(
                        name=integrated_result.microbial.candidate.name,
                        type="microbial",
                        score=integrated_result.microbial.combined_score,
                    )
                ],
            ),
            system_metrics=system_metrics,
            history=history,
        )

    def _build_system_metrics(self, integrated_result, risk_score: float) -> SystemMetricsState:
        crop = integrated_result.crop.candidate
        algae = integrated_result.algae.candidate
        microbial = integrated_result.microbial.candidate
        oxygen_level = min(100.0, (0.45 * crop.oxygen_contribution) + (0.55 * algae.oxygen_contribution))
        co2_balance = min(100.0, (0.35 * crop.co2_utilization) + (0.45 * algae.co2_utilization) + (0.20 * microbial.loop_closure_contribution))
        food_supply = min(100.0, (0.45 * crop.calorie_yield) + (0.25 * crop.nutrient_density) + (0.30 * algae.protein_potential))
        nutrient_cycle_efficiency = min(
            100.0,
            (0.30 * crop.waste_recycling_synergy)
            + (0.40 * microbial.nutrient_conversion_capability)
            + (0.30 * microbial.loop_closure_contribution),
        )
        return SystemMetricsState(
            oxygen_level=round(oxygen_level, 2),
            co2_balance=round(co2_balance, 2),
            food_supply=round(food_supply, 2),
            nutrient_cycle_efficiency=round(nutrient_cycle_efficiency, 2),
            risk_level=round(risk_score * 100, 2),
        )

    def _build_integrated_system_reasoning(self, mission: MissionProfile, grow_system_name: str, integrated_result) -> str:
        environment_label = self.explainer.format_environment(mission.environment)
        crop_name = integrated_result.crop.candidate.name.title()
        algae_name = integrated_result.algae.candidate.name.replace("_", " ").title()
        microbial_name = integrated_result.microbial.candidate.name.replace("_", " ").title()
        return (
            f"{grow_system_name.title()} anchors the plant layer for this {environment_label} mission, with {crop_name} "
            f"driving edible production, {algae_name} stabilizing oxygen and biomass support, and {microbial_name} "
            "closing nutrient and waste-recovery loops."
        )

    def _build_why_this_system(self, mission: MissionProfile, grow_system_name: str, integrated_result) -> str:
        return (
            f"{grow_system_name.title()} is the best fit because {integrated_result.crop.candidate.name.title()} fits the food objective, "
            f"{integrated_result.algae.candidate.name.replace('_', ' ').title()} improves atmospheric support, "
            f"and {integrated_result.microbial.candidate.name.replace('_', ' ').title()} improves loop closure while "
            "the integrated stack stays mission-compatible."
        )

    def _build_executive_summary(
        self,
        mission: MissionProfile,
        integrated_result,
        grow_system_name: str,
        mission_status,
    ) -> str:
        environment_label = self.explainer.format_environment(mission.environment)
        return (
            f"{environment_label} mission status is {mission_status.value}: {integrated_result.crop.candidate.name.title()} "
            f"leads food production under a {grow_system_name.title()} plant layer, while "
            f"{integrated_result.algae.candidate.name.replace('_', ' ').title()} and "
            f"{integrated_result.microbial.candidate.name.replace('_', ' ').title()} strengthen atmospheric and recycling support."
        )

    def _build_operational_note(self, risk_analysis, integrated_result, llm_analysis) -> str:
        if llm_analysis.weaknesses and "contamination" in llm_analysis.weaknesses[0].lower():
            return "Monitor microbial containment boundaries closely and preserve sanitation margin before scaling throughput."
        if risk_analysis.factors and "water" in risk_analysis.factors[0].lower():
            return "Protect water recovery throughput and verify that algae and crop loops remain coupled within expected margins."
        if integrated_result.interaction.complexity_penalty >= 0.58:
            return "Crew workload is becoming a visible constraint, so maintenance batching and subsystem simplification should be prioritized."
        return "Maintain the current loop configuration, log state changes, and monitor oxygen, nutrient, and contamination margins together."

    def _build_tradeoff_summary(self, integrated_result, grow_system_name: str) -> str:
        return (
            f"{grow_system_name.title()} and {integrated_result.algae.candidate.name.replace('_', ' ').title()} preserve loop performance, "
            f"but the main tradeoff is higher integrated complexity while "
            f"{integrated_result.microbial.candidate.name.replace('_', ' ').title()} remains the primary contamination watch item."
        )

    def _build_weak_points(self, llm_analysis, risk_analysis) -> str:
        if llm_analysis.weaknesses:
            return " ".join(llm_analysis.weaknesses[:2])
        if risk_analysis.factors:
            return "; ".join(risk_analysis.factors[:2])
        return "No dominant weak point was flagged."

    def _resources_from_constraints(self, constraints: MissionConstraints) -> MissionResources:
        return MissionResources(
            water=self._clamp_resource(constraint_to_resource_margin(constraints.water)),
            energy=self._clamp_resource(constraint_to_resource_margin(constraints.energy)),
            area=self._clamp_resource(constraint_to_resource_margin(constraints.area)),
        )

    def _clamp_resource(self, value: float) -> float:
        return round(max(0.0, min(100.0, value)), 2)

    def _margin_to_constraint(self, margin: float) -> ConstraintLevel:
        if margin >= 70:
            return ConstraintLevel.LOW
        if margin >= 45:
            return ConstraintLevel.MEDIUM
        return ConstraintLevel.HIGH

    def _resolve_active_candidates(self, state: MissionState) -> tuple[Any | None, Any | None, Any | None]:
        crop_name = state.active_system.crops[0].name if state.active_system.crops else None
        algae_name = state.active_system.algae[0].name if state.active_system.algae else None
        microbial_name = state.active_system.microbial[0].name if state.active_system.microbial else None

        crop = next((item for item in self.provider.get_crops() if item.name == crop_name), None)
        algae = next((item for item in self.provider.get_algae_systems() if item.name == algae_name), None)
        microbial = next((item for item in self.provider.get_microbial_systems() if item.name == microbial_name), None)
        return crop, algae, microbial

    def _apply_weekly_resource_usage(self, state: MissionState, weeks: int) -> MissionResources:
        crop, algae, microbial = self._resolve_active_candidates(state)

        crop_water = (0.8 + ((crop.water_need / 55) if crop else 0.9)) * weeks
        crop_energy = (0.55 + ((crop.energy_need / 85) if crop else 0.75)) * weeks
        crop_area = (0.25 + ((crop.area_need / 150) if crop else 0.35)) * weeks

        algae_water = max(0.0, ((100 - algae.water_system_compatibility) / 250) if algae else 0.18) * weeks
        algae_energy = (0.3 + ((algae.energy_light_dependency / 120) if algae else 0.45)) * weeks

        microbial_water_offset = ((microbial.waste_recycling_efficiency / 240) if microbial else 0.12) * weeks
        microbial_energy = (0.2 + ((microbial.reactor_dependency / 260) if microbial else 0.28)) * weeks
        microbial_area = (0.1 + ((microbial.maintenance_burden / 400) if microbial else 0.14)) * weeks

        water_use = max(0.8 * weeks, crop_water + algae_water + (0.25 * weeks) - microbial_water_offset)
        energy_use = max(0.8 * weeks, crop_energy + algae_energy + microbial_energy + (0.3 * weeks))
        area_use = max(0.25 * weeks, crop_area + microbial_area)

        return MissionResources(
            water=self._clamp_resource(state.resources.water - water_use),
            energy=self._clamp_resource(state.resources.energy - energy_use),
            area=self._clamp_resource(state.resources.area - area_use),
        )

    def _derive_weekly_adjustments(
        self,
        state: MissionState,
        resources: MissionResources,
        events: MissionEvents | None,
        weeks: int,
    ) -> dict[str, object]:
        crop, algae, microbial = self._resolve_active_candidates(state)
        temporary_penalties: dict[str, float] | None = None
        status_penalty = False
        risk_bias = 1.0
        complexity_bias = 1.0
        loop_bias = 1.0

        if crop is not None:
            risk_bias += weeks * ((crop.risk + crop.maintenance) / 5000)
            complexity_bias += weeks * (crop.maintenance / 7000)
        if algae is not None:
            risk_bias -= weeks * (algae.oxygen_contribution / 5000)
            complexity_bias += weeks * (algae.energy_light_dependency / 5000)
            loop_bias += weeks * (algae.co2_utilization / 7000)
        if microbial is not None:
            risk_bias -= weeks * (microbial.nutrient_conversion_capability / 6500)
            complexity_bias += weeks * (microbial.maintenance_burden / 7000)
            loop_bias += weeks * (microbial.loop_closure_contribution / 4500)

        if resources.water < 50:
            risk_bias += (50 - resources.water) / 220
        if resources.energy < 50:
            risk_bias += (50 - resources.energy) / 280
            complexity_bias += (50 - resources.energy) / 260
        if resources.area < 45:
            complexity_bias += (45 - resources.area) / 320

        if crop is not None and (resources.water < 45 or resources.energy < 45):
            shortage = max(45 - resources.water, 45 - resources.energy, 0) / 100
            temporary_penalties = {
                crop.name.lower(): min(0.35, 0.08 + shortage + (crop.growth_time / 500))
            }
            status_penalty = True

        if (
            events is not None
            and events.contamination is not None
            and microbial is not None
        ):
            risk_bias += (events.contamination * microbial.contamination_risk) / 12000

        return {
            "temporary_penalties": temporary_penalties,
            "status_penalty": status_penalty,
            "risk_bias": round(max(0.8, risk_bias), 3),
            "complexity_bias": round(max(0.85, complexity_bias), 3),
            "loop_bias": round(max(0.85, loop_bias), 3),
        }

    def _merge_penalties(
        self,
        first: dict[str, float] | None,
        second: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if not first and not second:
            return None
        merged = dict(first or {})
        for key, value in (second or {}).items():
            merged[key] = max(merged.get(key, 0.0), value)
        return merged

    def _apply_cumulative_risk(
        self,
        previous_state: MissionState,
        updated_state: MissionState,
        events: MissionEvents | None,
    ) -> tuple[MissionState, float]:
        previous_risk = previous_state.system_metrics.risk_level / 100
        delta_risk = self._compute_weekly_delta_risk(previous_state, updated_state, events)
        cumulative_risk = max(
            0.0,
            min(1.0, (previous_risk * (1 - RISK_DECAY)) + delta_risk),
        )
        cumulative_risk_level = round(cumulative_risk * 100, 2)
        risk_delta = round(cumulative_risk_level - previous_state.system_metrics.risk_level, 3)

        updated_metrics = updated_state.system_metrics.model_copy(
            update={"risk_level": cumulative_risk_level},
            deep=True,
        )
        updated_history = list(updated_state.history)
        if updated_history:
            updated_history[-1] = updated_history[-1].model_copy(
                update={"risk_level": cumulative_risk_level},
                deep=True,
            )

        return (
            updated_state.model_copy(
                update={
                    "system_metrics": updated_metrics,
                    "history": updated_history,
                },
                deep=True,
            ),
            risk_delta,
        )

    def _compute_weekly_delta_risk(
        self,
        previous_state: MissionState,
        updated_state: MissionState,
        events: MissionEvents | None,
    ) -> float:
        crop, algae, microbial = self._resolve_active_candidates(updated_state)
        instantaneous_risk = updated_state.system_metrics.risk_level / 100

        water_pressure = max(0.0, 45 - updated_state.resources.water) / 180
        energy_pressure = max(0.0, 45 - updated_state.resources.energy) / 200
        crop_pressure = (
            ((crop.risk / 2000) + (crop.maintenance / 2600))
            if crop is not None
            else 0.02
        )
        crop_mismatch = (
            max(0.0, (crop.water_need - updated_state.resources.water) / 900)
            if crop is not None
            else 0.0
        )
        microbial_gap = (
            max(0.0, 65 - microbial.loop_closure_contribution) / 1800
            if microbial is not None
            else 0.02
        )
        event_pressure = 0.0
        if events is not None:
            if events.contamination is not None:
                event_pressure += events.contamination / 300
            if events.water_drop is not None:
                event_pressure += events.water_drop / 700
            if events.energy_drop is not None:
                event_pressure += events.energy_drop / 800
            if events.yield_variation is not None and events.yield_variation < 0:
                event_pressure += abs(events.yield_variation) / 700

        atmospheric_relief = (
            ((algae.oxygen_contribution / 5000) + (algae.co2_utilization / 7000))
            if algae is not None
            else 0.0
        )
        microbial_relief = (
            ((microbial.nutrient_conversion_capability / 5500) + (microbial.waste_recycling_efficiency / 7000))
            if microbial is not None
            else 0.0
        )
        stability_relief = 0.012
        if updated_state.system_metrics.oxygen_level >= previous_state.system_metrics.oxygen_level:
            stability_relief += 0.008
        if updated_state.system_metrics.nutrient_cycle_efficiency >= previous_state.system_metrics.nutrient_cycle_efficiency:
            stability_relief += 0.008

        instantaneous_pressure = max(0.0, instantaneous_risk - 0.25) * 0.25

        delta_risk = (
            water_pressure
            + energy_pressure
            + crop_pressure
            + crop_mismatch
            + microbial_gap
            + event_pressure
            + instantaneous_pressure
            - atmospheric_relief
            - microbial_relief
            - stability_relief
        )
        return round(max(-0.03, min(0.16, delta_risk)), 4)

    def _derive_event_adjustments(
        self,
        state: MissionState,
        events: MissionEvents | None,
    ) -> dict[str, object]:
        temporary_penalties: dict[str, float] | None = None
        status_penalty = False
        risk_bias = 1.0
        complexity_bias = 1.0
        loop_bias = 1.0

        if events is None:
            return {
                "temporary_penalties": temporary_penalties,
                "status_penalty": status_penalty,
                "risk_bias": risk_bias,
                "complexity_bias": complexity_bias,
                "loop_bias": loop_bias,
            }

        if events.contamination is not None:
            risk_bias += events.contamination / 120
            complexity_bias += events.contamination / 240

        if events.yield_variation is not None and events.yield_variation < 0 and state.active_system.crops:
            crop_name = state.active_system.crops[0].name.lower()
            temporary_penalties = {crop_name: min(abs(events.yield_variation) / 100, 0.45)}
            status_penalty = True

        if events.water_drop is not None and events.water_drop >= 12:
            loop_bias += 0.05
        if events.energy_drop is not None and events.energy_drop >= 12:
            complexity_bias += 0.05

        return {
            "temporary_penalties": temporary_penalties,
            "status_penalty": status_penalty,
            "risk_bias": round(risk_bias, 3),
            "complexity_bias": round(complexity_bias, 3),
            "loop_bias": round(loop_bias, 3),
        }

    def _build_step_event_label(self, events: MissionEvents | None) -> str:
        if events is None:
            return "weekly_progression"
        active_events = [name for name, value in events.model_dump().items() if value is not None]
        return "weekly_progression_" + "_".join(active_events or ["none"])

    def _build_system_changes(self, previous_state: MissionState, updated_state: MissionState) -> list[str]:
        changes: list[str] = []
        previous_crop = previous_state.active_system.crops[0].name if previous_state.active_system.crops else None
        updated_crop = updated_state.active_system.crops[0].name if updated_state.active_system.crops else None
        previous_algae = previous_state.active_system.algae[0].name if previous_state.active_system.algae else None
        updated_algae = updated_state.active_system.algae[0].name if updated_state.active_system.algae else None
        previous_microbial = previous_state.active_system.microbial[0].name if previous_state.active_system.microbial else None
        updated_microbial = updated_state.active_system.microbial[0].name if updated_state.active_system.microbial else None
        previous_grow_system = previous_state.active_system.crops[0].support_system if previous_state.active_system.crops else None
        updated_grow_system = updated_state.active_system.crops[0].support_system if updated_state.active_system.crops else None

        if previous_crop != updated_crop:
            changes.append(f"crop:{previous_crop}->{updated_crop}")
        if previous_algae != updated_algae:
            changes.append(f"algae:{previous_algae}->{updated_algae}")
        if previous_microbial != updated_microbial:
            changes.append(f"microbial:{previous_microbial}->{updated_microbial}")
        if previous_grow_system != updated_grow_system:
            changes.append(f"grow_system:{previous_grow_system}->{updated_grow_system}")
        return changes

    def _build_event_pressure_summary(
        self,
        previous_state: MissionState,
        updated_state: MissionState,
        events: MissionEvents | None,
        request_time_step: int,
    ) -> str:
        fragments: list[str] = []
        if events is not None:
            if events.water_drop is not None:
                fragments.append("Water drop tightened weekly recovery margin")
            if events.energy_drop is not None:
                fragments.append("Energy drop increased weekly power pressure")
            if events.contamination is not None:
                fragments.append("Contamination raised biological risk")
            if events.yield_variation is not None:
                if events.yield_variation < 0:
                    fragments.append("Yield drop reduced crop output")
                elif events.yield_variation > 0:
                    fragments.append("Yield variation improved crop output")

        if not fragments:
            water_delta = previous_state.resources.water - updated_state.resources.water
            energy_delta = previous_state.resources.energy - updated_state.resources.energy
            if water_delta >= energy_delta:
                fragments.append("Weekly crop demand reduced water reserves")
            else:
                fragments.append("Weekly reactor and lighting demand reduced energy reserves")
            if request_time_step > 1:
                fragments.append(f"{request_time_step} weeks of baseline load accumulated")

        if len(fragments) == 1:
            return fragments[0]
        if len(fragments) == 2:
            return f"{fragments[0]} and {fragments[1].lower()}"
        return f"{fragments[0]}, {fragments[1].lower()}, and {fragments[2].lower()}"

    def _build_primary_metric_effect_summary(
        self,
        previous_state: MissionState,
        updated_state: MissionState,
    ) -> str:
        metric_deltas = {
            "oxygen support": updated_state.system_metrics.oxygen_level - previous_state.system_metrics.oxygen_level,
            "CO2 balance": updated_state.system_metrics.co2_balance - previous_state.system_metrics.co2_balance,
            "food supply": updated_state.system_metrics.food_supply - previous_state.system_metrics.food_supply,
            "nutrient cycling": (
                updated_state.system_metrics.nutrient_cycle_efficiency
                - previous_state.system_metrics.nutrient_cycle_efficiency
            ),
        }
        label, delta = max(metric_deltas.items(), key=lambda item: abs(item[1]))

        if abs(delta) < 0.25:
            return "core loop metrics stayed near baseline"
        if delta > 0:
            return f"{label} improved"
        return f"{label} weakened"

    def _build_weekly_driver_summary(
        self,
        updated_state: MissionState,
    ) -> str:
        crop, algae, microbial = self._resolve_active_candidates(updated_state)
        if crop is not None and updated_state.resources.water <= updated_state.resources.energy:
            return f"{crop.name.title()} set the heaviest weekly resource demand"
        if algae is not None and algae.oxygen_contribution >= 70:
            return f"{algae.name.title()} buffered atmospheric stress"
        if microbial is not None and microbial.nutrient_conversion_capability >= 65:
            return f"{microbial.name.title()} stabilized nutrient recovery"
        if crop is not None:
            return f"{crop.name.title()} remained the main food-pressure driver"
        return "The active biological stack remained the main weekly driver"

    def _build_system_change_scope_summary(self, system_changes: list[str]) -> str:
        if not system_changes:
            return "The stack held configuration"

        changed_layers: list[str] = []
        if any(change.startswith("crop:") for change in system_changes):
            changed_layers.append("crop")
        if any(change.startswith("algae:") for change in system_changes):
            changed_layers.append("algae")
        if any(change.startswith("microbial:") for change in system_changes):
            changed_layers.append("microbial")
        if any(change.startswith("grow_system:") for change in system_changes):
            changed_layers.append("plant system")

        if not changed_layers:
            return "The stack reconfigured"
        if len(changed_layers) == 1:
            return f"The {changed_layers[0]} layer reconfigured"
        if len(changed_layers) == 2:
            return f"The {changed_layers[0]} and {changed_layers[1]} layers reconfigured"
        return f"The stack reconfigured across {', '.join(changed_layers[:-1])}, and {changed_layers[-1]}"

    def _build_risk_shift_summary(
        self,
        previous_state: MissionState,
        updated_state: MissionState,
        risk_delta: float,
    ) -> str:
        previous_risk = previous_state.system_metrics.risk_level
        updated_risk = updated_state.system_metrics.risk_level
        if risk_delta > 0.05:
            return f"system stress accumulated and risk rose from {previous_risk:.2f} to {updated_risk:.2f}"
        if risk_delta < -0.05:
            return f"risk pressure eased from {previous_risk:.2f} to {updated_risk:.2f}"
        return f"risk held near {updated_risk:.2f} after weekly carry-over"

    def _build_mission_step_summary(
        self,
        previous_state: MissionState,
        updated_state: MissionState,
        events: MissionEvents | None,
        system_changes: list[str],
        risk_delta: float,
        request_time_step: int,
    ) -> str:
        event_summary = self._build_event_pressure_summary(
            previous_state=previous_state,
            updated_state=updated_state,
            events=events,
            request_time_step=request_time_step,
        )
        driver_summary = self._build_weekly_driver_summary(updated_state)
        metric_effect = self._build_primary_metric_effect_summary(previous_state, updated_state)
        change_scope = self._build_system_change_scope_summary(system_changes)
        risk_summary = self._build_risk_shift_summary(previous_state, updated_state, risk_delta)
        return (
            f"Week {updated_state.time}: {event_summary}. {driver_summary}. "
            f"{change_scope}; {metric_effect} and {risk_summary}."
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
