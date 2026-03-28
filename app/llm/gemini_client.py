"""Optional Gemini client used as a critic over deterministic results."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.models.response import LLMAnalysis


logger = logging.getLogger(__name__)


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
            logger.info("Gemini disabled: GEMINI_API_KEY is not set.")
            return None

        try:
            from google import genai
        except ImportError:
            logger.warning("Gemini enabled but google.genai is unavailable; using deterministic fallback.")
            return None

        prompt = self._build_prompt(payload)

        try:
            logger.info("Gemini enabled: sending critic request.")
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            text = getattr(response, "text", "") or ""
        except Exception:
            logger.warning("Gemini request failed; using deterministic fallback.", exc_info=True)
            return None

        if not text.strip():
            logger.warning("Gemini returned an empty response; using deterministic fallback.")
            return None

        extracted_json = self._extract_json_text(text)
        if extracted_json is None:
            logger.warning("Gemini response did not contain a JSON object; using deterministic fallback.")
            return None

        try:
            parsed = json.loads(extracted_json)
        except json.JSONDecodeError:
            logger.warning("Gemini JSON parsing failed; using deterministic fallback.", exc_info=True)
            return None

        if not isinstance(parsed, dict):
            logger.warning("Gemini returned non-object JSON; using deterministic fallback.")
            return None

        logger.info("Gemini analysis succeeded.")
        return LLMAnalysis.from_payload(
            parsed,
            default_reasoning="Gemini returned incomplete analysis; deterministic fallback remains active.",
        )

    def _build_prompt(self, payload: dict[str, Any]) -> str:
        schema = {
            "reasoning_summary": "string",
            "weaknesses": ["string"],
            "improvements": ["string"],
            "alternative": {
                "crop": "string|null",
                "algae": "string|null",
                "microbial": "string|null",
                "grow_system": "string|null",
                "rationale": "string",
            },
            "second_pass": {
                "decision": "retain|refine",
                "rationale": "string",
                "selected_configuration": {
                    "crop": "string|null",
                    "algae": "string|null",
                    "microbial": "string|null",
                    "grow_system": "string|null",
                },
            },
        }
        return (
            "You are the critic, explainer, tradeoff analyzer, and improvement suggester for a deterministic "
            "closed-loop mission decision engine. The deterministic result is authoritative. "
            "You must NOT score candidates, rescore candidates, replace the decision engine, or invent a new "
            "selection workflow. Your job is to analyze the already-selected deterministic configuration.\n\n"
            "Focus on:\n"
            "1. Why the deterministic configuration makes sense.\n"
            "2. Weak links and loop gaps.\n"
            "3. Improvements that preserve deterministic-first architecture.\n"
            "4. One alternative configuration idea.\n"
            "5. One second-pass recommendation object.\n"
            "6. Crop vs algae vs microbial roles separately.\n"
            "7. Mission resilience under constraints and crisis events when state or event data is present.\n\n"
            "Return ONLY valid JSON. Do not include markdown, code fences, commentary, or prose outside JSON. "
            "If a value is unknown, use an empty list, null-like string field, or empty object as appropriate.\n\n"
            f"Expected JSON schema:\n{json.dumps(schema, ensure_ascii=True, indent=2)}\n\n"
            f"Deterministic payload:\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
        )

    def _extract_json_text(self, text: str) -> str | None:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()

        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        start = stripped.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False

        for index in range(start, len(stripped)):
            char = stripped[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return stripped[start : index + 1]

        return None
