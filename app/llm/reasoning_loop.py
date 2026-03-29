"""Deterministic-first reasoning loop with optional Gemini critique."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from app.core.mission_state import MissionState
from app.core.simulation import MissionEvents
from app.engine.integration_engine import IntegrationEngine
from app.engine.types import IntegratedResult
from app.models.mission import Environment, MissionProfile
from app.models.response import GeminiNarrative, LLMAnalysis, RecommendationResponse, UIEnhancedNarrative
from app.models.system import GrowingSystem
from app.services.data_provider import DataProvider

from .ai_service import AIService
from .gemini_client import GeminiClient


logger = logging.getLogger(__name__)


class ReasoningLoop:
    """Run a bounded critic/refiner pass over deterministic results."""

    def __init__(
        self,
        provider: DataProvider,
        integration_engine: IntegrationEngine | None = None,
        gemini_client: GeminiClient | None = None,
        ai_service: AIService | None = None,
        max_iterations: int = 2,
    ) -> None:
        self.provider = provider
        self.integration_engine = integration_engine or IntegrationEngine(provider)
        self.gemini_client = gemini_client or GeminiClient()
        self.ai_service = ai_service or AIService(gemini_client=self.gemini_client)
        self.max_iterations = max_iterations

    def run(
        self,
        mission: MissionProfile,
        result: IntegratedResult,
        top_crop_rankings: list[Any],
        grow_system: GrowingSystem,
        temporary_penalties: dict[str, float] | None = None,
        base_biases: dict[str, float] | None = None,
        *,
        source: str = "recommend",
        deterministic_explanations: Mapping[str, Any] | None = None,
        mission_state: MissionState | Mapping[str, Any] | None = None,
        previous_state: MissionState | Mapping[str, Any] | None = None,
        events: MissionEvents | Mapping[str, Any] | None = None,
        deltas: Mapping[str, Any] | None = None,
        allow_refinement: bool = True,
        use_llm: bool = True,
    ) -> tuple[IntegratedResult, list[Any], GrowingSystem, GeminiNarrative]:
        narrative = self._analyze_result(
            source=source,
            mission=mission,
            result=result,
            grow_system=grow_system,
            deterministic_explanations=deterministic_explanations,
            mission_state=mission_state,
            previous_state=previous_state,
            events=events,
            deltas=deltas,
            allow_refinement=allow_refinement,
            use_llm=use_llm,
        )

        if not allow_refinement or self.max_iterations < 2:
            narrative = self._ensure_second_pass(
                narrative,
                source=source,
                selected_configuration=self._selected_configuration(result, grow_system.name),
                decision="retain",
                reason="Critique-only mode kept the deterministic configuration without rerunning selection.",
            )
            return result, top_crop_rankings, grow_system, narrative

        refinement = self._derive_refinement(narrative.debug_layer, mission, result)
        if refinement is None:
            narrative = self._ensure_second_pass(
                narrative,
                source=source,
                selected_configuration=self._selected_configuration(result, grow_system.name),
                decision="retain",
                reason="The deterministic configuration remained acceptable after critique.",
            )
            return result, top_crop_rankings, grow_system, narrative

        rerun_result, rerun_crops, rerun_grow_system = self.integration_engine.select_configuration(
            mission=mission,
            temporary_penalties=temporary_penalties,
            risk_bias=(base_biases or {}).get("risk_bias", 1.0) * refinement["risk_bias"],
            complexity_bias=(base_biases or {}).get("complexity_bias", 1.0) * refinement["complexity_bias"],
            loop_bias=(base_biases or {}).get("loop_bias", 1.0) * refinement["loop_bias"],
        )

        if rerun_result.integrated_score > result.integrated_score + 0.02:
            updated_debug = narrative.debug_layer.model_copy(
                update={
                    "second_pass": {
                        "decision": "refine",
                        "rationale": "A second deterministic pass improved the integrated score after critique.",
                        "applied_adjustments": refinement,
                        "selected_configuration": self._selected_configuration(
                            rerun_result,
                            rerun_grow_system.name,
                        ),
                    }
                }
            )
            updated_debug.second_pass_decision = dict(updated_debug.second_pass)
            narrative = narrative.model_copy(update={"debug_layer": updated_debug})
            return rerun_result, rerun_crops, rerun_grow_system, narrative

        updated_debug = narrative.debug_layer.model_copy(
            update={
                "second_pass": {
                    "decision": "retain",
                    "rationale": "The second deterministic pass did not outperform the baseline configuration.",
                    "applied_adjustments": refinement,
                    "selected_configuration": self._selected_configuration(result, grow_system.name),
                }
            }
        )
        updated_debug.second_pass_decision = dict(updated_debug.second_pass)
        narrative = narrative.model_copy(update={"debug_layer": updated_debug})
        return result, top_crop_rankings, grow_system, narrative

    def analyze_response(
        self,
        response: RecommendationResponse,
        *,
        source: str,
        previous_recommendation: RecommendationResponse | None = None,
        previous_state: MissionState | Mapping[str, Any] | None = None,
        events: MissionEvents | Mapping[str, Any] | None = None,
        deltas: Mapping[str, Any] | None = None,
        use_llm: bool = True,
    ) -> GeminiNarrative:
        narrative = self._analyze_payload(
            source=source,
            mission=response.mission_profile,
            selected_roles=self._selected_roles_from_response(response),
            scores=response.scores.model_dump(mode="json"),
            deterministic_explanations=self._deterministic_explanations_from_response(response),
            mission_state=response.mission_state,
            previous_state=previous_state or (previous_recommendation.mission_state if previous_recommendation else None),
            events=events,
            deltas=deltas,
            use_llm=use_llm,
        )
        return self._ensure_second_pass(
            narrative,
            source=source,
            selected_configuration={
                "crop": response.selected_system.crop.name,
                "algae": response.selected_system.algae.name,
                "microbial": response.selected_system.microbial.name,
                "grow_system": response.recommended_system,
            },
            decision="retain",
            reason="Critique-only mode did not rerun deterministic selection after the update.",
        )

    def _analyze_result(
        self,
        *,
        source: str,
        mission: MissionProfile,
        result: IntegratedResult,
        grow_system: GrowingSystem,
        deterministic_explanations: Mapping[str, Any] | None,
        mission_state: MissionState | Mapping[str, Any] | None,
        previous_state: MissionState | Mapping[str, Any] | None,
        events: MissionEvents | Mapping[str, Any] | None,
        deltas: Mapping[str, Any] | None,
        allow_refinement: bool,
        use_llm: bool,
    ) -> GeminiNarrative:
        return self._analyze_payload(
            source=source,
            mission=mission,
            selected_roles=self._selected_roles_from_result(result, grow_system),
            scores=self._scores_from_result(result),
            deterministic_explanations=deterministic_explanations,
            mission_state=mission_state,
            previous_state=previous_state,
            events=events,
            deltas={
                **(dict(deltas or {})),
                "allow_refinement": allow_refinement,
            },
            use_llm=use_llm,
        )

    def _analyze_payload(
        self,
        *,
        source: str,
        mission: MissionProfile,
        selected_roles: Mapping[str, Any],
        scores: Mapping[str, Any],
        deterministic_explanations: Mapping[str, Any] | None,
        mission_state: MissionState | Mapping[str, Any] | None,
        previous_state: MissionState | Mapping[str, Any] | None,
        events: MissionEvents | Mapping[str, Any] | None,
        deltas: Mapping[str, Any] | None,
        use_llm: bool,
    ) -> GeminiNarrative:
        payload = self._build_llm_payload(
            source=source,
            mission=mission,
            selected_roles=selected_roles,
            scores=scores,
            deterministic_explanations=deterministic_explanations,
            mission_state=mission_state,
            previous_state=previous_state,
            events=events,
            deltas=deltas,
        )
        fallback = self._build_rule_based_narrative(
            source=source,
            mission=mission,
            selected_roles=selected_roles,
            scores=scores,
            deterministic_explanations=deterministic_explanations,
            mission_state=mission_state,
            previous_state=previous_state,
            events=events,
            deltas=deltas,
        )

        llm_allowed = bool(use_llm and source == "recommend")
        if use_llm and not llm_allowed:
            logger.info(
                "Gemini blocked for source=%s; simulation/update flows are deterministic-only.",
                source,
            )
        if not llm_allowed:
            logger.info("Gemini blocked for source=%s; using deterministic ui/debug narrative.", source)
            return fallback

        self.ai_service.gemini_client = self.gemini_client
        gemini_narrative = self.ai_service.generate_recommendation_explanation(
            payload,
            fallback=fallback,
            use_ai=llm_allowed,
        )
        if gemini_narrative.debug_layer.reasoning_summary.endswith(" -gemini"):
            logger.info(
                "Gemini narrative available for source=%s: %s",
                source,
                gemini_narrative.debug_layer.reasoning_summary,
            )
        else:
            logger.info("Using deterministic fallback llm/ui narrative for source=%s.", source)
        return gemini_narrative

    def _build_llm_payload(
        self,
        *,
        source: str,
        mission: MissionProfile,
        selected_roles: Mapping[str, Any],
        scores: Mapping[str, Any],
        deterministic_explanations: Mapping[str, Any] | None,
        mission_state: MissionState | Mapping[str, Any] | None,
        previous_state: MissionState | Mapping[str, Any] | None,
        events: MissionEvents | Mapping[str, Any] | None,
        deltas: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        current_state_summary = self._summarize_state(mission_state)
        previous_state_summary = self._summarize_state(previous_state)
        return {
            "request_context": {
                "source": source,
                "deterministic_authoritative": True,
                "gemini_optional": True,
                "has_current_state": current_state_summary is not None,
                "has_previous_state": previous_state_summary is not None,
                "has_events": events is not None,
                "has_deltas": bool(deltas),
            },
            "mission": mission.model_dump(mode="json"),
            "selected_roles": dict(selected_roles),
            "scores": dict(scores),
            "deterministic_explanations": dict(deterministic_explanations or {}),
            "mission_state": current_state_summary,
            "previous_state": previous_state_summary,
            "history_summary": self._history_summary(mission_state),
            "events": self._serialize_optional(events),
            "deltas": dict(deltas or {}),
        }

    def _build_rule_based_narrative(
        self,
        *,
        source: str,
        mission: MissionProfile,
        selected_roles: Mapping[str, Any],
        scores: Mapping[str, Any],
        deterministic_explanations: Mapping[str, Any] | None,
        mission_state: MissionState | Mapping[str, Any] | None,
        previous_state: MissionState | Mapping[str, Any] | None,
        events: MissionEvents | Mapping[str, Any] | None,
        deltas: Mapping[str, Any] | None,
    ) -> GeminiNarrative:
        crop_name = self._role_name(selected_roles, "crop")
        algae_name = self._role_name(selected_roles, "algae")
        microbial_name = self._role_name(selected_roles, "microbial")
        grow_system = self._grow_system_name(selected_roles)
        interaction = scores.get("interaction", {}) if isinstance(scores, Mapping) else {}
        domain_scores = scores.get("domain", {}) if isinstance(scores, Mapping) else {}
        current_state_summary = self._summarize_state(mission_state)
        previous_state_summary = self._summarize_state(previous_state)
        serialized_events = self._serialize_optional(events) or {}
        deltas = dict(deltas or {})

        reasoning_summary = (
            f"The deterministic engine selected {crop_name}, {algae_name}, and {microbial_name} with {grow_system} "
            f"for the {mission.environment.value} mission because that stack best balances domain fit, "
            "interaction synergy, and closed-loop stability."
        )
        if source == "simulate":
            reasoning_summary = self._build_simulation_summary(
                base_summary=reasoning_summary,
                deltas=deltas,
                events=serialized_events,
            )
        elif source == "mission_step":
            reasoning_summary = self._build_mission_step_reasoning(
                base_summary=reasoning_summary,
                current_state=current_state_summary,
                previous_state=previous_state_summary,
                deltas=deltas,
                events=serialized_events,
            )
        elif deterministic_explanations and deterministic_explanations.get("executive_summary"):
            reasoning_summary = (
                f"{deterministic_explanations['executive_summary']} "
                f"{reasoning_summary}"
            )

        weaknesses: list[str] = []
        improvements: list[str] = []

        if self._interaction_metric(interaction, "complexity_penalty") >= 0.58:
            weaknesses.append("Integrated maintenance complexity is elevated across crop, algae, and microbial layers.")
            improvements.append("Bias the next deterministic pass toward lower-complexity algae or microbial support.")
        if self._interaction_metric(interaction, "loop_closure_bonus") <= 0.62:
            weaknesses.append("Loop closure is useful but not yet deeply redundant.")
            improvements.append("Strengthen recycling or CO2-utilization coverage to improve loop closure.")
        if self._domain_risk(domain_scores, "microbial") >= 0.55:
            weaknesses.append("Microbial contamination or reactor dependency remains a weak link.")
            improvements.append("Prefer a lower-contamination microbial pathway if constraints tighten further.")
        if self._event_value(serialized_events, "contamination") is not None:
            weaknesses.append("Contamination stress is a current operational risk for the closed-loop stack.")
            improvements.append("Increase containment monitoring and favor lower-burden recycling modes until contamination pressure eases.")
        if deltas.get("risk_score_delta", 0) and float(deltas.get("risk_score_delta", 0)) > 0:
            weaknesses.append("Recent changes increased the overall mission-agriculture risk score.")
            improvements.append("Protect resilience margin before pushing higher-complexity operating modes.")
        if source == "mission_step" and current_state_summary and previous_state_summary:
            current_risk = current_state_summary.get("system_metrics", {}).get("risk_level")
            previous_risk = previous_state_summary.get("system_metrics", {}).get("risk_level")
            if isinstance(current_risk, (int, float)) and isinstance(previous_risk, (int, float)) and current_risk > previous_risk:
                weaknesses.append("Mission-state risk indicators are degrading over time.")
                improvements.append("Use the next step to stabilize oxygen, nutrient cycling, and contamination exposure together.")

        if not weaknesses:
            weaknesses.append("No single weak link currently dominates the deterministic loop design.")
        if not improvements:
            improvements.append("Hold the current deterministic configuration and continue tracking state drift.")

        alternative = {
            "crop": crop_name,
            "algae": "chlorella_panel" if algae_name != "chlorella_panel" else algae_name,
            "microbial": "biofilm_polisher" if microbial_name != "biofilm_polisher" else microbial_name,
            "grow_system": "hydroponic" if mission.environment is Environment.ISS else grow_system,
            "rationale": "This alternative reduces maintenance burden while preserving a workable closed-loop posture.",
        }

        debug_layer = LLMAnalysis.from_payload(
            {
                "reasoning_summary": reasoning_summary,
                "weaknesses": weaknesses[:4],
                "improvements": improvements[:4],
                "alternative": alternative,
                "second_pass": {
                    "decision": "retain",
                    "rationale": "Deterministic fallback analysis did not trigger an additional rerun.",
                    "selected_configuration": {
                        "crop": crop_name,
                        "algae": algae_name,
                        "microbial": microbial_name,
                        "grow_system": grow_system,
                    },
                },
            },
            default_reasoning="Deterministic fallback analysis remains active.",
        )
        ui_layer = self._build_rule_based_ui_layer(
            source=source,
            mission=mission,
            selected_roles=selected_roles,
            deterministic_explanations=deterministic_explanations,
            deltas=deltas,
            events=serialized_events,
            fallback_reasoning=reasoning_summary,
        )
        return GeminiNarrative(ui_layer=ui_layer, debug_layer=debug_layer)

    def _build_rule_based_ui_layer(
        self,
        *,
        source: str,
        mission: MissionProfile,
        selected_roles: Mapping[str, Any],
        deterministic_explanations: Mapping[str, Any] | None,
        deltas: Mapping[str, Any] | None,
        events: Mapping[str, Any],
        fallback_reasoning: str,
    ) -> UIEnhancedNarrative:
        deltas = dict(deltas or {})
        executive_summary = ""
        if deterministic_explanations and isinstance(deterministic_explanations.get("executive_summary"), str):
            executive_summary = str(deterministic_explanations["executive_summary"]).strip()
        if not executive_summary:
            executive_summary = fallback_reasoning

        return UIEnhancedNarrative.from_payload(
            {
                "crop_note": self._build_domain_ui_note(selected_roles, "crop"),
                "algae_note": self._build_domain_ui_note(selected_roles, "algae"),
                "microbial_note": self._build_domain_ui_note(selected_roles, "microbial"),
                "executive_summary": executive_summary,
                "adaptation_summary": self._build_adaptation_ui_summary(
                    source=source,
                    mission=mission,
                    deltas=deltas,
                    events=events,
                ),
            }
        )

    def _build_domain_ui_note(self, selected_roles: Mapping[str, Any], role: str) -> str:
        role_payload = selected_roles.get(role, {})
        if not isinstance(role_payload, Mapping):
            return ""

        name = str(role_payload.get("name", role)).replace("_", " ").title()
        role_description = str(role_payload.get("role", "")).strip()
        support_system = role_payload.get("support_system")
        notes = role_payload.get("notes")
        note_text = ""
        if isinstance(notes, list):
            cleaned = []
            for item in notes:
                text = str(item).strip().rstrip(".")
                if not text:
                    continue
                cleaned.append(text[0].upper() + text[1:] if len(text) > 1 else text.upper())
            note_text = ". ".join(cleaned[:2]).strip()
            if note_text:
                note_text += "."

        parts: list[str] = []
        if role == "crop" and support_system:
            support_label = str(support_system).replace("_", " ").title()
            parts.append(f"{name} anchors {role_description} through the {support_label} plant layer.")
        elif role_description:
            parts.append(f"{name} covers {role_description}.")
        else:
            parts.append(f"{name} remains active in the {role} layer.")
        if note_text:
            parts.append(note_text)
        return " ".join(parts[:2]).strip()

    def _build_adaptation_ui_summary(
        self,
        *,
        source: str,
        mission: MissionProfile,
        deltas: Mapping[str, Any],
        events: Mapping[str, Any],
    ) -> str:
        if source == "recommend":
            return ""
        if source == "simulate":
            change_event = events.get("change_event", "condition change")
            risk_score_delta = deltas.get("risk_score_delta")
            parts = [f"{str(change_event).replace('_', ' ').title()} forced a deterministic re-check for the {mission.environment.value} mission."]
            if deltas.get("system_changed"):
                parts.append("The plant system changed to protect resilience.")
            elif deltas.get("previous_top_crop") != deltas.get("new_top_crop"):
                parts.append("Lead crop priority changed under the updated mission pressure.")
            if isinstance(risk_score_delta, (int, float)):
                direction = "rose" if risk_score_delta > 0 else "fell" if risk_score_delta < 0 else "held steady"
                parts.append(f"Overall mission-agriculture risk {direction}.")
            return " ".join(parts[:3]).strip()
        if source == "mission_step":
            active_events = [name for name, value in events.items() if value is not None]
            event_summary = ", ".join(active_events) if active_events else "no major events"
            parts = [f"Mission step processed {event_summary}."]
            if deltas.get("system_changes"):
                parts.append("The biological loop reconfigured to protect stability.")
            elif isinstance(deltas.get("risk_delta"), (int, float)):
                direction = "rose" if float(deltas["risk_delta"]) > 0 else "fell" if float(deltas["risk_delta"]) < 0 else "held steady"
                parts.append(f"The biological loop held configuration while risk {direction}.")
            return " ".join(parts[:2]).strip()
        return ""

    def _build_simulation_summary(
        self,
        *,
        base_summary: str,
        deltas: Mapping[str, Any],
        events: Mapping[str, Any],
    ) -> str:
        change_event = events.get("change_event", "simulation event")
        previous_top = deltas.get("previous_top_crop")
        new_top = deltas.get("new_top_crop")
        previous_system = deltas.get("previous_system")
        new_system = deltas.get("new_system")
        risk_delta = deltas.get("risk_score_delta")

        parts = [f"Simulation update after {change_event}: {base_summary}"]
        if previous_top and new_top:
            parts.append(f"Lead crop moved from {previous_top} to {new_top}.")
        if previous_system and new_system:
            if previous_system != new_system:
                parts.append(f"Plant system shifted from {previous_system} to {new_system}.")
            else:
                parts.append(f"Plant system remained at {new_system}.")
        if isinstance(risk_delta, (int, float)):
            parts.append(f"Risk score delta was {risk_delta:+.3f}.")
        return " ".join(parts)

    def _build_mission_step_reasoning(
        self,
        *,
        base_summary: str,
        current_state: Mapping[str, Any] | None,
        previous_state: Mapping[str, Any] | None,
        deltas: Mapping[str, Any],
        events: Mapping[str, Any],
    ) -> str:
        parts = [f"Mission step analysis: {base_summary}"]
        active_events = [name for name, value in events.items() if value is not None]
        if active_events:
            parts.append(f"Applied events: {', '.join(active_events)}.")
        if deltas.get("system_changes"):
            parts.append(f"System changes: {', '.join(deltas['system_changes'])}.")
        if isinstance(deltas.get("risk_delta"), (int, float)):
            parts.append(f"Mission-step risk delta was {float(deltas['risk_delta']):+.3f}.")
        if current_state and previous_state:
            current_metrics = current_state.get("system_metrics", {})
            previous_metrics = previous_state.get("system_metrics", {})
            current_nutrient = current_metrics.get("nutrient_cycle_efficiency")
            previous_nutrient = previous_metrics.get("nutrient_cycle_efficiency")
            if isinstance(current_nutrient, (int, float)) and isinstance(previous_nutrient, (int, float)):
                direction = "improving" if current_nutrient >= previous_nutrient else "degrading"
                parts.append(f"Nutrient-cycle efficiency is {direction} over time.")
        return " ".join(parts)

    def _derive_refinement(
        self,
        llm_analysis: LLMAnalysis,
        mission: MissionProfile,
        result: IntegratedResult,
    ) -> dict[str, float] | None:
        text = " ".join([llm_analysis.reasoning_summary, *llm_analysis.weaknesses, *llm_analysis.improvements]).lower()
        risk_bias = 1.0
        complexity_bias = 1.0
        loop_bias = 1.0
        changed = False

        if "contamination" in text or result.microbial.risk_score >= 0.55:
            risk_bias = 1.15
            changed = True
        if "complex" in text or "maintenance" in text or result.interaction.complexity_penalty >= 0.58:
            complexity_bias = 1.15 if mission.environment is Environment.ISS else 1.10
            changed = True
        if "loop closure" in text or result.interaction.loop_closure_bonus <= 0.62:
            loop_bias = 1.12
            changed = True

        if not changed:
            return None

        return {
            "risk_bias": risk_bias,
            "complexity_bias": complexity_bias,
            "loop_bias": loop_bias,
        }

    def _selected_roles_from_result(
        self,
        result: IntegratedResult,
        grow_system: GrowingSystem,
    ) -> dict[str, Any]:
        return {
            "crop": {
                "name": result.crop.candidate.name,
                "role": "plant food production",
                "support_system": grow_system.name,
                "metrics": result.crop.metrics,
                "notes": result.crop.notes,
            },
            "algae": {
                "name": result.algae.candidate.name,
                "role": "oxygen and biomass support",
                "metrics": result.algae.metrics,
                "notes": result.algae.notes,
            },
            "microbial": {
                "name": result.microbial.candidate.name,
                "role": "waste recycling and nutrient conversion",
                "metrics": result.microbial.metrics,
                "notes": result.microbial.notes,
            },
            "interaction": {
                "findings": result.interaction.notes,
                "grow_system": grow_system.name,
            },
        }

    def _selected_roles_from_response(self, response: RecommendationResponse) -> dict[str, Any]:
        return {
            "crop": {
                "name": response.selected_system.crop.name,
                "role": "plant food production",
                "support_system": response.selected_system.crop.support_system,
                "metrics": response.selected_system.crop.metrics,
                "notes": response.selected_system.crop.notes,
            },
            "algae": {
                "name": response.selected_system.algae.name,
                "role": "oxygen and biomass support",
                "metrics": response.selected_system.algae.metrics,
                "notes": response.selected_system.algae.notes,
            },
            "microbial": {
                "name": response.selected_system.microbial.name,
                "role": "waste recycling and nutrient conversion",
                "metrics": response.selected_system.microbial.metrics,
                "notes": response.selected_system.microbial.notes,
            },
            "interaction": {
                "findings": response.scores.interaction.model_dump(mode="json"),
                "grow_system": response.recommended_system,
            },
        }

    def _scores_from_result(self, result: IntegratedResult) -> dict[str, Any]:
        return {
            "domain": {
                "crop": {
                    "domain_score": result.crop.domain_score,
                    "mission_fit_score": result.crop.mission_fit_score,
                    "risk_score": result.crop.risk_score,
                },
                "algae": {
                    "domain_score": result.algae.domain_score,
                    "mission_fit_score": result.algae.mission_fit_score,
                    "risk_score": result.algae.risk_score,
                },
                "microbial": {
                    "domain_score": result.microbial.domain_score,
                    "mission_fit_score": result.microbial.mission_fit_score,
                    "risk_score": result.microbial.risk_score,
                },
            },
            "interaction": {
                "synergy_score": result.interaction.synergy_score,
                "conflict_score": result.interaction.conflict_score,
                "complexity_penalty": result.interaction.complexity_penalty,
                "resource_overlap": result.interaction.resource_overlap,
                "loop_closure_bonus": result.interaction.loop_closure_bonus,
                "findings": result.interaction.notes,
            },
            "integrated": result.integrated_score,
        }

    def _deterministic_explanations_from_response(self, response: RecommendationResponse) -> dict[str, Any]:
        explanations = response.explanations.model_dump(mode="json")
        explanations.update(
            {
                "why_this_system": response.why_this_system,
                "operational_note": response.operational_note,
                "mission_status": response.mission_status,
                "risk_analysis": response.risk_analysis.model_dump(mode="json"),
            }
        )
        return explanations

    def _summarize_state(
        self,
        state: MissionState | Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        if state is None:
            return None

        serialized = self._serialize_optional(state)
        if not isinstance(serialized, Mapping):
            return None

        return {
            "mission_id": serialized.get("mission_id"),
            "time": serialized.get("time"),
            "resources": serialized.get("resources"),
            "active_system": serialized.get("active_system"),
            "system_metrics": serialized.get("system_metrics"),
        }

    def _history_summary(
        self,
        state: MissionState | Mapping[str, Any] | None,
    ) -> list[dict[str, Any]]:
        if state is None:
            return []

        serialized = self._serialize_optional(state)
        if not isinstance(serialized, Mapping):
            return []

        history = serialized.get("history")
        if not isinstance(history, list):
            return []

        summary: list[dict[str, Any]] = []
        for item in history[-5:]:
            if isinstance(item, Mapping):
                summary.append(
                    {
                        "time": item.get("time"),
                        "event": item.get("event"),
                        "summary": item.get("summary"),
                        "risk_level": item.get("risk_level"),
                    }
                )
        return summary

    def _serialize_optional(self, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, Mapping):
            return {str(key): self._serialize_optional(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._serialize_optional(item) for item in value]
        return value

    def _role_name(self, selected_roles: Mapping[str, Any], role: str) -> str:
        role_payload = selected_roles.get(role, {})
        if isinstance(role_payload, Mapping):
            return str(role_payload.get("name", role))
        return role

    def _grow_system_name(self, selected_roles: Mapping[str, Any]) -> str:
        crop_payload = selected_roles.get("crop", {})
        if isinstance(crop_payload, Mapping):
            support_system = crop_payload.get("support_system")
            if support_system:
                return str(support_system)
        interaction_payload = selected_roles.get("interaction", {})
        if isinstance(interaction_payload, Mapping):
            grow_system = interaction_payload.get("grow_system")
            if grow_system:
                return str(grow_system)
        return "current plant system"

    def _interaction_metric(self, interaction: Mapping[str, Any], key: str) -> float:
        value = interaction.get(key, 0.0) if isinstance(interaction, Mapping) else 0.0
        return float(value) if isinstance(value, (int, float)) else 0.0

    def _domain_risk(self, domain_scores: Mapping[str, Any], domain: str) -> float:
        domain_payload = domain_scores.get(domain, {}) if isinstance(domain_scores, Mapping) else {}
        if isinstance(domain_payload, Mapping):
            risk_score = domain_payload.get("risk_score", 0.0)
            if isinstance(risk_score, (int, float)):
                return float(risk_score)
        return 0.0

    def _event_value(self, events: Mapping[str, Any], key: str) -> Any:
        return events.get(key) if isinstance(events, Mapping) else None

    def _selected_configuration(self, result: IntegratedResult, grow_system_name: str) -> dict[str, Any]:
        return {
            "crop": result.crop.candidate.name,
            "algae": result.algae.candidate.name,
            "microbial": result.microbial.candidate.name,
            "grow_system": grow_system_name,
        }

    def _ensure_second_pass(
        self,
        narrative: GeminiNarrative,
        *,
        source: str,
        selected_configuration: Mapping[str, Any],
        decision: str,
        reason: str,
    ) -> GeminiNarrative:
        analysis = narrative.debug_layer
        if analysis.second_pass:
            updated_debug = analysis.model_copy(
                update={"second_pass_decision": dict(analysis.second_pass)}
            )
            return narrative.model_copy(update={"debug_layer": updated_debug})

        updated_debug = analysis.model_copy(
            update={
                "second_pass": {
                    "decision": decision,
                    "rationale": reason,
                    "source": source,
                    "selected_configuration": dict(selected_configuration),
                }
            }
        )
        updated_debug.second_pass_decision = dict(updated_debug.second_pass)
        return narrative.model_copy(update={"debug_layer": updated_debug})
