"""Simple interpretable rule layer applied around weighted scoring."""

from __future__ import annotations

from app.models.crop import Crop
from app.models.mission import Duration, MissionProfile, is_tight_constraint
from app.models.system import GrowingSystem


def filter_compatible_crops(crops: list[Crop], system: GrowingSystem) -> list[Crop]:
    """Keep only crops compatible with the selected growing system."""

    return [crop for crop in crops if crop.system_fit_score(system.name) >= 0.6]


def mission_has_constrained_resources(mission: MissionProfile) -> bool:
    """Check if the mission has at least one tight resource."""

    constraints = mission.constraints
    return (
        is_tight_constraint(constraints.water)
        or is_tight_constraint(constraints.energy)
        or is_tight_constraint(constraints.area)
    )


def compute_rule_adjustment(crop: Crop, mission: MissionProfile) -> tuple[float, list[str]]:
    """Apply small interpretable bonuses and penalties to crop scores."""

    adjustment = 0.0
    notes: list[str] = []

    if crop.prefers_environment(mission.environment):
        adjustment += 0.05
        notes.append("environment-fit")

    if mission.duration is Duration.SHORT and crop.growth_time >= 60:
        adjustment -= 0.12
        notes.append("slow-cycle-penalty")

    if mission_has_constrained_resources(mission) and crop.maintenance >= 65:
        adjustment -= 0.08
        notes.append("maintenance-penalty")

    if is_tight_constraint(mission.constraints.area) and crop.area_need >= 55:
        adjustment -= 0.10
        notes.append("area-penalty")

    if is_tight_constraint(mission.constraints.water) and crop.water_need <= 35:
        adjustment += 0.04
        notes.append("water-efficiency-bonus")

    return adjustment, notes
