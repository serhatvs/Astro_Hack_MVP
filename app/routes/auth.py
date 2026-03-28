"""Authentication endpoints."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import TokenResponse, User, UserCreate
from app.services.auth_service import auth_service

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=User)
def register(user_data: UserCreate) -> User:
    try:
        return auth_service.create_user(user_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserCreate) -> TokenResponse:
    user = auth_service.authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    access_token = auth_service.create_access_token({"sub": user.username}, expires_delta=timedelta(minutes=60))
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=User)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
