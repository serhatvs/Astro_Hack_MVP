from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_demo_cases_endpoint_returns_three_named_presets() -> None:
    response = client.get("/demo-cases")

    assert response.status_code == 200
    data = response.json()
    assert [item["name"] for item in data] == [
        "Mars Water Crisis",
        "ISS Low Maintenance Mission",
        "Moon Long Duration Calorie Mission",
    ]
