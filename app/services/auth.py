"""Database-backed MVP auth service with persistent sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from threading import Lock
from urllib.parse import unquote, urlparse

from app.models.auth import AuthUser, StoredSession, StoredUser


logger = logging.getLogger(__name__)

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 310_000
PASSWORD_SALT_BYTES = 16
SESSION_TTL_HOURS = 12


class AuthError(ValueError):
    """Base auth error."""


class AccountExistsError(AuthError):
    """Raised when a user already exists."""


class DatabaseAuthStore:
    """Minimal auth persistence layer backed by Postgres in deploys."""

    def __init__(self, database_url: str) -> None:
        normalized_url = database_url.strip()
        if not normalized_url:
            raise RuntimeError("DATABASE_URL is required for auth persistence.")

        self.database_url = normalized_url
        self.backend = "sqlite" if normalized_url.startswith("sqlite") else "postgresql"
        self._schema_lock = Lock()
        self._schema_ready = False

    def initialize(self) -> None:
        """Create auth tables if they do not already exist."""

        if self._schema_ready:
            return

        with self._schema_lock:
            if self._schema_ready:
                return

            if self.backend == "sqlite":
                with self._sqlite_connection() as connection:
                    connection.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS users (
                            id TEXT PRIMARY KEY,
                            email TEXT NOT NULL UNIQUE,
                            password_hash TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            is_active INTEGER NOT NULL DEFAULT 1
                        );

                        CREATE TABLE IF NOT EXISTS sessions (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            session_token TEXT NOT NULL UNIQUE,
                            created_at TEXT NOT NULL,
                            expires_at TEXT NOT NULL,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                        );

                        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
                        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                        """
                    )
            else:
                with self._postgres_connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS users (
                                id TEXT PRIMARY KEY,
                                email TEXT NOT NULL UNIQUE,
                                password_hash TEXT NOT NULL,
                                created_at TIMESTAMPTZ NOT NULL,
                                is_active BOOLEAN NOT NULL DEFAULT TRUE
                            );
                            """
                        )
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS sessions (
                                id TEXT PRIMARY KEY,
                                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                session_token TEXT NOT NULL UNIQUE,
                                created_at TIMESTAMPTZ NOT NULL,
                                expires_at TIMESTAMPTZ NOT NULL
                            );
                            """
                        )
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);"
                        )
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);"
                        )

            self._schema_ready = True
            logger.info("Auth schema ensured on %s backend.", self.backend)

    def get_user_by_email(self, email: str) -> StoredUser | None:
        """Return a user for the given normalized email."""

        self.initialize()
        normalized_email = email.strip().lower()
        row = self._fetchone(
            postgres_sql=(
                "SELECT id, email, password_hash, created_at, is_active "
                "FROM users WHERE email = %s"
            ),
            sqlite_sql=(
                "SELECT id, email, password_hash, created_at, is_active "
                "FROM users WHERE email = ?"
            ),
            params=(normalized_email,),
        )
        return StoredUser.model_validate(row) if row is not None else None

    def get_user_by_id(self, user_id: str) -> StoredUser | None:
        """Return a user by id."""

        self.initialize()
        row = self._fetchone(
            postgres_sql=(
                "SELECT id, email, password_hash, created_at, is_active "
                "FROM users WHERE id = %s"
            ),
            sqlite_sql=(
                "SELECT id, email, password_hash, created_at, is_active "
                "FROM users WHERE id = ?"
            ),
            params=(user_id,),
        )
        return StoredUser.model_validate(row) if row is not None else None

    def create_user(self, *, email: str, password_hash: str) -> StoredUser:
        """Insert a new user into the auth database."""

        self.initialize()
        normalized_email = email.strip().lower()
        created_at = datetime.now(timezone.utc)
        user_id = secrets.token_urlsafe(16)

        if self.backend == "sqlite":
            with self._sqlite_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO users (id, email, password_hash, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, normalized_email, password_hash, created_at.isoformat(), 1),
                )
                if cursor.rowcount == 0:
                    raise AccountExistsError(normalized_email)
                row = connection.execute(
                    """
                    SELECT id, email, password_hash, created_at, is_active
                    FROM users
                    WHERE id = ?
                    """,
                    (user_id,),
                ).fetchone()
        else:
            with self._postgres_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (id, email, password_hash, created_at, is_active)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT(email) DO NOTHING
                        RETURNING id, email, password_hash, created_at, is_active
                        """,
                        (user_id, normalized_email, password_hash, created_at, True),
                    )
                    row = cursor.fetchone()
            if row is None:
                raise AccountExistsError(normalized_email)

        if row is None:
            raise RuntimeError("Failed to persist auth user.")

        logger.info("Auth register succeeded for %s.", normalized_email)
        return StoredUser.model_validate(self._normalize_row(row))

    def create_session(self, user_id: str, *, ttl_hours: int = SESSION_TTL_HOURS) -> StoredSession:
        """Create and persist a new login session."""

        self.initialize()
        self.delete_expired_sessions()
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=ttl_hours)
        session_id = secrets.token_urlsafe(16)
        session_token = secrets.token_urlsafe(32)

        if self.backend == "sqlite":
            with self._sqlite_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO sessions (id, user_id, session_token, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        user_id,
                        session_token,
                        created_at.isoformat(),
                        expires_at.isoformat(),
                    ),
                )
                row = connection.execute(
                    """
                    SELECT id, user_id, session_token, created_at, expires_at
                    FROM sessions
                    WHERE id = ?
                    """,
                    (session_id,),
                ).fetchone()
        else:
            with self._postgres_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO sessions (id, user_id, session_token, created_at, expires_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, user_id, session_token, created_at, expires_at
                        """,
                        (session_id, user_id, session_token, created_at, expires_at),
                    )
                    row = cursor.fetchone()

        if row is None:
            raise RuntimeError("Failed to persist auth session.")

        return StoredSession.model_validate(self._normalize_row(row))

    def get_session(self, session_token: str | None) -> tuple[StoredSession | None, str]:
        """Return a session by token and report whether it is valid, missing, or expired."""

        if not session_token:
            return None, "missing"

        self.initialize()
        row = self._fetchone(
            postgres_sql=(
                "SELECT id, user_id, session_token, created_at, expires_at "
                "FROM sessions WHERE session_token = %s"
            ),
            sqlite_sql=(
                "SELECT id, user_id, session_token, created_at, expires_at "
                "FROM sessions WHERE session_token = ?"
            ),
            params=(session_token,),
        )
        if row is None:
            return None, "missing"

        session = StoredSession.model_validate(row)
        if session.expires_at <= datetime.now(timezone.utc):
            self.delete_session(session_token)
            return None, "expired"
        return session, "ok"

    def delete_session(self, session_token: str | None) -> None:
        """Delete a session token from the auth database."""

        if not session_token:
            return

        self.initialize()
        self._execute(
            postgres_sql="DELETE FROM sessions WHERE session_token = %s",
            sqlite_sql="DELETE FROM sessions WHERE session_token = ?",
            params=(session_token,),
        )

    def delete_expired_sessions(self) -> None:
        """Remove expired sessions to keep the table tidy."""

        self.initialize()
        now = datetime.now(timezone.utc)
        sqlite_timestamp = now.isoformat()
        self._execute(
            postgres_sql="DELETE FROM sessions WHERE expires_at <= %s",
            sqlite_sql="DELETE FROM sessions WHERE expires_at <= ?",
            params=(now if self.backend == "postgresql" else sqlite_timestamp,),
        )

    def reset(self) -> None:
        """Clear auth tables. Used by tests."""

        self.initialize()
        if self.backend == "sqlite":
            with self._sqlite_connection() as connection:
                connection.execute("DELETE FROM sessions")
                connection.execute("DELETE FROM users")
        else:
            with self._postgres_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM sessions")
                    cursor.execute("DELETE FROM users")

    def _fetchone(
        self,
        *,
        postgres_sql: str,
        sqlite_sql: str,
        params: tuple[object, ...],
    ) -> dict[str, object] | None:
        if self.backend == "sqlite":
            with self._sqlite_connection() as connection:
                row = connection.execute(sqlite_sql, params).fetchone()
        else:
            with self._postgres_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(postgres_sql, params)
                    row = cursor.fetchone()

        return self._normalize_row(row) if row is not None else None

    def _execute(
        self,
        *,
        postgres_sql: str,
        sqlite_sql: str,
        params: tuple[object, ...],
    ) -> None:
        if self.backend == "sqlite":
            with self._sqlite_connection() as connection:
                connection.execute(sqlite_sql, params)
            return

        with self._postgres_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(postgres_sql, params)

    def _normalize_row(self, row: sqlite3.Row | Mapping[str, object] | None) -> dict[str, object] | None:
        if row is None:
            return None

        normalized = dict(row)
        if "is_active" in normalized:
            normalized["is_active"] = bool(normalized["is_active"])
        return normalized

    def _sqlite_connection(self) -> sqlite3.Connection:
        path = self._sqlite_path_from_url(self.database_url)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _postgres_connection(self):  # type: ignore[no-untyped-def]
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - depends on deploy environment
            raise RuntimeError("psycopg is required for PostgreSQL auth persistence.") from exc

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _sqlite_path_from_url(self, database_url: str) -> str:
        parsed = urlparse(database_url)
        raw_path = unquote(parsed.path or "")

        if raw_path == "/:memory:":
            return ":memory:"

        if raw_path.startswith("/") and len(raw_path) >= 3 and raw_path[2] == ":":
            return raw_path[1:]

        if raw_path:
            return raw_path

        raise RuntimeError("sqlite DATABASE_URL must include a database path.")


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


class AuthService:
    """Small auth service built on a persistent database store."""

    def __init__(self, store: DatabaseAuthStore) -> None:
        self.store = store

    def initialize(self) -> None:
        """Ensure auth tables exist before serving auth operations."""

        self.store.initialize()

    def register(self, email: str, password: str) -> StoredUser:
        """Create a user account."""

        return self.store.create_user(email=email, password_hash=hash_password(password))

    def authenticate(self, email: str, password: str) -> StoredUser | None:
        """Validate credentials and return the user when valid."""

        normalized = email.strip().lower()
        user = self.store.get_user_by_email(normalized)
        if user is None or not user.is_active:
            logger.warning("Auth login failed for %s.", normalized)
            return None
        if not verify_password(password, user.password_hash):
            logger.warning("Auth login failed for %s.", normalized)
            return None
        logger.info("Auth login succeeded for %s.", normalized)
        return user

    def create_session(self, user_id: str) -> StoredSession:
        """Create a new persistent session for the given user."""

        return self.store.create_session(user_id)

    def revoke_session(self, session_token: str | None) -> None:
        """Invalidate a session."""

        self.store.delete_session(session_token)

    def resolve_user_from_session(self, session_token: str | None) -> tuple[StoredUser | None, str]:
        """Resolve the current authenticated user from a session token."""

        if not session_token:
            return None, "missing"

        session, status = self.store.get_session(session_token)
        if session is None:
            return None, status

        user = self.store.get_user_by_id(session.user_id)
        if user is None or not user.is_active:
            self.store.delete_session(session.session_token)
            return None, "missing"

        return user, "ok"

    def to_public_user(self, user: StoredUser) -> AuthUser:
        """Convert a stored user into its public representation."""

        return AuthUser.model_validate(user)

    def reset(self) -> None:
        """Reset auth state used by tests."""

        self.store.reset()


@lru_cache
def get_auth_service() -> AuthService:
    """Return the shared auth service instance."""

    database_url = os.getenv("DATABASE_URL", "").strip()
    service = AuthService(store=DatabaseAuthStore(database_url))
    service.initialize()
    return service
