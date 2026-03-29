"""Domain-specific microbial evaluation engine."""

from __future__ import annotations

from app.core.normalization import build_metric_ranges, normalize_record
from app.engine.types import DomainEvaluation
from app.models.microbial import MicrobialSystem
from app.models.mission import Environment, Goal, MissionProfile, is_moderate_or_tight_constraint, is_tight_constraint


MICROBIAL_METRICS = (
    "waste_recycling_efficiency",
    "nutrient_conversion_capability",
    "loop_closure_contribution",
    "contamination_risk",
    "reactor_dependency",
    "environmental_sensitivity",
    "maintenance_burden",
)


class MicrobialEngine:
    """Evaluate microbial candidates for recycling and nutrient conversion."""

    def evaluate_all(self, systems: list[MicrobialSystem], mission: MissionProfile) -> list[DomainEvaluation]:
        ranges = build_metric_ranges(systems, MICROBIAL_METRICS)
        evaluations: list[DomainEvaluation] = []

        for system in systems:
            normalized = normalize_record(system, ranges)
            domain_score = self._domain_score(normalized)
            mission_fit = self._mission_fit(system, normalized, mission)
            risk_score = self._risk_score(system, normalized, mission)
            combined = max(0.0, min(1.0, (0.46 * domain_score) + (0.39 * mission_fit) + (0.15 * (1 - risk_score))))

            evaluations.append(
                DomainEvaluation(
                    candidate=system,
                    domain_type="microbial",
                    domain_score=round(domain_score, 3),
                    mission_fit_score=round(mission_fit, 3),
                    risk_score=round(risk_score, 3),
                    combined_score=round(combined, 3),
                    metrics={
                        "waste_recycling_efficiency": round(normalized["waste_recycling_efficiency"], 3),
                        "nutrient_conversion_capability": round(normalized["nutrient_conversion_capability"], 3),
                        "loop_closure_contribution": round(normalized["loop_closure_contribution"], 3),
                        "contamination_risk": round(1 - normalized["contamination_risk"], 3),
                        "reactor_dependency": round(1 - normalized["reactor_dependency"], 3),
                        "environmental_sensitivity": round(1 - normalized["environmental_sensitivity"], 3),
                        "maintenance_burden": round(1 - normalized["maintenance_burden"], 3),
                    },
                    notes=self._notes(system, mission),
                )
            )

        return sorted(evaluations, key=lambda item: item.combined_score, reverse=True)

    def _domain_score(self, normalized: dict[str, float]) -> float:
        return max(
            0.0,
            min(
                1.0,
                (0.26 * normalized["waste_recycling_efficiency"])
                + (0.24 * normalized["nutrient_conversion_capability"])
                + (0.22 * normalized["loop_closure_contribution"])
                + (0.10 * (1 - normalized["contamination_risk"]))
                + (0.10 * (1 - normalized["reactor_dependency"]))
                + (0.08 * (1 - normalized["maintenance_burden"])),
            ),
        )

    def _mission_fit(
        self,
        system: MicrobialSystem,
        normalized: dict[str, float],
        mission: MissionProfile,
    ) -> float:
        environment_fit = system.environment_fit_score(mission.environment, fallback=0.72)

        goal_fit = {
            Goal.BALANCED: (
                normalized["waste_recycling_efficiency"]
                + normalized["nutrient_conversion_capability"]
                + normalized["loop_closure_contribution"]
                + (1 - normalized["maintenance_burden"])
            )
            / 4,
            Goal.CALORIE_MAX: (0.60 * normalized["nutrient_conversion_capability"]) + (0.40 * normalized["loop_closure_contribution"]),
            Goal.WATER_EFFICIENCY: (0.60 * normalized["waste_recycling_efficiency"]) + (0.40 * normalized["loop_closure_contribution"]),
            Goal.LOW_MAINTENANCE: (0.65 * (1 - normalized["maintenance_burden"])) + (0.35 * (1 - normalized["contamination_risk"])),
        }[mission.goal]

        constraint_fit = 0.65
        if is_tight_constraint(mission.constraints.area):
            constraint_fit = 1 - normalized["reactor_dependency"]
        elif is_tight_constraint(mission.constraints.energy):
            constraint_fit = 1 - normalized["maintenance_burden"]
        elif is_moderate_or_tight_constraint(mission.constraints.area):
            constraint_fit = 0.5 + (0.5 * (1 - normalized["reactor_dependency"]))
        elif is_moderate_or_tight_constraint(mission.constraints.energy):
            constraint_fit = 0.5 + (0.5 * (1 - normalized["maintenance_burden"]))

        environment_bias = {
            Environment.MARS: (0.45 * normalized["loop_closure_contribution"]) + (0.35 * normalized["nutrient_conversion_capability"]) + (0.20 * (1 - normalized["contamination_risk"])),
            Environment.MOON: (0.40 * normalized["waste_recycling_efficiency"]) + (0.40 * normalized["loop_closure_contribution"]) + (0.20 * (1 - normalized["reactor_dependency"])),
            Environment.ISS: (0.45 * (1 - normalized["maintenance_burden"])) + (0.30 * (1 - normalized["contamination_risk"])) + (0.25 * normalized["nutrient_conversion_capability"]),
        }[mission.environment]

        return max(
            0.0,
            min(
                1.0,
                (0.30 * environment_fit)
                + (0.30 * goal_fit)
                + (0.15 * constraint_fit)
                + (0.25 * environment_bias),
            ),
        )

    def _risk_score(
        self,
        system: MicrobialSystem,
        normalized: dict[str, float],
        mission: MissionProfile,
    ) -> float:
        mismatch_penalty = 0.18 * (1 - system.environment_fit_score(mission.environment, fallback=0.72))
        return max(
            0.0,
            min(
                1.0,
                (0.40 * normalized["contamination_risk"])
                + (0.25 * normalized["reactor_dependency"])
                + (0.20 * normalized["environmental_sensitivity"])
                + (0.15 * normalized["maintenance_burden"])
                + mismatch_penalty,
            ),
        )

    def _notes(self, system: MicrobialSystem, mission: MissionProfile) -> list[str]:
        notes: list[str] = []
        if system.loop_closure_contribution >= 80:
            notes.append("strengthens loop closure through recycling")
        if system.contamination_risk <= 30:
            notes.append("keeps contamination exposure comparatively low")
        if mission.environment is Environment.MARS and system.nutrient_conversion_capability >= 85:
            notes.append("supports Mars nutrient independence")
        if mission.environment is Environment.ISS and system.maintenance_burden <= 35:
            notes.append("fits lower-touch station operations")
        return notes[:4]
