"""Centralized AI service layer with model routing and deterministic fallbacks."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from hashlib import sha256
from threading import Lock
from typing import Any

from app.models.response import (
    GeminiNarrative,
    UIEnhancedNarrative,
)

from .gemini_client import GeminiClient
from .safe_ai import safe_ai_call


logger = logging.getLogger(__name__)


class AIService:
    """Route low-frequency AI tasks to the appropriate Gemini model."""

    def __init__(self, gemini_client: GeminiClient | None = None) -> None:
        self.gemini_client = gemini_client or GeminiClient()
        self.summary_model = os.getenv("GEMINI_MODEL_SUMMARY_POLISH", "gemini-2.5-flash-lite")
        self.explanation_model = os.getenv("GEMINI_MODEL_EXPLANATION", "gemini-2.5-flash")
        self.recommendation_timeout_seconds = self._read_timeout_seconds(
            "AI_RECOMMENDATION_TIMEOUT_SECONDS",
            fallback_env="AI_CALL_TIMEOUT_SECONDS",
            default_seconds=20.0,
        )
        self.summary_timeout_seconds = self._read_timeout_seconds(
            "AI_SUMMARY_TIMEOUT_SECONDS",
            fallback_env="AI_CALL_TIMEOUT_SECONDS",
            default_seconds=8.0,
        )
        self._cache_lock = Lock()
        self._recommendation_cache: dict[str, GeminiNarrative] = {}
        self._summary_cache: dict[str, UIEnhancedNarrative] = {}

    def generate_recommendation_explanation(
        self,
        payload: Mapping[str, Any],
        *,
        fallback: GeminiNarrative,
        use_ai: bool = True,
    ) -> GeminiNarrative:
        """Generate the standard recommendation narrative with optional cheap UI polish."""

        cache_key = self._cache_key(
            "recommendation_explanation",
            {
                "model": self.explanation_model,
                "use_ai": use_ai,
                "payload": dict(payload),
            },
        )
        cached_narrative = self._get_recommendation_cache(cache_key)
        if cached_narrative is not None:
            logger.info("AI cache hit for recommendation explanation.")
            return cached_narrative

        narrative = safe_ai_call(
            lambda: self.gemini_client.analyze(
                dict(payload),
                model=self.explanation_model,
                use_llm=use_ai,
                fallback_ui=fallback.ui_layer.model_dump(mode="json"),
                default_reasoning=fallback.debug_layer.reasoning_summary,
            ),
            fallback=fallback.model_copy(deep=True),
            task_label="recommendation_explanation",
            timeout_seconds=self.recommendation_timeout_seconds,
            logger=logger,
        )
        if not narrative.debug_layer.reasoning_summary.endswith(" -gemini"):
            logger.info("AIService falling back to deterministic recommendation narrative.")
            return narrative

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
        narrative = narrative.model_copy(update={"ui_layer": polished_ui})
        self._set_recommendation_cache(cache_key, narrative)
        return narrative

    def generate_summary_polish(
        self,
        payload: Mapping[str, Any],
        *,
        fallback_ui: UIEnhancedNarrative,
        use_ai: bool = True,
    ) -> UIEnhancedNarrative:
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
        cache_key = self._cache_key(
            "summary_polish",
            {
                "model": self.summary_model,
                "use_ai": use_ai,
                "payload": dict(payload),
            },
        )
        cached_summary = self._get_summary_cache(cache_key)
        if cached_summary is not None:
            logger.info("AI cache hit for summary polish.")
            return cached_summary

        polished_ui = safe_ai_call(
            lambda: self._generate_summary_ui(prompt, fallback_ui, use_ai),
            fallback=fallback_ui.model_copy(deep=True),
            task_label="summary_polish",
            timeout_seconds=self.summary_timeout_seconds,
            logger=logger,
        )
        if polished_ui.model_dump(mode="json") != fallback_ui.model_dump(mode="json"):
            self._set_summary_cache(cache_key, polished_ui)
        return polished_ui

    def _generate_summary_ui(
        self,
        prompt: str,
        fallback_ui: UIEnhancedNarrative,
        use_ai: bool,
    ) -> UIEnhancedNarrative | None:
        parsed = self.gemini_client.generate_json(
            prompt,
            model=self.summary_model,
            use_llm=use_ai,
            task_label="summary_polish",
            response_schema={
                "type": "object",
                "properties": {
                    "crop_note": {"type": "string"},
                    "algae_note": {"type": "string"},
                    "microbial_note": {"type": "string"},
                    "executive_summary": {"type": "string"},
                    "adaptation_summary": {"type": "string"},
                },
                "required": [
                    "crop_note",
                    "algae_note",
                    "microbial_note",
                    "executive_summary",
                    "adaptation_summary",
                ],
            },
        )
        if parsed is None:
            return None
        return UIEnhancedNarrative.from_payload(parsed, defaults=fallback_ui.model_dump(mode="json"))

    def _cache_key(self, namespace: str, payload: Mapping[str, Any]) -> str:
        serialized = json.dumps(dict(payload), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return f"{namespace}:{sha256(serialized.encode('utf-8')).hexdigest()}"

    def _get_recommendation_cache(self, cache_key: str) -> GeminiNarrative | None:
        with self._cache_lock:
            cached = self._recommendation_cache.get(cache_key)
            return cached.model_copy(deep=True) if cached is not None else None

    def _set_recommendation_cache(self, cache_key: str, narrative: GeminiNarrative) -> None:
        with self._cache_lock:
            self._recommendation_cache[cache_key] = narrative.model_copy(deep=True)

    def _get_summary_cache(self, cache_key: str) -> UIEnhancedNarrative | None:
        with self._cache_lock:
            cached = self._summary_cache.get(cache_key)
            return cached.model_copy(deep=True) if cached is not None else None

    def _set_summary_cache(self, cache_key: str, narrative: UIEnhancedNarrative) -> None:
        with self._cache_lock:
            self._summary_cache[cache_key] = narrative.model_copy(deep=True)

    def _read_timeout_seconds(
        self,
        env_name: str,
        *,
        fallback_env: str | None,
        default_seconds: float,
    ) -> float:
        raw_value = os.getenv(env_name)
        if raw_value is None and fallback_env:
            raw_value = os.getenv(fallback_env)
        if raw_value is None:
            return default_seconds
        try:
            return max(1.0, float(raw_value))
        except ValueError:
            logger.warning("Invalid %s=%s; using %.1f seconds.", env_name, raw_value, default_seconds)
            return default_seconds
