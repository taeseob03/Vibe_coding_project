import asyncio

import httpx
from campus_records_prototype.analysis import AnalysisUnavailable, KeywordResult, extract_keywords
from google.genai.errors import APIError
from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.db import get_engine
from app.integrations.models import ActivityRecord
from app.integrations.state_store import apply_state_safely


def claim_record(record_id: str):
    with Session(get_engine()) as db, db.begin():
        claimed = db.execute(
            update(ActivityRecord)
            .where(
                ActivityRecord.id == record_id,
                ActivityRecord.status == "pending",
            )
            .values(status="processing", attempt=ActivityRecord.attempt + 1)
        )
        if claimed.rowcount != 1:
            return None
        record = db.get(ActivityRecord, record_id)
        return record.user_id, record.text, record.image_data, record.image_mime, record.attempt


def save_result(record_id: str, attempt: int, result: KeywordResult):
    with Session(get_engine()) as db, db.begin():
        saved = db.execute(
            update(ActivityRecord)
            .where(
                ActivityRecord.id == record_id,
                ActivityRecord.status == "processing",
                ActivityRecord.attempt == attempt,
            )
            .values(
                status="completed",
                analysis_data=result.model_dump(mode="json"),
                analysis_error=None,
            )
        )
        return saved.rowcount == 1


def safe_analysis_error(exc: Exception):
    code, message = "ANALYSIS_FAILED", "분석하지 못했습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(exc, AnalysisUnavailable):
        code, message = "ANALYSIS_UNAVAILABLE", "Gemini 설정 또는 분석 응답을 확인해 주세요."
    elif isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        code, message = "ANALYSIS_TIMEOUT", "분석 시간이 초과되었습니다. 다시 시도해 주세요."
    elif isinstance(exc, APIError):
        if exc.code == 429:
            code, message = (
                "ANALYSIS_RATE_LIMITED",
                "Gemini 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.",
            )
        elif exc.code in (400, 401, 403, 404):
            code, message = (
                "ANALYSIS_CONFIGURATION_ERROR",
                "서버의 Gemini 키·모델·접근 권한을 확인해 주세요.",
            )
    elif isinstance(exc, ValidationError):
        code, message = (
            "INVALID_ANALYSIS_RESPONSE",
            "분석 응답을 확인하지 못했습니다. 다시 시도해 주세요.",
        )
    return {"code": code, "message": message}


def fail_analysis(record_id: str, attempt: int, error: dict):
    with Session(get_engine()) as db, db.begin():
        db.execute(
            update(ActivityRecord)
            .where(
                ActivityRecord.id == record_id,
                ActivityRecord.status == "processing",
                ActivityRecord.attempt == attempt,
            )
            .values(status="failed", analysis_error=error)
        )


async def process_record(record_id: str):
    claimed = await run_in_threadpool(claim_record, record_id)
    if claimed is None:
        return
    user_id, text, image, mime, attempt = claimed
    try:
        result = KeywordResult.model_validate(await extract_keywords(text, image, mime))
    except asyncio.CancelledError:
        await run_in_threadpool(
            fail_analysis,
            record_id,
            attempt,
            {
                "code": "ANALYSIS_INTERRUPTED",
                "message": "분석이 중단되었습니다. 다시 시도해 주세요.",
            },
        )
        raise
    except Exception as exc:
        await run_in_threadpool(fail_analysis, record_id, attempt, safe_analysis_error(exc))
        return
    if await run_in_threadpool(save_result, record_id, attempt, result):
        await run_in_threadpool(apply_state_safely, user_id, record_id)


def recover_interrupted():
    # 단일 프로세스 개발 서버의 재시작 복구. 원본을 보존하고 명시적 재시도를 기다립니다.
    with Session(get_engine()) as db, db.begin():
        db.execute(
            update(ActivityRecord)
            .where(ActivityRecord.status.in_(["pending", "processing"]))
            .values(
                status="failed",
                analysis_error={
                    "code": "ANALYSIS_INTERRUPTED",
                    "message": "서버 재시작으로 분석이 중단되었습니다. 다시 시도해 주세요.",
                },
            )
        )
