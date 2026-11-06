from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    color: Mapped[str] = mapped_column(String(20))

    stats: Mapped[list | None] = mapped_column(JSON, nullable=True)

    stat_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    title_id: Mapped[str | None] = mapped_column(String(40), nullable=True)

    appearance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
