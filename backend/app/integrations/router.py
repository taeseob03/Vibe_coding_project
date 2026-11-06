from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from campus_records_prototype.routes import MAX_IMAGE_BYTES, validate_image
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.accounts.dependencies import AuthenticatedUser
from app.characters.models import Character
from app.core.db import get_db
from app.integrations.models import ActivityRecord
from app.integrations.schemas import ActivityRead
from app.integrations.state_store import apply_state_safely
from app.integrations.worker import process_record

router = APIRouter(prefix="/api/records", tags=["integrated records (A + B)"])
Database = Annotated[Session, Depends(get_db)]


def owned_record(db: Session, user_id: str, record_id: UUID):
    record = db.scalar(
        select(ActivityRecord).where(
            ActivityRecord.id == str(record_id),
            ActivityRecord.user_id == user_id,
        )
    )
    if record is None:
        raise HTTPException(
            404, detail={"code": "RECORD_NOT_FOUND", "message": "기록을 찾을 수 없습니다."}
        )
    return record


def public_record(record: ActivityRecord) -> ActivityRead:
    return ActivityRead(
        id=record.id,
        user_id=record.user_id,
        request_id=record.request_id,
        text=record.text,
        has_image=record.image_mime is not None,
        status=record.status,
        analysis=record.analysis_data,
        analysis_error=record.analysis_error,
        stat_status=record.stat_status,
        state_error=record.state_error,
        stats_snapshot=record.stats_snapshot,
        created_at=record.created_at,
    )


def save_input(
    db: Session, user_id: str, request_id: str, text: str, image: bytes | None, mime: str | None
):
    if db.scalar(select(Character.id).where(Character.user_id == user_id)) is None:
        raise HTTPException(
            409, detail={"code": "SETUP_REQUIRED", "message": "최초 설정을 완료해 주세요."}
        )
    fingerprint = sha256(text.encode() + b"\x00" + (image or b"")).hexdigest()
    existing = db.scalar(
        select(ActivityRecord).where(
            ActivityRecord.user_id == user_id,
            ActivityRecord.request_id == request_id,
        )
    )
    if existing is None:
        record = ActivityRecord(
            id=str(uuid4()),
            user_id=user_id,
            request_id=request_id,
            fingerprint=fingerprint,
            text=text,
            image_data=image,
            image_mime=mime,
            status="pending",
            stat_status="pending",
            attempt=0,
            created_at=datetime.now(UTC),
        )
        db.add(record)
        try:
            db.commit()
            db.refresh(record)
            return record, True
        except IntegrityError:
            db.rollback()
            existing = db.scalar(
                select(ActivityRecord).where(
                    ActivityRecord.user_id == user_id,
                    ActivityRecord.request_id == request_id,
                )
            )
            if existing is None:
                raise
    if existing.fingerprint != fingerprint:
        raise HTTPException(
            409,
            detail={
                "code": "REQUEST_ID_CONFLICT",
                "message": "같은 요청 ID로 다른 내용을 저장할 수 없습니다.",
            },
        )
    return existing, False


@router.post("", response_model=ActivityRead, status_code=201)
async def create_record(
    user: AuthenticatedUser,
    db: Database,
    background_tasks: BackgroundTasks,
    response: Response,
    text: Annotated[str, Form()] = "",
    image: Annotated[UploadFile | None, File()] = None,
    request_id: Annotated[UUID | None, Form()] = None,
):
    text = text.strip()
    if len(text) > 5000:
        raise HTTPException(
            400, detail={"code": "TEXT_TOO_LONG", "message": "글은 5,000자 이하로 입력해 주세요."}
        )
    data, mime = None, None
    if image is not None:
        try:
            data = await image.read(MAX_IMAGE_BYTES + 1)
        finally:
            await image.close()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(
                413,
                detail={"code": "IMAGE_TOO_LARGE", "message": "사진은 10MB 이하로 선택해 주세요."},
            )
        if not data:
            raise HTTPException(
                400, detail={"code": "EMPTY_IMAGE", "message": "빈 사진 파일입니다."}
            )
        mime = await run_in_threadpool(validate_image, data)
    if not text and not data:
        raise HTTPException(
            400, detail={"code": "EMPTY_RECORD", "message": "글 또는 사진을 입력해 주세요."}
        )
    record, created = await run_in_threadpool(
        save_input, db, user.id, str(request_id or uuid4()), text, data, mime
    )
    result = public_record(record)
    if created:
        background_tasks.add_task(process_record, record.id)
    else:
        response.status_code = 200
    return result


@router.get("", response_model=list[ActivityRead])
def list_records(
    user: AuthenticatedUser, db: Database, response: Response, limit: int = Query(50, ge=1, le=100)
):
    response.headers["Cache-Control"] = "no-store"
    records = db.scalars(
        select(ActivityRecord)
        .where(ActivityRecord.user_id == user.id)
        .order_by(ActivityRecord.created_at.desc())
        .limit(limit)
    ).all()
    return [public_record(record) for record in records]


@router.get("/{record_id}", response_model=ActivityRead)
def detail(record_id: UUID, user: AuthenticatedUser, db: Database, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return public_record(owned_record(db, user.id, record_id))


@router.get("/{record_id}/image")
def image(record_id: UUID, user: AuthenticatedUser, db: Database):
    record = owned_record(db, user.id, record_id)
    if record.image_data is None:
        raise HTTPException(
            404, detail={"code": "IMAGE_NOT_FOUND", "message": "사진이 없는 기록입니다."}
        )
    return Response(
        content=record.image_data,
        media_type=record.image_mime,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/{record_id}/retry", response_model=ActivityRead, status_code=202)
def retry(
    record_id: UUID, user: AuthenticatedUser, db: Database, background_tasks: BackgroundTasks
):
    record = owned_record(db, user.id, record_id)
    if record.status == "failed":
        updated = db.execute(
            update(ActivityRecord)
            .where(
                ActivityRecord.id == str(record_id),
                ActivityRecord.status == "failed",
            )
            .values(status="pending", analysis_error=None)
        )
        if updated.rowcount != 1:
            db.rollback()
            raise HTTPException(
                409, detail={"code": "RETRY_IN_PROGRESS", "message": "이미 다시 처리하고 있습니다."}
            )
        db.commit()
        db.refresh(record)
        result = public_record(record)
        background_tasks.add_task(process_record, str(record_id))
        return result
    if record.status == "completed" and record.stat_status in {"pending", "failed"}:
        result = public_record(record)
        background_tasks.add_task(apply_state_safely, user.id, str(record_id))
        return result
    raise HTTPException(
        409, detail={"code": "RETRY_NOT_ALLOWED", "message": "재시도가 필요한 기록이 아닙니다."}
    )
