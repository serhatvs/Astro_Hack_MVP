"""Minimal auth service with JSON-backed users and in-memory sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from threading import Lock

from app.models.auth import AuthUser, StoredUser


logger = logging.getLogger(__name__)

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 310_000
PASSWORD_SALT_BYTES = 16
SESSION_TTL_HOURS = 12


class AuthError(ValueError):
    """Base auth error."""


class AccountExistsError(AuthError):
    """Raised when a user already exists."""


@dataclass(frozen=True)
class SessionRecord:
    """Active authenticated session."""

    session_id: str
    user_id: str
    expires_at: datetime


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC."""

    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    salt_token = base64.b64encode(salt).decode("ascii")
    digest_token = base64.b64encode(digest).decode("ascii")
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt_token}${digest_token}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its stored PBKDF2 hash."""

    try:
        algorithm, raw_iterations, salt_token, digest_token = password_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(raw_iterations)
        salt = base64.b64decode(salt_token.encode("ascii"))
        expected_digest = base64.b64decode(digest_token.encode("ascii"))
    except (TypeError, ValueError, base64.binascii.Error):
        logger.warning("Invalid password hash encountered while verifying auth credentials.")
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest, expected_digest)


class JSONUserStore:
    """Very small JSON user store for MVP auth."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()

    def list_users(self) -> list[StoredUser]:
        """Load all users from disk."""

        with self._lock:
            if not self.path.exists():
                return []

            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.exception("Failed to parse auth user store at %s.", self.path)
                return []

        if not isinstance(payload, list):
            logger.warning("Unexpected auth user store shape at %s; falling back to an empty list.", self.path)
            return []

        users: list[StoredUser] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            users.append(StoredUser.model_validate(item))
        return users

    def get_by_email(self, email: str) -> StoredUser | None:
        """Look up a user by normalized email."""

        normalized = email.strip().lower()
        for user in self.list_users():
            if user.email == normalized:
                return user
        return None

    def get_by_id(self, user_id: str) -> StoredUser | None:
        """Look up a user by id."""

        for user in self.list_users():
            if user.id == user_id:
                return user
        return None

    def create_user(self, *, email: str, password_hash: str) -> StoredUser:
        """Create and persist a new user."""

        normalized = email.strip().lower()

        with self._lock:
            users = self._load_users_unlocked()
            if any(user.email == normalized for user in users):
                raise AccountExistsError(normalized)

            user = StoredUser(
                id=secrets.token_urlsafe(16),
                email=normalized,
                password_hash=password_hash,
            )
            users.append(user)
            self._write_users_unlocked(users)
            logger.info("Auth register succeeded for %s.", normalized)
            return user

    def _load_users_unlocked(self) -> list[StoredUser]:
        if not self.path.exists():
            return []

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.exception("Failed to parse auth user store at %s.", self.path)
            return []

        if not isinstance(payload, list):
            logger.warning("Unexpected auth user store shape at %s; falling back to an empty list.", self.path)
            return []

        users: list[StoredUser] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            users.append(StoredUser.model_validate(item))
        return users

    def _write_users_unlocked(self, users: list[StoredUser]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        serialized = [user.model_dump(mode="json") for user in users]
        temp_path.write_text(json.dumps(serialized, ensure_ascii=True, indent=2), encoding="utf-8")
        temp_path.replace(self.path)


class InMemorySessionStore:
    """Server-side session store."""

    def __init__(self, ttl_hours: int = SESSION_TTL_HOURS) -> None:
        self.ttl_hours = ttl_hours
        self._lock = Lock()
        self._sessions: dict[str, SessionRecord] = {}

    def create(self, user_id: str) -> SessionRecord:
        """Create a new server-side session."""

        now = datetime.now(timezone.utc)
        record = SessionRecord(
            session_id=secrets.token_urlsafe(32),
            user_id=user_id,
            expires_at=now + timedelta(hours=self.ttl_hours),
        )
        with self._lock:
            self._sessions[record.session_id] = record
            self._prune_expired_unlocked(now)
        return record

    def get(self, session_id: str) -> tuple[SessionRecord | None, str]:
        """Resolve a session by id."""

        if not session_id:
            return None, "missing"

        now = datetime.now(timezone.utc)
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None, "missing"
            if record.expires_at <= now:
                self._sessions.pop(session_id, None)
                return None, "expired"
            return record, "ok"

    def delete(self, session_id: str | None) -> None:
        """Invalidate a session."""

        if not session_id:
            return
        with self._lock:
            self._sessions.pop(session_id, None)

    def reset(self) -> None:
        """Clear all sessions. Used in tests."""

        with self._lock:
            self._sessions.clear()

    def _prune_expired_unlocked(self, now: datetime) -> None:
        expired = [key for key, value in self._sessions.items() if value.expires_at <= now]
        for key in expired:
            self._sessions.pop(key, None)


class AuthService:
    """MVP authentication service with cookie-backed sessions."""

    def __init__(
        self,
        user_store: JSONUserStore,
        session_store: InMemorySessionStore | None = None,
    ) -> None:
        self.user_store = user_store
        self.session_store = session_store or InMemorySessionStore()

    def register(self, email: str, password: str) -> StoredUser:
        """Create a user account."""

        return self.user_store.create_user(email=email, password_hash=hash_password(password))

    def authenticate(self, email: str, password: str) -> StoredUser | None:
        """Validate credentials and return the user when valid."""

        normalized = email.strip().lower()
        user = self.user_store.get_by_email(normalized)
        if user is None or not user.is_active:
            logger.warning("Auth login failed for %s.", normalized)
            return None
        if not verify_password(password, user.password_hash):
            logger.warning("Auth login failed for %s.", normalized)
            return None
        logger.info("Auth login succeeded for %s.", normalized)
        return user

    def create_session(self, user_id: str) -> SessionRecord:
        """Create a new session for the given user."""

        return self.session_store.create(user_id)

    def revoke_session(self, session_id: str | None) -> None:
        """Invalidate a session."""

        self.session_store.delete(session_id)

    def resolve_user_from_session(self, session_id: str | None) -> tuple[StoredUser | None, str]:
        """Resolve the current authenticated user from a session id."""

        if not session_id:
            return None, "missing"

        record, status = self.session_store.get(session_id)
        if record is None:
            return None, status

        user = self.user_store.get_by_id(record.user_id)
        if user is None or not user.is_active:
            self.session_store.delete(record.session_id)
            return None, "missing"

        return user, "ok"

    def to_public_user(self, user: StoredUser) -> AuthUser:
        """Convert a stored user into its public representation."""

        return AuthUser.model_validate(user)

    def reset(self) -> None:
        """Reset in-memory auth state used by tests."""

        self.session_store.reset()


@lru_cache
def get_auth_service() -> AuthService:
    """Return the shared auth service instance."""

    configured_path = os.getenv("AUTH_USER_STORE_PATH", "data/users.json").strip() or "data/users.json"
    return AuthService(user_store=JSONUserStore(Path(configured_path)))
