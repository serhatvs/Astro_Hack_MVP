"""AI-Driven agriculture optimization endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.mission import MissionProfile
from app.models.response import OptimizeAgricultureResponse
from app.services.ai_optimizer import AIAgricultureOptimizer
from app.services.data_provider import JSONDataProvider


router = APIRouter(tags=["optimize"])


@router.post("/optimize_agriculture", response_model=OptimizeAgricultureResponse)
async def optimize_agriculture(payload: MissionProfile) -> OptimizeAgricultureResponse:
    """AI-driven agriculture optimization using hybrid deterministic+LLM approach.
    
    Workflow:
    1. Load mission parameters and data (crops.json, systems.json)
    2. Apply deterministic hard-filter (exclude crops with growth_time > mission_duration)
    3. Build LLM context with remaining viable crops and system data
    4. Invoke LLM to select top 3 crops and optimal system with historical reasoning
    5. Return structured JSON response with AI reasoning and status
    
    Args:
        payload: MissionProfile containing environment, duration, constraints, and goal
    
    Returns:
        OptimizeAgricultureResponse with AI-selected crops, system, and reasoning
    """
    # Initialize data provider
    provider = JSONDataProvider()
    
    # Load crop and system data
    crops = provider.get_crops()
    systems = provider.get_systems()
    
    # Initialize AI optimizer
    optimizer = AIAgricultureOptimizer()
    
    # Perform optimization
    response = await optimizer.optimize(
        mission=payload,
        crops=crops,
        systems=systems,
    )
    
    return response
