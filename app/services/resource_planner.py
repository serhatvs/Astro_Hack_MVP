"""Simple resource allocation planning derived from top recommendations."""

from __future__ import annotations

from app.core.scoring import ScoredCrop
from app.models.response import ResourcePlan
from app.models.system import GrowingSystem


class ResourcePlanner:
    """Create a basic categorized resource plan for the selected portfolio."""

    def build_plan(self, ranked_crops: list[ScoredCrop], selected_system: GrowingSystem) -> ResourcePlan:
        if not ranked_crops:
            return ResourcePlan(
                water_level="medium",
                energy_level="moderate",
                area_usage="medium",
            )

        weights = [max(item.score, 0.1) for item in ranked_crops]
        total_weight = sum(weights)

        weighted_water = sum(item.crop.water_need * weight for item, weight in zip(ranked_crops, weights)) / total_weight
        weighted_energy = sum(item.crop.energy_need * weight for item, weight in zip(ranked_crops, weights)) / total_weight
        weighted_area = sum(item.crop.area_need * weight for item, weight in zip(ranked_crops, weights)) / total_weight

        effective_water = max(0.0, weighted_water - (selected_system.water_efficiency * 0.35))
        effective_energy = (weighted_energy * 0.60) + (selected_system.energy_cost * 0.40)

        if effective_water <= 15:
            water_level = "optimized-low"
        elif effective_water <= 35:
            water_level = "low"
        elif effective_water <= 55:
            water_level = "medium"
        else:
            water_level = "high"

        if effective_energy <= 35:
            energy_level = "low"
        elif effective_energy <= 60:
            energy_level = "moderate"
        else:
            energy_level = "high"

        if weighted_area <= 25:
            area_usage = "compact"
        elif weighted_area <= 55:
            area_usage = "medium"
        else:
            area_usage = "large"

        return ResourcePlan(
            water_level=water_level,
            energy_level=energy_level,
            area_usage=area_usage,
        )

