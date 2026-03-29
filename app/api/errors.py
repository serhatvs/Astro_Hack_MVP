"""Safe API error messages used across backend handlers."""

from __future__ import annotations

from typing import Any

from app.api.protection import COOLDOWN_MESSAGE, RATE_LIMIT_MESSAGE


INVALID_INPUT_MESSAGE = "Invalid input"
SIMULATION_NOT_INITIALIZED_MESSAGE = "Simulation not initialized"
SIMULATION_ALREADY_ENDED_MESSAGE = "Simulation already ended"
GENERIC_RETRY_MESSAGE = "Something went wrong, please retry"
INVALID_CREDENTIALS_MESSAGE = "Invalid credentials"
LOGIN_REQUIRED_MESSAGE = "Please log in to continue"
SESSION_EXPIRED_MESSAGE = "Session expired"
ACCOUNT_EXISTS_MESSAGE = "Account already exists"

SAFE_DETAIL_MESSAGES = {
    INVALID_INPUT_MESSAGE,
    SIMULATION_NOT_INITIALIZED_MESSAGE,
    SIMULATION_ALREADY_ENDED_MESSAGE,
    GENERIC_RETRY_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    LOGIN_REQUIRED_MESSAGE,
    SESSION_EXPIRED_MESSAGE,
    ACCOUNT_EXISTS_MESSAGE,
    RATE_LIMIT_MESSAGE,
    COOLDOWN_MESSAGE,
}


def normalize_http_error_detail(status_code: int, detail: Any) -> str:
    """Return a safe, user-facing message for an HTTP error."""

    if isinstance(detail, str):
        normalized = detail.strip()
        if normalized in SAFE_DETAIL_MESSAGES:
            return normalized
        if status_code == 409 and "ended" in normalized.lower():
            return SIMULATION_ALREADY_ENDED_MESSAGE

    if status_code in {400, 422}:
        return INVALID_INPUT_MESSAGE
    if status_code == 401:
        return LOGIN_REQUIRED_MESSAGE
    if status_code == 404:
        return SIMULATION_NOT_INITIALIZED_MESSAGE
    if status_code == 409:
        return SIMULATION_ALREADY_ENDED_MESSAGE
    return GENERIC_RETRY_MESSAGE
