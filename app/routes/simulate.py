"""Simulated runtime adaptation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.response import SimulationRequest, SimulationResponse
from app.models.user import User
from app.services.choice_service import choice_service
from app.services.recommender import get_default_engine


router = APIRouter(tags=["simulate"])


@router.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest, current_user: User = Depends(get_current_user)) -> SimulationResponse:
    """Simulate a runtime change event and rerun the planning engine."""

    # Prefer user chosen crop for simulation context if no affected_crop is explicitly provided.
    if payload.affected_crop is None:
        last_choice = choice_service.get_latest_choice(current_user.id)
        if last_choice:
            payload = payload.model_copy(update={"affected_crop": last_choice.crop_name})

    return get_default_engine().simulate(payload)

