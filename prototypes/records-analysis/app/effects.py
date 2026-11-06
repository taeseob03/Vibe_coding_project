"""Server-owned mapping; the model never invents or grants character items."""
from pydantic import BaseModel, ConfigDict

from .analysis import KeywordResult


class CharacterEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    icon: str
    slot: str


EFFECTS = {
    "술": CharacterEffect(id="drink_mug", name="맥주잔 소품", icon="🍺", slot="hand"),
    "공부": CharacterEffect(id="study_book", name="책 소품", icon="📚", slot="hand"),
    "연애": CharacterEffect(id="love_hearts", name="하트 효과", icon="💕", slot="aura"),
    "운동": CharacterEffect(id="exercise_dumbbell", name="덤벨 소품", icon="🏋️", slot="hand"),
}


class AnalysisResult(KeywordResult):
    character_effect: CharacterEffect | None
    record_id: str
    awarded: bool
    progress: list[dict]


def attach_effect(result: KeywordResult, record_id: str, awarded: bool, progress: list[dict]) -> AnalysisResult:
    effect = EFFECTS.get(result.category) if not result.needs_review else None
    return AnalysisResult(**result.model_dump(), character_effect=effect, record_id=record_id, awarded=awarded, progress=progress)
