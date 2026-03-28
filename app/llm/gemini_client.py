"""Optional Gemini client used as a critic over deterministic results."""

from __future__ import annotations

import json
import os
from typing import Any

from app.models.response import LLMAnalysis


class GeminiClient:
    """Thin optional wrapper around the Google GenAI SDK."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        self.model = model
        self.api_key = os.getenv("GEMINI_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def analyze(self, payload: dict[str, Any]) -> LLMAnalysis | None:
        """Ask Gemini to critique a deterministic recommendation.

        The app remains deterministic-first: if Gemini is unavailable, missing,
        or returns malformed output, callers should fall back to rule-based analysis.
        """

        if not self.is_available():
            return None

        try:
            from google import genai
        except ImportError:
            return None

        prompt = (
            "You are a closed-loop mission systems critic. Review the deterministic selection payload and "
            "return strict JSON with keys reasoning_summary, weaknesses, improvements, alternative, and second_pass. "
            "Do not add markdown. Keep weaknesses and improvements concise. "
            f"Payload: {json.dumps(payload, ensure_ascii=True)}"
        )

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            text = getattr(response, "text", "") or ""
            if not text:
                return None
            parsed = json.loads(text)
        except Exception:
            return None

        return LLMAnalysis.model_validate(
            {
                "reasoning_summary": parsed.get("reasoning_summary", ""),
                "weaknesses": parsed.get("weaknesses", []),
                "improvements": parsed.get("improvements", parsed.get("improvement_suggestions", [])),
                "improvement_suggestions": parsed.get(
                    "improvement_suggestions",
                    parsed.get("improvements", []),
                ),
                "alternative": parsed.get("alternative", parsed.get("alternative_configuration", {})),
                "alternative_configuration": parsed.get(
                    "alternative_configuration",
                    parsed.get("alternative", {}),
                ),
                "second_pass": parsed.get("second_pass", parsed.get("second_pass_decision", {})),
                "second_pass_decision": parsed.get(
                    "second_pass_decision",
                    parsed.get("second_pass", {}),
                ),
            }
        )
