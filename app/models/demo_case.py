"""Demo scenario models for hackathon presets."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.mission import MissionProfile


class DemoSelection(BaseModel):
    """Optional fixed stack used to make demo runs more predictable."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    selected_crop: str = Field(min_length=1)
    selected_algae: str = Field(min_length=1)
    selected_microbial: str = Field(min_length=1)


class DemoCase(MissionProfile):
    """Named mission preset used in live demos and UI quick starts."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    expected_outcome: str = ""
    selected_stack: DemoSelection | None = None
