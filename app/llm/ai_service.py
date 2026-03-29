"""Centralized AI service layer with model routing and deterministic fallbacks."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from typing import Any

from app.models.response import (
    AIInsight,
    AIInsightKind,
    AIInsightRequest,
    GeminiNarrative,
    UIEnhancedNarrative,
)

from .gemini_client import GeminiClient


logger = logging.getLogger(__name__)


class AIService:
    """Route low-frequency AI tasks to the appropriate Gemini model."""

    def __init__(self, gemini_client: GeminiClient | None = None) -> None:
        self.gemini_client = gemini_client or GeminiClient()
        self.summary_model = os.getenv("GEMINI_MODEL_SUMMARY_POLISH", "gemini-2.5-flash-lite")
        self.explanation_model = os.getenv("GEMINI_MODEL_EXPLANATION", "gemini-2.5-flash")
        self.deep_analysis_model = os.getenv("GEMINI_MODEL_DEEP_ANALYSIS", "gemini-2.5-pro")
        self.premium_model = os.getenv("GEMINI_MODEL_PREMIUM", "gemini-3.1-pro-preview")

    def generate_recommendation_explanation(
        self,
        payload: Mapping[str, Any],
        *,
        fallback: GeminiNarrative,
        use_ai: bool = True,
    ) -> GeminiNarrative:
        """Generate the standard recommendation narrative with optional cheap UI polish."""

        narrative = self.gemini_client.analyze(
            dict(payload),
            model=self.explanation_model,
            use_llm=use_ai,
            fallback_ui=fallback.ui_layer.model_dump(mode="json"),
            default_reasoning=fallback.debug_layer.reasoning_summary,
        )
        if narrative is None:
            logger.info("AIService falling back to deterministic recommendation narrative.")
            return fallback

        polished_ui = self.generate_summary_polish(
            {
                "source": payload.get("request_context", {}).get("source"),
                "selected_roles": payload.get("selected_roles", {}),
                "deterministic_explanations": payload.get("deterministic_explanations", {}),
                "current_ui": narrative.ui_layer.model_dump(mode="json"),
                "deltas": payload.get("deltas", {}),
            },
            fallback_ui=narrative.ui_layer,
            use_ai=use_ai,
        )
        if polished_ui is not None:
            narrative = narrative.model_copy(update={"ui_layer": polished_ui})
        return narrative

    def generate_summary_polish(
        self,
        payload: Mapping[str, Any],
        *,
        fallback_ui: UIEnhancedNarrative,
        use_ai: bool = True,
    ) -> UIEnhancedNarrative | None:
        """Use the lightest model to polish short UI-facing text."""

        schema = {
            "crop_note": "string",
            "algae_note": "string",
            "microbial_note": "string",
            "executive_summary": "string",
            "adaptation_summary": "string",
        }
        prompt = (
            "You are a low-cost UI summary polisher for a deterministic mission-planning system. "
            "Rewrite short user-facing summaries for clarity and readability. Preserve the technical truth, "
            "do not invent claims, keep the text concise, and avoid repetition. "
            "Return ONLY valid JSON with all keys present.\n\n"
            f"Expected JSON schema:\n{json.dumps(schema, ensure_ascii=True, indent=2)}\n\n"
            f"Payload:\n{json.dumps(dict(payload), ensure_ascii=True, indent=2)}"
        )
        parsed = self.gemini_client.generate_json(
            prompt,
            model=self.summary_model,
            use_llm=use_ai,
            task_label="summary_polish",
        )
        if parsed is None:
            return None
        return UIEnhancedNarrative.from_payload(parsed, defaults=fallback_ui.model_dump(mode="json"))

    def generate_simulation_intro_explanation(
        self,
        request: AIInsightRequest,
        *,
        use_ai: bool = True,
    ) -> AIInsight:
        return self._generate_insight(
            kind=AIInsightKind.SIMULATION_INTRO,
            request=request,
            model=self.explanation_model,
            model_tier="flash",
            use_ai=use_ai,
        )

    def generate_simulation_end_explanation(
        self,
        request: AIInsightRequest,
        *,
        use_ai: bool = True,
    ) -> AIInsight:
        return self._generate_insight(
            kind=AIInsightKind.SIMULATION_END,
            request=request,
            model=self.explanation_model,
            model_tier="flash",
            use_ai=use_ai,
        )

    def generate_deep_analysis(
        self,
        request: AIInsightRequest,
        *,
        use_ai: bool = True,
        premium: bool = False,
    ) -> AIInsight:
        return self._generate_insight(
            kind=AIInsightKind.DEEP_ANALYSIS,
            request=request,
            model=self.premium_model if premium else self.deep_analysis_model,
            model_tier="preview" if premium else "pro",
            use_ai=use_ai,
        )

    def _generate_insight(
        self,
        *,
        kind: AIInsightKind,
        request: AIInsightRequest,
        model: str,
        model_tier: str,
        use_ai: bool,
    ) -> AIInsight:
        fallback = self._build_fallback_insight(kind, request)
        if not use_ai:
            logger.info("AIService blocked %s by use_ai=False; using deterministic fallback.", kind.value)
            return fallback

        schema = {
            "title": "string",
            "summary": "string",
            "highlights": ["string"],
        }
        prompt = (
            "You are an explanation layer on top of a deterministic ecosystem mission engine. "
            "The deterministic selection and simulation state are authoritative. "
            "You must NOT choose systems, rescore systems, change risk, or modify simulation behavior. "
            "Explain the provided state clearly for users. Keep the output concise, factual, and grounded. "
            "Return ONLY valid JSON with all keys present.\n\n"
            f"Task kind: {kind.value}\n"
            f"Expected JSON schema:\n{json.dumps(schema, ensure_ascii=True, indent=2)}\n\n"
            f"Payload:\n{json.dumps(self._serialize_request(request), ensure_ascii=True, indent=2)}"
        )
        parsed = self.gemini_client.generate_json(
            prompt,
            model=model,
            use_llm=use_ai,
            task_label=kind.value,
        )
        if parsed is None:
            logger.info("AIService using deterministic fallback for %s.", kind.value)
            return fallback

        return AIInsight.from_payload(
            kind=kind,
            payload=parsed,
            defaults=fallback.model_dump(mode="json"),
            generated_by_ai=True,
            model_tier=model_tier,
            model_name=model,
        )

    def _serialize_request(self, request: AIInsightRequest) -> dict[str, Any]:
        payload = request.model_dump(mode="json")
        return payload

    def _build_fallback_insight(self, kind: AIInsightKind, request: AIInsightRequest) -> AIInsight:
        mission_state = request.mission_state
        selected = request.selected_system
        crop_name = selected.crop.name
        algae_name = selected.algae.name
        microbial_name = selected.microbial.name
        executive_summary = request.ui_enhanced.executive_summary if request.ui_enhanced else ""
        adaptation_summary = request.adaptation_summary or (request.ui_enhanced.adaptation_summary if request.ui_enhanced else "")
        reasoning = request.llm_analysis.reasoning_summary if request.llm_analysis else ""
        week_label = f"Week {mission_state.time}" if mission_state is not None else "Current state"

        if kind is AIInsightKind.SIMULATION_INTRO:
            return AIInsight(
                kind=kind,
                title="AI Insight: Expected System Behavior",
                summary=(
                    f"{crop_name}, {algae_name}, and {microbial_name} start from a deterministic baseline. "
                    f"The crop layer carries food production, the algae layer supports atmospheric balance, "
                    f"and the microbial layer supports loop closure over the planned mission horizon."
                ),
                highlights=[
                    executive_summary or "Deterministic stack selection is active.",
                    f"Starting risk: {mission_state.system_metrics.risk_level:.2f}%." if mission_state else "Mission state is available.",
                    f"Planned horizon: {mission_state.max_weeks} weeks." if mission_state else "Mission horizon is set by duration.",
                ],
                generated_by_ai=False,
                model_tier="deterministic",
                model_name="",
            )

        if kind is AIInsightKind.SIMULATION_END:
            end_reason = mission_state.end_reason if mission_state is not None else None
            return AIInsight(
                kind=kind,
                title="AI Insight: Simulation Outcome",
                summary=(
                    adaptation_summary
                    or f"{week_label} closed with a deterministic outcome of {end_reason or 'system transition'}."
                ),
                highlights=[
                    f"Final risk: {mission_state.system_metrics.risk_level:.2f}%." if mission_state else "Final risk not available.",
                    f"End reason: {end_reason or 'not provided'}." if mission_state else "End reason unavailable.",
                    reasoning or "Deterministic end-state analysis remains active.",
                ],
                generated_by_ai=False,
                model_tier="deterministic",
                model_name="",
            )

        return AIInsight(
            kind=kind,
            title="AI Insight: Deeper System Review",
            summary=(
                f"The deterministic stack remains {crop_name}, {algae_name}, and {microbial_name}. "
                "Requesting a deeper critique is optional and does not change the simulation outcome."
            ),
            highlights=[
                request.explanations.tradeoffs if request.explanations else "Tradeoffs remain available from deterministic scoring.",
                request.explanations.weak_points if request.explanations else "Weak points remain available from deterministic scoring.",
                reasoning or "Detailed fallback analysis remains deterministic.",
            ],
            generated_by_ai=False,
            model_tier="deterministic",
            model_name="",
        )
