from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models.choice import CropChoice, CropChoiceCreate
from app.models.mission import ConstraintLevel, Duration, Environment, Goal, MissionConstraints, MissionProfile
from app.services.data_provider import JSONDataProvider
from app.services.recommender import get_default_engine
from app.utils.loaders import DATA_DIR


CHOICES_STORE_PATH = DATA_DIR / "choices.json"


class ChoiceService:
    """Simple MVP user crop selection store."""

    def __init__(self, choices_path: Path | None = None) -> None:
        self.choices_path = choices_path or CHOICES_STORE_PATH
        self._choices: list[CropChoice] = []
        self._load_choices()

    def _load_choices(self) -> None:
        try:
            raw = self._read_json(self.choices_path)
            self._choices = [CropChoice.model_validate(item) for item in raw]
        except FileNotFoundError:
            self._choices = []

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save_choices(self) -> None:
        self.choices_path.parent.mkdir(parents=True, exist_ok=True)
        with self.choices_path.open("w", encoding="utf-8") as f:
            json.dump([choice.model_dump() for choice in self._choices], f, ensure_ascii=False, indent=2)

    def create_choice(self, user_id: str, payload: CropChoiceCreate) -> CropChoice:
        choice = CropChoice(
            id=str(uuid4()),
            user_id=user_id,
            crop_name=payload.crop_name,
            environment=payload.environment,
            timestamp=datetime.utcnow(),
        )
        self._choices.append(choice)
        self._save_choices()
        return choice

    def list_choices(self, user_id: str) -> list[CropChoice]:
        return [choice for choice in self._choices if choice.user_id == user_id]

    def get_latest_choice(self, user_id: str) -> CropChoice | None:
        user_choices = self.list_choices(user_id)
        if not user_choices:
            return None
        return sorted(user_choices, key=lambda c: c.timestamp, reverse=True)[0]

    def validate_choice_against_recommendations(self, crop_name: str, environment: str | None = None) -> bool:
        if environment is None:
            environment = Environment.MARS.value

        try:
            mission = MissionProfile(
                environment=Environment(environment),
                duration=Duration.MEDIUM,
                constraints=MissionConstraints(
                    water=ConstraintLevel.MEDIUM,
                    energy=ConstraintLevel.MEDIUM,
                    area=ConstraintLevel.MEDIUM,
                ),
                goal=Goal.BALANCED,
            )
        except ValueError:
            return False

        recommendation = get_default_engine().recommend(mission, persist_state=False)
        top_names = {crop.name.lower() for crop in recommendation.top_crops}
        return crop_name.lower() in top_names


choice_service = ChoiceService()
