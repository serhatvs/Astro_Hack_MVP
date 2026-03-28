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
from app.models.response import LLMAnalysis, SimulationRequest
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


def test_gemini_client_parses_fenced_json(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _install_fake_google(
        monkeypatch,
        """```json
        {
          "reasoning_summary": "The deterministic stack is well balanced.",
          "weaknesses": ["Microbial risk remains elevated."],
          "alternative": {"crop": "spinach"}
        }
        ```""",
    )

    analysis = GeminiClient().analyze({"request_context": {"source": "recommend"}})

    assert analysis is not None
    assert analysis.reasoning_summary == "The deterministic stack is well balanced."
    assert analysis.weaknesses == ["Microbial risk remains elevated."]
    assert analysis.improvements == []
    assert analysis.alternative["crop"] == "spinach"
    assert analysis.alternative_configuration == analysis.alternative


def test_gemini_client_returns_none_on_invalid_json(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    _install_fake_google(monkeypatch, "```json\nnot-valid-json\n```")

    analysis = GeminiClient().analyze({"request_context": {"source": "recommend"}})

    assert analysis is None


def test_recommend_payload_sent_to_gemini_includes_context() -> None:
    engine = RecommendationEngine(provider=JSONDataProvider())

    class CaptureGeminiClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def analyze(self, payload):
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


def test_simulate_generates_delta_aware_llm_analysis() -> None:
    engine = RecommendationEngine(provider=JSONDataProvider())

    class CaptureGeminiClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def analyze(self, payload):
            self.payloads.append(payload)
            return None

    capture = CaptureGeminiClient()
    engine.reasoning_loop.gemini_client = capture

    mission = _build_mission()
    baseline = engine.recommend(mission)
    response = engine.simulate(
        SimulationRequest(
            mission_profile=mission,
            change_event=ChangeEvent.WATER_DROP,
            previous_recommendation=baseline,
        )
    )

    simulate_payload = capture.payloads[-1]
    assert simulate_payload["request_context"]["source"] == "simulate"
    assert simulate_payload["deltas"]["ranking_diff"] == response.ranking_diff
    assert simulate_payload["deltas"]["risk_score_delta"] == response.risk_score_delta
    assert "simulation update" in response.updated_recommendation.llm_analysis.reasoning_summary.lower()


def test_mission_step_generates_state_and_event_aware_llm_analysis() -> None:
    engine = RecommendationEngine(provider=JSONDataProvider())

    class CaptureGeminiClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def analyze(self, payload):
            self.payloads.append(payload)
            return None

    capture = CaptureGeminiClient()
    engine.reasoning_loop.gemini_client = capture

    baseline = engine.recommend(_build_mission())
    response = engine.mission_step(
        MissionStepRequest(
            mission_id=baseline.mission_state.mission_id,
            time_step=2,
            events=MissionEvents(water_drop=14, contamination=18),
        )
    )

    mission_step_payload = capture.payloads[-1]
    assert mission_step_payload["request_context"]["source"] == "mission_step"
    assert mission_step_payload["previous_state"] is not None
    assert mission_step_payload["history_summary"]
    assert mission_step_payload["events"]["contamination"] == 18.0
    assert mission_step_payload["deltas"]["risk_delta"] == response.risk_delta
    assert "mission step analysis" in response.llm_analysis.reasoning_summary.lower()
