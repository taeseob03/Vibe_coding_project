"""User-owned feed content and mutually accepted friend requests for the local app."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WebPost(Base):
    __tablename__ = "web_posts"
    __table_args__ = (UniqueConstraint("user_id", "request_id", name="uq_web_post_request"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    fingerprint: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True, nullable=True)
    image_mime: Mapped[str | None] = mapped_column(String(30), nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(20))
    analysis_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WebFriendRequest(Base):
    __tablename__ = "web_friend_requests"
    __table_args__ = (UniqueConstraint("user_low", "user_high", name="uq_web_friend_pair"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_low: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    user_high: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
