"""Microbial system dataset model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.mission import Environment


class MicrobialSystem(BaseModel):
    """Seed microbial-system data for loop-support evaluation."""

    model_config = ConfigDict(extra="forbid")

    name: str
    waste_recycling_efficiency: float
    nutrient_conversion_capability: float
    loop_closure_contribution: float
    contamination_risk: float
    reactor_dependency: float
    environmental_sensitivity: float
    maintenance_burden: float
    preferred_environments: list[Environment]
    notes: str
