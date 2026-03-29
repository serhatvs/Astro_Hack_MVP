"""Scoring functions for growing systems and crops."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.filters import compute_rule_adjustment, filter_compatible_crops
from app.core.normalization import build_metric_ranges, normalize_record, normalize_scores
from app.core.weights import derive_crop_weights, derive_system_weights
from app.models.crop import Crop
from app.models.mission import Environment, Goal, MissionProfile, is_tight_constraint
from app.models.system import GrowingSystem


SYSTEM_METRICS = ("water_efficiency", "energy_cost", "complexity", "maintenance")
CROP_METRICS = (
    "calorie_yield",
    "water_need",
    "energy_need",
    "growth_time",
    "risk",
    "maintenance",
    "closed_loop_score",
    "crew_support_score",
)


@dataclass(slots=True)
class ScoredSystem:
    """Internal scored system result."""

    system: GrowingSystem
    raw_score: float
    normalized_metrics: dict[str, float]
    modifiers: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass(slots=True)
class ScoredCrop:
    """Internal scored crop result."""

    crop: Crop
    system_name: str
    raw_score: float
    normalized_metrics: dict[str, float]
    rule_notes: list[str] = field(default_factory=list)
    score: float = 0.0


def score_systems(systems: list[GrowingSystem], mission: MissionProfile) -> list[ScoredSystem]:
    """Rank growing systems against the mission profile."""

    ranges = build_metric_ranges(systems, SYSTEM_METRICS)
    weights = derive_system_weights(mission)
    results: list[ScoredSystem] = []

    for system in systems:
        normalized = normalize_record(system, ranges)
        raw_score = (
            weights["water_efficiency"] * normalized["water_efficiency"]
            - weights["energy_cost"] * normalized["energy_cost"]
            - weights["complexity"] * normalized["complexity"]
            - weights["maintenance"] * normalized["maintenance"]
        )
        modifiers: list[str] = []

        if mission.goal is Goal.BALANCED and system.name == "hybrid":
            raw_score += 0.05
            modifiers.append("balanced-profile-bonus")

        if is_tight_constraint(mission.constraints.water) and system.name == "aeroponic":
            raw_score += 0.08
            modifiers.append("water-priority-bonus")

        if is_tight_constraint(mission.constraints.energy) and system.name == "hydroponic":
            raw_score += 0.05
            modifiers.append("energy-savings-bonus")

        if mission.goal is Goal.LOW_MAINTENANCE and system.maintenance <= 40:
            raw_score += 0.04
            modifiers.append("low-maintenance-bonus")

        if mission.environment is Environment.MARS and system.name == "hybrid":
            raw_score += 0.10
            modifiers.append("mars-resilience-bonus")
        elif mission.environment is Environment.MARS and system.name == "aeroponic":
            raw_score -= 0.03
            modifiers.append("mars-complexity-penalty")

        if mission.environment is Environment.MOON and system.name == "aeroponic":
            bonus = 0.09 if not is_tight_constraint(mission.constraints.energy) else 0.04
            raw_score += bonus
            modifiers.append("moon-water-bonus")
        elif mission.environment is Environment.MOON and system.name == "hydroponic":
            raw_score += 0.02
            modifiers.append("moon-stability-bonus")

        if mission.environment is Environment.ISS and system.name == "hydroponic":
            raw_score += 0.10
            modifiers.append("iss-simplicity-bonus")
        elif mission.environment is Environment.ISS and system.name == "aeroponic":
            raw_score -= 0.05
            modifiers.append("iss-complexity-penalty")

        results.append(
            ScoredSystem(
                system=system,
                raw_score=raw_score,
                normalized_metrics=normalized,
                modifiers=modifiers,
            )
        )

    for item, normalized_score in zip(results, normalize_scores([result.raw_score for result in results])):
        item.score = normalized_score

    return sorted(results, key=lambda item: item.score, reverse=True)


def score_crops(
    crops: list[Crop],
    mission: MissionProfile,
    selected_system: GrowingSystem,
    temporary_penalties: Mapping[str, float] | None = None,
    weight_adjustments: Mapping[str, float] | None = None,
) -> list[ScoredCrop]:
    """Rank crops for the selected system and mission profile."""

    ranges = build_metric_ranges(crops, CROP_METRICS)
    eligible_crops = filter_compatible_crops(crops, selected_system)
    weights = derive_crop_weights(mission, manual_adjustments=weight_adjustments)
    results: list[ScoredCrop] = []

    for crop in eligible_crops:
        normalized = normalize_record(crop, ranges)
        raw_score = (
            weights["calorie"] * normalized["calorie_yield"]
            - weights["water"] * normalized["water_need"]
            - weights["energy"] * normalized["energy_need"]
            - weights["growth_time"] * normalized["growth_time"]
            - weights["risk"] * normalized["risk"]
            - weights["maintenance"] * normalized["maintenance"]
            + weights["closed_loop"] * normalized["closed_loop_score"]
            + weights["crew_support"] * normalized["crew_support_score"]
        )
        adjustment, notes = compute_rule_adjustment(crop, mission)
        raw_score += adjustment

        if mission.goal is Goal.CALORIE_MAX and crop.calorie_yield >= 80:
            raw_score += 0.18
            notes.append("calorie-priority-bonus")
        elif mission.goal is Goal.WATER_EFFICIENCY and crop.water_need <= 35:
            raw_score += 0.06
            notes.append("water-priority-bonus")
        elif mission.goal is Goal.LOW_MAINTENANCE and crop.maintenance <= 35:
            raw_score += 0.06
            notes.append("maintenance-priority-bonus")

        if mission.environment is Environment.MARS:
            if crop.calorie_yield >= 75:
                raw_score += 0.07
                notes.append("mars-calorie-bonus")
            if crop.risk <= 40:
                raw_score += 0.05
                notes.append("mars-robustness-bonus")
            if crop.closed_loop_score >= 0.72:
                raw_score += 0.04
                notes.append("mars-closed-loop-bonus")
        elif mission.environment is Environment.MOON:
            if crop.water_need <= 35:
                raw_score += 0.07
                notes.append("moon-water-bonus")
            if crop.waste_recycling_synergy >= 70:
                raw_score += 0.05
                notes.append("moon-recycling-bonus")
            if crop.closed_loop_score >= 0.72:
                raw_score += 0.03
                notes.append("moon-closed-loop-bonus")
        elif mission.environment is Environment.ISS:
            if crop.maintenance <= 35:
                raw_score += 0.07
                notes.append("iss-maintenance-bonus")
            if crop.risk <= 30:
                raw_score += 0.04
                notes.append("iss-stability-bonus")
            if crop.crew_support_score >= 0.70:
                raw_score += 0.05
                notes.append("iss-crew-support-bonus")

        if temporary_penalties and crop.name.lower() in temporary_penalties:
            raw_score -= temporary_penalties[crop.name.lower()]
            notes.append("temporary-yield-penalty")

        results.append(
            ScoredCrop(
                crop=crop,
                system_name=selected_system.name,
                raw_score=raw_score,
                normalized_metrics=normalized,
                rule_notes=notes,
            )
        )

    for item, normalized_score in zip(results, normalize_scores([result.raw_score for result in results])):
        item.score = normalized_score

    return sorted(results, key=lambda item: item.score, reverse=True)
