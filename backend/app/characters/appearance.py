from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Appearance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base: Literal["male", "female"] = "female"
    hair_length: Literal["short", "medium", "long"] = "long"
    hair_color: Literal["black", "brown", "blonde", "red", "blue", "pink", "silver"] = "black"


class ProfileLook(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grade: int = Field(default=1, ge=1, le=4, strict=True)
    major: Literal["embedded", "computer", "ict"] = "computer"
    appearance: Appearance = Field(default_factory=Appearance)
