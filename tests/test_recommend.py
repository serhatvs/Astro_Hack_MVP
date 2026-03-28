from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_recommend_returns_top_three_sorted_with_ui_fields() -> None:
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
    assert data["changed_fields"] == ["constraints.water"]
    assert isinstance(data["ranking_diff"], dict)
    assert data["risk_delta"] in {"increased", "decreased", "unchanged"}
    assert data["previous_top_crop"]
    assert data["new_top_crop"]
    assert len(data["updated_recommendation"]["top_crops"]) == 3
    assert data["reason"]
    assert data["adaptation_reason"]


def test_simulate_yield_drop_with_affected_crop_returns_clear_diff() -> None:
    payload = {
        "mission_profile": {
            "environment": "moon",
            "duration": "long",
            "constraints": {
                "water": "medium",
                "energy": "medium",
                "area": "medium",
            },
            "goal": "balanced",
        },
        "change_event": "yield_drop",
        "affected_crop": "potato",
    }

    response = client.post("/simulate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["changed_fields"] == ["yield_penalty.potato"]
    assert "potato" in data["ranking_diff"]
    assert data["updated_recommendation"]["top_crops"]
