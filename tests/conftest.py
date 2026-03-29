import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.protection import request_protection
from app.services.recommender import get_default_engine


@pytest.fixture(autouse=True)
def reset_runtime_state() -> None:
    request_protection.reset()
    get_default_engine.cache_clear()
    yield
    request_protection.reset()
    get_default_engine.cache_clear()
