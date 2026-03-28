"""Algae system dataset model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

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
    preferred_environments: list[str]
    mission_environments: list[Environment] = Field(default_factory=list)
    has_photosynthesis: bool = True
    notes: str

    def environment_fit_score(self, environment: Environment, fallback: float = 0.72) -> float:
        """Return explicit environment fit when available, otherwise a neutral fallback."""

        if not self.mission_environments:
            return fallback
        return 1.0 if environment in self.mission_environments else 0.62

    def prefers_environment(self, environment: Environment) -> bool:
        """Check whether the algae system explicitly targets the mission environment."""

        return environment in self.mission_environments
