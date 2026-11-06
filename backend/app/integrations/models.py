from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ActivityRecord(Base):
    __tablename__ = "activity_records"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_activity_request"),
        UniqueConstraint("user_id", "applied_order", name="uq_activity_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    fingerprint: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    image_mime: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    analysis_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stat_status: Mapped[str] = mapped_column(String(20), default="pending")
    state_error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stats_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    source: Mapped[str] = mapped_column(String(20), default="gemini", server_default="gemini")
    applied_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stack_changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
