"""Deterministic-first reasoning loop with optional Gemini critique."""

from __future__ import annotations

from typing import Any

from app.engine.integration_engine import IntegrationEngine
from app.engine.types import IntegratedResult
from app.models.mission import Environment, MissionProfile
from app.models.response import LLMAnalysis
from app.models.system import GrowingSystem
from app.services.data_provider import DataProvider

from .gemini_client import GeminiClient


class ReasoningLoop:
    """Run a bounded critic/refiner pass over deterministic results."""

    def __init__(
        self,
        provider: DataProvider,
        integration_engine: IntegrationEngine | None = None,
        gemini_client: GeminiClient | None = None,
        max_iterations: int = 2,
    ) -> None:
        self.provider = provider
        self.integration_engine = integration_engine or IntegrationEngine(provider)
        self.gemini_client = gemini_client or GeminiClient()
        self.max_iterations = max_iterations

    def run(
        self,
        mission: MissionProfile,
        result: IntegratedResult,
        top_crop_rankings: list[Any],
        grow_system: GrowingSystem,
        temporary_penalties: dict[str, float] | None = None,
        base_biases: dict[str, float] | None = None,
    ) -> tuple[IntegratedResult, list[Any], GrowingSystem, LLMAnalysis]:
        llm_analysis = self._build_rule_based_analysis(mission, result, grow_system)

        payload = self._build_llm_payload(mission, result, grow_system)
        gemini_analysis = self.gemini_client.analyze(payload)
        if gemini_analysis is not None:
            llm_analysis = gemini_analysis

        if self.max_iterations < 2:
            return result, top_crop_rankings, grow_system, llm_analysis

        refinement = self._derive_refinement(llm_analysis, mission, result)
        if refinement is None:
            llm_analysis.second_pass = {
                "decision": "retained",
                "reason": "The deterministic configuration remained acceptable after critique.",
                "applied_adjustments": {},
            }
            llm_analysis.second_pass_decision = llm_analysis.second_pass
            return result, top_crop_rankings, grow_system, llm_analysis

        rerun_result, rerun_crops, rerun_grow_system = self.integration_engine.select_configuration(
            mission=mission,
            temporary_penalties=temporary_penalties,
            risk_bias=(base_biases or {}).get("risk_bias", 1.0) * refinement["risk_bias"],
            complexity_bias=(base_biases or {}).get("complexity_bias", 1.0) * refinement["complexity_bias"],
            loop_bias=(base_biases or {}).get("loop_bias", 1.0) * refinement["loop_bias"],
        )

        if rerun_result.integrated_score > result.integrated_score + 0.02:
            llm_analysis.second_pass = {
                "decision": "refined",
                "reason": "A second deterministic pass improved the integrated score after critique.",
                "applied_adjustments": refinement,
                "selected_configuration": {
                    "crop": rerun_result.crop.candidate.name,
                    "algae": rerun_result.algae.candidate.name,
                    "microbial": rerun_result.microbial.candidate.name,
                    "grow_system": rerun_result.grow_system_name,
                },
            }
            llm_analysis.second_pass_decision = llm_analysis.second_pass
            return rerun_result, rerun_crops, rerun_grow_system, llm_analysis

        llm_analysis.second_pass = {
            "decision": "retained",
            "reason": "The second deterministic pass did not outperform the baseline configuration.",
            "applied_adjustments": refinement,
            "selected_configuration": {
                "crop": result.crop.candidate.name,
                "algae": result.algae.candidate.name,
                "microbial": result.microbial.candidate.name,
                "grow_system": result.grow_system_name,
            },
        }
        llm_analysis.second_pass_decision = llm_analysis.second_pass
        return result, top_crop_rankings, grow_system, llm_analysis

    def _build_llm_payload(
        self,
        mission: MissionProfile,
        result: IntegratedResult,
        grow_system: GrowingSystem,
    ) -> dict[str, Any]:
        return {
            "mission": mission.model_dump(mode="json"),
            "selected_systems": {
                "crop": result.crop.candidate.name,
                "algae": result.algae.candidate.name,
                "microbial": result.microbial.candidate.name,
                "grow_system": grow_system.name,
            },
            "scores": {
                "crop": {
                    "domain_score": result.crop.domain_score,
                    "mission_fit_score": result.crop.mission_fit_score,
                    "risk_score": result.crop.risk_score,
                },
                "algae": {
                    "domain_score": result.algae.domain_score,
                    "mission_fit_score": result.algae.mission_fit_score,
                    "risk_score": result.algae.risk_score,
                },
                "microbial": {
                    "domain_score": result.microbial.domain_score,
                    "mission_fit_score": result.microbial.mission_fit_score,
                    "risk_score": result.microbial.risk_score,
                },
                "interaction": {
                    "synergy_score": result.interaction.synergy_score,
                    "conflict_score": result.interaction.conflict_score,
                    "complexity_penalty": result.interaction.complexity_penalty,
                    "resource_overlap": result.interaction.resource_overlap,
                    "loop_closure_bonus": result.interaction.loop_closure_bonus,
                },
                "integrated_score": result.integrated_score,
            },
            "notes": {
                "crop": result.crop.notes,
                "algae": result.algae.notes,
                "microbial": result.microbial.notes,
                "interaction": result.interaction.notes,
            },
        }

    def _build_rule_based_analysis(
        self,
        mission: MissionProfile,
        result: IntegratedResult,
        grow_system: GrowingSystem,
    ) -> LLMAnalysis:
        weaknesses: list[str] = []
        improvements: list[str] = []

        if result.interaction.complexity_penalty >= 0.58:
            weaknesses.append("Integrated maintenance complexity is elevated across domains.")
            improvements.append("Bias the next pass toward lower-complexity algae or microbial support.")
        if result.interaction.loop_closure_bonus <= 0.62:
            weaknesses.append("Loop closure is useful but not yet deeply redundant.")
            improvements.append("Favor stronger microbial recycling or higher CO2 utilization on the next pass.")
        if result.microbial.risk_score >= 0.55:
            weaknesses.append("Microbial contamination or reactor dependency remains a weak link.")
            improvements.append("Prefer a lower-contamination microbial path for the next pass.")
        if mission.environment is Environment.ISS and grow_system.maintenance >= 45:
            weaknesses.append("The selected grow system may ask too much of ISS crew time.")
            improvements.append("Prefer the simpler hydroponic posture when scores are close.")

        if not weaknesses:
            weaknesses.append("No major weak link dominates the current loop design.")
            improvements.append("Hold the current configuration and monitor resource drift over time.")

        alternative = {
            "crop": result.crop.candidate.name,
            "algae": "chlorella_panel" if result.algae.candidate.name != "chlorella_panel" else result.algae.candidate.name,
            "microbial": "biofilm_polisher" if result.microbial.candidate.name != "biofilm_polisher" else result.microbial.candidate.name,
            "grow_system": "hydroponic" if mission.environment is Environment.ISS else result.grow_system_name,
        }

        summary = (
            f"The deterministic engine selected {result.crop.candidate.name}, {result.algae.candidate.name}, and "
            f"{result.microbial.candidate.name} with {grow_system.name} because that bundle balances domain scores, "
            "loop closure, and mission fit better than nearby alternatives."
        )

        return LLMAnalysis(
            reasoning_summary=summary,
            weaknesses=weaknesses,
            improvements=improvements,
            improvement_suggestions=improvements,
            alternative=alternative,
            alternative_configuration=alternative,
            second_pass={},
            second_pass_decision={},
        )

    def _derive_refinement(
        self,
        llm_analysis: LLMAnalysis,
        mission: MissionProfile,
        result: IntegratedResult,
    ) -> dict[str, float] | None:
        text = " ".join([llm_analysis.reasoning_summary, *llm_analysis.weaknesses, *llm_analysis.improvements]).lower()
        risk_bias = 1.0
        complexity_bias = 1.0
        loop_bias = 1.0
        changed = False

        if "contamination" in text or result.microbial.risk_score >= 0.55:
            risk_bias = 1.15
            changed = True
        if "complex" in text or "maintenance" in text or result.interaction.complexity_penalty >= 0.58:
            complexity_bias = 1.15 if mission.environment is Environment.ISS else 1.10
            changed = True
        if "loop closure" in text or result.interaction.loop_closure_bonus <= 0.62:
            loop_bias = 1.12
            changed = True

        if not changed:
            return None

        return {
            "risk_bias": risk_bias,
            "complexity_bias": complexity_bias,
            "loop_bias": loop_bias,
        }
