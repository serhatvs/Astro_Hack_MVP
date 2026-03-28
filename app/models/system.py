"""Growing system dataset model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GrowingSystem(BaseModel):
    """Growing system attributes used during system selection."""

    model_config = ConfigDict(extra="forbid")

    name: str
    water_efficiency: float
    energy_cost: float
    complexity: float
    maintenance: float
    environment_notes: dict[str, str] = Field(default_factory=dict)
    notes: str

