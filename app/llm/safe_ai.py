"""Safe execution helpers for optional external AI calls."""

from __future__ import annotations

import logging
import time
from threading import Thread
from typing import Callable, TypeVar


T = TypeVar("T")


def safe_ai_call(
    operation: Callable[[], T | None],
    *,
    fallback: T,
    task_label: str,
    timeout_seconds: float = 8.0,
    logger: logging.Logger | None = None,
) -> T:
    """Run an AI call with timeout, logging, and deterministic fallback."""

    active_logger = logger or logging.getLogger(__name__)
    result: dict[str, object] = {}

    def runner() -> None:
        try:
            result["value"] = operation()
        except Exception as exc:  # pragma: no cover - exercised through the wrapper outcome
            result["error"] = exc

    started_at = time.monotonic()
    thread = Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    elapsed = time.monotonic() - started_at

    if thread.is_alive():
        active_logger.warning(
            "AI timeout for %s after %.2fs; using deterministic fallback.",
            task_label,
            timeout_seconds,
        )
        return fallback

    error = result.get("error")
    if isinstance(error, Exception):
        active_logger.warning(
            "AI call failed for %s after %.2fs; using deterministic fallback.",
            task_label,
            elapsed,
            exc_info=(type(error), error, error.__traceback__),
        )
        return fallback

    value = result.get("value")
    if value is None:
        active_logger.info(
            "AI produced no result for %s after %.2fs; using deterministic fallback.",
            task_label,
            elapsed,
        )
        return fallback

    active_logger.info("AI call succeeded for %s in %.2fs.", task_label, elapsed)
    return value if isinstance(value, type(fallback)) else fallback
