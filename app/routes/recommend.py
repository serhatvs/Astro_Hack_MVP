"""Mission recommendation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.mission import MissionProfile, OptimizeAgricultureRequest
from app.models.response import OptimizeAgricultureResponse, RecommendationResponse
from app.models.user import User
from app.services.recommender import get_default_engine


router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendationResponse)
def recommend(payload: MissionProfile) -> RecommendationResponse:
    """Generate mission planning recommendations."""

    return get_default_engine().recommend(payload)


@router.post("/optimise_agriculture", response_model=OptimizeAgricultureResponse)
def optimise_agriculture(payload: OptimizeAgricultureRequest, current_user: User = Depends(get_current_user)) -> OptimizeAgricultureResponse:
    """Hybrid filter + ranking endpoint for quick MVP optimization. Requires authentication."""

    return get_default_engine().optimize_agriculture(payload)

