import base64
import json
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.dependencies import AuthenticatedUser
from app.accounts.models import User
from app.core.db import get_db
from app.preview.models import WebFriendRequest, WebPost

router = APIRouter(prefix="/api", tags=["INUstagram feed"])
Database = Annotated[Session, Depends(get_db)]


def friend_ids(db: Session, user_id: str):
    pairs = db.scalars(
        select(WebFriendRequest).where(
            WebFriendRequest.status == "accepted",
            or_(WebFriendRequest.user_low == user_id, WebFriendRequest.user_high == user_id),
        )
    ).all()
    return {row.user_high if row.user_low == user_id else row.user_low for row in pairs}


def author(user: User):
    return {"id": user.id, "nickname": user.nickname or user.username or "사용자", "emoji": "🧑"}


def stamp(value: datetime):
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def cursor_for(post: WebPost):
    return (
        base64.urlsafe_b64encode(
            json.dumps({"created": stamp(post.created_at), "id": post.id}).encode()
        )
        .decode()
        .rstrip("=")
    )


def parse_cursor(value: str):
    try:
        data = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
        created = datetime.fromisoformat(data["created"])
        if created.tzinfo is None:
            raise ValueError()
        return created.astimezone(UTC), str(UUID(data["id"]))
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise HTTPException(422, "게시물 조회 위치를 확인해 주세요.") from exc


@router.get("/feed")
def feed(
    user: AuthenticatedUser,
    db: Database,
    scope: Literal["all", "mine", "friends"] = "all",
    limit: int = Query(12, ge=1, le=50),
    before: str | None = Query(None, max_length=512),
):
    allowed = friend_ids(db, user.id) if scope != "mine" else set()
    if scope != "friends":
        allowed.add(user.id)
    query = select(WebPost).where(WebPost.user_id.in_(allowed))
    if before:
        time, identifier = parse_cursor(before)
        query = query.where(
            or_(
                WebPost.created_at < time, and_(WebPost.created_at == time, WebPost.id < identifier)
            )
        )
    rows = db.scalars(
        query.order_by(WebPost.created_at.desc(), WebPost.id.desc()).limit(limit + 1)
    ).all()
    more = len(rows) > limit
    rows = rows[:limit]
    people = {
        person.id: person
        for person in db.scalars(
            select(User).where(User.id.in_({post.user_id for post in rows}))
        ).all()
    }
    posts = [
        {
            "id": post.id,
            "author": author(people[post.user_id]),
            "text": post.text,
            "image_url": f"/api/posts/{post.id}/image" if post.image_mime else None,
            "keywords": (post.analysis_data or {}).get("keywords", []),
            "analysis_status": post.analysis_status,
            "created_at": stamp(post.created_at),
        }
        for post in rows
    ]
    return {"posts": posts, "next_cursor": cursor_for(rows[-1]) if more and rows else None}


@router.get("/posts/{post_id}/image")
def image(post_id: UUID, user: AuthenticatedUser, db: Database):
    post = db.get(WebPost, str(post_id))
    if (
        post is None
        or post.user_id not in {user.id, *friend_ids(db, user.id)}
        or not post.image_mime
    ):
        raise HTTPException(404, "사진을 찾을 수 없습니다.")
    return Response(
        post.image_data,
        media_type=post.image_mime,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/people")
def search_people(user: AuthenticatedUser, db: Database, nickname: str = Query("", max_length=30)):
    query = nickname.strip()
    if not query:
        return []
    users = db.scalars(
        select(User)
        .where(
            User.id != user.id,
            User.onboarding_completed.is_(True),
            User.nickname.contains(query, autoescape=True),
        )
        .order_by(User.nickname, User.id)
        .limit(20)
    ).all()
    pairs = db.scalars(
        select(WebFriendRequest).where(
            or_(WebFriendRequest.user_low == user.id, WebFriendRequest.user_high == user.id)
        )
    ).all()
    relationships = {p.user_high if p.user_low == user.id else p.user_low: p for p in pairs}
    results = []
    for person in users:
        pair = relationships.get(person.id)
        relation = "none"
        if pair and pair.status == "accepted":
            relation = "friend"
        elif pair and pair.status == "pending":
            relation = "outgoing" if pair.requester_id == user.id else "incoming"
        results.append({**author(person), "relationship": relation})
    return results


@router.get("/friends")
def friends(user: AuthenticatedUser, db: Database):
    pairs = db.scalars(
        select(WebFriendRequest)
        .where(or_(WebFriendRequest.user_low == user.id, WebFriendRequest.user_high == user.id))
        .order_by(WebFriendRequest.created_at.desc())
    ).all()
    others = {p.user_high if p.user_low == user.id else p.user_low for p in pairs}
    users = {p.id: p for p in db.scalars(select(User).where(User.id.in_(others))).all()}
    result = {"friends": [], "incoming": [], "outgoing": []}
    for pair in pairs:
        person = users[pair.user_high if pair.user_low == user.id else pair.user_low]
        item = {"id": pair.id, "person": author(person)}
        if pair.status == "accepted":
            result["friends"].append(author(person))
        elif pair.status == "pending":
            result["outgoing" if pair.requester_id == user.id else "incoming"].append(item)
    return result


class FriendCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient_id: UUID


class FriendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    accept: bool


@router.post("/friend-requests", status_code=201)
def request_friend(body: FriendCreate, user: AuthenticatedUser, db: Database):
    if not db.get(User, user.id).onboarding_completed:
        raise HTTPException(409, "최초 설정을 완료한 뒤 친구를 등록해 주세요.")
    recipient = str(body.recipient_id)
    person = db.get(User, recipient)
    if person is None or not person.onboarding_completed or recipient == user.id:
        raise HTTPException(400, "친구로 등록할 사용자를 확인해 주세요.")
    low, high = sorted([user.id, recipient])
    existing = db.scalar(
        select(WebFriendRequest).where(
            WebFriendRequest.user_low == low, WebFriendRequest.user_high == high
        )
    )
    if existing:
        if existing.status != "declined":
            raise HTTPException(409, "이미 친구이거나 수락을 기다리는 요청이 있습니다.")
        changed = db.execute(
            update(WebFriendRequest)
            .where(WebFriendRequest.id == existing.id, WebFriendRequest.status == "declined")
            .values(status="pending", requester_id=user.id, created_at=datetime.now(UTC))
        )
        if changed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "친구 요청이 이미 변경되었습니다.")
        identifier = existing.id
    else:
        identifier = str(uuid4())
        db.add(
            WebFriendRequest(
                id=identifier,
                user_low=low,
                user_high=high,
                requester_id=user.id,
                status="pending",
                created_at=datetime.now(UTC),
            )
        )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "이미 친구 요청이 있습니다.") from exc
    return {"id": identifier, "status": "pending"}


@router.post("/friend-requests/{request_id}/response")
def respond_friend(request_id: UUID, body: FriendResponse, user: AuthenticatedUser, db: Database):
    pair = db.get(WebFriendRequest, str(request_id))
    if (
        pair is None
        or user.id not in {pair.user_low, pair.user_high}
        or pair.requester_id == user.id
    ):
        raise HTTPException(404, "받은 친구 요청을 찾을 수 없습니다.")
    status = "accepted" if body.accept else "declined"
    changed = db.execute(
        update(WebFriendRequest)
        .where(
            WebFriendRequest.id == pair.id,
            WebFriendRequest.status == "pending",
            WebFriendRequest.requester_id == pair.requester_id,
        )
        .values(status=status)
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "이미 응답한 친구 요청입니다.")
    db.commit()
    return {"id": pair.id, "status": status}
