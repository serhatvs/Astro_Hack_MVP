"""State models and in-memory storage for mission-aware loop execution."""

from __future__ import annotations

from threading import Lock
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.mission import ConstraintLevel, Duration, Environment, Goal, MissionConstraints


class MissionResources(BaseModel):
    """Current numeric resource margins for a mission."""

    model_config = ConfigDict(extra="forbid")

    water: float = Field(ge=0, le=100)
    energy: float = Field(ge=0, le=100)
    area: float = Field(ge=0, le=100)


class ActiveDomainItem(BaseModel):
    """Runtime-selected domain item tracked inside mission state."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    score: float = Field(ge=0, le=1)
    support_system: str | None = None


class ActiveSystemState(BaseModel):
    """Current active biological portfolio split by domain."""

    model_config = ConfigDict(extra="forbid")

    crops: list[ActiveDomainItem] = Field(default_factory=list)
    algae: list[ActiveDomainItem] = Field(default_factory=list)
    microbial: list[ActiveDomainItem] = Field(default_factory=list)


class SystemMetricsState(BaseModel):
    """Closed-loop health indicators tracked over time."""

    model_config = ConfigDict(extra="forbid")

    oxygen_level: float = Field(ge=0, le=100)
    co2_balance: float = Field(ge=0, le=100)
    food_supply: float = Field(ge=0, le=100)
    nutrient_cycle_efficiency: float = Field(ge=0, le=100)
    risk_level: float = Field(ge=0, le=100)


class MissionHistoryEntry(BaseModel):
    """Single state transition record."""

    model_config = ConfigDict(extra="forbid")

    time: int = Field(ge=0)
    event: str
    summary: str
    selected_crop: str | None = None
    selected_algae: str | None = None
    selected_microbial: str | None = None
    risk_level: float = Field(ge=0, le=100)


class MissionState(BaseModel):
    """Persistent mission state that evolves through loop execution."""

    model_config = ConfigDict(extra="forbid")

    mission_id: str
    environment: Environment
    duration: Duration
    goal: Goal
    constraints: MissionConstraints
    time: int = Field(default=0, ge=0)
    max_weeks: int = Field(default=12, ge=1)
    initial_risk_level: float = Field(default=0, ge=0, le=100)
    end_reason: str | None = None
    resources: MissionResources
    active_system: ActiveSystemState
    system_metrics: SystemMetricsState
    history: list[MissionHistoryEntry] = Field(default_factory=list)


def constraint_to_resource_margin(level: ConstraintLevel) -> float:
    """Convert qualitative constraint level to a numeric available margin."""

    mapping = {
        ConstraintLevel.LOW: 82.0,
        ConstraintLevel.MEDIUM: 62.0,
        ConstraintLevel.HIGH: 38.0,
    }
    return mapping[level]


class MissionStateStore:
    """Simple in-memory mission store for the MVP."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[str, MissionState] = {}

    def create(self, state: MissionState) -> MissionState:
        with self._lock:
            self._states[state.mission_id] = state
        return state

    def new_id(self) -> str:
        return uuid4().hex

    def get(self, mission_id: str) -> MissionState | None:
        with self._lock:
            state = self._states.get(mission_id)
        return state.model_copy(deep=True) if state is not None else None

    def save(self, state: MissionState) -> MissionState:
        with self._lock:
            self._states[state.mission_id] = state
        return state
