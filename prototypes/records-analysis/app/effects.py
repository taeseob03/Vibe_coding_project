"""Server-owned mapping; the model never invents or grants character items."""

from pydantic import BaseModel, ConfigDict, Field

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
    stack_changes: dict[str, int] = Field(default_factory=dict)


def attach_effect(
    result: KeywordResult,
    record_id: str,
    awarded: bool,
    progress: list[dict],
    stack_changes: dict[str, int] | None = None,
) -> AnalysisResult:
    effect = EFFECTS.get(result.category) if not result.needs_review else None
    return AnalysisResult(
        **result.model_dump(),
        character_effect=effect,
        record_id=record_id,
        awarded=awarded,
        progress=progress,
        stack_changes=stack_changes or {},
    )


def character_state(progress):
    """초기 표현 규칙: 저장된 현재 스탯에서 표시 상태를 결정합니다."""
    active = [item for item in progress if item["count"] > 0]
    if not active:
        return {"expression": "neutral", "intensity": 0, "dominant_activity": None}
    dominant = max(active, key=lambda item: item["count"])
    expressions = {"공부": "focused", "운동": "energetic", "연애": "heart_eyes", "술": "relaxed"}
    return {"expression": expressions[dominant["category"]], "intensity": dominant["level"],
            "dominant_activity": dominant["category"]}
