from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.accounts.dependencies import AuthenticatedUser
from app.accounts.models import User
from app.accounts.profile_schemas import ProfileComplete, ProfileDraft, ProfileRead, SetupRead
from app.accounts.profile_service import (
    finish_setup,
    read_profile,
    save_draft,
    update_customization,
)
from app.characters.appearance import Customization
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
def appearance(body: Customization, user: AuthenticatedUser, db: Database):
    return update_customization(db, user.id, body)
