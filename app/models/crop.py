"""Crop dataset model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

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
    preferred_environments: list[str]
    mission_environments: list[Environment] = Field(default_factory=list)
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

    def environment_fit_score(self, environment: Environment, fallback: float = 0.72) -> float:
        """Return explicit environment fit when available, otherwise a neutral fallback."""

        if not self.mission_environments:
            return fallback
        return 1.0 if environment in self.mission_environments else 0.6

    def prefers_environment(self, environment: Environment) -> bool:
        """Check whether the crop explicitly targets the mission environment."""

        return environment in self.mission_environments

    def system_fit_score(self, system_name: str, fallback: float = 0.72) -> float:
        """Resolve broad grow-system compatibility from descriptive labels."""

        if not self.compatible_systems:
            return fallback

        normalized_labels = [label.casefold() for label in self.compatible_systems]
        system_name = system_name.casefold()
        keywords = {
            "hydroponic": ("hydropon", "hidropon", "nft", "wrads"),
            "aeroponic": ("aeropon", "aero", "mist", "fog"),
            "hybrid": (
                "hybrid",
                "hibrit",
                "substrat",
                "substrate",
                "media",
                "bpc",
                "aph",
                "habitat",
                "tunnel",
                "tünel",
                "dikey",
                "vertical",
                "biyoreakt",
                "bioreact",
                "kök",
                "root",
                "trellis",
                "bağlı",
                "bagli",
            ),
        }.get(system_name, (system_name,))

        if any(system_name == label for label in normalized_labels):
            return 1.0
        if any(keyword in label for label in normalized_labels for keyword in keywords):
            return 1.0
        return fallback

    def supports_system(self, system_name: str) -> bool:
        """Check whether the crop explicitly or descriptively supports the grow system."""

        return self.system_fit_score(system_name, fallback=0.0) >= 0.99
