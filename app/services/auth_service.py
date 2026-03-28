from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.models.user import TokenResponse, User, UserCreate
from app.utils.loaders import DATA_DIR, load_json_file


SECRET_KEY = "a7549d7a54076d8f4af3f0c5d49d945e9f6da2a9e7a04a3a8f670a11d5c9f9a2"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
USER_STORE_PATH = DATA_DIR / "users.json"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Simple file-backed user and token service for MVP auth."""

    def __init__(self, user_store_path: Path | None = None) -> None:
        self.user_store_path = user_store_path or USER_STORE_PATH
        self._users: dict[str, User] = {}
        self._load_users()

    def _load_users(self) -> None:
        try:
            raw = load_json_file(self.user_store_path)
            self._users = {
                entry["username"]: User.model_validate(entry)
                for entry in raw
                if "username" in entry
            }
        except FileNotFoundError:
            self._users = {}

    def _save_users(self) -> None:
        self.user_store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.user_store_path.open("w", encoding="utf-8") as f:
            json.dump([user.model_dump() for user in self._users.values()], f, ensure_ascii=False, indent=2)

    def create_user(self, user_data: UserCreate) -> User:
        if user_data.username in self._users:
            raise ValueError("username already exists")

        user = User(
            id=str(uuid4()),
            username=user_data.username,
            hashed_password=self.hash_password(user_data.password),
        )
        self._users[user.username] = user
        self._save_users()
        return user

    def authenticate_user(self, username: str, password: str) -> User | None:
        user = self._users.get(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as exc:
            raise ValueError("Invalid token") from exc


auth_service = AuthService()
