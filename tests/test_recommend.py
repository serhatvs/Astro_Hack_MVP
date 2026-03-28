from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_recommend_returns_top_three_sorted_with_ui_fields(monkeypatch) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
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


def test_simulate_returns_ranking_diff_and_risk_delta() -> None:
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
    assert data["adaptation_summary"]
    assert data["reason"] == data["adaptation_summary"]
    assert data["adaptation_reason"] == data["adaptation_summary"]


def test_simulate_yield_drop_with_affected_crop_returns_clear_diff() -> None:
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


def create_auth_headers(username: str = "test-user", password: str = "secret") -> dict[str, str]:
    client.post("/api/register", json={"username": username, "password": password})
    token_response = client.post("/api/login", json={"username": username, "password": password})
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_choose_crop_stores_user_choice(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    headers = create_auth_headers("choice-user", "choicesecret")

    rec = client.post(
        "/api/recommend",
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
        headers=headers,
    )
    assert rec.status_code == 200
    top_crop = rec.json()["top_crops"][0]["name"]

    response = client.post(
        "/api/choose-crop",
        json={"crop_name": top_crop, "environment": "mars"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["choice"]["crop_name"] == top_crop
    assert "warning" not in payload

    choices_response = client.get("/api/my-choices", headers=headers)
    assert choices_response.status_code == 200
    choices = choices_response.json()
    assert isinstance(choices, list)
    assert any(choice["crop_name"] == top_crop for choice in choices)


def test_choose_suboptimal_crop_returns_warning(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    headers = create_auth_headers("suboptimal-user", "choicesecret")

    rec = client.post(
        "/api/recommend",
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
        headers=headers,
    )
    assert rec.status_code == 200
    all_crop_names = [c["name"] for c in rec.json()["top_crops"]]
    fallback = "unicorn-crop"
    # pick a likely non-recommended crop from data set
    from app.services.data_provider import JSONDataProvider

    candidate_names = [c.name for c in JSONDataProvider().get_crops() if c.name not in all_crop_names]
    if candidate_names:
        fallback = candidate_names[0]

    response = client.post(
        "/api/choose-crop",
        json={"crop_name": fallback, "environment": "mars"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["choice"]["crop_name"] == fallback
    assert "warning" in payload


def test_simulate_prefers_last_user_choice(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    headers = create_auth_headers("simulate-user", "simsecret")

    mission = {
        "environment": "moon",
        "duration": "medium",
        "constraints": {"water": "medium", "energy": "medium", "area": "medium"},
        "goal": "balanced",
    }

    rec = client.post("/api/recommend", json=mission, headers=headers)
    assert rec.status_code == 200
    chosen_crop = rec.json()["top_crops"][0]["name"]

    choose_resp = client.post(
        "/api/choose-crop",
        json={"crop_name": chosen_crop, "environment": "moon"},
        headers=headers,
    )
    assert choose_resp.status_code == 200

    sim = client.post(
        "/api/simulate",
        json={"mission_profile": mission, "change_event": "yield_drop"},
        headers=headers,
    )
    assert sim.status_code == 200
    sim_data = sim.json()
    assert sim_data["previous_top_crop"] is not None
    assert sim_data["new_top_crop"] is not None


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
    assert "crop" in data["scores"]["domain"]
    assert "interaction" in data["scores"]
    assert data["explanations"]["executive_summary"] == data["executive_summary"]
    assert data["llm_analysis"]["reasoning_summary"]
    assert isinstance(data["llm_analysis"]["weaknesses"], list)
    assert "second_pass" in data["llm_analysis"]


def test_mission_step_updates_stored_state() -> None:
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
    assert len(data["mission_state"]["history"]) >= 2
    assert data["adaptation_summary"]
    assert isinstance(data["system_changes"], list)
    assert isinstance(data["risk_delta"], float)
