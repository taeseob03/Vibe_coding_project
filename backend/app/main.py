from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.accounts.router import router as accounts_router
from app.character_preview.router import router as character_preview_router
from app.characters.router import router as characters_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.records.router import router as records_router


def create_app() -> FastAPI:
    get_settings()  # 운영 환경에서 임시 인증을 켜면 시작 단계에서 거부합니다.
    app = FastAPI(title="Campus Character API", version="0.1.0")
    install_error_handlers(app)

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    app.include_router(accounts_router)
    app.include_router(characters_router)
    app.include_router(records_router)
    app.include_router(character_preview_router)
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
