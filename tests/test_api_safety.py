import time

from fastapi.testclient import TestClient

from app.llm.ai_service import AIService
from app.main import app
from app.models.response import GeminiNarrative, UIEnhancedNarrative


client = TestClient(app)


def _mission_payload() -> dict:
    return {
        "environment": "mars",
        "duration": "long",
        "constraints": {
            "water": "medium",
            "energy": "medium",
            "area": "medium",
        },
        "goal": "balanced",
    }


def _fallback_narrative() -> GeminiNarrative:
    return GeminiNarrative.from_payload(
        {
            "ui_layer": {
                "crop_note": "System analysis generated using deterministic model.",
                "algae_note": "AI explanation unavailable. Displaying baseline reasoning.",
                "microbial_note": "Baseline deterministic note.",
                "executive_summary": "System analysis generated using deterministic model.",
                "adaptation_summary": "",
            },
            "debug_layer": {
                "reasoning_summary": (
                    "System analysis generated using deterministic model. "
                    "AI explanation unavailable. Displaying baseline reasoning."
                )
            },
        }
    )


def test_recommend_allows_repeated_requests_without_rate_limit() -> None:
    headers = {"X-Session-ID": "no-rate-limit-session"}

    for _ in range(6):
        response = client.post("/recommend", json=_mission_payload(), headers=headers)
        assert response.status_code == 200


def test_ai_service_caches_identical_inputs() -> None:
    class FakeGeminiClient:
        def __init__(self) -> None:
            self.analyze_calls = 0
            self.summary_calls = 0

        def analyze(self, payload, **kwargs):  # noqa: ARG002
            self.analyze_calls += 1
            return GeminiNarrative.from_payload(
                {
                    "ui_layer": {
                        "crop_note": "AI crop note.",
                        "algae_note": "AI algae note.",
                        "microbial_note": "AI microbial note.",
                        "executive_summary": "AI executive summary.",
                        "adaptation_summary": "",
                    },
                    "debug_layer": {
                        "reasoning_summary": "AI narrative ready. -gemini",
                    },
                }
            )

        def generate_json(self, prompt, **kwargs):  # noqa: ARG002
            self.summary_calls += 1
            return {
                "crop_note": "Polished crop note.",
                "algae_note": "Polished algae note.",
                "microbial_note": "Polished microbial note.",
                "executive_summary": "Polished executive summary.",
                "adaptation_summary": "",
            }

    service = AIService(gemini_client=FakeGeminiClient())
    payload = {
        "request_context": {"source": "recommend"},
        "selected_roles": {"crop": {"name": "lettuce"}},
        "deterministic_explanations": {"executive_summary": "Baseline summary."},
    }
    fallback = _fallback_narrative()

    first = service.generate_recommendation_explanation(payload, fallback=fallback)
    second = service.generate_recommendation_explanation(payload, fallback=fallback)

    assert first.ui_layer.executive_summary == "Polished executive summary."
    assert second.ui_layer.executive_summary == "Polished executive summary."
    assert service.gemini_client.analyze_calls == 1
    assert service.gemini_client.summary_calls == 1


def test_ai_service_uses_fallback_when_ai_errors() -> None:
    class FailingGeminiClient:
        def analyze(self, payload, **kwargs):  # noqa: ARG002
            raise RuntimeError("upstream failure")

        def generate_json(self, prompt, **kwargs):  # noqa: ARG002
            raise AssertionError("summary polish should not run when the main call fails")

    fallback = _fallback_narrative()
    service = AIService(gemini_client=FailingGeminiClient())

    result = service.generate_recommendation_explanation(
        {"request_context": {"source": "recommend"}},
        fallback=fallback,
    )

    assert result.debug_layer.reasoning_summary == fallback.debug_layer.reasoning_summary
    assert result.ui_layer.executive_summary == fallback.ui_layer.executive_summary


def test_ai_service_does_not_cache_fallback_results() -> None:
    class FailingGeminiClient:
        def __init__(self) -> None:
            self.analyze_calls = 0

        def analyze(self, payload, **kwargs):  # noqa: ARG002
            self.analyze_calls += 1
            raise RuntimeError("upstream failure")

        def generate_json(self, prompt, **kwargs):  # noqa: ARG002
            raise AssertionError("summary polish should not run when the main call fails")

    fallback = _fallback_narrative()
    gemini_client = FailingGeminiClient()
    service = AIService(gemini_client=gemini_client)

    first = service.generate_recommendation_explanation(
        {"request_context": {"source": "recommend"}},
        fallback=fallback,
    )
    second = service.generate_recommendation_explanation(
        {"request_context": {"source": "recommend"}},
        fallback=fallback,
    )

    assert first.debug_layer.reasoning_summary == fallback.debug_layer.reasoning_summary
    assert second.debug_layer.reasoning_summary == fallback.debug_layer.reasoning_summary
    assert gemini_client.analyze_calls == 2


def test_ai_service_times_out_and_returns_fallback() -> None:
    class SlowGeminiClient:
        def analyze(self, payload, **kwargs):  # noqa: ARG002
            time.sleep(0.05)
            return GeminiNarrative.from_payload(
                {
                    "ui_layer": {
                        "crop_note": "Late crop note.",
                        "algae_note": "Late algae note.",
                        "microbial_note": "Late microbial note.",
                        "executive_summary": "Late summary.",
                        "adaptation_summary": "",
                    },
                    "debug_layer": {"reasoning_summary": "Late narrative. -gemini"},
                }
            )

        def generate_json(self, prompt, **kwargs):  # noqa: ARG002
            return UIEnhancedNarrative(
                crop_note="Unused",
                algae_note="Unused",
                microbial_note="Unused",
                executive_summary="Unused",
                adaptation_summary="",
            ).model_dump(mode="json")

    fallback = _fallback_narrative()
    service = AIService(gemini_client=SlowGeminiClient())
    service.timeout_seconds = 0.01

    result = service.generate_recommendation_explanation(
        {"request_context": {"source": "recommend"}},
        fallback=fallback,
    )

    assert result.debug_layer.reasoning_summary == fallback.debug_layer.reasoning_summary
    assert result.ui_layer.executive_summary == fallback.ui_layer.executive_summary
