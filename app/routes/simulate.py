"""Simulated runtime adaptation endpoint."""

from __future__ import annotations
from fastapi import APIRouter
from app.models.response import SimulationRequest, SimulationResponse
from app.services.choice_service import choice_service
from app.services.recommender import get_default_engine

router = APIRouter(tags=["simulate"])

@router.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest) -> SimulationResponse:
    """Simulate a runtime change event and rerun the planning engine."""

    # --- HACKATHON MVP: Auth geçici olarak devre dışı bırakıldı ---
    # ID tipin veritabanında neyse ona göre ayarla (Integer ise 1, UUID ise string bir ID)
    mock_user_id = 1 
    
    # Kullanıcı mahsul seçmediyse, son seçimini baz al
    if payload.affected_crop is None:
        last_choice = choice_service.get_latest_choice(mock_user_id)
        if last_choice:
            payload = payload.model_copy(update={"affected_crop": last_choice.crop_name})

    return get_default_engine().simulate(payload)