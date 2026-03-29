"""Basic mission and agriculture risk heuristics."""

from __future__ import annotations

from app.core.scoring import ScoredCrop
from app.models.mission import Duration, Environment, MissionProfile, is_tight_constraint
from app.models.response import RiskAnalysis, RiskLevel
from app.models.system import GrowingSystem


def _has_tight_resources(mission: MissionProfile) -> bool:
    return (
        is_tight_constraint(mission.constraints.water)
        or is_tight_constraint(mission.constraints.energy)
        or is_tight_constraint(mission.constraints.area)
    )


def evaluate_risk(
    mission: MissionProfile,
    selected_system: GrowingSystem,
    ranked_crops: list[ScoredCrop],
) -> RiskAnalysis:
    """Estimate overall mission-agriculture risk from simple heuristics."""

    factors: list[str] = []
    points = 0.0
    lead_crop = ranked_crops[0].crop if ranked_crops else None

    if is_tight_constraint(mission.constraints.water) and selected_system.complexity >= 70:
        points += 1.0
        factors.append("water scarcity paired with system complexity")

    if (
        mission.duration is Duration.LONG
        and lead_crop is not None
        and lead_crop.growth_time >= 70
    ):
        points += 1.0
        factors.append("long mission depends on a slower lead crop")

    if _has_tight_resources(mission) and any(item.crop.maintenance >= 65 for item in ranked_crops):
        points += 1.0
        factors.append("high-maintenance crops under constrained resources")

    if is_tight_constraint(mission.constraints.area) and any(
        item.crop.area_need >= 55 for item in ranked_crops
    ):
        points += 1.0
        factors.append("limited area with large-footprint crop options")

    if mission.environment is Environment.MARS and (
        selected_system.complexity >= 50 or any(item.crop.risk >= 45 for item in ranked_crops[:2])
    ):
        points += 1.0
        factors.append("Mars missions demand stronger robustness margins")

    if mission.environment is Environment.MARS and lead_crop is not None and lead_crop.calorie_yield < 60:
        points += 0.5
        factors.append("Mars calorie continuity is light for the selected lead crop")

    if mission.environment is Environment.MOON and (
        any(item.crop.water_need >= 50 for item in ranked_crops[:2])
        or selected_system.water_efficiency < 70
    ):
        points += 1.0
        factors.append("Moon missions amplify water recovery pressure")

    if mission.environment is Environment.MOON and any(
        item.crop.waste_recycling_synergy < 60 for item in ranked_crops[:2]
    ):
        points += 0.5
        factors.append("Moon missions benefit from stronger recycling synergy")

    if mission.environment is Environment.ISS and (
        selected_system.maintenance >= 45
        or selected_system.complexity >= 45
        or any(item.crop.maintenance >= 45 for item in ranked_crops[:2])
    ):
        points += 1.0
        factors.append("ISS operations prefer lower-maintenance crop cycles")

    if mission.environment is Environment.ISS and any(
        item.crop.crew_acceptance < 65 for item in ranked_crops[:2]
    ):
        points += 0.5
        factors.append("ISS crews benefit from higher crop acceptance")

    score = round(min(points / 6.0, 1.0), 3)

    if points >= 4.0:
        level = RiskLevel.HIGH
    elif points >= 2.0:
        level = RiskLevel.MODERATE
    else:
        level = RiskLevel.LOW

    if not factors:
        factors.append("no major mission stressors detected")

    return RiskAnalysis(level=level, score=score, factors=factors[:3])
