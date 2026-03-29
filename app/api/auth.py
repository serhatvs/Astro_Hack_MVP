"""Minimal cookie-based authentication routes and helpers."""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.errors import (
    ACCOUNT_EXISTS_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    LOGIN_REQUIRED_MESSAGE,
    SESSION_EXPIRED_MESSAGE,
)
from app.api.protection import protect_auth_login, protect_auth_register
from app.models.auth import (
    AuthLoginRequest,
    AuthLogoutResponse,
    AuthRegisterRequest,
    AuthSessionResponse,
    AuthUser,
)
from app.services.auth import AccountExistsError, AuthService, get_auth_service


logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "astro_session"
LOCAL_AUTH_HOSTS = {"localhost", "127.0.0.1", "testserver"}

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_secure(request: Request) -> bool:
    host = (request.url.hostname or "").strip().lower()
    return host not in LOCAL_AUTH_HOSTS


def _cookie_samesite(request: Request) -> Literal["lax", "none"]:
    host = (request.url.hostname or "").strip().lower()
    origin = (request.headers.get("origin") or "").strip()
    origin_host = (urlparse(origin).hostname or "").strip().lower()

    if (
        origin_host
        and origin_host not in LOCAL_AUTH_HOSTS
        and host not in LOCAL_AUTH_HOSTS
        and origin_host != host
    ):
        return "none"
    return "lax"


def _set_session_cookie(response: Response, request: Request, session_token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite=_cookie_samesite(request),
        secure=_cookie_secure(request),
        max_age=60 * 60 * 12,
    )


def clear_session_cookie(response: Response, request: Request) -> None:
    """Remove the auth session cookie from the response."""

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=_cookie_secure(request),
        samesite=_cookie_samesite(request),
    )


def _session_token_from_request(request: Request) -> str | None:
    raw_session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_session_token is None:
        return None
    normalized = raw_session_token.strip()
    return normalized or None


def get_optional_current_user(
    request: Request,
) -> AuthUser | None:
    """Resolve the current user when a valid session exists."""

    session_token = _session_token_from_request(request)
    if session_token is None:
        request.state.auth_session_state = "missing"
        request.state.auth_subject = None
        return None

    auth_service = get_auth_service()
    user, state = auth_service.resolve_user_from_session(session_token)
    request.state.auth_session_state = state

    if user is None:
        request.state.auth_subject = None
        return None

    public_user = auth_service.to_public_user(user)
    request.state.auth_subject = f"user:{public_user.id}"
    request.state.current_user = public_user
    return public_user


def require_current_user(
    request: Request,
    current_user: AuthUser | None = Depends(get_optional_current_user),
) -> AuthUser:
    """Require a valid authenticated user for the current request."""

    if current_user is not None:
        return current_user

    session_state: Literal["missing", "expired", "ok"] | str = getattr(
        request.state,
        "auth_session_state",
        "missing",
    )
    detail = SESSION_EXPIRED_MESSAGE if session_state == "expired" else LOGIN_REQUIRED_MESSAGE
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


@router.post(
    "/register",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(protect_auth_register)],
)
def register(
    payload: AuthRegisterRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    """Create a new account and immediately open a session."""

    try:
        user = auth_service.register(payload.email, payload.password)
    except AccountExistsError as exc:
        logger.warning("Auth register rejected because %s already exists.", payload.email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ACCOUNT_EXISTS_MESSAGE) from exc

    session = auth_service.create_session(user.id)
    _set_session_cookie(response, request, session.session_token)
    return AuthSessionResponse(user=auth_service.to_public_user(user))


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    dependencies=[Depends(protect_auth_login)],
)
def login(
    payload: AuthLoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    """Authenticate a user and open a new session."""

    user = auth_service.authenticate(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS_MESSAGE)

    session = auth_service.create_session(user.id)
    _set_session_cookie(response, request, session.session_token)
    return AuthSessionResponse(user=auth_service.to_public_user(user))


@router.post("/logout", response_model=AuthLogoutResponse)
def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthLogoutResponse:
    """Invalidate the current session and clear the auth cookie."""

    session_token = _session_token_from_request(request)
    auth_service.revoke_session(session_token)
    clear_session_cookie(response, request)
    logger.info("Auth logout completed.")
    return AuthLogoutResponse(success=True)


@router.get("/me", response_model=AuthSessionResponse)
def me(current_user: AuthUser = Depends(require_current_user)) -> AuthSessionResponse:
    """Return the current authenticated user."""

    return AuthSessionResponse(user=current_user)
