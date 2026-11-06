from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.analysis import KeywordResult
from app import routes, progress
from app.main import app


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("PROGRESS_DB", str(tmp_path / "progress.sqlite3"))


def result(category="연애", review=False):
    return KeywordResult(keywords=["반지", "데이트"], summary="데이트 기록", category=category,
                         category_keywords=["반지", "데이트"] if category else [],
                         category_reason="키워드 의미", needs_review=review)


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
        KeywordResult(keywords=["구름"], summary="하늘", category="연애", category_keywords=["데이트"], category_reason="", needs_review=False)
