"""Integrated selection engine across crop, algae, and microbial domains."""

from __future__ import annotations

from itertools import product

from app.core.scoring import score_systems
from app.engine.algae_engine import AlgaeEngine
from app.engine.crop_engine import CropEngine
from app.engine.interaction_engine import InteractionEngine
from app.engine.microbial_engine import MicrobialEngine
from app.engine.types import DomainEvaluation, DomainRankingSet, IntegratedResult
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
    ) -> tuple[IntegratedResult, DomainRankingSet, GrowingSystem]:
        crops = self.provider.get_crops()
        algae_systems = self.provider.get_algae_systems()
        microbial_systems = self.provider.get_microbial_systems()
        grow_system_rankings = score_systems(self.provider.get_systems(), mission)

        all_results: list[IntegratedResult] = []
        crop_rankings_by_system: dict[str, list[DomainEvaluation]] = {}
        grow_system_lookup = {item.system.name: item.system for item in grow_system_rankings}

        algae_rankings = self.algae_engine.evaluate_all(algae_systems, mission)
        microbial_rankings = self.microbial_engine.evaluate_all(microbial_systems, mission)

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
                algae_rankings[:3],
                microbial_rankings[:3],
            ):
                all_results.append(
                    self._build_integrated_result(
                        crop_eval=crop_eval,
                        algae_eval=algae_eval,
                        microbial_eval=microbial_eval,
                        grow_system=grow_system,
                        mission=mission,
                        ranked_system_score=ranked_system.score,
                        risk_bias=risk_bias,
                        complexity_bias=complexity_bias,
                        loop_bias=loop_bias,
                    )
                )

        best = max(all_results, key=lambda item: item.integrated_score)
        return (
            best,
            DomainRankingSet(
                crop=crop_rankings_by_system[best.grow_system_name],
                algae=algae_rankings,
                microbial=microbial_rankings,
            ),
            grow_system_lookup[best.grow_system_name],
        )

    def evaluate_selected_configuration(
        self,
        mission: MissionProfile,
        selected_crop_name: str,
        selected_algae_name: str,
        selected_microbial_name: str,
        temporary_penalties: dict[str, float] | None = None,
        mission_fit_bias: float = 0.0,
        risk_bias: float = 1.0,
        complexity_bias: float = 1.0,
        loop_bias: float = 1.0,
    ) -> tuple[IntegratedResult, DomainRankingSet, GrowingSystem]:
        """Score an explicit crop/algae/microbial stack without changing the chosen domains."""

        crops = self.provider.get_crops()
        algae_systems = self.provider.get_algae_systems()
        microbial_systems = self.provider.get_microbial_systems()
        grow_system_rankings = score_systems(self.provider.get_systems(), mission)

        grow_system_lookup = {item.system.name: item.system for item in grow_system_rankings}
        algae_rankings = self.algae_engine.evaluate_all(algae_systems, mission)
        microbial_rankings = self.microbial_engine.evaluate_all(microbial_systems, mission)
        algae_eval = self._find_named_evaluation(algae_rankings, selected_algae_name, "algae")
        microbial_eval = self._find_named_evaluation(microbial_rankings, selected_microbial_name, "microbial")

        crop_rankings_by_system: dict[str, list[DomainEvaluation]] = {}
        candidate_results: list[IntegratedResult] = []

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
            crop_eval = self._find_named_evaluation(
                crop_rankings,
                selected_crop_name,
                "crop",
                allow_missing=True,
            )
            if crop_eval is None:
                continue

            candidate_results.append(
                self._build_integrated_result(
                    crop_eval=crop_eval,
                    algae_eval=algae_eval,
                    microbial_eval=microbial_eval,
                    grow_system=grow_system,
                    mission=mission,
                    ranked_system_score=ranked_system.score,
                    risk_bias=risk_bias,
                    complexity_bias=complexity_bias,
                    loop_bias=loop_bias,
                )
            )

        if not candidate_results:
            raise ValueError(
                f"Selected crop '{selected_crop_name}' is not compatible with any available plant support system."
            )

        best = max(candidate_results, key=lambda item: item.integrated_score)
        return (
            best,
            DomainRankingSet(
                crop=crop_rankings_by_system[best.grow_system_name],
                algae=algae_rankings,
                microbial=microbial_rankings,
            ),
            grow_system_lookup[best.grow_system_name],
        )

    def _build_integrated_result(
        self,
        *,
        crop_eval: DomainEvaluation,
        algae_eval: DomainEvaluation,
        microbial_eval: DomainEvaluation,
        grow_system: GrowingSystem,
        mission: MissionProfile,
        ranked_system_score: float,
        risk_bias: float,
        complexity_bias: float,
        loop_bias: float,
    ) -> IntegratedResult:
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
            + (0.20 * ranked_system_score)
            + self._environment_system_bonus(mission.environment, grow_system.name)
        )
        return IntegratedResult(
            crop=crop_eval,
            algae=algae_eval,
            microbial=microbial_eval,
            interaction=interaction,
            grow_system_name=grow_system.name,
            integrated_score=round(integrated_score, 3),
        )

    def _find_named_evaluation(
        self,
        evaluations: list[DomainEvaluation],
        candidate_name: str,
        domain_type: str,
        *,
        allow_missing: bool = False,
    ) -> DomainEvaluation | None:
        for evaluation in evaluations:
            if evaluation.candidate.name == candidate_name:
                return evaluation
        if allow_missing:
            return None
        raise ValueError(f"Selected {domain_type} '{candidate_name}' was not found in the current candidate pool.")

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
