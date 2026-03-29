"""Centralized AI service layer with model routing and deterministic fallbacks."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from typing import Any

from app.models.response import (
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
