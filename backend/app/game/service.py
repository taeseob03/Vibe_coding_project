from datetime import UTC
from zoneinfo import ZoneInfo

from campus_records_prototype.effects import character_state
from campus_records_prototype.progress import calculate_snapshot
from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.characters.models import Character
from app.game.models import Invitation, Lounge, Member, Title
from app.integrations.models import ActivityRecord

TITLE_CATALOG = {
    "first_step": ("첫 발자국", "첫 활동 기록 반영"),
    "steady_challenger": ("꾸준한 도전자", "서로 다른 5일의 공부 기록"),
    "campus_explorer": ("캠퍼스 탐험가", "서로 다른 활동 3종 기록"),
}


def fail(code, message, status=409):
    raise HTTPException(status, detail={"code": code, "message": message})


def character_stats(character):
    return character.stats if character.stats is not None else calculate_snapshot([])[0]


def award_titles(db: Session, user_id: str):
    records = db.scalars(
        select(ActivityRecord).where(
            ActivityRecord.user_id == user_id, ActivityRecord.stat_status == "applied"
        )
    ).all()
    earned = set()
    if records:
        earned.add("first_step")
    if len({record.category for record in records}) >= 3:
        earned.add("campus_explorer")
    dates = {
        (
            record.created_at.replace(tzinfo=UTC)
            if record.created_at.tzinfo is None
            else record.created_at
        )
        .astimezone(ZoneInfo("Asia/Seoul"))
        .date()
        for record in records
        if record.category == "공부"
    }
    if len(dates) >= 5:
        earned.add("steady_challenger")
    new_first = "first_step" in earned and db.get(Title, (user_id, "first_step")) is None
    for title_id in earned:
        if db.get(Title, (user_id, title_id)) is None:
            db.add(Title(user_id=user_id, title_id=title_id))
    character = db.scalar(select(Character).where(Character.user_id == user_id))
    if character and not character.title_id and new_first:
        character.title_id = "first_step"


def user_view(db: Session, user_id: str):
    user = db.get(User, user_id)
    character = db.scalar(select(Character).where(Character.user_id == user_id))
    if user is None or character is None:
        fail("SETUP_REQUIRED", "최초 설정을 완료해 주세요.", 409)
    stats = character_stats(character)
    title = TITLE_CATALOG.get(character.title_id)
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "emoji": "🧑",
        "state": character_state(stats),
        "color": character.color,
        "stats": stats,
        "counts": {item["category"]: item["count"] for item in stats},
        "title": title[0] if title else None,
    }


def own_room(db: Session, user_id: str):
    user_view(db, user_id)
    room = db.scalar(select(Lounge).where(Lounge.owner_id == user_id))
    if room is None:
        room = Lounge(owner_id=user_id)
        db.add(room)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            room = db.scalar(select(Lounge).where(Lounge.owner_id == user_id))
            if room is None:
                raise
    if db.get(Member, (room.id, user_id)) is None:
        db.add(Member(room_id=room.id, user_id=user_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.get(Member, (room.id, user_id)) is None:
            raise
    return room


def require_member(db: Session, user_id: str, room_id: str):
    if db.get(Member, (room_id, user_id)) is None:
        fail("LOUNGE_NOT_FOUND", "참여 중인 라운지를 찾을 수 없습니다.", 404)


def members(db: Session, user_id: str, room_id: str):
    require_member(db, user_id, room_id)
    ids = db.scalars(
        select(Member.user_id).where(Member.room_id == room_id).order_by(Member.user_id)
    ).all()
    return [user_view(db, uid) for uid in ids]


def invite(db: Session, user_id: str, room_id: str, recipient_id: str):
    locked = db.execute(
        update(Lounge)
        .where(Lounge.id == room_id, Lounge.owner_id == user_id)
        .values(owner_id=Lounge.owner_id)
    )
    if locked.rowcount != 1:
        fail("LOUNGE_FORBIDDEN", "라운지 주인만 초대할 수 있습니다.", 403)
    if user_id == recipient_id:
        fail("SELF_INVITATION", "자신을 초대할 수 없습니다.")
    recipient = db.get(User, recipient_id)
    if recipient is None or not recipient.onboarding_completed:
        fail("USER_NOT_FOUND", "사용자를 찾을 수 없습니다.", 404)
    if db.get(Member, (room_id, recipient_id)):
        fail("ALREADY_MEMBER", "이미 참여 중인 사용자입니다.")
    invitation = db.scalar(
        select(Invitation).where(
            Invitation.room_id == room_id, Invitation.recipient_id == recipient_id
        )
    )
    if invitation and invitation.status == "pending":
        fail("INVITATION_PENDING", "이미 초대를 보냈습니다.")
    if invitation is None:
        invitation = Invitation(room_id=room_id, sender_id=user_id, recipient_id=recipient_id)
        db.add(invitation)
    else:
        invitation.status = "pending"
    db.commit()
    return {"id": invitation.id, "status": invitation.status}


def respond(db: Session, user_id: str, invitation_id: str, accept: bool):
    locked = db.execute(
        update(Invitation)
        .where(Invitation.id == invitation_id, Invitation.recipient_id == user_id)
        .values(status=Invitation.status)
    )
    if locked.rowcount != 1:
        fail("INVITATION_NOT_FOUND", "초대를 찾을 수 없습니다.", 404)
    invitation = db.get(Invitation, invitation_id)
    target = "accepted" if accept else "declined"
    if invitation.status != "pending" and invitation.status != target:
        fail("INVITATION_ALREADY_PROCESSED", "이미 처리한 초대입니다.")
    if invitation.status == "pending":
        invitation.status = target
        if accept and db.get(Member, (invitation.room_id, user_id)) is None:
            db.add(Member(room_id=invitation.room_id, user_id=user_id))
    db.commit()
    return {"id": invitation.id, "room_id": invitation.room_id, "status": invitation.status}


def invitations(db: Session, user_id: str):
    rows = db.scalars(
        select(Invitation).where(
            or_(Invitation.sender_id == user_id, Invitation.recipient_id == user_id)
        )
    ).all()
    return [
        {
            "id": row.id,
            "room_id": row.room_id,
            "sender_id": row.sender_id,
            "recipient_id": row.recipient_id,
            "status": row.status,
            "sender": {"nickname": db.get(User, row.sender_id).nickname},
            "recipient": {"nickname": db.get(User, row.recipient_id).nickname},
        }
        for row in rows
    ]
