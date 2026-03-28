"""Mission input models and enums."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Environment(StrEnum):
    MARS = "mars"
    MOON = "moon"
    ISS = "iss"


class Duration(StrEnum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class ConstraintLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Goal(StrEnum):
    BALANCED = "balanced"
    CALORIE_MAX = "calorie_max"
    WATER_EFFICIENCY = "water_efficiency"
    LOW_MAINTENANCE = "low_maintenance"


class ChangeEvent(StrEnum):
    WATER_DROP = "water_drop"
    ENERGY_DROP = "energy_drop"
    YIELD_DROP = "yield_drop"
    CONTAMINATION = "contamination"
    YIELD_VARIATION = "yield_variation"


class MissionConstraints(BaseModel):
    """Resource constraint levels for the mission."""

    model_config = ConfigDict(extra="forbid")

    water: ConstraintLevel
    energy: ConstraintLevel
    area: ConstraintLevel


class MissionProfile(BaseModel):
    """Mission profile consumed by the recommendation engine."""

    model_config = ConfigDict(extra="forbid")

    environment: Environment
    duration: Duration
    constraints: MissionConstraints
    goal: Goal


def downgrade_constraint(level: ConstraintLevel) -> ConstraintLevel:
    """Decrease a constraint by one step while clamping at low."""

    if level is ConstraintLevel.HIGH:
        return ConstraintLevel.MEDIUM
    if level is ConstraintLevel.MEDIUM:
        return ConstraintLevel.LOW
    return ConstraintLevel.LOW


class OptimizeAgricultureRequest(BaseModel):
    """Lightweight request for optimized agriculture endpoint."""

    model_config = ConfigDict(extra="forbid")

    mission_duration: int
    water_limit: float
    energy_limit: float
    environment: Environment
