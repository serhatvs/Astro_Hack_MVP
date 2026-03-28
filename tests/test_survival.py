from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_survival_days_calculation_with_known_crops() -> None:
    response = client.post(
        "/survival-days",
        json={
            "people_count": 4,
            "selected_crops": ["potato", "wheat"],
            "duration_days": 30,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_calories"] > 0
    assert payload["daily_consumption"] == 4 * 2500
    assert payload["survival_days"] > 0
    assert payload["computed_cycles"]


def test_survival_days_empty_crops_returns_warning() -> None:
    response = client.post(
        "/survival-days",
        json={
            "people_count": 5,
            "selected_crops": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["survival_days"] == 0
    assert payload["warning"] is not None


def test_survival_days_invalid_people_count_returns_bad_request() -> None:
    response = client.post(
        "/survival-days",
        json={
            "people_count": 0,
            "selected_crops": ["potato"],
        },
    )

    assert response.status_code == 422
