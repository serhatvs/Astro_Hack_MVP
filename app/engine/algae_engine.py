"""Domain-specific algae evaluation engine."""

from __future__ import annotations

from app.core.normalization import build_metric_ranges, normalize_record
from app.engine.types import DomainEvaluation
from app.models.algae import AlgaeSystem
from app.models.mission import Environment, Goal, MissionProfile, is_moderate_or_tight_constraint, is_tight_constraint


ALGAE_METRICS = (
    "oxygen_contribution",
    "co2_utilization",
    "biomass_production",
    "protein_potential",
    "photobioreactor_compatibility",
    "water_system_compatibility",
    "energy_light_dependency",
    "maintenance_complexity",
)


class AlgaeEngine:
    """Evaluate algae candidates for atmospheric and biomass support."""

    def evaluate_all(self, algae_systems: list[AlgaeSystem], mission: MissionProfile) -> list[DomainEvaluation]:
        ranges = build_metric_ranges(algae_systems, ALGAE_METRICS)
        evaluations: list[DomainEvaluation] = []

        for system in algae_systems:
            normalized = normalize_record(system, ranges)
            domain_score = self._domain_score(normalized)
            mission_fit = self._mission_fit(system, normalized, mission)
            risk_score = self._risk_score(system, normalized, mission)
            combined = max(0.0, min(1.0, (0.45 * domain_score) + (0.40 * mission_fit) + (0.15 * (1 - risk_score))))

            evaluations.append(
                DomainEvaluation(
                    candidate=system,
                    domain_type="algae",
                    domain_score=round(domain_score, 3),
                    mission_fit_score=round(mission_fit, 3),
                    risk_score=round(risk_score, 3),
                    combined_score=round(combined, 3),
                    metrics={
                        "oxygen_contribution": round(normalized["oxygen_contribution"], 3),
                        "co2_utilization": round(normalized["co2_utilization"], 3),
                        "biomass_production": round(normalized["biomass_production"], 3),
                        "protein_potential": round(normalized["protein_potential"], 3),
                        "photobioreactor_compatibility": round(normalized["photobioreactor_compatibility"], 3),
                        "water_system_compatibility": round(normalized["water_system_compatibility"], 3),
                        "energy_light_dependency": round(1 - normalized["energy_light_dependency"], 3),
                        "maintenance_complexity": round(1 - normalized["maintenance_complexity"], 3),
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
                (0.20 * normalized["oxygen_contribution"])
                + (0.18 * normalized["co2_utilization"])
                + (0.16 * normalized["biomass_production"])
                + (0.14 * normalized["protein_potential"])
                + (0.14 * normalized["photobioreactor_compatibility"])
                + (0.10 * normalized["water_system_compatibility"])
                + (0.04 * (1 - normalized["energy_light_dependency"]))
                + (0.04 * (1 - normalized["maintenance_complexity"])),
            ),
        )

    def _mission_fit(
        self,
        system: AlgaeSystem,
        normalized: dict[str, float],
        mission: MissionProfile,
    ) -> float:
        environment_fit = system.environment_fit_score(mission.environment, fallback=0.72)

        goal_fit = {
            Goal.BALANCED: (
                normalized["oxygen_contribution"]
                + normalized["protein_potential"]
                + normalized["water_system_compatibility"]
                + (1 - normalized["maintenance_complexity"])
            )
            / 4,
            Goal.CALORIE_MAX: (0.55 * normalized["biomass_production"]) + (0.45 * normalized["protein_potential"]),
            Goal.WATER_EFFICIENCY: (0.65 * normalized["water_system_compatibility"]) + (0.35 * normalized["co2_utilization"]),
            Goal.LOW_MAINTENANCE: (0.65 * (1 - normalized["maintenance_complexity"])) + (0.35 * normalized["photobioreactor_compatibility"]),
        }[mission.goal]

        constraint_fit = 0.65
        if is_tight_constraint(mission.constraints.energy):
            constraint_fit = 1 - normalized["energy_light_dependency"]
        elif is_tight_constraint(mission.constraints.water):
            constraint_fit = normalized["water_system_compatibility"]
        elif is_moderate_or_tight_constraint(mission.constraints.energy):
            constraint_fit = 0.5 + (0.5 * (1 - normalized["energy_light_dependency"]))
        elif is_moderate_or_tight_constraint(mission.constraints.water):
            constraint_fit = 0.5 + (0.5 * normalized["water_system_compatibility"])

        environment_bias = {
            Environment.MARS: (0.35 * normalized["oxygen_contribution"]) + (0.35 * normalized["protein_potential"]) + (0.30 * normalized["co2_utilization"]),
            Environment.MOON: (0.45 * normalized["water_system_compatibility"]) + (0.35 * normalized["co2_utilization"]) + (0.20 * normalized["photobioreactor_compatibility"]),
            Environment.ISS: (0.40 * (1 - normalized["maintenance_complexity"])) + (0.30 * normalized["oxygen_contribution"]) + (0.30 * (1 - normalized["energy_light_dependency"])),
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
        system: AlgaeSystem,
        normalized: dict[str, float],
        mission: MissionProfile,
    ) -> float:
        mismatch_penalty = 0.16 * (1 - system.environment_fit_score(mission.environment, fallback=0.72))
        return max(
            0.0,
            min(
                1.0,
                (0.38 * normalized["energy_light_dependency"])
                + (0.32 * normalized["maintenance_complexity"])
                + mismatch_penalty,
            ),
        )

    def _notes(self, system: AlgaeSystem, mission: MissionProfile) -> list[str]:
        notes: list[str] = []
        if system.oxygen_contribution >= 80:
            notes.append("creates a meaningful oxygen buffer")
        if system.protein_potential >= 80:
            notes.append("adds non-crop protein resilience")
        if mission.environment is Environment.MOON and system.water_system_compatibility >= 80:
            notes.append("supports Moon water-loop coupling")
        if mission.environment is Environment.ISS and system.maintenance_complexity <= 50:
            notes.append("keeps algae upkeep manageable for station crews")
        return notes[:4]
