"""Stateful mission and legacy simulation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.simulation import MissionStepRequest
from app.models.response import (
    AIInsight,
    AIInsightRequest,
    MissionStepResponse,
    SimulationRequest,
    SimulationResponse,
    SimulationStartRequest,
    SimulationStartResponse,
)
from app.services.recommender import get_default_engine


router = APIRouter(tags=["mission"])


@router.post("/simulation/start", response_model=SimulationStartResponse)
def start_simulation(payload: SimulationStartRequest) -> SimulationStartResponse:
    """Bootstrap a stateful mission simulation from a user-selected ecosystem stack."""

    return get_default_engine().start_simulation(payload)


@router.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest) -> SimulationResponse:
    """Legacy stateless simulation endpoint retained for compatibility."""

    return get_default_engine().simulate(payload)


@router.post("/mission/step", response_model=MissionStepResponse)
def mission_step(payload: MissionStepRequest) -> MissionStepResponse:
    """Advance a stored mission state by one bounded time step."""

    return get_default_engine().mission_step(payload)


@router.post("/simulation/insight", response_model=AIInsight)
def simulation_insight(payload: AIInsightRequest) -> AIInsight:
    """Generate optional AI insight for simulation start/end or manual deep analysis."""

    return get_default_engine().generate_ai_insight(payload)
