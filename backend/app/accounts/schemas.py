import re
import unicodedata
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = unicodedata.normalize("NFC", value.strip()).lower()
        if not re.fullmatch(r"[a-z0-9가-힣_]{2,20}", value):
            raise ValueError("아이디는 한글, 영문, 숫자, 밑줄 2~20자로 입력하세요.")
        return value


class AccountRead(BaseModel):
    id: UUID
    username: str | None
    auth_mode: Literal["id-only", "local-development"]
