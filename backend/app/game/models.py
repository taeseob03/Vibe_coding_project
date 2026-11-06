from uuid import uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Title(Base):
    __tablename__ = "character_titles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    title_id: Mapped[str] = mapped_column(String(40), primary_key=True)


class Lounge(Base):
    __tablename__ = "lounges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)


class Member(Base):
    __tablename__ = "lounge_members"
    room_id: Mapped[str] = mapped_column(ForeignKey("lounges.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Invitation(Base):
    __tablename__ = "lounge_invitations"
    __table_args__ = (UniqueConstraint("room_id", "recipient_id", name="uq_lounge_recipient"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    room_id: Mapped[str] = mapped_column(ForeignKey("lounges.id"), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
