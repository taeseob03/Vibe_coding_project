import io
import json
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import select, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers

from app.accounts.dependencies import AuthenticatedUser, get_current_user
from app.accounts.models import User
from app.characters.models import Character
from app.core.config import get_settings
from app.core.db import get_db
from app.integrations.router import save_input
from app.integrations.state_store import apply_saved_state, current_stats
from app.preview.bridge import PROTOTYPE, analysis, progress, routes
from app.preview.posts import claim_analysis, prepare_post

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
        "feedMode": "server",
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
    character = db.scalar(select(Character).where(Character.user_id == user.id))
    return {"progress": current_stats(character)}


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
    db.execute(update(Character).where(Character.user_id == user.id).values(color=Character.color))
    character = db.scalar(select(Character).where(Character.user_id == user.id))
    db.refresh(character)
    character.stats = current_stats(character)
    db.commit()
    text = text.strip()
    if len(text) > 5000:
        raise HTTPException(400, "글은 5,000자 이하로 입력해 주세요.")
    data, mime = None, None
    if image is not None:
        try:
            data = await image.read(routes.MAX_IMAGE_BYTES + 1)
        finally:
            await image.close()
        if len(data) > routes.MAX_IMAGE_BYTES:
            raise HTTPException(413, "이미지는 10MB 이하로 올려 주세요.")
        if not data:
            raise HTTPException(400, "빈 이미지 파일입니다.")
        mime = await run_in_threadpool(routes.validate_image, data)
    if not text and not data:
        raise HTTPException(400, "글 또는 사진을 하나 이상 올려 주세요.")
    record_id = record_id or uuid4()
    post = prepare_post(db, user.id, str(record_id), text, data, mime)
    with progress.use_database(user_database(user.id)):
        if post.analysis_status == "completed" and post.analysis_data:
            parsed = analysis.KeywordResult.model_validate(
                {key: post.analysis_data[key] for key in analysis.KeywordResult.model_fields}
            )
            return {
                **routes.attach_effect(
                    parsed, str(record_id), False, current_stats(character)
                ).model_dump(),
                "post_id": post.id,
            }
        claim_analysis(db, post)
        activity, _ = save_input(db, user.id, str(record_id), text, data, mime)
        upload = (
            UploadFile(
                file=io.BytesIO(data), filename="photo", headers=Headers({"content-type": mime})
            )
            if data
            else None
        )
        try:
            before = {item["category"]: item["count"] for item in current_stats(character)}
            already_applied = activity.stat_status in {"applied", "skipped"}
            if activity.status == "completed" and activity.analysis_data:
                result_data = analysis.KeywordResult.model_validate(
                    activity.analysis_data
                ).model_dump()
            else:
                result = await routes.keywords(text=text, image=upload, record_id=record_id)
                result_data = result.model_dump()
                activity.status = "completed"
                activity.analysis_data = {
                    key: result_data[key] for key in analysis.KeywordResult.model_fields
                }
                activity.analysis_error = None
                db.commit()
            stats = await run_in_threadpool(apply_saved_state, user.id, activity.id)
            db.expire_all()
            changes = (
                {
                    item["category"]: item["count"] - before[item["category"]]
                    for item in stats
                    if item["count"] != before[item["category"]]
                }
                if not already_applied
                else {}
            )
            parsed = analysis.KeywordResult.model_validate(
                {key: result_data[key] for key in analysis.KeywordResult.model_fields}
            )
            payload = {
                **routes.attach_effect(
                    parsed,
                    str(record_id),
                    bool(changes),
                    current_stats(db.get(Character, character.id)),
                    changes,
                ).model_dump(),
                "post_id": post.id,
            }
            post.analysis_status = "completed"
            post.analysis_data = payload
            db.commit()
            return payload
        except Exception:
            db.rollback()
            db.refresh(activity)
            if activity.status != "completed":
                activity.status = "failed"
                activity.analysis_error = {
                    "code": "ANALYSIS_FAILED",
                    "message": "분석에 실패했습니다. 다시 시도해 주세요.",
                }
            post.analysis_status = "failed"
            db.commit()
            raise
