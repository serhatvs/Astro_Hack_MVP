import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.protection import request_protection
from app.services.auth import get_auth_service
from app.services.recommender import get_default_engine


@pytest.fixture(autouse=True)
def reset_runtime_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_path = (tmp_path / "auth.sqlite3").as_posix()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    request_protection.reset()
    get_auth_service.cache_clear()
    get_default_engine.cache_clear()
    yield
    request_protection.reset()
    get_auth_service().reset()
    get_auth_service.cache_clear()
    get_default_engine.cache_clear()
