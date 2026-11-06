from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.dependencies import AuthenticatedUser
from app.accounts.models import User
from app.accounts.profile_schemas import ProfileComplete, ProfileDraft, ProfileRead, SetupRead
from app.accounts.profile_service import finish_setup, read_profile, save_draft
from app.characters.appearance import ProfileLook
from app.characters.models import Character
from app.core.db import get_db

router = APIRouter(prefix="/profile", tags=["onboarding (A)"])
Database = Annotated[Session, Depends(get_db)]


@router.get("/me", response_model=ProfileRead)
def profile(user: AuthenticatedUser, db: Database):
    return read_profile(db.get(User, user.id))


@router.put("/me/draft", response_model=ProfileRead)
def draft(body: ProfileDraft, user: AuthenticatedUser, db: Database):
    return save_draft(db, user.id, body)


@router.post("/me/complete", response_model=SetupRead)
def complete(body: ProfileComplete, user: AuthenticatedUser, db: Database):
    return finish_setup(db, user.id, body)


@router.put("/me/appearance", response_model=ProfileRead)
def appearance(body: ProfileLook, user: AuthenticatedUser, db: Database):
    profile = db.get(User, user.id)
    character = db.scalar(select(Character).where(Character.user_id == user.id))
    if character is None:
        raise HTTPException(
            409, detail={"code": "SETUP_REQUIRED", "message": "최초 설정을 완료해 주세요."}
        )
    profile.grade = body.grade
    profile.major = body.major
    profile.draft_appearance = body.appearance.model_dump()
    character.appearance = body.appearance.model_dump()
    db.commit()
    return read_profile(profile)
