from __future__ import annotations

from collections import Counter

from app.models.survival import SurvivalDaysRequest, SurvivalDaysResponse
from app.services.data_provider import JSONDataProvider


DEFAULT_DAILY_CALORIES = 2500


class SurvivalService:
    def __init__(self, data_provider: JSONDataProvider | None = None) -> None:
        self.data_provider = data_provider or JSONDataProvider()

    def calculate(self, payload: SurvivalDaysRequest) -> SurvivalDaysResponse:
        if payload.people_count < 1:
            raise ValueError("people_count must be 1 or greater")

        if not payload.selected_crops:
            return SurvivalDaysResponse(
                total_calories=0.0,
                daily_consumption=payload.people_count * DEFAULT_DAILY_CALORIES,
                survival_days=0.0,
                warning="No crops selected. Please choose one or more crops.",
                computed_cycles={},
            )

        known_crops = {crop.name.lower(): crop for crop in self.data_provider.get_crops()}
        selected_lower = [crop.lower().strip() for crop in payload.selected_crops]

        crop_counts: Counter[str] = Counter(selected_lower)

        total_calories = 0.0
        computed_cycles: dict[str, int] = {}

        for name, count in crop_counts.items():
            crop = known_crops.get(name)
            if crop is None:
                # Unknown crop contributes nothing but is reported.
                continue

            cycles = 1
            if payload.duration_days is not None and payload.duration_days > 0:
                cycles = max(1, payload.duration_days // max(1, int(crop.growth_time)))

            calories_from_crop = crop.calorie_yield * count * cycles
            total_calories += calories_from_crop
            computed_cycles[crop.name] = cycles

        daily_consumption = payload.people_count * DEFAULT_DAILY_CALORIES

        survival_days = float(total_calories / daily_consumption) if daily_consumption > 0 else 0.0

        warning = None
        if total_calories <= 0:
            warning = "Selected crops do not match any known crop names; no calories are available."
        elif survival_days < 1:
            warning = "Insufficient calories for even one day at the current population and selection."
        elif survival_days < 14:
            warning = "Low reserve: plan for additional crop types or improved yield."

        return SurvivalDaysResponse(
            total_calories=round(total_calories, 2),
            daily_consumption=float(daily_consumption),
            survival_days=round(survival_days, 2),
            warning=warning,
            computed_cycles=computed_cycles,
        )


survival_service = SurvivalService()
