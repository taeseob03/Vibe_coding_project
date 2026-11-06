from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Record(Base):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    effect_status: Mapped[str] = mapped_column(String(20), default="not_requested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
