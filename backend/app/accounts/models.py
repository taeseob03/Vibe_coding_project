from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # 기존 개발 사용자와 기록은 유지합니다. 실제 접속 계정만 username을 갖습니다.
    username: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)

    nickname: Mapped[str | None] = mapped_column(String(12), nullable=True)
    draft_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    setup_step: Mapped[str] = mapped_column(
        String(20), default="nickname", server_default="nickname"
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )

    grade: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    major: Mapped[str] = mapped_column(String(20), default="computer", server_default="computer")
    draft_appearance: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class LoginSession(Base):
    __tablename__ = "login_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
