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

    @property
    def closed_loop_score(self) -> float:
        """Aggregate closed-loop contribution score on a 0..1 scale."""

        return (
            self.nutrient_density
            + self.oxygen_contribution
            + self.co2_utilization
            + self.waste_recycling_synergy
        ) / 400

    @property
    def crew_support_score(self) -> float:
        """Crew support score derived from acceptance on a 0..1 scale."""

        return self.crew_acceptance / 100
