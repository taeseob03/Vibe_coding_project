from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routes import router

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
app = FastAPI(title="Campus keyword extraction", version="0.1.0")
app.include_router(router)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(ROOT / "static" / "index.html")
