"""Mission recommendation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.auth import get_optional_current_user
from app.models.auth import AuthUser
from app.models.mission import MissionProfile
from app.models.response import RecommendationResponse
from app.services.recommender import get_default_engine


router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendationResponse)
def recommend(
    payload: MissionProfile,
    current_user: AuthUser | None = Depends(get_optional_current_user),
) -> RecommendationResponse:
    """Generate mission planning recommendations."""

    return get_default_engine().recommend(payload, use_llm=current_user is not None)
