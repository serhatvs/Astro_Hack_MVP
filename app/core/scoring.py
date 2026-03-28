"""Scoring functions for growing systems and crops."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.filters import compute_rule_adjustment, filter_compatible_crops
from app.core.normalization import build_metric_ranges, normalize_record, normalize_scores
from app.core.weights import derive_crop_weights, derive_system_weights
from app.models.crop import Crop
from app.models.mission import ConstraintLevel, Goal, MissionProfile
from app.models.system import GrowingSystem


SYSTEM_METRICS = ("water_efficiency", "energy_cost", "complexity", "maintenance")
CROP_METRICS = (
    "calorie_yield",
    "water_need",
    "energy_need",
    "growth_time",
    "risk",
    "maintenance",
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

        if mission.constraints.water is ConstraintLevel.LOW and system.name == "aeroponic":
            raw_score += 0.08
            modifiers.append("water-priority-bonus")

        if mission.constraints.energy is ConstraintLevel.LOW and system.name == "hydroponic":
            raw_score += 0.05
            modifiers.append("energy-savings-bonus")

        if mission.goal is Goal.LOW_MAINTENANCE and system.maintenance <= 40:
            raw_score += 0.04
            modifiers.append("low-maintenance-bonus")

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
    if len(eligible_crops) < 3:
        eligible_crops = list(crops)

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
        )
        adjustment, notes = compute_rule_adjustment(crop, mission)
        raw_score += adjustment

        if temporary_penalties and crop.name in temporary_penalties:
            raw_score -= temporary_penalties[crop.name]
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

