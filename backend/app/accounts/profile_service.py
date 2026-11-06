from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.profile_schemas import ProfileComplete, ProfileDraft, ProfileRead, SetupRead
from app.characters.appearance import Customization
from app.characters.models import Character
from app.characters.service import read_character


def read_profile(user: User) -> ProfileRead:
    return ProfileRead(
        user_id=user.id,
        nickname=user.nickname,
        color=user.draft_color,
        step=user.setup_step,
        onboarding_completed=user.onboarding_completed,
        **Customization.model_validate(user.character_setup or {}).model_dump(),
    )


def save_draft(db: Session, user_id: str, body: ProfileDraft) -> ProfileRead:
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.onboarding_completed.is_(False))
        .values(
            nickname=body.nickname,
            draft_color=body.color,
            setup_step=body.step,
            character_setup=customization_data(body),
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            409,
            detail={"code": "SETUP_ALREADY_COMPLETED", "message": "이미 최초 설정을 완료했습니다."},
        )
    db.commit()
    return read_profile(db.get(User, user_id))


def finish_setup(db: Session, user_id: str, body: ProfileComplete) -> SetupRead:
    # 완료 전 상태만 원자적으로 변경해 동시/반복 요청이 기존 설정을 덮어쓰지 않게 합니다.
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.onboarding_completed.is_(False))
        .values(
            nickname=body.nickname,
            draft_color=body.color,
            setup_step="color",
            onboarding_completed=True,
            character_setup=customization_data(body),
        )
    )
    if result.rowcount == 1:
        db.add(Character(user_id=user_id, color=body.color))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.get(User, user_id)
            if not user.onboarding_completed:
                raise
    else:
        db.rollback()
    user = db.get(User, user_id)
    db.refresh(user)
    character = db.scalar(select(Character).where(Character.user_id == user_id))
    if character is None or not user.onboarding_completed:
        raise RuntimeError("Completed setup requires a character")
    return SetupRead(profile=read_profile(user), character=read_character(db, character))


def customization_data(body: Customization):
    return body.model_dump(mode="json", include={"grade", "major", "appearance"})


def update_customization(db: Session, user_id: str, body: Customization) -> ProfileRead:
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.onboarding_completed.is_(True))
        .values(character_setup=customization_data(body))
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "최초 설정을 먼저 완료해 주세요.")
    db.commit()
    return read_profile(db.get(User, user_id))
