"""Deterministic explanation helpers for recommendations and simulation updates."""

from __future__ import annotations

from app.core.scoring import ScoredCrop
from app.models.mission import ChangeEvent, ConstraintLevel, Duration, Environment, Goal, MissionProfile
from app.models.response import (
    CropRecommendation,
    MetricBreakdown,
    MissionStatus,
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

    def build_system_reasoning(self, mission: MissionProfile, selected_system: GrowingSystem) -> str:
        environment_label = self.format_environment(mission.environment)
        driver = self._dominant_driver(mission)
        system_templates = {
            "aeroponic": "Aeroponic systems favor aggressive water savings and compact production when scarcity dominates the mission.",
            "hydroponic": "Hydroponic systems favor operational simplicity, predictable upkeep, and steadier crew handling.",
            "hybrid": "Hybrid systems balance resilience, efficiency, and operational flexibility across mixed constraints.",
        }
        base_reason = system_templates[selected_system.name]
        environment_note = selected_system.environment_notes.get(mission.environment.value, selected_system.notes)
        return (
            f"{base_reason} The dominant driver on this {environment_label} mission is {driver}. {environment_note}"
        )

    def build_system_reason(self, mission: MissionProfile, selected_system: GrowingSystem) -> str:
        return self.build_system_reasoning(mission, selected_system)

    def build_why_this_system(self, mission: MissionProfile, selected_system: GrowingSystem) -> str:
        environment_label = self.format_environment(mission.environment)
        driver = self._dominant_driver(mission)
        system_label = self._format_system(selected_system.name)
        fit_fragments = {
            "aeroponic": "it preserves water aggressively when recovery margin matters most",
            "hydroponic": "it keeps upkeep predictable for crew-facing operations",
            "hybrid": "it balances resilience and efficiency without overcommitting to one tradeoff",
        }
        return (
            f"{system_label} is the best fit because {driver} dominates this {environment_label} mission, and "
            f"{fit_fragments[selected_system.name]}."
        )

    def build_tradeoff_summary(
        self,
        selected_system: GrowingSystem,
        top_crop_recommendation: CropRecommendation,
    ) -> str:
        system_drawbacks = {
            "hydroponic": "it gives up peak water efficiency to keep operations simpler and more stable",
            "aeroponic": "it raises maintenance and power demand to maximize water savings",
            "hybrid": "it accepts moderate resource overhead to preserve resilience and adaptability",
        }
        crop_tradeoff = (
            top_crop_recommendation.tradeoffs[0]
            if top_crop_recommendation.tradeoffs
            else "the lead crop still needs routine monitoring"
        )
        system_label = self._format_system(selected_system.name)
        return (
            f"{system_label} was selected even though {system_drawbacks[selected_system.name]}; "
            f"the lead crop tradeoff is that {self._lowercase_first(crop_tradeoff)}."
        )

    def build_operational_note(
        self,
        risk_analysis: RiskAnalysis,
        selected_system: GrowingSystem,
    ) -> str:
        primary_factor = risk_analysis.factors[0]
        if primary_factor == "no major mission stressors detected":
            return (
                f"Maintain the {selected_system.name} baseline and continue routine monitoring of water, "
                "energy, and crew workload margins."
            )
        if "water" in primary_factor.lower():
            return "Protect water reserves, verify recycler performance, and watch irrigation stability closely."
        if "energy" in primary_factor.lower():
            return "Preserve power margin and defer nonessential grow-module energy loads until conditions stabilize."
        if "maintenance" in primary_factor.lower() or "crew" in primary_factor.lower():
            return "Reduce crew handling churn and schedule maintenance checks before workload compounds."
        if "area" in primary_factor.lower():
            return "Protect compact grow capacity and prioritize high-return crops until area pressure relaxes."
        if "calorie" in primary_factor.lower():
            return "Protect staple-crop continuity and consider shifting reserve area toward higher calorie output."
        if "robustness" in primary_factor.lower():
            return "Keep contingency margin available and avoid pushing the system into higher-complexity operating modes."
        return "Maintain current operating margins and continue watching the lead crop and system health indicators."

    def build_mission_status(
        self,
        mission: MissionProfile,
        risk_analysis: RiskAnalysis,
        selected_system: GrowingSystem,
        lead_crop_compatibility_score: float,
        penalty_on_previous_lead_crop: bool = False,
    ) -> MissionStatus:
        score = {
            "low": 0,
            "moderate": 1,
            "high": 2,
        }[risk_analysis.level.value]

        low_constraints = sum(
            1
            for constraint in (
                mission.constraints.water,
                mission.constraints.energy,
                mission.constraints.area,
            )
            if constraint is ConstraintLevel.LOW
        )
        if low_constraints >= 2:
            score += 1

        if self._has_system_pairing_penalty(mission, selected_system):
            score += 1

        if lead_crop_compatibility_score < 0.60:
            score += 1

        if penalty_on_previous_lead_crop:
            score += 1

        if score >= 4:
            return MissionStatus.CRITICAL
        if score >= 2:
            return MissionStatus.WATCH
        return MissionStatus.NOMINAL

    def build_executive_summary(
        self,
        mission: MissionProfile,
        top_crop_recommendation: CropRecommendation,
        selected_system: GrowingSystem,
        mission_status: MissionStatus,
        risk_analysis: RiskAnalysis,
    ) -> str:
        environment_label = self.format_environment(mission.environment)
        lead_crop = top_crop_recommendation.name.title()
        system_label = self._format_system(selected_system.name)
        primary_strength = (
            top_crop_recommendation.strengths[0].lower()
            if top_crop_recommendation.strengths
            else "balanced mission fit"
        )
        driver = self._dominant_driver(mission)
        return (
            f"{environment_label} mission status is {mission_status.value}: {lead_crop} leads the crop portfolio with "
            f"{system_label} as the primary system. The plan prioritizes {driver}, with {lead_crop.lower()} providing "
            f"{primary_strength} while agriculture risk remains {risk_analysis.level.value}."
        )

    def build_explanation(self, executive_summary: str, operational_note: str) -> str:
        return f"{executive_summary} {operational_note}"

    def build_simulation_reason(
        self,
        change_event: ChangeEvent,
        previous_recommendation: RecommendationResponse,
        updated_recommendation: RecommendationResponse,
        risk_delta: RiskDelta,
        system_changed: bool,
        affected_crop: str | None,
        penalty_applied: bool,
        risk_score_delta: float,
    ) -> str:
        previous_top = previous_recommendation.top_crops[0].name
        new_top = updated_recommendation.top_crops[0].name
        event_reason = {
            ChangeEvent.WATER_DROP: (
                "Water availability decreased, so the engine reweighted the mission toward water efficiency and "
                "closed-loop recovery."
            ),
            ChangeEvent.ENERGY_DROP: (
                "Energy availability decreased, so the engine shifted toward lower-energy crops and simpler system load."
            ),
            ChangeEvent.YIELD_DROP: "A simulated yield disruption triggered a deterministic re-ranking of the crop portfolio.",
        }[change_event]

        parts = [event_reason]

        if change_event is ChangeEvent.YIELD_DROP and affected_crop:
            if penalty_applied:
                parts.append(f"{affected_crop.title()} received a direct temporary yield penalty.")
            else:
                parts.append(
                    f"{affected_crop.title()} was not found in the active crop pool, so the engine applied a generic resilience re-ranking."
                )

        if previous_top != new_top:
            parts.append(f"The lead crop changed from {previous_top.title()} to {new_top.title()}.")
        else:
            parts.append(
                f"{new_top.title()} remained the lead crop because it still best matched the updated mission profile."
            )

        if system_changed:
            parts.append(
                f"The primary system changed from {self._format_system(previous_recommendation.recommended_system)} "
                f"to {self._format_system(updated_recommendation.recommended_system)}."
            )
        else:
            parts.append(
                f"The primary system stayed at {self._format_system(updated_recommendation.recommended_system)}."
            )

        parts.append(
            f"Risk score moved by {risk_score_delta:+.3f} and is now "
            f"{updated_recommendation.risk_analysis.score:.3f} ({risk_delta.value})."
        )

        if previous_recommendation.mission_status != updated_recommendation.mission_status:
            parts.append(
                f"Mission status shifted from {previous_recommendation.mission_status.value} to "
                f"{updated_recommendation.mission_status.value}."
            )
        else:
            parts.append(
                f"Mission status remains {updated_recommendation.mission_status.value}."
            )

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
            boosts["Strong recycling synergy"] = max(boosts.get("Strong recycling synergy", 0.0), 0.04)

        if mission.goal is Goal.WATER_EFFICIENCY or mission.environment is Environment.MOON:
            boosts["Water efficient under constrained operations"] = 0.12
            boosts["Strong recycling synergy"] = 0.08
            boosts["Strong CO2 utilization"] = max(boosts.get("Strong CO2 utilization", 0.0), 0.04)

        if mission.goal is Goal.LOW_MAINTENANCE or mission.environment is Environment.ISS:
            boosts["Low crew maintenance demand"] = 0.12
            boosts["Operational stability"] = max(boosts.get("Operational stability", 0.0), 0.08)
            boosts["High crew acceptance"] = 0.08

        if mission.duration is Duration.LONG:
            boosts["High calorie density"] = max(boosts.get("High calorie density", 0.0), 0.08)
            boosts["Useful oxygen contribution"] = max(boosts.get("Useful oxygen contribution", 0.0), 0.04)

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
            return "calorie continuity"
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

    def _has_system_pairing_penalty(
        self,
        mission: MissionProfile,
        selected_system: GrowingSystem,
    ) -> bool:
        if mission.environment in {Environment.MARS, Environment.MOON}:
            return selected_system.complexity >= 65 or selected_system.maintenance >= 60
        if mission.environment is Environment.ISS:
            return selected_system.maintenance >= 45 or selected_system.complexity >= 50
        return False

    def _lowercase_first(self, text: str) -> str:
        if not text:
            return text
        return text[0].lower() + text[1:]

    def _format_system(self, system_name: str) -> str:
        return system_name.replace("_", " ").title()
