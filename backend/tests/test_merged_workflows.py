from unittest.mock import AsyncMock
from uuid import uuid4

from app.integrations import worker
from app.preview.bridge import analysis, progress, routes
from app.preview.router import user_database
from test_web_preview import login


def result(category):
    return analysis.KeywordResult(
        keywords=[category],
        summary=category,
        category=category,
        category_keywords=[category],
        category_reason="활동 근거",
        needs_review=False,
    )


def counts(client, endpoint):
    data = client.get(endpoint).json()
    return {item["category"]: item["count"] for item in data.get("stats", data.get("progress"))}


def test_both_upload_apis_share_counts_drink_rule_and_feed(web_client, monkeypatch):
    login(web_client)
    monkeypatch.setattr(worker, "extract_keywords", AsyncMock(return_value=result("운동")))
    monkeypatch.setattr(routes, "extract_keywords", AsyncMock(return_value=result("술")))
    request_id = str(uuid4())
    first = web_client.post("/api/records", data={"text": "운동", "request_id": request_id})
    assert first.status_code == 201
    assert counts(web_client, "/api/progress")["운동"] == 1
    drink = {"text": "술", "record_id": str(uuid4())}
    second = web_client.post("/api/keywords", data=drink)
    assert second.status_code == 200
    assert second.json()["stack_changes"] == {"술": 1, "운동": -1}
    expected = {"술": 1, "공부": 0, "연애": 0, "운동": 0}
    assert counts(web_client, "/characters/me") == expected
    assert counts(web_client, "/api/progress") == expected
    assert len(web_client.get("/api/feed").json()["posts"]) == 2
    # Replay through the other entrypoint must not call AI or award twice.
    replay = web_client.post("/api/keywords", data={"text": "운동", "record_id": request_id})
    assert replay.status_code == 200 and not replay.json()["awarded"]
    assert counts(web_client, "/characters/me") == expected
    monkeypatch.setattr(worker, "extract_keywords", AsyncMock(return_value=result("운동")))
    web_client.post("/api/records", data={"text": "다시 운동"})
    assert counts(web_client, "/api/progress")["운동"] == 1


def test_legacy_account_counts_survive_first_integrated_upload(web_client, monkeypatch):
    login(web_client)
    user_id = web_client.get("/auth/me").json()["id"]
    with progress.use_database(user_database(user_id)):
        for _ in range(5):
            progress.save(str(uuid4()), "legacy", result("연애"))
    monkeypatch.setattr(worker, "extract_keywords", AsyncMock(return_value=result("공부")))
    web_client.post("/api/records", data={"text": "공부"})
    expected = {"술": 0, "공부": 1, "연애": 5, "운동": 0}
    assert counts(web_client, "/characters/me") == expected
    assert counts(web_client, "/api/progress") == expected
