"""Deterministic explanation helpers for recommendations and simulation updates."""

from __future__ import annotations

from app.core.scoring import ScoredCrop
from app.models.mission import ChangeEvent, ConstraintLevel, Duration, Environment, Goal, MissionProfile
from app.models.response import (
    CropRecommendation,
    MetricBreakdown,
    RecommendationResponse,
    RiskAnalysis,
    RiskDelta,
)
from app.models.system import GrowingSystem


class Explainer:
    """Build human-readable explanations without external LLM calls."""

    def build_metric_breakdown(self, scored_crop: ScoredCrop) -> MetricBreakdown:
        return MetricBreakdown(
            calorie=round(scored_crop.normalized_metrics["calorie_yield"], 3),
            water=round(scored_crop.normalized_metrics["water_need"], 3),
            energy=round(scored_crop.normalized_metrics["energy_need"], 3),
            growth_time=round(scored_crop.normalized_metrics["growth_time"], 3),
            risk=round(scored_crop.normalized_metrics["risk"], 3),
            maintenance=round(scored_crop.normalized_metrics["maintenance"], 3),
        )

    def build_crop_strengths(self, scored_crop: ScoredCrop, mission: MissionProfile) -> list[str]:
        crop = scored_crop.crop
        metric_scores = scored_crop.normalized_metrics
        priority_boosts = self._strength_priority_boosts(mission)
        candidates = [
            ("High calorie density", metric_scores["calorie_yield"]),
            ("Water efficient under constrained operations", 1 - metric_scores["water_need"]),
            ("Lower energy burden", 1 - metric_scores["energy_need"]),
            ("Fast harvest cycle", 1 - metric_scores["growth_time"]),
            ("Operational stability", 1 - metric_scores["risk"]),
            ("Low crew maintenance demand", 1 - metric_scores["maintenance"]),
            ("High nutrient density", crop.nutrient_density / 100),
            ("Useful oxygen contribution", crop.oxygen_contribution / 100),
            ("Strong CO2 utilization", crop.co2_utilization / 100),
            ("Strong recycling synergy", crop.waste_recycling_synergy / 100),
            ("High crew acceptance", crop.crew_acceptance / 100),
        ]
        ordered_candidates = list(candidates)
        ranked = sorted(
            candidates,
            key=lambda item: (
                item[1] + priority_boosts.get(item[0], 0.0),
                item[1],
                -ordered_candidates.index(item),
            ),
            reverse=True,
        )
        return [label for label, _score in ranked[:2]]

    def build_crop_tradeoffs(self, scored_crop: ScoredCrop, mission: MissionProfile) -> list[str]:
        crop = scored_crop.crop
        metric_scores = scored_crop.normalized_metrics
        candidates = [
            ("Lower calorie density than staple crops", 1 - metric_scores["calorie_yield"]),
            ("Higher water demand than compact alternatives", metric_scores["water_need"]),
            ("Higher energy demand than simpler crop options", metric_scores["energy_need"]),
            ("Longer growth cycle delays replenishment", metric_scores["growth_time"]),
            ("Operational fragility is higher than core staples", metric_scores["risk"]),
            ("Needs more crew attention than easier crops", metric_scores["maintenance"]),
            ("Requires more grow area than compact options", crop.area_need / 100),
            ("Crew acceptance is lower than familiar fresh crops", 1 - (crop.crew_acceptance / 100)),
        ]

        if mission.constraints.water is ConstraintLevel.LOW:
            candidates[1] = (candidates[1][0], candidates[1][1] + 0.10)
        if mission.constraints.energy is ConstraintLevel.LOW:
            candidates[2] = (candidates[2][0], candidates[2][1] + 0.10)
        if mission.duration is Duration.SHORT:
            candidates[3] = (candidates[3][0], candidates[3][1] + 0.10)

        tradeoff = max(candidates, key=lambda item: item[1])[0]
        return [tradeoff]

    def build_compatibility_score(
        self,
        scored_crop: ScoredCrop,
        mission: MissionProfile,
        selected_system: GrowingSystem,
    ) -> float:
        crop = scored_crop.crop
        system_fit = 1.0 if selected_system.name in crop.compatible_systems else 0.0
        environment_fit = 1.0 if mission.environment in crop.preferred_environments else 0.65
        closed_loop_fit = (
            crop.nutrient_density
            + crop.oxygen_contribution
            + crop.co2_utilization
            + crop.waste_recycling_synergy
            + crop.crew_acceptance
        ) / 500
        stability_fit = 1 - scored_crop.normalized_metrics["risk"]
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

    def build_crop_reason(
        self,
        scored_crop: ScoredCrop,
        mission: MissionProfile,
        selected_system: GrowingSystem,
        strengths: list[str],
    ) -> str:
        primary_strength = strengths[0]
        environment_label = self.format_environment(mission.environment)

        templates = {
            "High calorie density": f"High calorie density supports {mission.duration.value}-duration food continuity.",
            "Water efficient under constrained operations": "Water-efficient behavior fits tight resource conditions.",
            "Lower energy burden": "Lower energy demand helps preserve life-support power margin.",
            "Fast harvest cycle": "Fast harvest cycles improve replenishment speed during mission shifts.",
            "Operational stability": "Operational stability supports more reliable food production.",
            "Low crew maintenance demand": "Low crew maintenance demand suits limited operational attention.",
            "High nutrient density": "High nutrient density improves food quality per growth cycle.",
            "Useful oxygen contribution": "Useful oxygen contribution strengthens closed-loop life-support value.",
            "Strong CO2 utilization": "Strong CO2 utilization supports closed-loop atmospheric recovery.",
            "Strong recycling synergy": "Recycling synergy improves closed-loop efficiency under constrained operations.",
            "High crew acceptance": "High crew acceptance helps sustain adoption over longer missions.",
        }

        reason = templates.get(primary_strength, "The crop matches the active mission priorities.")

        if mission.environment in scored_crop.crop.preferred_environments:
            return reason[:-1] + f" and it aligns well with {environment_label} mission conditions."

        if mission.constraints.water is ConstraintLevel.LOW and selected_system.name == "aeroponic":
            return reason[:-1] + " while pairing well with the selected water-efficient system."

        return reason

    def build_system_reason(self, mission: MissionProfile, selected_system: GrowingSystem) -> str:
        environment_label = self.format_environment(mission.environment)
        driver = self._dominant_driver(mission)
        system_templates = {
            "aeroponic": "Aeroponic systems favor water efficiency and compact production when scarcity is the main pressure.",
            "hydroponic": "Hydroponic systems favor operational simplicity and steadier crew handling.",
            "hybrid": "Hybrid systems balance resilience, efficiency, and adaptability across mixed constraints.",
        }
        environment_templates = {
            Environment.MARS: "Mars missions reward calorie continuity and resilient operating margins.",
            Environment.MOON: "Moon missions amplify water recovery value and recycling resilience.",
            Environment.ISS: "ISS missions favor lower-maintenance, crew-friendly agricultural operations.",
        }
        base_reason = system_templates[selected_system.name]
        env_reason = environment_templates[mission.environment]
        return f"{base_reason} In this {environment_label} mission, the dominant driver is {driver}, so {selected_system.name} is the best fit. {env_reason}"

    def build_overall_explanation(
        self,
        mission: MissionProfile,
        selected_system: GrowingSystem,
        top_crop: ScoredCrop,
        crop_recommendation: CropRecommendation,
        risk_analysis: RiskAnalysis,
        system_reason: str,
    ) -> str:
        environment_label = self.format_environment(mission.environment)
        driver = self._dominant_driver(mission)
        duration_clause = f"{mission.duration.value}-duration " if mission.duration in {Duration.LONG, Duration.SHORT} else ""
        risk_clause = (
            "Overall agriculture risk remains low."
            if risk_analysis.level.value == "low"
            else f"Risk is {risk_analysis.level.value} because of {risk_analysis.factors[0]}."
        )
        return (
            f"Given the {duration_clause}{environment_label} mission and {driver}, the engine ranked "
            f"{top_crop.crop.name} first because {crop_recommendation.reason[0].lower()}{crop_recommendation.reason[1:]} "
            f"The chosen {selected_system.name} system fits because {system_reason[0].lower()}{system_reason[1:]} "
            f"{risk_clause}"
        )

    def build_simulation_reason(
        self,
        change_event: ChangeEvent,
        previous_recommendation: RecommendationResponse,
        updated_recommendation: RecommendationResponse,
        risk_delta: RiskDelta,
        system_changed: bool,
        affected_crop: str | None,
        penalty_applied: bool,
    ) -> str:
        previous_top = previous_recommendation.top_crops[0].name
        new_top = updated_recommendation.top_crops[0].name
        event_reason = {
            ChangeEvent.WATER_DROP: "Water availability decreased, so the engine shifted toward more water-efficient crops and systems.",
            ChangeEvent.ENERGY_DROP: "Energy availability decreased, so the engine shifted toward lower-energy crop and system choices.",
            ChangeEvent.YIELD_DROP: "A simulated yield disruption triggered a re-ranking of the crop portfolio.",
        }[change_event]

        parts = [event_reason]

        if change_event is ChangeEvent.YIELD_DROP and affected_crop:
            if penalty_applied:
                parts.append(f"{affected_crop} received a direct temporary yield penalty.")
            else:
                parts.append(f"{affected_crop} was not found in the active crop pool, so the engine applied a generic resilience re-ranking.")

        if previous_top != new_top:
            parts.append(f"The lead crop changed from {previous_top} to {new_top}.")
        else:
            parts.append(f"{new_top} remained the lead crop because it still best matched the updated mission profile.")

        if system_changed:
            parts.append(
                f"The primary system changed from {previous_recommendation.recommended_system} to "
                f"{updated_recommendation.recommended_system}."
            )
        else:
            parts.append(f"The primary system stayed at {updated_recommendation.recommended_system}.")

        if risk_delta is RiskDelta.INCREASED:
            parts.append("Overall mission-agriculture risk increased.")
        elif risk_delta is RiskDelta.DECREASED:
            parts.append("Overall mission-agriculture risk decreased.")
        else:
            parts.append("Overall mission-agriculture risk stayed stable.")

        return " ".join(parts)

    def format_environment(self, environment: Environment) -> str:
        if environment is Environment.ISS:
            return "ISS"
        return environment.value.title()

    def _strength_priority_boosts(self, mission: MissionProfile) -> dict[str, float]:
        boosts: dict[str, float] = {}

        if mission.goal is Goal.CALORIE_MAX or mission.environment is Environment.MARS:
            boosts["High calorie density"] = 0.12
            boosts["Operational stability"] = 0.08

        if mission.goal is Goal.WATER_EFFICIENCY or mission.environment is Environment.MOON:
            boosts["Water efficient under constrained operations"] = 0.12
            boosts["Strong recycling synergy"] = 0.07

        if mission.goal is Goal.LOW_MAINTENANCE or mission.environment is Environment.ISS:
            boosts["Low crew maintenance demand"] = 0.12
            boosts["Operational stability"] = max(boosts.get("Operational stability", 0.0), 0.08)
            boosts["High crew acceptance"] = 0.05

        if mission.duration is Duration.LONG:
            boosts["High calorie density"] = max(boosts.get("High calorie density", 0.0), 0.08)

        if mission.constraints.water is ConstraintLevel.LOW:
            boosts["Water efficient under constrained operations"] = max(
                boosts.get("Water efficient under constrained operations", 0.0),
                0.10,
            )

        return boosts

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
        if mission.environment is Environment.MARS:
            return "calorie continuity and robustness"
        if mission.environment is Environment.MOON:
            return "water recovery resilience"
        if mission.environment is Environment.ISS:
            return "crew-friendly operational stability"
        return "balanced trade-offs"
