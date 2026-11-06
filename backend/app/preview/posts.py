import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.preview.models import WebPost


def prepare_post(
    db: Session, user_id: str, request_id: str, text: str, image: bytes | None, mime: str | None
):
    fingerprint = hashlib.sha256(text.encode() + b"\x00" + (image or b"")).hexdigest()
    lookup = select(WebPost).where(WebPost.user_id == user_id, WebPost.request_id == request_id)
    post = db.scalar(lookup)
    if post is None:
        post = WebPost(
            id=str(uuid4()),
            user_id=user_id,
            request_id=request_id,
            fingerprint=fingerprint,
            text=text,
            image_data=image,
            image_mime=mime,
            analysis_status="pending",
            created_at=datetime.now(UTC),
        )
        db.add(post)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            post = db.scalar(lookup)
            if post is None:
                raise
    if post.fingerprint != fingerprint:
        raise HTTPException(409, "같은 게시 ID로 다른 내용을 제출할 수 없습니다.")
    return post


def claim_analysis(db: Session, post: WebPost):
    now = datetime.now(UTC)
    changed = db.execute(
        update(WebPost)
        .where(
            WebPost.id == post.id,
            or_(
                WebPost.analysis_status.in_(["pending", "failed"]),
                (WebPost.analysis_status == "processing")
                & (WebPost.started_at < now - timedelta(seconds=120)),
            ),
        )
        .values(analysis_status="processing", started_at=now)
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "이미 게시물을 처리 중이에요. 잠시 후 다시 시도해 주세요.")
    db.commit()
