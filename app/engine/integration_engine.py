"""Integrated selection engine across crop, algae, and microbial domains."""

from __future__ import annotations

from itertools import product

from app.core.scoring import score_systems
from app.engine.algae_engine import AlgaeEngine
from app.engine.crop_engine import CropEngine
from app.engine.interaction_engine import InteractionEngine
from app.engine.microbial_engine import MicrobialEngine
from app.engine.types import DomainEvaluation, IntegratedResult
from app.models.mission import Environment, MissionProfile
from app.models.system import GrowingSystem
from app.services.data_provider import DataProvider


class IntegrationEngine:
    """Choose the best multi-domain closed-loop configuration."""

    def __init__(
        self,
        provider: DataProvider,
        crop_engine: CropEngine | None = None,
        algae_engine: AlgaeEngine | None = None,
        microbial_engine: MicrobialEngine | None = None,
        interaction_engine: InteractionEngine | None = None,
    ) -> None:
        self.provider = provider
        self.crop_engine = crop_engine or CropEngine()
        self.algae_engine = algae_engine or AlgaeEngine()
        self.microbial_engine = microbial_engine or MicrobialEngine()
        self.interaction_engine = interaction_engine or InteractionEngine()

    def select_configuration(
        self,
        mission: MissionProfile,
        temporary_penalties: dict[str, float] | None = None,
        mission_fit_bias: float = 0.0,
        risk_bias: float = 1.0,
        complexity_bias: float = 1.0,
        loop_bias: float = 1.0,
    ) -> tuple[IntegratedResult, list[DomainEvaluation], GrowingSystem]:
        crops = self.provider.get_crops()
        algae_systems = self.provider.get_algae_systems()
        microbial_systems = self.provider.get_microbial_systems()
        grow_system_rankings = score_systems(self.provider.get_systems(), mission)

        all_results: list[IntegratedResult] = []
        crop_rankings_by_system: dict[str, list[DomainEvaluation]] = {}
        grow_system_lookup = {item.system.name: item.system for item in grow_system_rankings}

        algae_rankings = self.algae_engine.evaluate_all(algae_systems, mission)[:3]
        microbial_rankings = self.microbial_engine.evaluate_all(microbial_systems, mission)[:3]

        for ranked_system in grow_system_rankings:
            grow_system = ranked_system.system
            crop_rankings = self.crop_engine.evaluate_all(
                crops=crops,
                mission=mission,
                grow_system=grow_system,
                temporary_penalties=temporary_penalties,
                mission_fit_bias=mission_fit_bias,
            )
            crop_rankings_by_system[grow_system.name] = crop_rankings

            for crop_eval, algae_eval, microbial_eval in product(
                crop_rankings[:3],
                algae_rankings,
                microbial_rankings,
            ):
                interaction = self.interaction_engine.evaluate(
                    crop=crop_eval,
                    algae=algae_eval,
                    microbial=microbial_eval,
                    grow_system=grow_system,
                    mission=mission,
                )
                total_risk = (
                    crop_eval.risk_score
                    + algae_eval.risk_score
                    + microbial_eval.risk_score
                    + interaction.conflict_score
                ) / 4
                integrated_score = (
                    crop_eval.combined_score
                    + algae_eval.combined_score
                    + microbial_eval.combined_score
                    + interaction.synergy_score
                    + (loop_bias * interaction.loop_closure_bonus)
                    - (complexity_bias * interaction.complexity_penalty)
                    - (0.5 * interaction.resource_overlap)
                    - (risk_bias * total_risk)
                    + (0.20 * ranked_system.score)
                    + self._environment_system_bonus(mission.environment, grow_system.name)
                )

                all_results.append(
                    IntegratedResult(
                        crop=crop_eval,
                        algae=algae_eval,
                        microbial=microbial_eval,
                        interaction=interaction,
                        grow_system_name=grow_system.name,
                        integrated_score=round(integrated_score, 3),
                    )
                )

        best = max(all_results, key=lambda item: item.integrated_score)
        return best, crop_rankings_by_system[best.grow_system_name], grow_system_lookup[best.grow_system_name]

    def _environment_system_bonus(self, environment: Environment, system_name: str) -> float:
        if environment is Environment.MARS:
            if system_name == "hybrid":
                return 0.16
            if system_name == "aeroponic":
                return -0.04
        if environment is Environment.MOON:
            if system_name == "aeroponic":
                return 0.18
            if system_name == "hybrid":
                return 0.03
        if environment is Environment.ISS:
            if system_name == "hydroponic":
                return 0.16
            if system_name == "aeroponic":
                return -0.06
        return 0.0
