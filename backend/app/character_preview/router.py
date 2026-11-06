"""캐릭터 미리보기(/preview/character.html)의 게시물 분석 API.

글·사진을 받아 Gemini로 분류만 하고 저장하지 않습니다.
레벨은 미리보기 화면이 브라우저에 보관합니다. 실제 저장은 기록·캐릭터 기능에서 연결합니다.
"""

import io
import warnings
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.character_preview import gemini
from app.core.config import get_settings

router = APIRouter(prefix="/character-preview", tags=["character preview"])

MAX_TEXT = 5000
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
CATEGORY_KEYS = {"술": "drink", "공부": "study", "운동": "exercise", "연애": "love"}


class PostAnalysis(BaseModel):
    category: Literal["drink", "study", "exercise", "love"] | None
    category_label: str | None
    keywords: list[str]
    summary: str
    reason: str
    needs_review: bool


def error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, detail={"code": code, "message": message})


def validate_image(data: bytes) -> str:
    from PIL import Image, UnidentifiedImageError

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                mime = ALLOWED_FORMATS.get(image.format)
                if not mime or getattr(image, "is_animated", False):
                    raise error(400, "IMAGE_FORMAT", "JPG, PNG, WEBP 사진만 올릴 수 있어요.")
                if image.width * image.height > 25_000_000:
                    raise error(400, "IMAGE_TOO_LARGE", "사진은 2,500만 픽셀 이하로 올려 주세요.")
                image.verify()
        return mime
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise error(400, "IMAGE_INVALID", "사진 파일을 읽을 수 없어요.") from exc


@router.post("/analyze", response_model=PostAnalysis)
async def analyze_post(text: str = Form(""), image: UploadFile | None = File(None)):
    if get_settings().app_env != "development":
        raise error(404, "NOT_FOUND", "로컬 개발 환경에서만 사용할 수 있어요.")
    text = text.strip()
    if len(text) > MAX_TEXT:
        raise error(400, "TEXT_TOO_LONG", "글은 5,000자 이하로 써 주세요.")

    data, mime = None, None
    if image is not None and image.filename:
        try:
            data = await image.read(MAX_IMAGE_BYTES + 1)
        finally:
            await image.close()
        if len(data) > MAX_IMAGE_BYTES:
            raise error(400, "IMAGE_TOO_LARGE", "사진은 10MB 이하로 올려 주세요.")
        if data:
            mime = validate_image(data)
        else:
            data = None
    if not text and data is None:
        raise error(400, "EMPTY_POST", "글이나 사진 중 하나는 올려 주세요.")

    try:
        result = await gemini.extract_keywords(text, data, mime)
    except gemini.AnalysisUnavailable as exc:
        raise error(503, "GEMINI_NOT_CONFIGURED", str(exc)) from exc
    except gemini.AnalysisFailed as exc:
        raise error(
            502, "ANALYSIS_FAILED", "분석하지 못했어요. 잠시 후 다시 시도해 주세요."
        ) from exc

    return PostAnalysis(
        category=CATEGORY_KEYS.get(result.category) if result.category else None,
        category_label=result.category,
        keywords=result.keywords,
        summary=result.summary,
        reason=result.category_reason,
        needs_review=result.needs_review,
    )
