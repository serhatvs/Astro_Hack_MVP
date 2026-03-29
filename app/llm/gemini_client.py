"""Optional Gemini client used as a structured generator over deterministic results."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.models.response import GeminiNarrative


logger = logging.getLogger(__name__)


class GeminiClient:
    """Thin optional wrapper around the Google GenAI SDK."""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self.model = os.getenv("GEMINI_MODEL", model)
        self.api_key = os.getenv("GEMINI_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def analyze(
        self,
        payload: dict[str, Any],
        *,
        model: str | None = None,
        use_llm: bool = True,
        fallback_ui: dict[str, Any] | None = None,
        default_reasoning: str = "Gemini returned incomplete analysis; deterministic fallback remains active.",
    ) -> GeminiNarrative | None:
        """Ask Gemini to rewrite UI summaries and critique a deterministic recommendation.

        The app remains deterministic-first: if Gemini is unavailable, missing,
        or returns malformed output, callers should fall back to rule-based analysis.
        """

        parsed = self.generate_json(
            self._build_narrative_prompt(payload),
            model=model,
            use_llm=use_llm,
            task_label="recommendation_narrative",
        )
        if parsed is None:
            return None

        narrative = GeminiNarrative.from_payload(
            parsed,
            default_ui=fallback_ui,
            default_reasoning=default_reasoning,
        )
        if not narrative.debug_layer.reasoning_summary.endswith(" -gemini"):
            narrative = narrative.model_copy(
                update={
                    "debug_layer": narrative.debug_layer.model_copy(
                        update={
                            "reasoning_summary": f"{narrative.debug_layer.reasoning_summary} -gemini"
                        }
                    )
                }
            )
        logger.info("Gemini analysis succeeded.")
        return narrative

    def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        use_llm: bool = True,
        task_label: str = "generic_task",
    ) -> dict[str, Any] | None:
        if not use_llm:
            logger.info("Gemini blocked by use_llm=False; skipping external AI call for %s.", task_label)
            return None

        if not self.is_available():
            logger.info("Gemini disabled: GEMINI_API_KEY is not set.")
            return None

        try:
            from google import genai
        except ImportError:
            logger.warning("Gemini enabled but google.genai is unavailable; using deterministic fallback.")
            return None

        resolved_model = model or self.model

        try:
            logger.info("Gemini enabled: sending %s request with model=%s.", task_label, resolved_model)
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=resolved_model,
                contents=prompt,
            )
            text = getattr(response, "text", "") or ""
        except Exception:
            logger.warning("Gemini request failed for %s; using deterministic fallback.", task_label, exc_info=True)
            return None

        if not text.strip():
            logger.warning("Gemini returned an empty response for %s; using deterministic fallback.", task_label)
            return None

        extracted_json = self._extract_json_text(text)
        if extracted_json is None:
            logger.warning("Gemini response did not contain a JSON object for %s; using deterministic fallback.", task_label)
            return None

        try:
            parsed = json.loads(extracted_json)
        except json.JSONDecodeError:
            logger.warning("Gemini JSON parsing failed for %s; using deterministic fallback.", task_label, exc_info=True)
            return None

        if not isinstance(parsed, dict):
            logger.warning("Gemini returned non-object JSON for %s; using deterministic fallback.", task_label)
            return None

        logger.info("Gemini %s succeeded with model=%s.", task_label, resolved_model)
        return parsed

    def _build_narrative_prompt(self, payload: dict[str, Any]) -> str:
        schema = {
            "ui_layer": {
                "crop_note": "string",
                "algae_note": "string",
                "microbial_note": "string",
                "executive_summary": "string",
                "adaptation_summary": "string",
            },
            "debug_layer": {
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
                    "decision": "retain|rerank",
                    "rationale": "string",
                    "selected_candidate_id": "string|null",
                    "selected_configuration": {
                        "crop": "string|null",
                        "algae": "string|null",
                        "microbial": "string|null",
                        "grow_system": "string|null",
                    },
                },
            },
        }
        return (
            "You are the summary rewriter, shortlist reviewer, reranking critic, explainer, tradeoff analyzer, and "
            "improvement suggester for a deterministic closed-loop mission decision engine. The deterministic engine "
            "provides the only valid shortlist. You may review and rerank ONLY the candidates inside "
            "`candidate_shortlist`. You must NOT invent candidates, score anything outside the shortlist, or create "
            "a new selection workflow.\n\n"
            "Optimize for low token usage, low verbosity, concise outputs, and no repetition.\n\n"
            "Focus on:\n"
            "1. Review `candidate_shortlist` and choose exactly one `selected_candidate_id` from that shortlist.\n"
            "2. If the deterministic top candidate is still best, set `decision` to `retain` and keep the baseline id.\n"
            "3. If another shortlisted candidate is better, set `decision` to `rerank` and return that shortlist id.\n"
            "4. Rewrite concise UI notes for crop, algae, and microbial cards using the candidate you selected.\n"
            "5. Write a short executive summary of the selected integrated stack.\n"
            "6. Write an adaptation summary only if the payload includes events, deltas, or state change context.\n"
            "7. Explain why the selected shortlist candidate makes sense.\n"
            "8. Identify weak links, tradeoffs, and improvements.\n"
            "9. Provide one alternative configuration idea and one second-pass recommendation object.\n"
            "10. Reason explicitly about crop vs algae vs microbial roles.\n"
            "11. If state or event data exists, comment on resilience and degradation over time.\n\n"
            "UI layer rules:\n"
            "- Keep each card note to 1-3 short sentences.\n"
            "- Preserve technical truth from deterministic data.\n"
            "- Do not invent unsupported claims.\n"
            "- Keep executive_summary and adaptation_summary concise.\n\n"
            "Rerank rules:\n"
            "- `selected_candidate_id` must be one of the ids already present in `candidate_shortlist`.\n"
            "- `selected_configuration` must match the candidate you selected.\n"
            "- If you are uncertain, retain the baseline deterministic candidate instead of inventing a new one.\n\n"
            "Return ONLY valid JSON. Do not include markdown, code fences, commentary, or prose outside JSON. "
            "All keys must exist. If a value is not relevant, use an empty string, empty list, or empty object.\n\n"
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
