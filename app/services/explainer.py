"""Deterministic explanation helpers for recommendations and simulation updates."""

from __future__ import annotations

from app.core.scoring import ScoredCrop
from app.models.mission import ChangeEvent, ConstraintLevel, Duration, Goal, MissionProfile
from app.models.response import RecommendationResponse, RiskAnalysis
from app.models.system import GrowingSystem


class Explainer:
    """Build human-readable explanations without external LLM calls."""

    def build_crop_reason(
        self,
        scored_crop: ScoredCrop,
        mission: MissionProfile,
        selected_system: GrowingSystem,
    ) -> str:
        strengths = {
            "calorie output": scored_crop.normalized_metrics["calorie_yield"],
            "water efficiency": 1 - scored_crop.normalized_metrics["water_need"],
            "energy efficiency": 1 - scored_crop.normalized_metrics["energy_need"],
            "fast growth": 1 - scored_crop.normalized_metrics["growth_time"],
            "operational stability": 1 - scored_crop.normalized_metrics["risk"],
            "low maintenance": 1 - scored_crop.normalized_metrics["maintenance"],
        }
        priority_order = self._priority_order(mission)
        strength_key = next(
            (
                key
                for key in priority_order
                if strengths[key] >= 0.55
            ),
            max(strengths, key=strengths.get),
        )

        templates = {
            "calorie output": f"High calorie output makes it a strong anchor crop for {mission.duration.value}-duration missions.",
            "water efficiency": "Strong water efficiency supports tight water budgets.",
            "energy efficiency": "Lower energy demand helps preserve power for life-support operations.",
            "fast growth": "Fast growth improves replenishment speed during changing mission conditions.",
            "operational stability": "Lower operational risk improves continuous food production reliability.",
            "low maintenance": "Low maintenance demand fits crew-limited mission operations.",
        }

        reason = templates[strength_key]

        if "environment-fit" in scored_crop.rule_notes:
            return (
                reason[:-1]
                + f" and it aligns well with {mission.environment.value.title()} mission conditions."
            )

        if mission.constraints.water is ConstraintLevel.LOW and selected_system.name == "aeroponic":
            return reason[:-1] + " while pairing well with the selected water-efficient system."

        return reason

    def build_overall_explanation(
        self,
        mission: MissionProfile,
        selected_system: GrowingSystem,
        top_crop: ScoredCrop,
        crop_reason: str,
        risk_analysis: RiskAnalysis,
    ) -> str:
        dominant_driver = self._dominant_driver(mission)
        system_note = selected_system.environment_notes.get(
            mission.environment.value,
            selected_system.notes,
        )

        if risk_analysis.level.value == "low":
            risk_clause = "Overall mission-agriculture risk remains low."
        else:
            risk_clause = (
                f"Risk is {risk_analysis.level.value} because of "
                f"{risk_analysis.factors[0]}."
            )

        return (
            f"For a {mission.duration.value}-duration {mission.environment.value.title()} mission shaped by "
            f"{dominant_driver}, the engine selected {selected_system.name} as the primary growing method and "
            f"ranked {top_crop.crop.name} first. {crop_reason} {system_note} {risk_clause}"
        )

    def build_adaptation_reason(
        self,
        change_event: ChangeEvent,
        updated_recommendation: RecommendationResponse,
        previous_recommendation: RecommendationResponse | None = None,
        affected_crop: str | None = None,
    ) -> str:
        event_reason = {
            ChangeEvent.WATER_DROP: "Water availability was downgraded one level, so the engine increased water penalties.",
            ChangeEvent.ENERGY_DROP: "Energy availability was downgraded one level, so the engine increased energy penalties.",
            ChangeEvent.YIELD_DROP: "The engine re-evaluated crop performance under a simulated yield disruption.",
        }[change_event]

        lead_crop = updated_recommendation.top_crops[0].name
        parts = [event_reason]

        if affected_crop:
            parts.append(f"{affected_crop} received a temporary performance penalty during the simulation.")

        if previous_recommendation and previous_recommendation.top_crops:
            previous_lead = previous_recommendation.top_crops[0].name
            if previous_lead != lead_crop:
                parts.append(f"The lead recommendation shifted from {previous_lead} to {lead_crop}.")
            else:
                parts.append(f"{lead_crop} remained the lead crop after re-ranking.")
        else:
            parts.append(f"{lead_crop} is now the lead crop under the updated mission profile.")

        return " ".join(parts)

    def _priority_order(self, mission: MissionProfile) -> list[str]:
        order: list[str] = []

        if mission.constraints.water is ConstraintLevel.LOW or mission.goal is Goal.WATER_EFFICIENCY:
            order.append("water efficiency")

        if mission.constraints.energy is ConstraintLevel.LOW:
            order.append("energy efficiency")

        if mission.duration is Duration.SHORT:
            order.append("fast growth")
        elif mission.duration is Duration.LONG or mission.goal is Goal.CALORIE_MAX:
            order.append("calorie output")

        if mission.goal is Goal.LOW_MAINTENANCE:
            order.append("low maintenance")

        order.extend(
            [
                "operational stability",
                "calorie output",
                "water efficiency",
                "fast growth",
                "low maintenance",
                "energy efficiency",
            ]
        )

        return list(dict.fromkeys(order))

    def _dominant_driver(self, mission: MissionProfile) -> str:
        if mission.constraints.water is ConstraintLevel.LOW:
            return "water scarcity"
        if mission.constraints.energy is ConstraintLevel.LOW:
            return "energy pressure"
        if mission.constraints.area is ConstraintLevel.LOW:
            return "tight area limits"
        if mission.goal is Goal.CALORIE_MAX:
            return "calorie maximization"
        if mission.goal is Goal.WATER_EFFICIENCY:
            return "water efficiency"
        if mission.goal is Goal.LOW_MAINTENANCE:
            return "low-maintenance operations"
        return "balanced trade-offs"

