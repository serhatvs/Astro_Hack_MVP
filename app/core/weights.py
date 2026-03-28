"""Dynamic weight derivation based on mission context."""

from __future__ import annotations

from collections.abc import Mapping

from app.models.mission import ConstraintLevel, Duration, Environment, Goal, MissionProfile


BASE_CROP_WEIGHTS = {
    "calorie": 0.30,
    "water": 0.20,
    "energy": 0.15,
    "growth_time": 0.15,
    "risk": 0.10,
    "maintenance": 0.10,
    "closed_loop": 0.08,
    "crew_support": 0.04,
}

BASE_SYSTEM_WEIGHTS = {
    "water_efficiency": 0.45,
    "energy_cost": 0.25,
    "complexity": 0.20,
    "maintenance": 0.10,
}


def _renormalize(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def derive_crop_weights(
    mission: MissionProfile,
    manual_adjustments: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Adjust crop weights from the mission profile and optional runtime bias."""

    weights = dict(BASE_CROP_WEIGHTS)

    if mission.goal is Goal.CALORIE_MAX:
        weights["calorie"] += 0.40
        weights["closed_loop"] += 0.04
    elif mission.goal is Goal.WATER_EFFICIENCY:
        weights["water"] += 0.25
        weights["risk"] += 0.05
        weights["closed_loop"] += 0.04
    elif mission.goal is Goal.LOW_MAINTENANCE:
        weights["maintenance"] += 0.25
        weights["risk"] += 0.05
        weights["crew_support"] += 0.04

    if mission.duration is Duration.LONG:
        weights["calorie"] += 0.10
        weights["growth_time"] += 0.10
        weights["closed_loop"] += 0.03
    elif mission.duration is Duration.SHORT:
        weights["growth_time"] += 0.08 if mission.goal is Goal.CALORIE_MAX else 0.20

    if mission.constraints.water is ConstraintLevel.LOW:
        weights["water"] += 0.15
        weights["closed_loop"] += 0.03

    if mission.constraints.energy is ConstraintLevel.LOW:
        weights["energy"] += 0.10

    if mission.environment is Environment.MARS:
        weights["calorie"] += 0.12
        weights["risk"] += 0.10
        weights["closed_loop"] += 0.06
    elif mission.environment is Environment.MOON:
        weights["water"] += 0.15
        weights["risk"] += 0.06
        weights["closed_loop"] += 0.08
    elif mission.environment is Environment.ISS:
        weights["maintenance"] += 0.15
        weights["risk"] += 0.08
        weights["crew_support"] += 0.08

    if manual_adjustments:
        for metric, delta in manual_adjustments.items():
            if metric in weights:
                weights[metric] += delta

    return _renormalize(weights)


def derive_system_weights(mission: MissionProfile) -> dict[str, float]:
    """Adjust system scoring emphasis from mission constraints and environment."""

    weights = dict(BASE_SYSTEM_WEIGHTS)

    if mission.constraints.water is ConstraintLevel.LOW:
        weights["water_efficiency"] += 0.22

    if mission.constraints.energy is ConstraintLevel.LOW:
        weights["energy_cost"] += 0.18

    if mission.constraints.area is ConstraintLevel.LOW:
        weights["complexity"] += 0.04

    if mission.goal is Goal.WATER_EFFICIENCY:
        weights["water_efficiency"] += 0.12
    elif mission.goal is Goal.LOW_MAINTENANCE:
        weights["maintenance"] += 0.12
        weights["complexity"] += 0.04
    elif mission.goal is Goal.CALORIE_MAX:
        weights["complexity"] += 0.04

    if mission.environment is Environment.MARS:
        weights["complexity"] += 0.12
        weights["maintenance"] += 0.08
    elif mission.environment is Environment.MOON:
        weights["water_efficiency"] += 0.18
        weights["complexity"] += 0.05
    elif mission.environment is Environment.ISS:
        weights["maintenance"] += 0.16
        weights["complexity"] += 0.10
        weights["energy_cost"] += 0.04

    return _renormalize(weights)
