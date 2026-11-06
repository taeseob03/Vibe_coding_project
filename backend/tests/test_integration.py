import io
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.core.db import get_engine
from app.integrations import state_store, worker
from app.integrations.models import ActivityRecord
from app.integrations.router import save_input
from campus_records_prototype.analysis import KeywordResult
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session


def result(category="공부", review=False):
    return KeywordResult(
        keywords=["도서관"],
        summary="도서관 활동 기록입니다.",
        category=category,
        category_keywords=["도서관"] if category else [],
        category_reason="활동 키워드",
        needs_review=review,
    )


def png():
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "green").save(output, format="PNG")
    return output.getvalue()


def login(client, username):
    user = client.post("/auth/login", json={"username": username}).json()
    assert (
        client.post(
            "/profile/me/complete", json={"nickname": username, "color": "blue"}
        ).status_code
        == 200
    )
    return user


@pytest.fixture
def integrated(client, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    ai = AsyncMock(return_value=result())
    monkeypatch.setattr(worker, "extract_keywords", ai)
    user = login(client, "student_a")
    return client, user, ai


def counts(client):
    return {
        stat["category"]: stat["count"] for stat in client.get("/characters/me").json()["stats"]
    }


def submit(client, **options):
    data = {"text": "도서관에서 공부했다", "request_id": str(uuid4())} | options.pop("data", {})
    return client.post("/api/records", data=data, **options)


@pytest.mark.parametrize("mode", ["text", "image", "both"])
def test_b_analysis_to_user_stats_in_three_modes(integrated, mode):
    client, user, ai = integrated
    text = "도서관" if mode != "image" else ""
    files = {"image": ("photo.png", png(), "image/png")} if mode != "text" else None
    response = submit(client, data={"text": text}, files=files)
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    record = client.get(f"/api/records/{response.json()['id']}").json()
    assert record["status"] == "completed" and record["stat_status"] == "applied"
    assert record["analysis"] == result().model_dump()
    assert record["user_id"] == user["id"]
    assert record["has_image"] == (mode != "text")
    assert counts(client)["공부"] == 1
    assert client.get("/characters/me").json()["effects"] == []
    args = ai.call_args.args
    assert bool(args[0]) == (mode != "image")
    assert bool(args[1]) == (mode != "text")
    if files:
        image = client.get(f"/api/records/{record['id']}/image")
        assert image.content == png()
        assert image.headers["content-type"] == "image/png"
        assert image.headers["cache-control"] == "private, no-store"
    client.post("/auth/logout")
    login(client, "student_a")
    assert counts(client)["공부"] == 1
    assert client.get("/api/records").json()[0]["id"] == record["id"]


def test_user_isolation_including_images_retries_and_request_ids(integrated):
    client, user, ai = integrated
    request_id = str(uuid4())
    first = submit(
        client, data={"request_id": request_id}, files={"image": ("a.png", png())}
    ).json()
    second_user = login(client, "student_b")
    assert counts(client)["공부"] == 0
    assert client.get("/api/records").json() == []
    for suffix in ["", "/image"]:
        assert client.get(f"/api/records/{first['id']}{suffix}").status_code == 404
    assert client.post(f"/api/records/{first['id']}/retry").status_code == 404
    second = submit(client, data={"request_id": request_id}).json()
    assert second["id"] != first["id"] and second["user_id"] == second_user["id"]
    assert counts(client)["공부"] == 1
    login(client, "student_a")
    assert (
        counts(client)["공부"] == 1
        and client.get("/api/records").json()[0]["user_id"] == user["id"]
    )
    assert ai.await_count == 2


def test_duplicate_request_does_not_call_ai_or_count_again(integrated):
    client, _, ai = integrated
    request_id = str(uuid4())
    first = submit(client, data={"request_id": request_id}).json()
    second = submit(client, data={"request_id": request_id})
    assert second.status_code == 200 and second.json()["id"] == first["id"]
    assert counts(client)["공부"] == 1 and ai.await_count == 1
    assert submit(client, data={"request_id": request_id, "text": "다른 입력"}).status_code == 409
    assert ai.await_count == 1


def test_analysis_failure_preserves_original_and_retry_succeeds(integrated):
    client, _, ai = integrated
    ai.side_effect = RuntimeError("private-api-key-never-expose")
    record_id = submit(client, files={"image": ("photo.png", png())}).json()["id"]
    saved = client.get(f"/api/records/{record_id}").json()
    assert saved["status"] == "failed" and saved["analysis"] is None
    assert "private" not in str(saved["analysis_error"])
    assert client.get(f"/api/records/{record_id}/image").content == png()
    assert counts(client)["공부"] == 0
    ai.side_effect = None
    assert client.post(f"/api/records/{record_id}/retry").status_code == 202
    assert client.get(f"/api/records/{record_id}").json()["stat_status"] == "applied"
    assert counts(client)["공부"] == 1 and ai.await_count == 2
    assert client.post(f"/api/records/{record_id}/retry").status_code == 409


def test_state_failure_retries_saved_analysis_without_ai(integrated, monkeypatch):
    client, _, ai = integrated
    calculate = state_store.calculate_progress

    def failing_calculation(values):
        if values:
            raise RuntimeError("state save simulation")
        return calculate(values)

    with monkeypatch.context() as patch:
        patch.setattr(state_store, "calculate_progress", failing_calculation)
        record_id = submit(client).json()["id"]
    saved = client.get(f"/api/records/{record_id}").json()
    assert saved["status"] == "completed" and saved["stat_status"] == "failed"
    assert saved["analysis"] == result().model_dump()
    assert counts(client)["공부"] == 0
    assert client.post(f"/api/records/{record_id}/retry").status_code == 202
    assert client.get(f"/api/records/{record_id}").json()["stat_status"] == "applied"
    assert counts(client)["공부"] == 1 and ai.await_count == 1


@pytest.mark.parametrize("category", [None, "공부"])
def test_b_ambiguous_rules_skip_stats(integrated, category):
    client, _, ai = integrated
    ai.return_value = result(category, True)
    record_id = submit(client).json()["id"]
    record = client.get(f"/api/records/{record_id}").json()
    assert record["status"] == "completed" and record["stat_status"] == "skipped"
    assert all(value == 0 for value in counts(client).values())


def test_b_calculation_boundaries_are_used(integrated):
    client, _, _ = integrated
    for count in range(1, 11):
        assert submit(client).status_code == 201
        stats = next(
            stat
            for stat in client.get("/characters/me").json()["stats"]
            if stat["category"] == "공부"
        )
        assert stats["count"] == count
        assert stats["level"] == (1 if count < 5 else 2 if count < 10 else 3)


def test_concurrent_duplicate_and_state_replay(integrated):
    client, user, ai = integrated
    request_id = str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(lambda _: submit(client, data={"request_id": request_id}), range(4))
        )
    assert all(response.status_code in (200, 201) for response in responses)
    assert len({response.json()["id"] for response in responses}) == 1
    assert ai.await_count == 1 and counts(client)["공부"] == 1
    record_id = responses[0].json()["id"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: state_store.apply_saved_state(user["id"], record_id), range(4)))
    assert counts(client)["공부"] == 1


def test_concurrent_distinct_records_do_not_lose_counts(integrated):
    client, _, ai = integrated
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: submit(client), range(4)))
    assert all(response.status_code == 201 for response in responses)
    assert counts(client)["공부"] == 4 and ai.await_count == 4


@pytest.mark.parametrize(
    "data,files,expected",
    [
        ({"text": " "}, None, 400),
        ({"text": "a" * 5001}, None, 400),
        ({}, {"image": ("fake.png", b"bad image", "image/png")}, 400),
        ({}, {"image": ("empty.png", b"", "image/png")}, 400),
        ({}, {"image": ("large.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")}, 413),
    ],
)
def test_invalid_inputs_never_call_b(integrated, data, files, expected):
    client, _, ai = integrated
    assert client.post("/api/records", data=data, files=files).status_code == expected
    ai.assert_not_called()
    assert client.get("/api/records").json() == []


def test_requires_account_and_character(integrated):
    client, _, ai = integrated
    client.post("/auth/logout")
    assert submit(client).status_code == 401
    assert client.get("/api/records").status_code == 401
    client.post("/auth/login", json={"username": "new_account"})
    assert submit(client).status_code == 409
    ai.assert_not_called()


def test_interrupted_analysis_recovers_for_explicit_retry(integrated):
    client, user, ai = integrated
    with Session(get_engine()) as db:
        record, _ = save_input(db, user["id"], str(uuid4()), "보존할 원본", png(), "image/png")
        record_id = record.id
    claim = worker.claim_record(record_id)
    assert claim[-1] == 1
    worker.recover_interrupted()
    record = client.get(f"/api/records/{record_id}").json()
    assert (
        record["status"] == "failed" and record["analysis_error"]["code"] == "ANALYSIS_INTERRUPTED"
    )
    assert client.get(f"/api/records/{record_id}/image").content == png()
    assert client.post(f"/api/records/{record_id}/retry").status_code == 202
    assert not worker.save_result(record_id, 1, result("운동"))
    assert counts(client)["공부"] == 1 and ai.await_count == 1
    with Session(get_engine()) as db:
        assert db.scalar(select(ActivityRecord).where(ActivityRecord.id == record_id)).attempt == 2


def test_missing_gemini_key_keeps_record_for_later_retry(integrated, monkeypatch):
    from campus_records_prototype.analysis import extract_keywords

    client, _, _ = integrated
    monkeypatch.setattr(worker, "extract_keywords", extract_keywords)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    record_id = submit(client).json()["id"]
    record = client.get(f"/api/records/{record_id}").json()
    assert record["status"] == "failed"
    assert record["analysis_error"]["code"] == "ANALYSIS_UNAVAILABLE"
    assert record["text"] == "도서관에서 공부했다"
    assert counts(client)["공부"] == 0


def test_invalid_b_response_is_rejected_before_state_save(integrated):
    client, _, ai = integrated
    ai.return_value = {
        "keywords": ["구름"],
        "summary": "하늘",
        "category": "공부",
        "category_keywords": ["없는 근거"],
        "category_reason": "잘못된 근거",
        "needs_review": False,
    }
    record_id = submit(client).json()["id"]
    record = client.get(f"/api/records/{record_id}").json()
    assert record["status"] == "failed" and record["analysis"] is None
    assert record["analysis_error"]["code"] == "INVALID_ANALYSIS_RESPONSE"
    assert counts(client)["공부"] == 0


def test_static_modules_are_reachable_alongside_record_api(integrated):
    client, _, _ = integrated
    page = client.get("/")
    assert "/static/shared/main.js" in page.text
    for path in [
        "/static/records/index.js",
        "/static/characters/index.js",
        "/static/accounts/onboarding.js",
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
    assert client.get("/api/records").status_code == 200
    assert client.get("/records").status_code == 200
