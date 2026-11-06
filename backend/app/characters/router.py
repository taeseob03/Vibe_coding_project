from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.dependencies import AuthenticatedUser
from app.characters.models import Character
from app.characters.schemas import CharacterRead
from app.characters.service import read_character
from app.core.db import get_db

router = APIRouter(prefix="/characters", tags=["characters (A)"])


@router.get("/me", response_model=CharacterRead)
def character(user: AuthenticatedUser, db: Annotated[Session, Depends(get_db)]):
    character = db.scalar(select(Character).where(Character.user_id == user.id))
    if character is None:
        raise HTTPException(
            404, detail={"code": "CHARACTER_NOT_FOUND", "message": "최초 설정을 완료해 주세요."}
        )
    return read_character(db, character)
