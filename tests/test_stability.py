from fastapi.testclient import TestClient

from app.main import app
from app.services.recommender import get_default_engine


client = TestClient(app)


def _mission_profile() -> dict:
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


def test_invalid_recommend_payload_returns_safe_message() -> None:
    response = client.post("/recommend", json={})

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid input"


def test_start_simulation_with_blank_selection_returns_safe_message() -> None:
    response = client.post(
        "/simulation/start",
        json={
            "mission_profile": _mission_profile(),
            "selected_crop": "   ",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid input"


def test_mission_step_returns_not_initialized_for_unknown_state() -> None:
    response = client.post(
        "/mission/step",
        json={
            "mission_id": "missing-mission",
            "time_step": 1,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Simulation not initialized"


def test_mission_step_blocks_actions_after_simulation_end() -> None:
    start_response = client.post(
        "/simulation/start",
        json={
            "mission_profile": _mission_profile(),
            "selected_crop": "Lactuca sativa (Marul)",
            "selected_algae": "Chlorella vulgaris",
            "selected_microbial": "Saccharomyces boulardii",
        },
    )
    assert start_response.status_code == 200

    mission_id = start_response.json()["mission_state"]["mission_id"]
    engine = get_default_engine()
    stored_state = engine.state_store.get(mission_id)
    assert stored_state is not None
    engine.state_store.save(stored_state.model_copy(update={"end_reason": "duration_complete"}, deep=True))

    response = client.post(
        "/mission/step",
        json={
            "mission_id": mission_id,
            "time_step": 1,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Simulation already ended"
