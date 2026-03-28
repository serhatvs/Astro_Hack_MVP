"""Mission recommendation endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.mission import MissionProfile
from app.models.response import RecommendationResponse
from app.services.recommender import get_default_engine


router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendationResponse)
def recommend(payload: MissionProfile) -> RecommendationResponse:
    """Generate mission planning recommendations."""

    return get_default_engine().recommend(payload)
