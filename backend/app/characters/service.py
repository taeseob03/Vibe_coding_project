from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import exists, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.analysis.schemas import AnalysisResult, Category
from app.characters.appearance import Customization
from app.characters.effect_models import CharacterEffect, EffectGrant
from app.characters.models import Character
from app.characters.schemas import CharacterRead, EffectApplicationRead, EffectId, EffectRead
from app.core.db import get_engine
from app.integrations.state_store import current_stats
from app.records.models import Record

EFFECT_BY_CATEGORY = {
    Category.study: EffectId.book,
    Category.social: EffectId.heart,
    Category.exercise: EffectId.dumbbell,
    Category.culture: EffectId.palette,
    Category.daily: EffectId.star,
}


class EffectApplicationError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def read_character(db: Session, character: Character) -> CharacterRead:
    effects = db.scalars(
        select(CharacterEffect)
        .where(CharacterEffect.character_id == character.id)
        .order_by(CharacterEffect.effect_id)
    ).all()
    return CharacterRead(
        id=character.id,
        user_id=character.user_id,
        color=character.color,
        effects=[EffectRead.model_validate(effect) for effect in effects],
        stats=current_stats(character),
        **Customization.model_validate(
            db.get(User, character.user_id).character_setup or {}
        ).model_dump(),
    )


def _increment_effect(db: Session, character_id: str, effect_id: EffectId):
    effect = db.get(CharacterEffect, (character_id, effect_id))
    if effect is None:
        db.add(
            CharacterEffect(character_id=character_id, effect_id=effect_id, level=1, visible=True)
        )
    else:
        effect.level += 1
    db.flush()


def _mark_failed(user_id: str, record_id: str):
    # 별도 트랜잭션으로 실패를 기록하되, 다른 요청에서 지급을 완료했다면 덮어쓰지 않습니다.
    try:
        with Session(get_engine()) as db, db.begin():
            db.execute(
                update(Record)
                .where(
                    Record.id == record_id,
                    Record.user_id == user_id,
                    Record.status == "completed",
                    ~exists(
                        select(EffectGrant.record_id).where(EffectGrant.record_id == record_id)
                    ),
                )
                .values(effect_status="failed")
            )
    except SQLAlchemyError:
        # DB 자체가 중단된 경우 상태 갱신도 실패할 수 있습니다. 저장된 분석으로 재시도합니다.
        pass


def _apply(db: Session, user_id: str, record_id: str, analysis: AnalysisResult | None):
    # SQLite와 행 잠금을 지원하는 DB 양쪽에서 동일 기록의 처리를 직렬화합니다.
    owned = db.execute(
        update(Record)
        .where(Record.id == record_id, Record.user_id == user_id)
        .values(effect_status=Record.effect_status)
    )
    if owned.rowcount != 1:
        raise EffectApplicationError("RECORD_NOT_FOUND", "기록을 찾을 수 없습니다.")
    record = db.get(Record, record_id)
    if record.status != "completed" or record.analysis is None:
        raise EffectApplicationError(
            "ANALYSIS_NOT_COMPLETED", "분석 완료 후 효과를 반영할 수 있습니다."
        )
    try:
        saved = AnalysisResult.model_validate(record.analysis)
    except ValidationError as exc:
        raise EffectApplicationError(
            "INVALID_SAVED_ANALYSIS", "저장된 분석 결과를 확인해 주세요."
        ) from exc
    if analysis is not None and analysis != saved:
        raise EffectApplicationError("ANALYSIS_MISMATCH", "저장된 분석 결과와 일치하지 않습니다.")
    grant = db.get(EffectGrant, record_id)
    if grant:
        record.effect_status = "applied"
        return EffectApplicationRead(
            record_id=record_id,
            already_applied=True,
            effects=grant.effects_snapshot,
        )
    effect_id = EFFECT_BY_CATEGORY.get(saved.category)
    if effect_id is None:
        raise EffectApplicationError(
            "EFFECT_RULE_NOT_CONFIGURED",
            "이 활동의 효과 지급 규칙은 아직 준비 중입니다.",
        )
    # 서로 다른 기록이 같은 효과를 동시에 강화할 때도 캐릭터별로 직렬화합니다.
    locked = db.execute(
        update(Character).where(Character.user_id == user_id).values(color=Character.color)
    )
    if locked.rowcount != 1:
        raise EffectApplicationError(
            "CHARACTER_NOT_FOUND", "최초 설정을 완료한 뒤 다시 시도해 주세요.", retryable=True
        )
    character = db.scalar(select(Character).where(Character.user_id == user_id))
    _increment_effect(db, character.id, effect_id)
    snapshot = [effect.model_dump(mode="json") for effect in read_character(db, character).effects]
    db.add(
        EffectGrant(
            record_id=record_id,
            character_id=character.id,
            category=saved.category,
            effects_snapshot=snapshot,
        )
    )
    record.effect_status = "applied"
    return EffectApplicationRead(record_id=record_id, already_applied=False, effects=snapshot)


def apply_analysis_effects(
    *,
    user_id: UUID,
    record_id: UUID,
    analysis: AnalysisResult | None = None,
) -> EffectApplicationRead:
    """B는 기록/분석을 commit한 뒤 호출합니다. 함수가 자체 세션/트랜잭션을 소유합니다.

    복구 시 analysis를 생략하면 저장된 분석을 검증해 사용하며 AI를 다시 호출하지 않습니다.
    오류 형식과 호출 예시는 docs/api-contract.md를 참고하세요.
    """
    user_id, record_id = str(UUID(str(user_id))), str(UUID(str(record_id)))
    try:
        with Session(get_engine()) as db, db.begin():
            result = _apply(db, user_id, record_id, analysis)
        return result
    except EffectApplicationError as exc:
        if exc.code not in {"RECORD_NOT_FOUND", "ANALYSIS_NOT_COMPLETED", "ANALYSIS_MISMATCH"}:
            _mark_failed(user_id, record_id)
        raise
    except Exception as exc:
        _mark_failed(user_id, record_id)
        raise EffectApplicationError(
            "EFFECT_APPLICATION_FAILED",
            "효과 반영에 실패했습니다. 다시 시도해 주세요.",
            retryable=True,
        ) from exc
