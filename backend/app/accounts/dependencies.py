from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.config import get_settings
from app.core.db import get_db


@dataclass(frozen=True)
class CurrentUser:
    id: str


def get_current_user(db: Annotated[Session, Depends(get_db)]) -> CurrentUser:
    settings = get_settings()
    # A: 실제 인증 구현 시 이 함수 내부만 Bearer 토큰 검증으로 교체합니다.
    # 요청 헤더/본문으로 임시 사용자 ID를 변경할 수 없습니다.
    if settings.app_env != "development" or not settings.dev_auth_enabled:
        raise HTTPException(
            401, detail={"code": "UNAUTHENTICATED", "message": "로그인이 필요합니다."}
        )
    user_id = str(settings.dev_user_id)
    if db.get(User, user_id) is None:
        db.add(User(id=user_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if db.get(User, user_id) is None:
                raise
    return CurrentUser(user_id)


AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
