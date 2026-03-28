"""Filesystem loading helpers for local JSON datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def load_json_file(path: Path) -> Any:
    """Load a UTF-8 JSON file from disk."""

    with path.open("r", encoding="utf-8") as file_pointer:
        return json.load(file_pointer)


def load_dataset(filename: str) -> Any:
    """Load a JSON dataset from the local data directory."""

    return load_json_file(DATA_DIR / filename)

