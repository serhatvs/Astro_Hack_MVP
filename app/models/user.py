from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    username: str
    hashed_password: str


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = Field(default="bearer")
