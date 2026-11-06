import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.accounts.dependencies import AuthenticatedUser, get_current_user
from app.accounts.models import User
from app.characters.models import Character
from app.core.config import get_settings
from app.core.db import get_db
from app.preview.bridge import PROTOTYPE, progress, routes

router = APIRouter(tags=["local web preview"])
Database = Annotated[Session, Depends(get_db)]


def require_development():
    if get_settings().app_env != "development":
        raise HTTPException(404, "로컬 테스트 환경에서만 사용할 수 있습니다.")


def profile(db: Session, user_id: str):
    user = db.get(User, user_id)
    character = db.scalar(select(Character).where(Character.user_id == user_id))
    if user is None or not user.onboarding_completed or character is None:
        raise HTTPException(409, "최초 캐릭터 설정을 완료해 주세요.")
    return {
        "id": user.id,
        "nickname": user.nickname,
        "emoji": "🧑",
        "color": character.color,
    }


def user_database(user_id: str):
    # UUID comes exclusively from the authenticated dependency, never request content.
    identifier = str(UUID(user_id))
    url = make_url(get_settings().database_url)
    base = (
        Path(url.database).resolve().parent
        if url.drivername.startswith("sqlite")
        else Path("backend/data").resolve()
    )
    return base / "web-preview" / f"{identifier}.sqlite3"


@router.get("/app", include_in_schema=False, dependencies=[Depends(require_development)])
def app_page(request: Request, db: Database):
    try:
        user = get_current_user(request, db)
        profile(db, user.id)
    except HTTPException:
        return RedirectResponse("/", headers={"Cache-Control": "no-store"})
    return FileResponse(PROTOTYPE / "static" / "index.html", headers={"Cache-Control": "no-store"})


@router.get("/api/frontend-config.js", include_in_schema=False)
def frontend_config(user: AuthenticatedUser, db: Database):
    require_development()
    config = {
        "profileMode": "server",
        "socialMode": "demo",
        "demoMe": profile(db, user.id),
        "loginUrl": "/",
    }
    return Response(
        "window.CAMPUS_CONFIG = " + json.dumps(config, ensure_ascii=True) + ";",
        media_type="application/javascript",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/me")
def me(user: AuthenticatedUser, db: Database):
    require_development()
    return profile(db, user.id)


@router.get("/api/progress")
async def current_progress(user: AuthenticatedUser, db: Database):
    require_development()
    profile(db, user.id)
    with progress.use_database(user_database(user.id)):
        return {"progress": await run_in_threadpool(progress.state)}


@router.post("/api/keywords")
async def post_record(
    user: AuthenticatedUser,
    db: Database,
    text: str = Form(""),
    image: UploadFile | None = File(None),
    record_id: UUID | None = Form(None),
):
    require_development()
    profile(db, user.id)
    with progress.use_database(user_database(user.id)):
        return await routes.keywords(text=text, image=image, record_id=record_id)
