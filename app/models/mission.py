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


def tighten_constraint(level: ConstraintLevel) -> ConstraintLevel:
    """Increase constraint severity by one step while clamping at high."""

    if level is ConstraintLevel.LOW:
        return ConstraintLevel.MEDIUM
    if level is ConstraintLevel.MEDIUM:
        return ConstraintLevel.HIGH
    return ConstraintLevel.HIGH


def downgrade_constraint(level: ConstraintLevel) -> ConstraintLevel:
    """Backward-compatible alias for tightening mission constraints after a resource drop."""

    return tighten_constraint(level)


def is_tight_constraint(level: ConstraintLevel) -> bool:
    """Return whether the constraint represents a truly resource-tight mission condition."""

    return level is ConstraintLevel.HIGH


def is_moderate_or_tight_constraint(level: ConstraintLevel) -> bool:
    """Return whether the constraint is meaningful enough to influence scoring."""

    return level in {ConstraintLevel.MEDIUM, ConstraintLevel.HIGH}
