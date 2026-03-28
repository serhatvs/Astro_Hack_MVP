from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SurvivalDaysRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    people_count: int = Field(..., ge=1, description="Number of crew members to support")
    selected_crops: list[str] = Field(default_factory=list, description="List of crop names selected for production")
    duration_days: int | None = Field(None, ge=1, description="Optional mission duration to scale crop cycles")


class SurvivalDaysResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_calories: float
    daily_consumption: float
    survival_days: float
    warning: str | None = None
    computed_cycles: dict[str, int] = Field(default_factory=dict)
