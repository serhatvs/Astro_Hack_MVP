from fastapi.testclient import TestClient

from app.api.errors import (
    ACCOUNT_EXISTS_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    LOGIN_REQUIRED_MESSAGE,
)
from app.main import app
from app.services.recommender import get_default_engine


def _credentials() -> dict[str, str]:
    return {
        "email": "demo.user@example.com",
        "password": "StrongPass123",
    }


def _mission_payload() -> dict:
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


def test_register_creates_account_and_session() -> None:
    with TestClient(app) as client:
        response = client.post("/auth/register", json=_credentials())

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "demo.user@example.com"
        assert data["user"]["is_active"] is True
        assert data["user"]["id"]

        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["user"]["email"] == "demo.user@example.com"


def test_register_rejects_duplicate_account() -> None:
    with TestClient(app) as client:
        first = client.post("/auth/register", json=_credentials())
        second = client.post("/auth/register", json=_credentials())

        assert first.status_code == 201
        assert second.status_code == 409
        assert second.json()["detail"] == ACCOUNT_EXISTS_MESSAGE


def test_login_success_returns_authenticated_user() -> None:
    credentials = _credentials()
    with TestClient(app) as register_client:
        register_client.post("/auth/register", json=credentials)

    with TestClient(app) as client:
        response = client.post("/auth/login", json=credentials)

        assert response.status_code == 200
        assert response.json()["user"]["email"] == credentials["email"]

        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["user"]["email"] == credentials["email"]


def test_login_failure_returns_safe_message() -> None:
    with TestClient(app) as client:
        client.post("/auth/register", json=_credentials())
        response = client.post(
            "/auth/login",
            json={
                "email": "demo.user@example.com",
                "password": "WrongPass123",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == INVALID_CREDENTIALS_MESSAGE


def test_auth_me_requires_authenticated_session() -> None:
    with TestClient(app) as client:
        response = client.get("/auth/me")

        assert response.status_code == 401
        assert response.json()["detail"] == LOGIN_REQUIRED_MESSAGE


def test_logout_clears_session() -> None:
    with TestClient(app) as client:
        client.post("/auth/register", json=_credentials())

        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["success"] is True

        me_response = client.get("/auth/me")
        assert me_response.status_code == 401
        assert me_response.json()["detail"] == LOGIN_REQUIRED_MESSAGE


def test_recommend_enables_ai_only_for_authenticated_sessions(monkeypatch) -> None:
    engine = get_default_engine()
    original_recommend = engine.recommend
    captured_use_llm: list[bool] = []

    def capture_recommend(*args, **kwargs):
        captured_use_llm.append(bool(kwargs.get("use_llm")))
        return original_recommend(*args, **kwargs)

    monkeypatch.setattr(engine, "recommend", capture_recommend)

    with TestClient(app) as client:
        logged_out = client.post("/recommend", json=_mission_payload())
        assert logged_out.status_code == 200
        assert captured_use_llm[-1] is False

        register_response = client.post("/auth/register", json=_credentials())
        assert register_response.status_code == 201

        logged_in = client.post("/recommend", json=_mission_payload())
        assert logged_in.status_code == 200
        assert captured_use_llm[-1] is True
