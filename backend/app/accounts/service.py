from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import LoginSession, User
from app.core.config import get_settings


def hash_session_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def find_session_user(db: Session, token: str) -> User | None:
    return db.scalar(
        select(User)
        .join(LoginSession, LoginSession.user_id == User.id)
        .where(
            LoginSession.token_hash == hash_session_token(token),
            LoginSession.expires_at > datetime.now(UTC),
        )
    )


def login_by_username(db: Session, username: str, previous_token: str | None) -> tuple[User, str]:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        user = User(id=str(uuid4()), username=username)
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            # 같은 아이디의 첫 접속이 동시에 들어와도 계정은 하나만 생성합니다.
            db.rollback()
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                raise
    if previous_token:
        db.execute(
            delete(LoginSession).where(
                LoginSession.token_hash == hash_session_token(previous_token)
            )
        )
    now = datetime.now(UTC)
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    token = token_urlsafe(32)
    db.add(
        LoginSession(
            token_hash=hash_session_token(token),
            user_id=user.id,
            expires_at=now + timedelta(seconds=get_settings().session_max_age),
        )
    )
    db.commit()
    return user, token


def logout_session(db: Session, token: str | None):
    if token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == hash_session_token(token)))
        db.commit()
