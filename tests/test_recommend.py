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
