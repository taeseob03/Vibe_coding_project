from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app import progress, routes
from app.analysis import KeywordResult
from app.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("PROGRESS_DB", str(tmp_path / "progress.sqlite3"))


def result(category="연애", review=False):
    return KeywordResult(
        keywords=["반지", "데이트"],
        summary="데이트 기록",
        category=category,
        category_keywords=["반지", "데이트"] if category else [],
        category_reason="키워드 의미",
        needs_review=review,
    )


def test_growth_boundaries_and_persistence():
    for count in range(1, 11):
        progress.save(str(uuid4()), "hash", result())
        row = next(x for x in progress.state() if x["category"] == "연애")
        assert row["count"] == count
        assert row["level"] == (1 if count < 5 else 2 if count < 10 else 3)
    assert next(x for x in progress.state() if x["category"] == "공부")["count"] == 0


def test_idempotent_requests_and_conflict(monkeypatch):
    service = AsyncMock(return_value=result())
    monkeypatch.setattr(routes, "extract_keywords", service)
    client = TestClient(app)
    data = {"text": "반지 데이트", "record_id": str(uuid4())}
    first = client.post("/api/keywords", data=data).json()
    second = client.post("/api/keywords", data=data).json()
    assert first["awarded"] and not second["awarded"]
    assert next(x for x in second["progress"] if x["category"] == "연애")["count"] == 1
    service.assert_awaited_once()
    assert client.post("/api/keywords", data={**data, "text": "다른 기록"}).status_code == 409


def test_concurrent_duplicate_is_counted_once():
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: progress.save("same-id", "hash", result()), range(8)))
    assert next(x for x in progress.state() if x["category"] == "연애")["count"] == 1


@pytest.mark.parametrize("category", [None, "연애"])
def test_ambiguous_or_unrelated_not_counted(category):
    progress.save(str(uuid4()), "hash", result(category, True))
    assert all(x["count"] == 0 for x in progress.state())


def test_invented_evidence_rejected():
    with pytest.raises(ValidationError):
        KeywordResult(
            keywords=["구름"],
            summary="하늘",
            category="연애",
            category_keywords=["데이트"],
            category_reason="",
            needs_review=False,
        )


def count(category):
    return next(item for item in progress.state() if item["category"] == category)["count"]


def test_drinking_reduces_exercise_and_drops_design_level():
    for _ in range(5):
        progress.save(str(uuid4()), "hash", result("운동"))
    assert next(item for item in progress.state() if item["category"] == "운동")["level"] == 2
    record_id = str(uuid4())
    progress.save(record_id, "hash", result("술"))
    assert count("술") == 1 and count("운동") == 4
    assert next(item for item in progress.state() if item["category"] == "운동")["level"] == 1
    assert progress.snapshot(record_id)[1] == {"술": 1, "운동": -1}
    assert count("공부") == 0 and count("연애") == 0


def test_drinking_at_zero_never_borrows_from_future_exercise():
    for _ in range(3):
        progress.save(str(uuid4()), "hash", result("술"))
    assert count("운동") == 0
    progress.save(str(uuid4()), "hash", result("운동"))
    assert count("운동") == 1
    progress.save(str(uuid4()), "hash", result("술"))
    assert count("운동") == 0
    assert next(item for item in progress.state() if item["category"] == "운동")["level"] == 0


def test_uncertain_drinking_never_reduces_stacks():
    progress.save(str(uuid4()), "hash", result("운동"))
    progress.save(str(uuid4()), "hash", result("술", True))
    assert count("운동") == 1 and count("술") == 0


def test_concurrent_drinking_retry_deducts_only_once():
    for _ in range(3):
        progress.save(str(uuid4()), "hash", result("운동"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: progress.save("drink-once", "hash", result("술")), range(8)))
    assert count("운동") == 2 and count("술") == 1


def test_drinking_api_reports_changes_and_retry_does_not_deduct(monkeypatch):
    progress.save(str(uuid4()), "hash", result("운동"))
    monkeypatch.setattr(routes, "extract_keywords", AsyncMock(return_value=result("술")))
    client = TestClient(app)
    data = {"text": "술을 마셨다", "record_id": str(uuid4())}
    first = client.post("/api/keywords", data=data).json()
    second = client.post("/api/keywords", data=data).json()
    assert first["stack_changes"] == {"술": 1, "운동": -1}
    assert second["stack_changes"] == {} and second["awarded"] is False
    assert count("운동") == 0 and count("술") == 1
