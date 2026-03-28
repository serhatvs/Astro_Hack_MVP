"""Basic mission and agriculture risk heuristics."""

from __future__ import annotations

from app.core.scoring import ScoredCrop
from app.models.mission import ConstraintLevel, Duration, MissionProfile
from app.models.response import RiskAnalysis, RiskLevel
from app.models.system import GrowingSystem


def _has_tight_resources(mission: MissionProfile) -> bool:
    return (
        mission.constraints.water is ConstraintLevel.LOW
        or mission.constraints.energy is ConstraintLevel.LOW
        or mission.constraints.area is ConstraintLevel.LOW
    )


def evaluate_risk(
    mission: MissionProfile,
    selected_system: GrowingSystem,
    ranked_crops: list[ScoredCrop],
) -> RiskAnalysis:
    """Estimate overall mission-agriculture risk from simple heuristics."""

    factors: list[str] = []
    points = 0
    lead_crop = ranked_crops[0].crop if ranked_crops else None

    if mission.constraints.water is ConstraintLevel.LOW and selected_system.complexity >= 70:
        points += 1
        factors.append("water scarcity paired with system complexity")

    if (
        mission.duration is Duration.LONG
        and lead_crop is not None
        and lead_crop.growth_time >= 70
    ):
        points += 1
        factors.append("long mission depends on a slower lead crop")

    if _has_tight_resources(mission) and any(item.crop.maintenance >= 65 for item in ranked_crops):
        points += 1
        factors.append("high-maintenance crops under constrained resources")

    if mission.constraints.area is ConstraintLevel.LOW and any(
        item.crop.area_need >= 55 for item in ranked_crops
    ):
        points += 1
        factors.append("limited area with large-footprint crop options")

    if points >= 4:
        level = RiskLevel.HIGH
    elif points >= 2:
        level = RiskLevel.MODERATE
    else:
        level = RiskLevel.LOW

    if not factors:
        factors.append("no major mission stressors detected")

    return RiskAnalysis(level=level, factors=factors[:3])
