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
    GeminiNarrative,
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
        "baseline_candidate_id",
        "candidate_shortlist",
        "events",
        "deltas",
    }
    assert payload["request_context"]["source"] == "recommend"
    assert payload["baseline_candidate_id"] == "candidate_1"
    assert len(payload["candidate_shortlist"]) >= 1
    assert payload["selected_roles"]["crop"]["role"] == "plant food production"
    assert payload["selected_roles"]["algae"]["role"] == "oxygen and biomass support"
    assert payload["selected_roles"]["microbial"]["role"] == "waste recycling and nutrient conversion"
    assert "system_reasoning" in payload["deterministic_explanations"]
    assert "interaction" in payload["scores"]
    assert "ui_layer" not in payload


def test_ai_rerank_can_change_recommendation_selection() -> None:
    engine = RecommendationEngine(provider=JSONDataProvider())

    class RerankingGeminiClient:
        def __init__(self) -> None:
            self.payloads: list[dict] = []

        def analyze(self, payload, **kwargs):  # noqa: ARG002
            self.payloads.append(payload)
            shortlist = payload["candidate_shortlist"]
            chosen = shortlist[1]
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
                        "reasoning_summary": "AI shortlisted review completed. -gemini",
                        "second_pass": {
                            "decision": "rerank",
                            "rationale": "Candidate 2 gives a stronger integrated stack.",
                            "selected_candidate_id": chosen["candidate_id"],
                            "selected_configuration": chosen["configuration"],
                        },
                    },
                }
            )

        def generate_json(self, prompt, **kwargs):  # noqa: ARG002
            return {
                "crop_note": "AI crop note.",
                "algae_note": "AI algae note.",
                "microbial_note": "AI microbial note.",
                "executive_summary": "AI executive summary.",
                "adaptation_summary": "",
            }

    gemini_client = RerankingGeminiClient()
    engine.reasoning_loop.gemini_client = gemini_client  # type: ignore[assignment]

    response = engine.recommend(_build_mission())
    chosen_configuration = gemini_client.payloads[-1]["candidate_shortlist"][1]["configuration"]

    assert response.ai_status.status == "reranked"
    assert response.ai_status.reviewed is True
    assert response.ai_status.selection_changed is True
    assert response.selected_system.crop.name == chosen_configuration["crop"]
    assert response.selected_system.algae.name == chosen_configuration["algae"]
    assert response.selected_system.microbial.name == chosen_configuration["microbial"]
    assert response.recommended_system == chosen_configuration["grow_system"]


def test_invalid_ai_rerank_metadata_keeps_baseline_but_counts_as_ai_review() -> None:
    engine = RecommendationEngine(provider=JSONDataProvider())

    class InvalidRerankGeminiClient:
        def analyze(self, payload, **kwargs):  # noqa: ARG002
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
                        "reasoning_summary": "AI shortlisted review completed. -gemini",
                        "second_pass": {
                            "decision": "rerank",
                            "rationale": "Trying an invalid id.",
                            "selected_candidate_id": "candidate_99",
                            "selected_configuration": {},
                        },
                    },
                }
            )

        def generate_json(self, prompt, **kwargs):  # noqa: ARG002
            return {
                "crop_note": "AI crop note.",
                "algae_note": "AI algae note.",
                "microbial_note": "AI microbial note.",
                "executive_summary": "AI executive summary.",
                "adaptation_summary": "",
            }

    baseline_engine = RecommendationEngine(provider=JSONDataProvider())
    baseline = baseline_engine.recommend(_build_mission(), use_llm=False)

    engine.reasoning_loop.gemini_client = InvalidRerankGeminiClient()  # type: ignore[assignment]
    response = engine.recommend(_build_mission())

    assert response.ai_status.status == "reviewed"
    assert response.ai_status.reviewed is True
    assert response.ai_status.selection_changed is False
    assert response.selected_system.crop.name == baseline.selected_system.crop.name
    assert response.selected_system.algae.name == baseline.selected_system.algae.name
    assert response.selected_system.microbial.name == baseline.selected_system.microbial.name
    assert response.recommended_system == baseline.recommended_system


def test_missing_ai_rerank_metadata_still_counts_as_ai_review() -> None:
    engine = RecommendationEngine(provider=JSONDataProvider())
    baseline = RecommendationEngine(provider=JSONDataProvider()).recommend(_build_mission(), use_llm=False)

    class MissingMetadataGeminiClient:
        def analyze(self, payload, **kwargs):  # noqa: ARG002
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
                        "reasoning_summary": "AI shortlisted review completed. -gemini",
                        "second_pass": {},
                    },
                }
            )

        def generate_json(self, prompt, **kwargs):  # noqa: ARG002
            return {
                "crop_note": "AI crop note.",
                "algae_note": "AI algae note.",
                "microbial_note": "AI microbial note.",
                "executive_summary": "AI executive summary.",
                "adaptation_summary": "",
            }

    engine.reasoning_loop.gemini_client = MissingMetadataGeminiClient()  # type: ignore[assignment]
    response = engine.recommend(_build_mission())

    assert response.ai_status.status == "reviewed"
    assert response.ai_status.reviewed is True
    assert response.ai_status.selection_changed is False
    assert response.selected_system.crop.name == baseline.selected_system.crop.name
    assert response.selected_system.algae.name == baseline.selected_system.algae.name
    assert response.selected_system.microbial.name == baseline.selected_system.microbial.name
    assert response.recommended_system == baseline.recommended_system


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
