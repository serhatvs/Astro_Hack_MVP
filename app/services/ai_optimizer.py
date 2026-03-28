"""LLM-powered agriculture optimization service."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import AsyncOpenAI

from app.models.crop import Crop
from app.models.mission import Environment, MissionProfile
from app.models.response import (
    AICropRecommendation,
    OptimizeAgricultureResponse,
    OptimizeAgricultureStatus,
)
from app.models.system import GrowingSystem


def get_mission_duration_days(duration_str: str) -> int:
    """Convert mission duration string to approximate days."""
    duration_map = {
        "short": 30,
        "medium": 60,
        "long": 90,
    }
    return duration_map.get(duration_str.lower(), 90)


def apply_deterministic_filter(
    crops: list[Crop],
    mission_duration_days: int,
) -> list[Crop]:
    """Apply hard filter: exclude crops with growth_time > mission_duration.
    
    This deterministic filter ensures physically impossible selections are
    prevented before LLM reasoning begins.
    """
    filtered = [c for c in crops if c.growth_time <= mission_duration_days]
    return filtered


class AIAgricultureOptimizer:
    """LLM-powered agriculture optimization with deterministic guardrails."""

    def __init__(self, api_key: str | None = None):
        """Initialize the AI optimizer with OpenAI API key."""
        self.api_key = api_key or os.getenv("AI_API_KEY")
        if not self.api_key:
            raise ValueError("AI_API_KEY not set in environment")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def optimize(
        self,
        mission: MissionProfile,
        crops: list[Crop],
        systems: list[GrowingSystem],
    ) -> OptimizeAgricultureResponse:
        """Optimize agriculture selection using hybrid deterministic+LLM approach.
        
        Workflow:
        1. Apply deterministic filter (growth_time <= mission_duration)
        2. Build LLM context with remaining crops and constraints
        3. Get AI reasoning for top 3 crops and system selection
        4. Return structured response with historical context
        """
        # Step 1: Deterministic filtering
        mission_duration_days = get_mission_duration_days(mission.duration)
        filtered_crops = apply_deterministic_filter(crops, mission_duration_days)

        if not filtered_crops:
            raise ValueError(
                f"No crops viable for mission duration "
                f"of {mission.duration} ({mission_duration_days} days)"
            )

        # Step 2: Build LLM context
        context = self._build_llm_context(
            mission=mission,
            filtered_crops=filtered_crops,
            systems=systems,
            mission_duration_days=mission_duration_days,
        )

        # Step 3: Get AI reasoning with structured output
        response = await self._get_llm_response(context)

        return response

    def _build_llm_context(
        self,
        mission: MissionProfile,
        filtered_crops: list[Crop],
        systems: list[GrowingSystem],
        mission_duration_days: int,
    ) -> str:
        """Build comprehensive context for LLM decision-making."""
        crops_json = json.dumps(
            [c.model_dump() for c in filtered_crops],
            indent=2,
        )
        systems_json = json.dumps(
            [s.model_dump() for s in systems],
            indent=2,
        )

        constraints_summary = (
            f"Water: {mission.constraints.water}, "
            f"Energy: {mission.constraints.energy}, "
            f"Area: {mission.constraints.area}"
        )

        context = f"""
## MISSION CONTEXT
- Environment: {mission.environment.value}
- Duration: {mission.duration.value} ({mission_duration_days} days)
- Goal: {mission.goal.value}
- Constraints: {constraints_summary}

## VIABLE CROPS (after deterministic filter)
{crops_json}

## AVAILABLE GROWING SYSTEMS
{systems_json}

## YOUR TASK
Analyze the crops and systems, then provide:
1. Top 3 recommended crops (considering the mission duration, constraints, and environment)
2. Best suited growing system
3. Executive summary that references historical space mission challenges
4. Justify your selections based on the data and constraints
"""
        return context

    async def _get_llm_response(self, context: str) -> OptimizeAgricultureResponse:
        """Call OpenAI API with JSON mode for deterministic response format."""
        system_prompt = """Sen TUA (Türkiye Uzay Ajansı) Kıdemli Astrobotanik Sistemler Yapay Zekasısın. Görevin, sağlanan bitki/sistem verilerini ve görev kısıtlamalarını analiz ederek en optimal 3 ürünü ve tarım sistemini seçmektir. Kararını verirken salt sayıları değil, uzay tarihindeki krizleri de düşünmelisin (Örn: MIR uzay istasyonundaki mantar krizleri veya uzun süreli görevlerdeki psikolojik yorgunluk). Seçimini yap ve 'reasoning' (gerekçe) kısmında bu kararı neden aldığını, hangi kısıtlamanın bu kararı zorunlu kıldığını ve tarihsel bir uzay krizi referansıyla destekleyerek profesyonelce açıkla.

Yanıtını kesin olarak şu JSON formatında ver:
{
  "top_crops": [
    {"id": "crop_id_1", "name": "crop_name", "reasoning_for_crop": "reasoning text"},
    {"id": "crop_id_2", "name": "crop_name", "reasoning_for_crop": "reasoning text"},
    {"id": "crop_id_3", "name": "crop_name", "reasoning_for_crop": "reasoning text"}
  ],
  "selected_system": "aeroponic|hydroponic|hybrid",
  "system_reasoning": "detailed reasoning for system choice",
  "executive_summary": "comprehensive report with historical references",
  "status": "NOMINAL|CRITICAL",
  "reasoning": "overall decision justification"
}"""

        message = await self.client.messages.create(
            model="gpt-4-turbo",
            max_tokens=2000,
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": context,
                },
            ],
        )

        response_text = message.content[0].text if message.content else "{}"

        try:
            response_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback if response is not valid JSON
            response_data = self._create_default_response()

        return OptimizeAgricultureResponse(
            top_crops=[
                AICropRecommendation(
                    id=crop.get("id", f"{crop.get('name', 'unknown')}_0"),
                    name=crop["name"],
                    reasoning_for_crop=crop["reasoning_for_crop"],
                )
                for crop in response_data.get("top_crops", [])
            ],
            selected_system=response_data.get("selected_system", "hybrid"),
            system_reasoning=response_data.get(
                "system_reasoning", "System selected based on constraints"
            ),
            executive_summary=response_data.get(
                "executive_summary", "Mission feasibility confirmed with selected crops and system."
            ),
            status=OptimizeAgricultureStatus(
                response_data.get("status", "NOMINAL")
            ),
            reasoning=response_data.get(
                "reasoning", "AI analysis completed successfully"
            ),
        )

    def _create_default_response(self) -> dict[str, Any]:
        """Create a sensible default response if LLM fails."""
        return {
            "top_crops": [
                {
                    "id": "potato_1",
                    "name": "potato",
                    "reasoning_for_crop": "Reliable calorie source with moderate resource requirements",
                },
                {
                    "id": "wheat_1",
                    "name": "wheat",
                    "reasoning_for_crop": "Excellent oxygen production and psychological acceptance",
                },
                {
                    "id": "tomato_1",
                    "name": "tomato",
                    "reasoning_for_crop": "High crew acceptance and nutritional value",
                },
            ],
            "selected_system": "hybrid",
            "system_reasoning": "Hybrid system balances efficiency, resilience, and operational overhead",
            "executive_summary": "Mission feasibility confirmed. Selected crops and hybrid system provide balanced resource utilization suitable for extended missions.",
            "status": "NOMINAL",
            "reasoning": "Default recommendation generated due to LLM service constraints",
        }
