from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint_returns_service_overview() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Astro Hack MVP API is running",
        "status": "ok",
        "endpoints": [
            "/health",
            "/demo-cases",
            "/recommend",
            "/simulate",
        ],
    }


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "space_agri_ai",
    }
