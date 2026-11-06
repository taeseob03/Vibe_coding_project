from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from app.analysis.schemas import AnalysisResult, Category
from app.characters import service
from app.characters.effect_models import CharacterEffect, EffectGrant
from app.core.db import get_engine
from app.records.models import Record
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@pytest.fixture
def campus(client):
    user = client.post("/auth/login", json={"username": "student_a"}).json()
    assert (
        client.post(
            "/profile/me/complete", json={"nickname": "새내기", "color": "green"}
        ).status_code
        == 200
    )
    return client, UUID(user["id"])


def analysis(category="study"):
    return AnalysisResult(
        category=Category(category), keywords=["활동"], summary="활동을 기록했어요."
    )


def create_record(client, category="study"):
    record = client.post("/records", json={"text": "나의 대학생활"}).json()
    # B가 완료한 분석을 저장한 상황을 구성합니다. 실제 AI는 호출하지 않습니다.
    with Session(get_engine()) as db, db.begin():
        saved = db.get(Record, record["id"])
        saved.analysis = analysis(category).model_dump(mode="json")
    return UUID(record["id"])


def grant(user_id, record_id, result=None):
    return service.apply_analysis_effects(user_id=user_id, record_id=record_id, analysis=result)


def inventory(client):
    return {
        effect["effect_id"]: effect["level"]
        for effect in client.get("/characters/me").json()["effects"]
    }


def test_distinct_effects_accumulate_and_new_records_increase_level(campus):
    client, user_id = campus
    book_record = create_record(client)
    result = grant(user_id, book_record, analysis())
    assert result.effect_status == "applied" and not result.already_applied
    assert inventory(client) == {"book": 1}
    grant(user_id, create_record(client, "social"))
    assert inventory(client) == {"book": 1, "heart": 1}
    grant(user_id, create_record(client))
    assert inventory(client) == {"book": 2, "heart": 1}
    # 같은 기록은 지급 당시 결과를 반환하며, 최신 캐릭터 레벨은 그대로입니다.
    replay = grant(user_id, book_record)
    assert replay.already_applied
    assert replay.effects == result.effects
    assert inventory(client) == {"book": 2, "heart": 1}
    with Session(get_engine()) as db:
        assert db.get(Record, str(book_record)).effect_status == "applied"
        assert db.scalar(select(func.count()).select_from(EffectGrant)) == 3
    client.post("/auth/logout")
    client.post("/auth/login", json={"username": "student_a"})
    assert inventory(client) == {"book": 2, "heart": 1}


def test_other_user_cannot_claim_record(campus):
    client, owner_id = campus
    record_id = create_record(client)
    other = client.post("/auth/login", json={"username": "student_b"}).json()
    client.post("/profile/me/complete", json={"nickname": "다른친구", "color": "blue"})
    with pytest.raises(service.EffectApplicationError) as error:
        grant(UUID(other["id"]), record_id)
    assert error.value.code == "RECORD_NOT_FOUND"
    assert inventory(client) == {}
    with Session(get_engine()) as db:
        assert db.get(Record, str(record_id)).effect_status == "not_requested"
    assert grant(owner_id, record_id).effects[0].level == 1


def test_mismatched_caller_analysis_does_not_replace_saved_result(campus):
    client, user_id = campus
    record_id = create_record(client)
    with pytest.raises(service.EffectApplicationError) as error:
        grant(user_id, record_id, analysis("social"))
    assert error.value.code == "ANALYSIS_MISMATCH"
    assert inventory(client) == {}
    assert grant(user_id, record_id).effects[0].effect_id == "book"


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_unfinished_analysis_cannot_grant(campus, status):
    client, user_id = campus
    record_id = create_record(client)
    with Session(get_engine()) as db, db.begin():
        db.get(Record, str(record_id)).status = status
    with pytest.raises(service.EffectApplicationError) as error:
        grant(user_id, record_id)
    assert error.value.code == "ANALYSIS_NOT_COMPLETED"
    assert inventory(client) == {}
    with Session(get_engine()) as db:
        assert db.get(Record, str(record_id)).effect_status == "not_requested"


def test_bad_saved_analysis_is_not_rewarded(campus):
    client, user_id = campus
    record_id = create_record(client)
    with Session(get_engine()) as db, db.begin():
        db.get(Record, str(record_id)).analysis = {"category": "invented"}
    with pytest.raises(service.EffectApplicationError) as error:
        grant(user_id, record_id)
    assert error.value.code == "INVALID_SAVED_ANALYSIS"
    assert inventory(client) == {}
    with Session(get_engine()) as db:
        record = db.get(Record, str(record_id))
        assert record.status == "completed" and record.effect_status == "failed"
        assert db.get(EffectGrant, str(record_id)) is None


@pytest.mark.parametrize(
    "category,effect_id",
    [
        ("exercise", "dumbbell"),
        ("culture", "palette"),
        ("daily", "star"),
    ],
)
def test_new_effects_grant_strengthen_and_do_not_duplicate(campus, category, effect_id):
    client, user_id = campus
    first = create_record(client, category)
    grant(user_id, first)
    assert inventory(client) == {effect_id: 1}
    grant(user_id, first)
    assert inventory(client) == {effect_id: 1}
    grant(user_id, create_record(client, category))
    assert inventory(client) == {effect_id: 2}
    client.post("/auth/logout")
    client.post("/auth/login", json={"username": "student_a"})
    assert inventory(client) == {effect_id: 2}


def test_all_five_effects_remain_owned_together(campus):
    client, user_id = campus
    categories = ["study", "social", "exercise", "culture", "daily"]
    for category in categories:
        grant(user_id, create_record(client, category))
    assert inventory(client) == {"book": 1, "heart": 1, "dumbbell": 1, "palette": 1, "star": 1}


def test_failure_rolls_back_level_and_recovers_from_saved_analysis(campus, monkeypatch):
    client, user_id = campus
    grant(user_id, create_record(client))
    record_id = create_record(client)
    increment = service._increment_effect

    def fail_after_increment(*args):
        increment(*args)
        raise RuntimeError("private failure details must not be returned")

    with monkeypatch.context() as patch:
        patch.setattr(service, "_increment_effect", fail_after_increment)
        with pytest.raises(service.EffectApplicationError) as error:
            grant(user_id, record_id)
    assert error.value.code == "EFFECT_APPLICATION_FAILED"
    assert error.value.retryable
    assert "private" not in error.value.message
    assert inventory(client) == {"book": 1}
    with Session(get_engine()) as db:
        record = db.get(Record, str(record_id))
        assert record.status == "completed" and record.effect_status == "failed"
        assert record.analysis == analysis().model_dump(mode="json")
        assert db.get(EffectGrant, str(record_id)) is None
    assert not grant(user_id, record_id).already_applied
    assert inventory(client) == {"book": 2}
    assert grant(user_id, record_id).already_applied
    assert inventory(client) == {"book": 2}


def test_character_setup_can_be_completed_before_retry(campus):
    client, _ = campus
    user = client.post("/auth/login", json={"username": "not_ready"}).json()
    record_id = create_record(client)
    with pytest.raises(service.EffectApplicationError) as error:
        grant(UUID(user["id"]), record_id)
    assert error.value.code == "CHARACTER_NOT_FOUND"
    client.post("/profile/me/complete", json={"nickname": "준비완료", "color": "blue"})
    assert grant(UUID(user["id"]), record_id).effects[0].level == 1


def test_simultaneous_same_record_only_increases_once(campus):
    client, user_id = campus
    record_id = create_record(client)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: grant(user_id, record_id), range(4)))
    assert sum(not result.already_applied for result in results) == 1
    assert inventory(client) == {"book": 1}
    with Session(get_engine()) as db:
        assert db.scalar(select(func.count()).select_from(EffectGrant)) == 1


def test_simultaneous_distinct_records_do_not_lose_level_increments(campus):
    client, user_id = campus
    ids = [create_record(client) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda record_id: grant(user_id, record_id), ids))
    assert all(not result.already_applied for result in results)
    assert inventory(client) == {"book": 4}


def test_visibility_is_separate_and_retained_when_level_increases(campus):
    client, user_id = campus
    grant(user_id, create_record(client))
    with Session(get_engine()) as db, db.begin():
        db.scalar(select(CharacterEffect)).visible = False
    grant(user_id, create_record(client))
    effect = client.get("/characters/me").json()["effects"][0]
    assert effect == {"effect_id": "book", "level": 2, "visible": False}
