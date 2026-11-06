from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CharacterEffect(Base):
    __tablename__ = "character_effects"
    __table_args__ = (CheckConstraint("level >= 1", name="ck_character_effect_level"),)

    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id"), primary_key=True)
    effect_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    level: Mapped[int] = mapped_column(Integer)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)


class EffectGrant(Base):
    __tablename__ = "effect_grants"

    # 기록 ID 자체가 PK이므로 동일 기록의 보상은 하나뿐입니다.
    record_id: Mapped[str] = mapped_column(ForeignKey("records.id"), primary_key=True)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    effects_snapshot: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
