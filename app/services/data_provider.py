"""Data provider abstraction for JSON-backed MVP datasets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.algae import AlgaeSystem
from app.models.crop import Crop
from app.models.demo_case import DemoCase
from app.models.microbial import MicrobialSystem
from app.models.system import GrowingSystem
from app.utils.loaders import DATA_DIR, load_json_file


class DataProvider(ABC):
    """Abstract provider interface so JSON can later be swapped for SQL."""

    @abstractmethod
    def get_crops(self) -> list[Crop]:
        """Return crop records."""

    @abstractmethod
    def get_systems(self) -> list[GrowingSystem]:
        """Return growing system records."""

    @abstractmethod
    def get_algae_systems(self) -> list[AlgaeSystem]:
        """Return algae system records."""

    @abstractmethod
    def get_microbial_systems(self) -> list[MicrobialSystem]:
        """Return microbial system records."""

    @abstractmethod
    def get_demo_cases(self) -> list[DemoCase]:
        """Return named demo mission presets."""


class JSONDataProvider(DataProvider):
    """JSON-backed provider for the hackathon MVP."""

    def __init__(
        self,
        crops_path: Path | None = None,
        systems_path: Path | None = None,
        algae_path: Path | None = None,
        microbial_path: Path | None = None,
        demo_cases_path: Path | None = None,
    ) -> None:
        self.crops_path = crops_path or (DATA_DIR / "crops.json")
        self.systems_path = systems_path or (DATA_DIR / "systems.json")
        self.algae_path = algae_path or (DATA_DIR / "algae.json")
        self.microbial_path = microbial_path or (DATA_DIR / "microbial.json")
        self.demo_cases_path = demo_cases_path or (DATA_DIR / "demo_cases.json")
        self._crops: list[Crop] | None = None
        self._systems: list[GrowingSystem] | None = None
        self._algae_systems: list[AlgaeSystem] | None = None
        self._microbial_systems: list[MicrobialSystem] | None = None
        self._demo_cases: list[DemoCase] | None = None

    def get_crops(self) -> list[Crop]:
        if self._crops is None:
            records = load_json_file(self.crops_path)
            self._crops = [Crop.model_validate(record) for record in records]
        return list(self._crops)

    def get_systems(self) -> list[GrowingSystem]:
        if self._systems is None:
            records = load_json_file(self.systems_path)
            self._systems = [GrowingSystem.model_validate(record) for record in records]
        return list(self._systems)

    def get_algae_systems(self) -> list[AlgaeSystem]:
        if self._algae_systems is None:
            records = load_json_file(self.algae_path)
            self._algae_systems = [AlgaeSystem.model_validate(record) for record in records]
        return list(self._algae_systems)

    def get_microbial_systems(self) -> list[MicrobialSystem]:
        if self._microbial_systems is None:
            records = load_json_file(self.microbial_path)
            self._microbial_systems = [MicrobialSystem.model_validate(record) for record in records]
        return list(self._microbial_systems)

    def get_demo_cases(self) -> list[DemoCase]:
        if self._demo_cases is None:
            records = load_json_file(self.demo_cases_path)
            self._demo_cases = [DemoCase.model_validate(record) for record in records]
        return list(self._demo_cases)
