import io
import warnings
import hashlib
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import httpx
from google.genai.errors import APIError
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from .analysis import AnalysisUnavailable, KeywordResult, extract_keywords
from .effects import AnalysisResult, attach_effect
from . import progress

router = APIRouter(prefix="/api", tags=["keywords"])
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def validate_image(data: bytes) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                mime = ALLOWED_FORMATS.get(image.format)
                if not mime or getattr(image, "is_animated", False):
                    raise HTTPException(400, "정지 이미지 JPG, PNG, WEBP만 지원합니다.")
                if image.width * image.height > 25_000_000:
                    raise HTTPException(400, "이미지는 2,500만 픽셀 이하로 올려 주세요.")
                image.verify()
        return mime
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, "이미지 파일을 읽을 수 없습니다. 정상적인 JPG, PNG, WEBP를 선택해 주세요.")


@router.post("/keywords", response_model=AnalysisResult)
async def keywords(text: str = Form(""), image: UploadFile | None = File(None), record_id: UUID | None = Form(None)):
    text = text.strip()
    if len(text) > 5000:
        raise HTTPException(400, "글은 5,000자 이하로 입력해 주세요.")
    data, mime = None, None
    if image is not None:
        try:
            data = await image.read(MAX_IMAGE_BYTES + 1)
        finally:
            await image.close()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "이미지는 10MB 이하로 올려 주세요.")
        if not data:
            raise HTTPException(400, "빈 이미지 파일입니다.")
        mime = await run_in_threadpool(validate_image, data)
    if not text and not data:
        raise HTTPException(400, "글 또는 이미지를 하나 이상 입력해 주세요.")
    record_id = str(record_id or uuid4())
    fingerprint = hashlib.sha256(text.encode() + b"\x00" + (data or b"")).hexdigest()
    try:
        cached = await run_in_threadpool(progress.lookup, record_id, fingerprint)
        if cached:
            return attach_effect(cached, record_id, False, await run_in_threadpool(progress.state))
        result = await extract_keywords(text, data, mime)
        saved, awarded = await run_in_threadpool(progress.save, record_id, fingerprint, result)
        return attach_effect(saved, record_id, awarded, await run_in_threadpool(progress.state))
    except AnalysisUnavailable as exc:
        raise HTTPException(503, str(exc))
    except APIError as exc:
        if exc.code == 504:
            raise HTTPException(504, "Gemini 서버의 분석 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.")
        if exc.code == 429:
            raise HTTPException(429, "Gemini 요청 한도를 초과했습니다. AI Studio의 할당량을 확인하고 잠시 후 다시 시도해 주세요.")
        if exc.code in (400, 401, 403):
            raise HTTPException(503, "Gemini API 키 또는 요청 권한을 확인해 주세요.")
        if exc.code == 404:
            raise HTTPException(503, "Gemini 모델을 찾을 수 없습니다. GEMINI_MODEL 설정을 확인해 주세요.")
        raise HTTPException(502, "Gemini 서버가 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.")
    except (httpx.TimeoutException, TimeoutError):
        raise HTTPException(504, "분석 시간이 초과되었습니다. 다시 시도해 주세요.")
    except httpx.RequestError:
        raise HTTPException(502, "AI 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")
    except ValidationError:
        raise HTTPException(502, "AI 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.get("/progress")
async def get_progress():
    return {"progress": await run_in_threadpool(progress.state)}
