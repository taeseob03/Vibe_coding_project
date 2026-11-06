from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.dependencies import AuthenticatedUser
from app.analysis.provider import analyze_mock
from app.core.db import get_db
from app.records.models import Record
from app.records.schemas import RecordCreate, RecordRead

router = APIRouter(prefix="/records", tags=["records (B)"])
Database = Annotated[Session, Depends(get_db)]


def owned_record(record_id: UUID, user_id: str, db: Session) -> Record:
    record = db.scalar(select(Record).where(Record.id == str(record_id), Record.user_id == user_id))
    if record is None:
        raise HTTPException(
            404, detail={"code": "RECORD_NOT_FOUND", "message": "기록을 찾을 수 없습니다."}
        )
    return record


@router.post("", response_model=RecordRead, status_code=201)
def create_record(body: RecordCreate, user: AuthenticatedUser, db: Database):
    # 환경 확인용 동기 mock입니다. B: 저장 후 pending 반환/작업 실행/복구로 교체합니다.
    record = Record(
        id=str(uuid4()),
        user_id=user.id,
        text=body.text,
        status="completed",
        analysis=analyze_mock(body.text).model_dump(mode="json"),
        effect_status="not_requested",
        created_at=datetime.now(UTC),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[RecordRead])
def list_records(user: AuthenticatedUser, db: Database, limit: int = Query(50, ge=1, le=100)):
    return db.scalars(
        select(Record)
        .where(Record.user_id == user.id)
        .order_by(Record.created_at.desc())
        .limit(limit)
    ).all()


@router.get("/{record_id}", response_model=RecordRead)
def detail(record_id: UUID, user: AuthenticatedUser, db: Database):
    return owned_record(record_id, user.id, db)


@router.post("/{record_id}/retry")
def retry(record_id: UUID, user: AuthenticatedUser, db: Database):
    owned_record(record_id, user.id, db)
    raise HTTPException(
        501,
        detail={"code": "NOT_IMPLEMENTED", "message": "B 담당: 분석 실패·재시도를 구현해 주세요."},
    )
