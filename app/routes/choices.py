"""Crop choice endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.choice import CropChoiceCreate, CropChoiceResponse
from app.models.user import User
from app.services.choice_service import choice_service

router = APIRouter(tags=["choices"])


@router.post("/choose-crop", response_model=dict)
def choose_crop(payload: CropChoiceCreate, current_user: User = Depends(get_current_user)) -> dict:
    """Persist user crop selection with recommendation validation."""

    exists_in_top = choice_service.validate_choice_against_recommendations(
        payload.crop_name,
        payload.environment,
    )

    if not exists_in_top:
        warning = (
            "Selected crop is not in current top recommendation list; "
            "it will be saved as user-preferred but may be suboptimal."
        )
    else:
        warning = None

    choice = choice_service.create_choice(current_user.id, payload)

    response: dict = {
        "success": True,
        "choice": CropChoiceResponse.model_validate(choice).model_dump(),
    }

    if warning:
        response["warning"] = warning

    return response


@router.get("/my-choices", response_model=list[CropChoiceResponse])
def my_choices(current_user: User = Depends(get_current_user)) -> list[CropChoiceResponse]:
    choices = choice_service.list_choices(current_user.id)
    return [CropChoiceResponse.model_validate(choice) for choice in choices]
