from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.accounts.dependencies import AuthenticatedUser
from app.accounts.schemas import AccountRead, LoginRequest
from app.accounts.service import login_by_username, logout_session
from app.core.config import get_settings
from app.core.db import get_db

router = APIRouter(prefix="/auth", tags=["accounts (A)"])
Database = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=AccountRead)
def login(body: LoginRequest, request: Request, response: Response, db: Database):
    settings = get_settings()
    user, token = login_by_username(
        db, body.username, request.cookies.get(settings.session_cookie_name)
    )
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return AccountRead(id=user.id, username=user.username, auth_mode="id-only")


@router.get("/me", response_model=AccountRead)
def me(user: AuthenticatedUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return AccountRead(id=user.id, username=user.username, auth_mode=user.auth_mode)


@router.post("/logout", status_code=204)
def logout(request: Request, db: Database):
    settings = get_settings()
    logout_session(db, request.cookies.get(settings.session_cookie_name))
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(settings.session_cookie_name, path="/", httponly=True, samesite="lax")
    return response
