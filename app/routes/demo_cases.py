"""Demo case endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.demo_case import DemoCase
from app.services.recommender import get_default_engine


router = APIRouter(tags=["demo-cases"])


@router.get("/demo-cases", response_model=list[DemoCase])
def list_demo_cases() -> list[DemoCase]:
    """Return named demo presets for UI and live pitch flow."""

    return get_default_engine().list_demo_cases()
