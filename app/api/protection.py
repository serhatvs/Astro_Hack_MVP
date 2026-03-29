"""Lightweight in-memory request protection for burst control."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock

from fastapi import HTTPException, Request


logger = logging.getLogger(__name__)

RATE_LIMIT_MESSAGE = "Too many requests, please try again shortly"
COOLDOWN_MESSAGE = "Please wait a few seconds before requesting another AI analysis."


@dataclass(frozen=True)
class RequestPolicy:
    """Simple request policy for one endpoint group."""

    key: str
    max_requests: int
    window_seconds: float
    cooldown_seconds: float = 0.0


class RequestProtection:
    """In-memory rate limiter and cooldown tracker."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._request_history: dict[tuple[str, str], deque[float]] = {}
        self._last_request_at: dict[tuple[str, str], float] = {}

    def reset(self) -> None:
        """Clear stored counters. Primarily used by tests."""

        with self._lock:
            self._request_history.clear()
            self._last_request_at.clear()

    def enforce(self, request: Request, policy: RequestPolicy) -> None:
        """Apply the configured burst and cooldown protections."""

        client_key = self._resolve_client_key(request)
        if client_key is None:
            logger.debug("Skipping request protection for %s because no stable client key was available.", request.url.path)
            return

        now = time.monotonic()
        bucket_key = (policy.key, client_key)

        with self._lock:
            history = self._request_history.setdefault(bucket_key, deque())
            cutoff = now - policy.window_seconds
            while history and history[0] <= cutoff:
                history.popleft()

            if len(history) >= policy.max_requests:
                retry_after = max(1, int(policy.window_seconds - (now - history[0])))
                logger.warning(
                    "Rate limit triggered for %s on %s (client=%s, retry_after=%ss).",
                    policy.key,
                    request.url.path,
                    client_key,
                    retry_after,
                )
                raise HTTPException(
                    status_code=429,
                    detail=RATE_LIMIT_MESSAGE,
                    headers={"Retry-After": str(retry_after)},
                )

            last_request_at = self._last_request_at.get(bucket_key)
            if policy.cooldown_seconds > 0 and last_request_at is not None:
                elapsed = now - last_request_at
                if elapsed < policy.cooldown_seconds:
                    retry_after = max(1, int(policy.cooldown_seconds - elapsed))
                    logger.warning(
                        "Cooldown triggered for %s on %s (client=%s, retry_after=%ss).",
                        policy.key,
                        request.url.path,
                        client_key,
                        retry_after,
                    )
                    raise HTTPException(
                        status_code=429,
                        detail=COOLDOWN_MESSAGE,
                        headers={"Retry-After": str(retry_after)},
                    )

            history.append(now)
            self._last_request_at[bucket_key] = now
            self._prune_inactive(now)

    def _resolve_client_key(self, request: Request) -> str | None:
        auth_subject = getattr(request.state, "auth_subject", None)
        if isinstance(auth_subject, str) and auth_subject.strip():
            return auth_subject.strip()

        session_id = request.headers.get("x-session-id")
        if session_id:
            return f"session:{session_id.strip()}"

        auth_cookie = request.cookies.get("astro_session")
        if auth_cookie:
            return f"session:{auth_cookie.strip()}"

        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            forwarded_ip = forwarded_for.split(",")[0].strip()
            if forwarded_ip:
                return f"ip:{forwarded_ip}"

        client = request.client
        if client and client.host and client.host != "testclient":
            return f"ip:{client.host}"

        return None

    def _prune_inactive(self, now: float) -> None:
        stale_history_before = now - 300.0
        empty_history_keys = [
            key
            for key, history in self._request_history.items()
            if not history or history[-1] <= stale_history_before
        ]
        for key in empty_history_keys:
            self._request_history.pop(key, None)

        stale_request_keys = [
            key
            for key, last_seen in self._last_request_at.items()
            if last_seen <= stale_history_before
        ]
        for key in stale_request_keys:
            self._last_request_at.pop(key, None)


request_protection = RequestProtection()

RECOMMEND_POLICY = RequestPolicy(
    key="recommend",
    max_requests=5,
    window_seconds=60.0,
    cooldown_seconds=10.0,
)
AUTH_REGISTER_POLICY = RequestPolicy(
    key="auth_register",
    max_requests=4,
    window_seconds=60.0,
)
AUTH_LOGIN_POLICY = RequestPolicy(
    key="auth_login",
    max_requests=10,
    window_seconds=60.0,
    cooldown_seconds=2.0,
)
SIMULATION_START_POLICY = RequestPolicy(
    key="simulation_start",
    max_requests=10,
    window_seconds=60.0,
)
SIMULATE_POLICY = RequestPolicy(
    key="simulate",
    max_requests=8,
    window_seconds=60.0,
)
MISSION_STEP_POLICY = RequestPolicy(
    key="mission_step",
    max_requests=20,
    window_seconds=60.0,
)


def protect_recommend(request: Request) -> None:
    """Guard the recommendation endpoint with stricter AI limits."""

    request_protection.enforce(request, RECOMMEND_POLICY)


def protect_auth_register(request: Request) -> None:
    """Guard register requests."""

    request_protection.enforce(request, AUTH_REGISTER_POLICY)


def protect_auth_login(request: Request) -> None:
    """Guard login requests."""

    request_protection.enforce(request, AUTH_LOGIN_POLICY)


def protect_simulation_start(request: Request) -> None:
    """Guard simulation bootstrap requests."""

    request_protection.enforce(request, SIMULATION_START_POLICY)


def protect_simulate(request: Request) -> None:
    """Guard stateless simulation requests."""

    request_protection.enforce(request, SIMULATE_POLICY)


def protect_mission_step(request: Request) -> None:
    """Guard mission-step requests."""

    request_protection.enforce(request, MISSION_STEP_POLICY)
