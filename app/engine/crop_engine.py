"""Domain-specific crop evaluation engine."""

from __future__ import annotations

from collections.abc import Mapping

from app.core.filters import filter_compatible_crops
from app.core.normalization import build_metric_ranges, normalize_record
from app.models.crop import Crop
from app.models.mission import ConstraintLevel, Environment, Goal, MissionProfile
from app.models.system import GrowingSystem
from app.engine.types import DomainEvaluation


CROP_METRICS = (
    "calorie_yield",
    "nutrient_density",
    "growth_time",
    "water_need",
    "area_need",
    "crew_acceptance",
    "maintenance",
    "risk",
    "energy_need",
    "closed_loop_score",
)

ALGAE_LIKE_NAMES = {"spirulina", "spirulina_loop", "chlorella", "chlorella_panel", "scenedesmus", "scenedesmus_reserve"}


class CropEngine:
    """Evaluate plant candidates for edible production and mission fit."""

    def evaluate_all(
        self,
        crops: list[Crop],
        mission: MissionProfile,
        grow_system: GrowingSystem,
        temporary_penalties: Mapping[str, float] | None = None,
        mission_fit_bias: float = 0.0,
    ) -> list[DomainEvaluation]:
        eligible = [
            crop
            for crop in filter_compatible_crops(crops, grow_system)
            if crop.name.lower() not in ALGAE_LIKE_NAMES
        ]
        ranges = build_metric_ranges(eligible, CROP_METRICS)
        evaluations: list[DomainEvaluation] = []

        for crop in eligible:
            normalized = normalize_record(crop, ranges)
            domain_score = self._domain_score(normalized)
            mission_fit = self._mission_fit(crop, normalized, mission, grow_system) + mission_fit_bias
            risk_score = self._risk_score(crop, normalized, mission, grow_system)
            combined = max(0.0, min(1.0, (0.46 * domain_score) + (0.42 * mission_fit) + (0.12 * (1 - risk_score))))
            notes = self._notes(crop, mission, grow_system)

            if temporary_penalties and crop.name.lower() in temporary_penalties:
                penalty = temporary_penalties[crop.name.lower()]
                combined = max(0.0, combined - penalty)
                risk_score = min(1.0, risk_score + (penalty * 0.5))
                notes.append("temporary yield penalty applied to protect mission continuity")

            evaluations.append(
                DomainEvaluation(
                    candidate=crop,
                    domain_type="crop",
                    domain_score=round(domain_score, 3),
                    mission_fit_score=round(max(0.0, min(1.0, mission_fit)), 3),
                    risk_score=round(risk_score, 3),
                    combined_score=round(combined, 3),
                    metrics={
                        "edible_yield": round(normalized["calorie_yield"], 3),
                        "calorie_density": round(normalized["calorie_yield"], 3),
                        "nutrient_density": round(normalized["nutrient_density"], 3),
                        "growth_time": round(1 - normalized["growth_time"], 3),
                        "water_efficiency": round(1 - normalized["water_need"], 3),
                        "area_efficiency": round(1 - normalized["area_need"], 3),
                        "crew_acceptance": round(normalized["crew_acceptance"], 3),
                        "maintenance_cost": round(1 - normalized["maintenance"], 3),
                        "closed_loop_contribution": round(normalized["closed_loop_score"], 3),
                    },
                    notes=notes,
                    support_system=grow_system.name,
                )
            )

        return sorted(evaluations, key=lambda item: item.combined_score, reverse=True)

    def _domain_score(self, normalized: dict[str, float]) -> float:
        return max(
            0.0,
            min(
                1.0,
                (0.24 * normalized["calorie_yield"])
                + (0.18 * normalized["nutrient_density"])
                + (0.14 * (1 - normalized["growth_time"]))
                + (0.14 * (1 - normalized["water_need"]))
                + (0.12 * (1 - normalized["area_need"]))
                + (0.10 * normalized["crew_acceptance"])
                + (0.08 * (1 - normalized["maintenance"])),
            ),
        )

    def _mission_fit(
        self,
        crop: Crop,
        normalized: dict[str, float],
        mission: MissionProfile,
        grow_system: GrowingSystem,
    ) -> float:
        environment_fit = crop.environment_fit_score(mission.environment, fallback=0.72)
        system_fit = crop.system_fit_score(grow_system.name, fallback=0.72)

        goal_fit = {
            Goal.BALANCED: (
                normalized["calorie_yield"]
                + (1 - normalized["water_need"])
                + (1 - normalized["maintenance"])
                + normalized["closed_loop_score"]
            )
            / 4,
            Goal.CALORIE_MAX: (0.65 * normalized["calorie_yield"]) + (0.35 * normalized["closed_loop_score"]),
            Goal.WATER_EFFICIENCY: (0.70 * (1 - normalized["water_need"])) + (0.30 * normalized["closed_loop_score"]),
            Goal.LOW_MAINTENANCE: (0.60 * (1 - normalized["maintenance"])) + (0.40 * normalized["crew_acceptance"]),
        }[mission.goal]

        constraint_fit = 0.0
        if mission.constraints.water is ConstraintLevel.LOW:
            constraint_fit += 1 - normalized["water_need"]
        if mission.constraints.energy is ConstraintLevel.LOW:
            constraint_fit += 1 - normalized["energy_need"]
        if mission.constraints.area is ConstraintLevel.LOW:
            constraint_fit += 1 - normalized["area_need"]
        if constraint_fit == 0.0:
            constraint_fit = 0.65
        else:
            constraint_fit /= 3

        environment_bias = {
            Environment.MARS: (0.45 * normalized["calorie_yield"]) + (0.35 * normalized["closed_loop_score"]) + (0.20 * (1 - normalized["risk"])),
            Environment.MOON: (0.45 * (1 - normalized["water_need"])) + (0.35 * normalized["closed_loop_score"]) + (0.20 * (1 - normalized["area_need"])),
            Environment.ISS: (0.40 * (1 - normalized["maintenance"])) + (0.30 * normalized["crew_acceptance"]) + (0.30 * (1 - normalized["risk"])),
        }[mission.environment]

        return max(
            0.0,
            min(
                1.0,
                (0.30 * environment_fit)
                + (0.20 * system_fit)
                + (0.25 * goal_fit)
                + (0.10 * constraint_fit)
                + (0.15 * environment_bias),
            ),
        )

    def _risk_score(
        self,
        crop: Crop,
        normalized: dict[str, float],
        mission: MissionProfile,
        grow_system: GrowingSystem,
    ) -> float:
        mismatch_penalty = 0.18 * (1 - crop.environment_fit_score(mission.environment, fallback=0.72))
        system_penalty = 0.20 * (1 - crop.system_fit_score(grow_system.name, fallback=0.72))
        return max(
            0.0,
            min(
                1.0,
                (0.35 * normalized["risk"])
                + (0.20 * normalized["maintenance"])
                + (0.20 * normalized["growth_time"])
                + (0.10 * normalized["energy_need"])
                + mismatch_penalty
                + system_penalty,
            ),
        )

    def _notes(self, crop: Crop, mission: MissionProfile, grow_system: GrowingSystem) -> list[str]:
        notes: list[str] = []
        if crop.prefers_environment(mission.environment):
            notes.append("aligned with the mission environment")
        if crop.closed_loop_score >= 0.72:
            notes.append("supports closed-loop nutrient and gas recovery")
        if crop.crew_acceptance >= 80:
            notes.append("strong crew acceptance for repeated use")
        if mission.environment is Environment.MARS and crop.calorie_yield >= 75:
            notes.append("supports Mars calorie continuity")
        if mission.environment is Environment.MOON and crop.water_need <= 40:
            notes.append("fits Moon water-pressure conditions")
        if mission.environment is Environment.ISS and crop.maintenance <= 35:
            notes.append("keeps ISS crew maintenance lighter")
        if grow_system.name == "hybrid":
            notes.append("benefits from hybrid redundancy")
        return notes[:4]
