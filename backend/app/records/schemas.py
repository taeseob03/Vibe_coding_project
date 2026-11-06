from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.analysis.schemas import AnalysisResult


class RecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=10000)


class RecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    text: str
    status: Literal["pending", "processing", "completed", "failed"]
    analysis: AnalysisResult | None
    effect_status: Literal["not_requested", "pending", "applied", "failed"]
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return (
            value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
            if value.tzinfo is None
            else value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        )
