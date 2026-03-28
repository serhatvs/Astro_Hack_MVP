from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CropChoiceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_name: str
    environment: str | None = None


class CropChoiceCreate(CropChoiceBase):
    pass


class CropChoice(CropChoiceBase):
    id: str
    user_id: str
    timestamp: datetime


class CropChoiceResponse(CropChoice):
    pass
