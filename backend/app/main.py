import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.accounts.profile_router import router as profile_router
from app.accounts.router import router as accounts_router
from app.characters.router import router as characters_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.request_security import same_origin_writes
from app.records.router import router as records_router


def create_app() -> FastAPI:
    get_settings()  # 운영 환경에서 임시 인증을 켜면 시작 단계에서 거부합니다.
    app = FastAPI(title="INUstagram", version="0.1.0")
    install_error_handlers(app)
    app.middleware("http")(same_origin_writes)

    @app.middleware("http")
    async def fresh_local_assets(request, call_next):
        response = await call_next(request)
        if get_settings().app_env == "development":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    @app.get("/api/preview-status", include_in_schema=False)
    def preview_status():
        settings = get_settings()
        return {"enabled": settings.app_env == "development" and settings.local_web_preview_enabled}

    app.include_router(accounts_router)
    app.include_router(profile_router)
    app.include_router(characters_router)
    app.include_router(records_router)
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("application/javascript", ".mjs")
    if get_settings().app_env == "development" and get_settings().local_web_preview_enabled:
        from app.preview.bridge import PROTOTYPE
        from app.preview.feed import router as feed_router
        from app.preview.router import router as preview_router

        app.include_router(preview_router)
        app.include_router(feed_router)
        app.mount("/static", StaticFiles(directory=PROTOTYPE / "static"), name="web-preview")
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
