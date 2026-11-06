from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.schemas import StatRead


class CharacterColor(StrEnum):
    green = "green"
    blue = "blue"
    yellow = "yellow"
    pink = "pink"
    purple = "purple"


class EffectId(StrEnum):
    book = "book"
    heart = "heart"
    dumbbell = "dumbbell"
    palette = "palette"
    star = "star"


class EffectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    effect_id: EffectId
    level: int = Field(ge=1)
    visible: bool


class EffectApplicationRead(BaseModel):
    record_id: UUID
    effect_status: Literal["applied"] = "applied"
    already_applied: bool
    effects: list[EffectRead]


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    color: CharacterColor
    effects: list[EffectRead] = Field(default_factory=list)

    stats: list[StatRead] = Field(default_factory=list)
