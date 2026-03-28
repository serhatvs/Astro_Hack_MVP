from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_recommend_returns_top_three_sorted() -> None:
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
    assert len(data["top_crops"]) == 3
    assert data["top_crops"][0]["score"] >= data["top_crops"][1]["score"] >= data["top_crops"][2]["score"]
    assert all(item["reason"] for item in data["top_crops"])
    assert data["explanation"]


def test_simulate_updates_profile_without_crashing() -> None:
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
    assert len(data["updated_recommendation"]["top_crops"]) == 3
    assert data["adaptation_reason"]

