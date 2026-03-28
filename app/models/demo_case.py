"""Demo scenario models for hackathon presets."""

from __future__ import annotations

from pydantic import ConfigDict

from app.models.mission import MissionProfile


class DemoCase(MissionProfile):
    """Named mission preset used in live demos and UI quick starts."""

    model_config = ConfigDict(extra="forbid")

    name: str
