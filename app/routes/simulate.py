"""Simulated runtime adaptation endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.response import SimulationRequest, SimulationResponse
from app.services.recommender import get_default_engine


router = APIRouter(tags=["simulate"])


@router.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest) -> SimulationResponse:
    """Simulate a runtime change event and rerun the planning engine."""

    return get_default_engine().simulate(payload)

