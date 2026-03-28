from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_recommend_returns_top_three_sorted_with_ui_fields(monkeypatch) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    payload = {
        "environment": "mars",
        "duration": "long",
        "constraints": {
            "water": "low",
            "energy": "medium",
            "area": "medium",
        },
        "goal": "balanced",
    }

    response = client.post("/recommend", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["mission_profile"] == payload
    assert data["recommended_system"] in {"hydroponic", "aeroponic", "hybrid"}
    assert data["system_reason"]
    assert data["system_reasoning"]
    assert data["why_this_system"]
    assert data["tradeoff_summary"]
    assert data["mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["executive_summary"]
    assert data["operational_note"]
    assert data["ui_enhanced"]["crop_note"]
    assert data["ui_enhanced"]["algae_note"]
    assert data["ui_enhanced"]["microbial_note"]
    assert data["ranked_candidates"]["crop"]
    assert data["ranked_candidates"]["algae"]
    assert data["ranked_candidates"]["microbial"]
    assert data["ranked_candidates"]["crop"][0]["rank"] == 1
    assert len(data["top_crops"]) == 3
    assert data["top_crops"][0]["score"] >= data["top_crops"][1]["score"] >= data["top_crops"][2]["score"]
    assert all(item["reason"] for item in data["top_crops"])
    assert all(len(item["strengths"]) == 2 for item in data["top_crops"])
    assert all(len(item["tradeoffs"]) == 1 for item in data["top_crops"])
    assert all("metric_breakdown" in item for item in data["top_crops"])
    assert all("compatibility_score" in item for item in data["top_crops"])
    assert "water_score" in data["resource_plan"]
    assert "score" in data["risk_analysis"]
    assert data["explanation"]


def test_simulate_returns_ranking_diff_and_risk_delta(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    payload = {
        "mission_profile": {
            "environment": "mars",
            "duration": "long",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
        "change_event": "water_drop",
    }

    response = client.post("/simulate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["updated_mission_profile"]["constraints"]["water"] == "low"
    assert data["changed_fields"][0] == "constraints.water"
    assert isinstance(data["ranking_diff"], dict)
    assert data["risk_delta"] in {"increased", "decreased", "unchanged"}
    assert isinstance(data["risk_score_delta"], float)
    assert data["previous_mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["new_mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["previous_top_crop"]
    assert data["new_top_crop"]
    assert len(data["updated_recommendation"]["top_crops"]) == 3
    assert data["updated_recommendation"]["executive_summary"]
    assert data["updated_recommendation"]["ui_enhanced"]["adaptation_summary"]
    assert data["updated_recommendation"]["ranked_candidates"]["algae"]
    assert data["adaptation_summary"]
    assert "water" in data["adaptation_summary"].lower()
    assert "risk" in data["adaptation_summary"].lower()
    assert data["reason"] == data["adaptation_summary"]
    assert data["adaptation_reason"] == data["adaptation_summary"]
    assert not data["updated_recommendation"]["llm_analysis"]["reasoning_summary"].endswith(" -gemini")


def test_simulate_yield_drop_with_affected_crop_returns_clear_diff(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mission = {
        "environment": "moon",
        "duration": "long",
        "constraints": {
            "water": "medium",
            "energy": "medium",
            "area": "medium",
        },
        "goal": "balanced",
    }
    baseline = client.post("/recommend", json=mission)
    assert baseline.status_code == 200
    top_crop = baseline.json()["top_crops"][0]["name"]

    payload = {
        "mission_profile": {
            **mission,
        },
        "change_event": "yield_drop",
        "affected_crop": top_crop,
    }

    response = client.post("/simulate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "top_crops" in data["changed_fields"]
    assert top_crop in data["ranking_diff"]
    assert top_crop.title() in data["adaptation_summary"]
    assert data["previous_top_crop"] == top_crop
    assert data["new_top_crop"] != top_crop
    assert data["updated_recommendation"]["top_crops"]
    assert data["updated_recommendation"]["mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}


def test_openapi_and_requirements_have_no_external_ai_runtime_dependency(monkeypatch) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post(
        "/recommend",
        json={
            "environment": "iss",
            "duration": "medium",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
    )

    assert response.status_code == 200
    assert "/optimize_agriculture" not in app.openapi()["paths"]

    requirements_text = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "openai" not in requirements_text
    assert "anthropic" not in requirements_text


def test_recommend_returns_stateful_multidomain_payload(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post(
        "/recommend",
        json={
            "environment": "mars",
            "duration": "long",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["mission_id"]
    assert data["mission_state"]["active_system"]["crops"][0]["type"] == "crop"
    assert data["mission_state"]["active_system"]["algae"][0]["type"] == "algae"
    assert data["mission_state"]["active_system"]["microbial"][0]["type"] == "microbial"
    assert data["selected_system"]["crop"]["support_system"] == data["recommended_system"]
    assert data["ranked_candidates"]["crop"][0]["type"] == "crop"
    assert data["ranked_candidates"]["algae"][0]["type"] == "algae"
    assert data["ranked_candidates"]["microbial"][0]["type"] == "microbial"
    assert "crop" in data["scores"]["domain"]
    assert "interaction" in data["scores"]
    assert data["explanations"]["executive_summary"] == data["executive_summary"]
    assert data["llm_analysis"]["reasoning_summary"]
    assert isinstance(data["llm_analysis"]["weaknesses"], list)
    assert "second_pass" in data["llm_analysis"]
    assert data["ui_enhanced"]["executive_summary"]
    assert "crop_note" in data["ui_enhanced"]


def test_simulation_start_bootstraps_selected_stack(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    baseline = client.post(
        "/recommend",
        json={
            "environment": "mars",
            "duration": "long",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
    )
    assert baseline.status_code == 200
    baseline_data = baseline.json()

    response = client.post(
        "/simulation/start",
        json={
            "mission_profile": baseline_data["mission_profile"],
            "selected_crop": baseline_data["selected_system"]["crop"]["name"],
            "selected_algae": baseline_data["selected_system"]["algae"]["name"],
            "selected_microbial": baseline_data["selected_system"]["microbial"]["name"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["mission_id"]
    assert data["selected_system"]["crop"]["name"] == baseline_data["selected_system"]["crop"]["name"]
    assert data["selected_system"]["algae"]["name"] == baseline_data["selected_system"]["algae"]["name"]
    assert data["selected_system"]["microbial"]["name"] == baseline_data["selected_system"]["microbial"]["name"]
    assert data["ranked_candidates"]["crop"]
    assert data["scores"]["integrated"] >= 0
    assert data["mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["operational_note"]
    assert data["ui_enhanced"]["executive_summary"]
    assert not data["llm_analysis"]["reasoning_summary"].endswith(" -gemini")


def test_simulation_start_rejects_invalid_selected_names(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "mars",
                "duration": "long",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "not-a-real-crop",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )

    assert response.status_code == 400
    assert "not compatible" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()


def test_mission_step_updates_stored_state(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    baseline = client.post(
        "/recommend",
        json={
            "environment": "moon",
            "duration": "medium",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
    )
    assert baseline.status_code == 200
    mission_state = baseline.json()["mission_state"]

    response = client.post(
        "/mission/step",
        json={
            "mission_id": mission_state["mission_id"],
            "time_step": 3,
            "events": {
                "water_drop": 18,
                "yield_variation": -20,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["mission_id"] == mission_state["mission_id"]
    assert data["mission_state"]["time"] == mission_state["time"] + 3
    assert data["mission_state"]["resources"]["water"] < mission_state["resources"]["water"]
    assert data["mission_state"]["resources"]["energy"] < mission_state["resources"]["energy"]
    assert len(data["mission_state"]["history"]) >= 2
    assert data["adaptation_summary"]
    assert data["adaptation_summary"].startswith("Week 3:")
    assert "water drop" in data["adaptation_summary"].lower()
    assert "risk" in data["adaptation_summary"].lower()
    assert data["ui_enhanced"]["adaptation_summary"]
    assert data["ranked_candidates"]["crop"]
    assert isinstance(data["system_changes"], list)
    assert isinstance(data["risk_delta"], float)
    assert not data["llm_analysis"]["reasoning_summary"].endswith(" -gemini")


def test_mission_step_works_after_simulation_start(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Arthrospira platensis (Spirulina)",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert bootstrap.status_code == 200
    mission_id = bootstrap.json()["mission_state"]["mission_id"]

    response = client.post(
        "/mission/step",
        json={
            "mission_id": mission_id,
            "time_step": 2,
            "events": {
                "water_drop": 10,
                "contamination": 15,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["mission_id"] == mission_id
    assert data["mission_state"]["time"] == 2
    assert data["adaptation_summary"].startswith("Week 2:")
    assert data["mission_status"] in {"NOMINAL", "WATCH", "CRITICAL"}
    assert data["operational_note"]
    assert data["adaptation_summary"]


def test_mission_step_applies_weekly_baseline_drain_without_explicit_events(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    bootstrap = client.post(
        "/simulation/start",
        json={
            "mission_profile": {
                "environment": "moon",
                "duration": "medium",
                "constraints": {
                    "water": "medium",
                    "energy": "medium",
                    "area": "medium",
                },
                "goal": "balanced",
            },
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert bootstrap.status_code == 200
    bootstrap_data = bootstrap.json()

    response = client.post(
        "/mission/step",
        json={
            "mission_id": bootstrap_data["mission_state"]["mission_id"],
            "time_step": 1,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mission_state"]["time"] == 1
    assert data["mission_state"]["resources"]["water"] < bootstrap_data["mission_state"]["resources"]["water"]
    assert data["mission_state"]["resources"]["energy"] < bootstrap_data["mission_state"]["resources"]["energy"]
    assert data["adaptation_summary"].startswith("Week 1:")
