"""Auth request and response models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized or "@" not in normalized:
        raise ValueError("invalid email")
    local_part, _, domain = normalized.partition("@")
    if not local_part or not domain or "." not in domain:
        raise ValueError("invalid email")
    return normalized


class AuthUser(BaseModel):
    """Public user payload returned by auth endpoints."""

    id: str
    email: str
    created_at: datetime
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class AuthSessionResponse(BaseModel):
    """Authenticated user response."""

    user: AuthUser


class AuthRegisterRequest(BaseModel):
    """Register payload."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        password = value.strip()
        if len(password) < 8:
            raise ValueError("password too short")
        return password


class AuthLoginRequest(AuthRegisterRequest):
    """Login payload."""


class AuthLogoutResponse(BaseModel):
    """Logout response."""

    success: bool = True


class StoredUser(BaseModel):
    """Persistent user representation stored on disk."""

    id: str
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)
