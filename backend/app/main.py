from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.accounts.profile_router import router as profile_router
from app.accounts.router import router as accounts_router
from app.characters.router import router as characters_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.request_security import same_origin_writes
from app.integrations.router import router as integrated_router
from app.integrations.worker import recover_interrupted
from app.records.router import router as records_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(recover_interrupted)
    yield


def create_app() -> FastAPI:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    get_settings()  # 운영 환경에서 임시 인증을 켜면 시작 단계에서 거부합니다.
    app = FastAPI(title="Campus Character API", version="0.2.0", lifespan=lifespan)
    install_error_handlers(app)
    app.middleware("http")(same_origin_writes)

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    app.include_router(accounts_router)
    app.include_router(profile_router)
    app.include_router(characters_router)
    app.include_router(records_router, deprecated=True)
    app.include_router(integrated_router)
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/static", StaticFiles(directory=frontend), name="assets")
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
