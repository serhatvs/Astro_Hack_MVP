from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_demo_cases_endpoint_returns_three_named_presets() -> None:
    response = client.get("/demo-cases")

    assert response.status_code == 200
    data = response.json()
    assert [item["name"] for item in data] == [
        "Demo Scenario: Strong System",
        "Demo Scenario: Average System",
        "Demo Scenario: Failure Case",
    ]
    assert data[0]["expected_outcome"]
    assert data[0]["selected_stack"]["selected_crop"]
