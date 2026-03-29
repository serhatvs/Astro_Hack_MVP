"""Stateful mission and legacy simulation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.protection import (
    protect_mission_step,
    protect_simulate,
    protect_simulation_start,
)
from app.core.simulation import MissionStepRequest
from app.models.response import (
    MissionStepResponse,
    SimulationRequest,
    SimulationResponse,
    SimulationStartRequest,
    SimulationStartResponse,
)
from app.services.recommender import get_default_engine


router = APIRouter(tags=["mission"])


@router.post(
    "/simulation/start",
    response_model=SimulationStartResponse,
    dependencies=[Depends(protect_simulation_start)],
)
def start_simulation(payload: SimulationStartRequest) -> SimulationStartResponse:
    """Bootstrap a stateful mission simulation from a user-selected ecosystem stack."""

    return get_default_engine().start_simulation(payload)


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    dependencies=[Depends(protect_simulate)],
)
def simulate(payload: SimulationRequest) -> SimulationResponse:
    """Legacy stateless simulation endpoint retained for compatibility."""

    return get_default_engine().simulate(payload)


@router.post(
    "/mission/step",
    response_model=MissionStepResponse,
    dependencies=[Depends(protect_mission_step)],
)
def mission_step(payload: MissionStepRequest) -> MissionStepResponse:
    """Advance a stored mission state by one bounded time step."""

    return get_default_engine().mission_step(payload)
