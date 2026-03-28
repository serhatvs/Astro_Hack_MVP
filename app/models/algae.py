"""Algae system dataset model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.mission import Environment


class AlgaeSystem(BaseModel):
    """Seed algae-system data for loop-support evaluation."""

    model_config = ConfigDict(extra="forbid")

    name: str
    oxygen_contribution: float
    co2_utilization: float
    biomass_production: float
    protein_potential: float
    photobioreactor_compatibility: float
    water_system_compatibility: float
    energy_light_dependency: float
    maintenance_complexity: float
    preferred_environments: list[Environment]
    notes: str
