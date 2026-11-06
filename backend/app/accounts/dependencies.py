from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.service import find_session_user
from app.core.config import get_settings
from app.core.db import get_db


@dataclass(frozen=True)
class CurrentUser:
    id: str
    username: str | None = None
    auth_mode: str = "local-development"


def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> CurrentUser:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        user = find_session_user(db, token)
        if user:
            return CurrentUser(user.id, user.username, "id-only")
        # 잘못되거나 만료된 쿠키는 개발 사용자로 바꾸지 않습니다.
        raise HTTPException(
            401, detail={"code": "SESSION_EXPIRED", "message": "다시 접속해 주세요."}
        )
    # B의 독립 개발을 위해 명시적으로 켠 환경에서만 기존 임시 인증을 유지합니다.
    if settings.app_env != "development" or not settings.dev_auth_enabled:
        raise HTTPException(
            401, detail={"code": "UNAUTHENTICATED", "message": "아이디로 접속해 주세요."}
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
