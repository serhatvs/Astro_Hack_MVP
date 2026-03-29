"""Mission-step request models and state transition helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.mission_state import MissionResources, MissionState
from app.models.mission import Duration

SIMULATION_STEP_WEEKS = 1
SIMULATION_MAX_REQUEST_STEP = 48


def max_weeks_for_duration(duration: Duration) -> int:
    mapping = {
        Duration.SHORT: 12,
        Duration.MEDIUM: 24,
        Duration.LONG: 48,
    }
    return mapping[duration]


class MissionEvents(BaseModel):
    """Optional environmental events applied during a mission step."""

    model_config = ConfigDict(extra="forbid")

    water_drop: float | None = Field(default=None, ge=0, le=100)
    energy_drop: float | None = Field(default=None, ge=0, le=100)
    contamination: float | None = Field(default=None, ge=0, le=100)
    yield_variation: float | None = Field(default=None, ge=-100, le=100)


class MissionStepRequest(BaseModel):
    """Stateful weekly mission-step request."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mission_id: str = Field(min_length=1)
    time_step: int = Field(default=SIMULATION_STEP_WEEKS, gt=0, le=SIMULATION_MAX_REQUEST_STEP)
    events: MissionEvents | None = None


def apply_resource_events(resources: MissionResources, events: MissionEvents | None) -> MissionResources:
    """Apply event-driven resource deltas to the numeric mission margins."""

    if events is None:
        return resources.model_copy(deep=True)

    updated = resources.model_copy(deep=True)
    if events.water_drop is not None:
        updated.water = max(0.0, updated.water - events.water_drop)
    if events.energy_drop is not None:
        updated.energy = max(0.0, updated.energy - events.energy_drop)
    return updated


def advance_state_time(state: MissionState, time_step: int) -> MissionState:
    """Advance the mission time in weekly units without mutating the input state."""

    return state.model_copy(update={"time": state.time + time_step}, deep=True)
