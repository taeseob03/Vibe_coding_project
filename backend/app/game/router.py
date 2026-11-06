import os
from typing import Annotated
from uuid import UUID

from campus_records_prototype.effects import character_state
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.dependencies import AuthenticatedUser
from app.accounts.models import User
from app.characters.models import Character
from app.core.config import get_settings
from app.core.db import get_db
from app.game import service
from app.game.models import Lounge, Member, Title

router = APIRouter(prefix="/api", tags=["game and social"])
Database = Annotated[Session, Depends(get_db)]


class InviteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient_id: UUID


class RespondBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    accept: bool


class SelectTitle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title_id: str | None


@router.get("/runtime")
def runtime():
    return {
        "gemini_available": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "demo_available": get_settings().app_env == "development",
    }


@router.get("/me")
def me(user: AuthenticatedUser, db: Database):
    return service.user_view(db, user.id)


@router.get("/progress")
def progress(user: AuthenticatedUser, db: Database):
    stats = service.user_view(db, user.id)["stats"]
    return {"progress": stats, "state": character_state(stats)}


@router.get("/titles")
def titles(user: AuthenticatedUser, db: Database):
    character = db.scalar(select(Character).where(Character.user_id == user.id))
    if character is None:
        service.fail("SETUP_REQUIRED", "최초 설정을 완료해 주세요.")
    owned = set(db.scalars(select(Title.title_id).where(Title.user_id == user.id)).all())
    return [
        {
            "id": tid,
            "name": values[0],
            "description": values[1],
            "earned": tid in owned,
            "selected": character.title_id == tid,
        }
        for tid, values in service.TITLE_CATALOG.items()
    ]


@router.put("/titles/selected")
def select_title(body: SelectTitle, user: AuthenticatedUser, db: Database):
    character = db.scalar(select(Character).where(Character.user_id == user.id))
    if character is None:
        service.fail("SETUP_REQUIRED", "최초 설정을 완료해 주세요.")
    if body.title_id is not None and db.get(Title, (user.id, body.title_id)) is None:
        service.fail("TITLE_NOT_OWNED", "획득한 칭호만 선택할 수 있습니다.", 403)
    character.title_id = body.title_id
    db.commit()
    return {"title_id": character.title_id}


@router.get("/lounges")
def rooms(user: AuthenticatedUser, db: Database):
    own = service.own_room(db, user.id)
    rows = db.scalars(
        select(Lounge)
        .join(Member, Member.room_id == Lounge.id)
        .where(Member.user_id == user.id)
        .order_by(Lounge.id)
    ).all()
    rows.sort(key=lambda row: row.id != own.id)
    return [
        {
            "id": row.id,
            "owner_id": row.owner_id,
            "name": f"{db.get(User, row.owner_id).nickname}의 라운지",
        }
        for row in rows
    ]


@router.get("/lounges/{room_id}/members")
def members(room_id: UUID, user: AuthenticatedUser, db: Database):
    return service.members(db, user.id, str(room_id))


@router.get("/users")
def search(
    user: AuthenticatedUser, db: Database, nickname: str = Query(min_length=1, max_length=30)
):
    query = nickname.strip()
    if not query:
        return []
    rows = db.scalars(
        select(User)
        .where(
            User.id != user.id,
            User.onboarding_completed.is_(True),
            User.nickname.contains(query, autoescape=True),
        )
        .limit(20)
    ).all()
    return [
        {"id": row.id, "username": row.username, "nickname": row.nickname, "emoji": "🧑"}
        for row in rows
    ]


@router.post("/lounges/{room_id}/invitations", status_code=201)
def invite(room_id: UUID, body: InviteBody, user: AuthenticatedUser, db: Database):
    return service.invite(db, user.id, str(room_id), str(body.recipient_id))


@router.get("/lounge-invitations")
def invitations(user: AuthenticatedUser, db: Database):
    return service.invitations(db, user.id)


@router.post("/lounge-invitations/{invitation_id}/response")
def respond(invitation_id: UUID, body: RespondBody, user: AuthenticatedUser, db: Database):
    return service.respond(db, user.id, str(invitation_id), body.accept)
