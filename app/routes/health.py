"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.response import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Basic health endpoint for demos and tests."""

    return HealthResponse(status="healthy", service="space_agri_ai")

