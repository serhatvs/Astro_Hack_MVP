import sys
from types import ModuleType, SimpleNamespace

from app.core.simulation import MissionEvents, MissionStepRequest
from app.llm.gemini_client import GeminiClient
from app.models.mission import (
    ChangeEvent,
    ConstraintLevel,
    Duration,
    Environment,
    Goal,
    MissionConstraints,
    MissionProfile,
)
from app.models.response import (
    LLMAnalysis,
    SimulationRequest,
    SimulationStartRequest,
    UIEnhancedNarrative,
)
from app.services.data_provider import JSONDataProvider
from app.services.recommender import RecommendationEngine


def _install_fake_google(monkeypatch, response_text: str) -> None:
    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

    class FakeClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key
            self.models = self

        def generate_content(self, model: str, contents: str) -> FakeResponse:  # noqa: ARG002
            return FakeResponse(response_text)

    google_module = ModuleType("google")
    google_module.genai = SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "google", google_module)


def _build_mission() -> MissionProfile:
    return MissionProfile(
        environment=Environment.MARS,
        duration=Duration.LONG,
        constraints=MissionConstraints(
            water=ConstraintLevel.MEDIUM,
            energy=ConstraintLevel.MEDIUM,
            area=ConstraintLevel.MEDIUM,
        ),
        goal=Goal.BALANCED,
    )


def test_llm_analysis_normalizes_missing_keys() -> None:
    analysis = LLMAnalysis.from_payload({"reasoning_summary": "Stable deterministic fallback."})

    assert analysis.reasoning_summary == "Stable deterministic fallback."
    assert analysis.weaknesses == []
    assert analysis.improvements == []
    assert analysis.improvement_suggestions == []
    assert analysis.alternative == {}
    assert analysis.alternative_configuration == {}
    assert analysis.second_pass == {}
    assert analysis.second_pass_decision == {}


def test_ui_enhanced_normalizes_missing_keys() -> None:
    narrative = UIEnhancedNarrative.from_payload({"crop_note": "Plant layer stable."})

    assert narrative.crop_note == "Plant layer stable."
    assert narrative.algae_note == ""
    assert narrative.microbial_note == ""
    assert narrative.executive_summary == ""
    assert narrative.adaptation_summary == ""


def test_gemini_client_parses_fenced_json(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _install_fake_google(
        monkeypatch,
        """```json
        {
          "ui_layer": {
            "crop_note": "Spinach stabilizes the food layer.",
            "algae_note": "Spirulina supports oxygen and protein buffering.",
            "microbial_note": "The bioreactor reinforces nutrient recovery.",
            "executive_summary": "The closed-loop stack stays balanced.",
            "adaptation_summary": ""
          },
          "debug_layer": {
            "reasoning_summary": "The deterministic stack is well balanced.",
            "weaknesses": ["Microbial risk remains elevated."],
            "alternative": {"crop": "spinach"}
          }
        }
        ```""",
    )

    narrative = GeminiClient().analyze({"request_context": {"source": "recommend"}})

    assert narrative is not None
    assert narrative.ui_layer.crop_note == "Spinach stabilizes the food layer."
    assert narrative.debug_layer.reasoning_summary == "The deterministic stack is well balanced. -gemini"
    assert narrative.debug_layer.weaknesses == ["Microbial risk remains elevated."]
    assert narrative.debug_layer.improvements == []
    assert narrative.debug_layer.alternative["crop"] == "spinach"
    assert narrative.debug_layer.alternative_configuration == narrative.debug_layer.alternative


def test_gemini_client_returns_none_on_invalid_json(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _install_fake_google(monkeypatch, "```json\nnot-valid-json\n```")

    analysis = GeminiClient().analyze({"request_context": {"source": "recommend"}})

    assert analysis is None


def test_gemini_client_respects_use_llm_false(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _install_fake_google(monkeypatch, '{"ui_layer": {}, "debug_layer": {"reasoning_summary": "Should not run."}}')

    analysis = GeminiClient().analyze(
        {"request_context": {"source": "simulate"}},
        use_llm=False,
    )

    assert analysis is None


def test_recommend_payload_sent_to_gemini_includes_context(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    engine = RecommendationEngine(provider=JSONDataProvider())

    class CaptureGeminiClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def analyze(self, payload, **kwargs):  # noqa: ARG002
            self.payloads.append(payload)
            return None

    capture = CaptureGeminiClient()
    engine.reasoning_loop.gemini_client = capture

    engine.recommend(_build_mission())

    assert capture.payloads
    payload = capture.payloads[-1]
    assert set(payload.keys()) == {
        "request_context",
        "mission",
        "selected_roles",
        "scores",
        "deterministic_explanations",
        "mission_state",
        "previous_state",
        "history_summary",
        "events",
        "deltas",
    }
    assert payload["request_context"]["source"] == "recommend"
    assert payload["selected_roles"]["crop"]["role"] == "plant food production"
    assert payload["selected_roles"]["algae"]["role"] == "oxygen and biomass support"
    assert payload["selected_roles"]["microbial"]["role"] == "waste recycling and nutrient conversion"
    assert "system_reasoning" in payload["deterministic_explanations"]
    assert "interaction" in payload["scores"]
    assert "ui_layer" not in payload


def test_simulate_is_deterministic_and_does_not_call_gemini(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    engine = RecommendationEngine(provider=JSONDataProvider())
    baseline = engine.recommend(_build_mission())

    class CaptureGeminiClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def analyze(self, payload, **kwargs):  # noqa: ARG002
            self.payloads.append(payload)
            return None

    capture = CaptureGeminiClient()
    engine.reasoning_loop.gemini_client = capture

    response = engine.simulate(
        SimulationRequest(
            mission_profile=_build_mission(),
            change_event=ChangeEvent.WATER_DROP,
            previous_recommendation=baseline,
        )
    )

    assert capture.payloads == []
    assert "simulation update" in response.updated_recommendation.llm_analysis.reasoning_summary.lower()
    assert response.updated_recommendation.ui_enhanced.adaptation_summary
    assert response.updated_recommendation.ui_enhanced.crop_note


def test_start_simulation_is_deterministic_and_does_not_call_gemini(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    engine = RecommendationEngine(provider=JSONDataProvider())
    baseline = engine.recommend(_build_mission())

    class CaptureGeminiClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def analyze(self, payload, **kwargs):  # noqa: ARG002
            self.payloads.append(payload)
            return None

    capture = CaptureGeminiClient()
    engine.reasoning_loop.gemini_client = capture

    response = engine.start_simulation(
        SimulationStartRequest(
            mission_profile=baseline.mission_profile,
            selected_crop=baseline.selected_system.crop.name,
            selected_algae=baseline.selected_system.algae.name,
            selected_microbial=baseline.selected_system.microbial.name,
        )
    )

    assert capture.payloads == []
    assert response.ui_enhanced.executive_summary
    assert response.llm_analysis.reasoning_summary


def test_mission_step_is_deterministic_and_does_not_call_gemini(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    engine = RecommendationEngine(provider=JSONDataProvider())
    baseline = engine.recommend(_build_mission())

    class CaptureGeminiClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def analyze(self, payload, **kwargs):  # noqa: ARG002
            self.payloads.append(payload)
            return None

    capture = CaptureGeminiClient()
    engine.reasoning_loop.gemini_client = capture

    response = engine.mission_step(
        MissionStepRequest(
            mission_id=baseline.mission_state.mission_id,
            time_step=2,
            events=MissionEvents(water_drop=14, contamination=18),
        )
    )

    assert capture.payloads == []
    assert "mission step analysis" in response.llm_analysis.reasoning_summary.lower()
    assert response.ui_enhanced.adaptation_summary
    assert response.ui_enhanced.algae_note
