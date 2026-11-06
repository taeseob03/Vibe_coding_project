from campus_records_prototype.analysis import KeywordResult
from campus_records_prototype.progress import advance_counts, calculate_progress, eligible_category
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.characters.models import Character
from app.core.db import get_engine
from app.integrations.models import ActivityRecord
from app.integrations.schemas import StatRead


def current_stats(character: Character) -> list[dict]:
    if character.stats is not None:
        return character.stats
    # Import the existing local account ledger once as the canonical baseline.
    from app.preview.bridge import progress
    from app.preview.router import user_database

    path = user_database(character.user_id)
    if path.exists():
        with progress.use_database(path):
            return progress.state()
    return calculate_progress({})


def apply_saved_state(user_id: str, record_id: str) -> list[dict]:
    """A는 소유자/중복/트랜잭션을 처리하고, 계산은 B 함수에 맡깁니다."""
    with Session(get_engine()) as db, db.begin():
        locked = db.execute(
            update(ActivityRecord)
            .where(
                ActivityRecord.id == record_id,
                ActivityRecord.user_id == user_id,
            )
            .values(stat_status=ActivityRecord.stat_status)
        )
        if locked.rowcount != 1:
            raise ValueError("Record not found")
        record = db.get(ActivityRecord, record_id)
        if record.status != "completed" or record.analysis_data is None:
            raise ValueError("Analysis is not completed")
        if record.stat_status in {"applied", "skipped"}:
            return record.stats_snapshot
        locked = db.execute(
            update(Character).where(Character.user_id == user_id).values(color=Character.color)
        )
        if locked.rowcount != 1:
            raise ValueError("Character not found")
        character = db.scalar(select(Character).where(Character.user_id == user_id))
        result = KeywordResult.model_validate(record.analysis_data)
        record.category = eligible_category(result)
        record.stat_status = "applied" if record.category is not None else "skipped"
        record.state_error = None
        db.flush()
        counts = {item["category"]: item["count"] for item in current_stats(character)}
        counts = advance_counts(counts, record.category)
        stats = [StatRead.model_validate(item).model_dump() for item in calculate_progress(counts)]
        character.stats = stats
        record.stats_snapshot = stats
        # Both upload entrypoints publish to the same friend-protected feed.
        from app.preview.models import WebPost

        post = db.scalar(
            select(WebPost).where(
                WebPost.user_id == user_id, WebPost.request_id == record.request_id
            )
        )
        if post is None:
            from uuid import uuid4

            post = WebPost(
                id=str(uuid4()),
                user_id=user_id,
                request_id=record.request_id,
                fingerprint=record.fingerprint,
                text=record.text,
                image_data=record.image_data,
                image_mime=record.image_mime,
                created_at=record.created_at,
            )
            db.add(post)
        post.analysis_status = "completed"
        post.analysis_data = record.analysis_data
        return stats


def apply_state_safely(user_id: str, record_id: str):
    try:
        apply_saved_state(user_id, record_id)
    except Exception:
        with Session(get_engine()) as db, db.begin():
            db.execute(
                update(ActivityRecord)
                .where(
                    ActivityRecord.id == record_id,
                    ActivityRecord.user_id == user_id,
                    ActivityRecord.status == "completed",
                    ActivityRecord.stat_status.not_in(["applied", "skipped"]),
                )
                .values(
                    stat_status="failed",
                    state_error={
                        "code": "STATE_SAVE_FAILED",
                        "message": "분석 완료 후 상태 저장에 실패했습니다. 다시 시도해 주세요.",
                    },
                )
            )
