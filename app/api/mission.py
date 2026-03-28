"""Stateful mission and legacy simulation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.simulation import MissionStepRequest
from app.models.response import MissionStepResponse, SimulationRequest, SimulationResponse
from app.services.recommender import get_default_engine


router = APIRouter(tags=["mission"])


@router.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest) -> SimulationResponse:
    """Legacy stateless simulation endpoint retained for compatibility."""

    return get_default_engine().simulate(payload)


@router.post("/mission/step", response_model=MissionStepResponse)
def mission_step(payload: MissionStepRequest) -> MissionStepResponse:
    """Advance a stored mission state by one bounded time step."""

    return get_default_engine().mission_step(payload)
