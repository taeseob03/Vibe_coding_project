from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from campus_records_prototype.analysis import KeywordResult
from campus_records_prototype.effects import CharacterEffect
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class StatRead(CharacterEffect):
    category: str
    count: int = Field(ge=0)
    level: int = Field(ge=0)
    color: str


class SafeError(BaseModel):
    code: str
    message: str


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    request_id: UUID
    text: str
    has_image: bool
    source: Literal["gemini", "demo"] = "gemini"
    stack_changes: dict[str, int] | None = None
    status: Literal["pending", "processing", "completed", "failed"]
    analysis: KeywordResult | None
    analysis_error: SafeError | None
    stat_status: Literal["pending", "applied", "skipped", "failed"]
    state_error: SafeError | None
    stats_snapshot: list[StatRead] | None
    created_at: datetime

    @field_serializer("created_at")
    def utc_time(self, value: datetime):
        return (
            value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
            if value.tzinfo is None
            else value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        )
