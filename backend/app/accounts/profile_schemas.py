from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.characters.appearance import Appearance, ProfileLook
from app.characters.schemas import CharacterColor, CharacterRead


class ProfileDraft(ProfileLook):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nickname: str = Field(default="", max_length=12)
    color: CharacterColor | None = None
    step: Literal["nickname", "color"] = "nickname"

    @model_validator(mode="after")
    def validate_step(self):
        if self.step == "color" and len(self.nickname) < 2:
            raise ValueError("닉네임을 2~12자로 입력하세요.")
        return self


class ProfileComplete(ProfileLook):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nickname: str = Field(min_length=2, max_length=12)
    color: CharacterColor


class ProfileRead(BaseModel):
    user_id: UUID
    nickname: str | None
    color: CharacterColor | None
    step: Literal["nickname", "color"]
    grade: int = 1
    major: str = "computer"
    appearance: Appearance = Field(default_factory=Appearance)
    onboarding_completed: bool


class SetupRead(BaseModel):
    profile: ProfileRead
    character: CharacterRead
