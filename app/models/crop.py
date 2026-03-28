"""Crop dataset model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.mission import Environment


class Crop(BaseModel):
    """Seed crop data used by the scoring engine."""

    model_config = ConfigDict(extra="forbid")

    name: str
    calorie_yield: float
    water_need: float
    energy_need: float
    growth_time: float
    risk: float
    maintenance: float
    area_need: float
    nutrient_density: float
    oxygen_contribution: float
    co2_utilization: float
    waste_recycling_synergy: float
    crew_acceptance: float
    compatible_systems: list[str]
    preferred_environments: list[Environment]
    notes: str
