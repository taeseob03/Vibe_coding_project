from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Appearance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base: Literal["male", "female"] = "female"
    hair_length: Literal["short", "medium", "long"] = "long"
    hair_color: Literal["black", "brown", "blonde", "red", "blue", "pink", "silver"] = "black"


class Customization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grade: int | None = Field(default=None, ge=1, le=4)
    major: Literal["embedded", "computer", "ict"] | None = None
    appearance: Appearance = Field(default_factory=Appearance)
