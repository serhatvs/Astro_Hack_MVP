"""Survival evaluation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.survival import SurvivalDaysRequest, SurvivalDaysResponse
from app.services.survival_service import survival_service

router = APIRouter(tags=["survival"])


@router.post("/survival-days", response_model=SurvivalDaysResponse)
def survival_days(payload: SurvivalDaysRequest) -> SurvivalDaysResponse:
    """Estimate survival days from selected crops and people count."""
    try:
        result = survival_service.calculate(payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
