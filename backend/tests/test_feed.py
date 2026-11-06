import asyncio
import base64
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.core.db import get_engine
from app.preview.models import WebPost
from PIL import Image
from sqlalchemy.orm import Session


def login(client, name):
    result = client.post("/auth/login", json={"username": name})
    assert result.status_code == 200
    assert (
        client.post("/profile/me/complete", json={"nickname": name, "color": "blue"}).status_code
        == 200
    )
    return result.json()["id"]


def png():
    stream = io.BytesIO()
    Image.new("RGB", (24, 24), "blue").save(stream, "PNG")
    return stream.getvalue()


@pytest.fixture
def analyzer(monkeypatch):
    from app.preview.bridge import analysis, routes

    def result(category="공부"):
        return analysis.KeywordResult(
            keywords=[category],
            summary="화면에 표시하지 않는 AI 요약",
            category=category,
            category_keywords=[category],
            category_reason="키워드",
            needs_review=False,
        )

    service = AsyncMock(return_value=result())
    monkeypatch.setattr(routes, "extract_keywords", service)
    return service, result


def post(client, text="my post", record_id=None, photo=False):
    return client.post(
        "/api/keywords",
        data={"text": text, "record_id": record_id or str(uuid4())},
        files={"image": ("image.png", png(), "image/png")} if photo else None,
    )


def test_private_photo_and_friend_feed_require_acceptance(web_client, analyzer):
    alice = login(web_client, "alice")
    saved = post(web_client, "내가 작성한 글", photo=True)
    assert saved.status_code == 200
    post_id = saved.json()["post_id"]
    own = web_client.get("/api/feed").json()["posts"]
    assert len(own) == 1 and own[0]["text"] == "내가 작성한 글"
    assert "summary" not in own[0]
    image_url = own[0]["image_url"]
    image = web_client.get(image_url)
    assert image.content == png() and image.headers["content-type"] == "image/png"
    bob = login(web_client, "bobby")
    assert web_client.get("/api/feed").json()["posts"] == []
    assert web_client.get(image_url).status_code == 404
    search = web_client.get("/api/people", params={"nickname": "alice"}).json()
    assert search[0]["id"] == alice
    request = web_client.post("/api/friend-requests", json={"recipient_id": alice})
    assert request.status_code == 201
    request_id = request.json()["id"]
    assert web_client.get(image_url).status_code == 404
    assert web_client.get("/api/feed?scope=friends").json()["posts"] == []
    assert (
        web_client.post(
            f"/api/friend-requests/{request_id}/response", json={"accept": True}
        ).status_code
        == 404
    )
    login(web_client, "third_user")
    assert (
        web_client.post(
            f"/api/friend-requests/{request_id}/response", json={"accept": True}
        ).status_code
        == 404
    )
    login(web_client, "alice")
    incoming = web_client.get("/api/friends").json()["incoming"]
    assert incoming[0]["person"]["id"] == bob
    assert (
        web_client.post(
            f"/api/friend-requests/{request_id}/response", json={"accept": True}
        ).status_code
        == 200
    )
    assert web_client.get("/api/friends").json()["friends"][0]["id"] == bob
    login(web_client, "bobby")
    assert web_client.get("/api/feed?scope=friends").json()["posts"][0]["id"] == post_id
    assert web_client.get(image_url).content == png()
    assert web_client.get("/api/feed?scope=mine").json()["posts"] == []
    login(web_client, "third_user")
    assert web_client.get(image_url).status_code == 404
    web_client.post("/auth/logout")
    assert web_client.get(image_url).status_code == 401
    assert web_client.get("/api/feed").status_code == 401


def test_latest_first_cursor_pagination_and_new_upload_during_paging(web_client, analyzer):
    login(web_client, "pager")
    for i in range(3):
        item = post(web_client, str(i)).json()
        with Session(get_engine()) as db, db.begin():
            db.get(WebPost, item["post_id"]).created_at = datetime(
                2026, 1, 1, tzinfo=UTC
            ) + timedelta(seconds=i)
    first = web_client.get("/api/feed?limit=1").json()
    assert first["posts"][0]["text"] == "2" and first["next_cursor"]
    post(web_client, "new")
    second = web_client.get("/api/feed", params={"limit": 1, "before": first["next_cursor"]}).json()
    assert second["posts"][0]["text"] == "1"
    third = web_client.get("/api/feed", params={"limit": 1, "before": second["next_cursor"]}).json()
    assert third["posts"][0]["text"] == "0" and third["next_cursor"] is None
    assert web_client.get("/api/feed").json()["posts"][0]["text"] == "new"


def test_retry_never_duplicates_photo_or_stacks_and_rejects_changed_content(web_client, analyzer):
    login(web_client, "repeat")
    identifier = str(uuid4())
    first = post(web_client, "original", identifier, True).json()
    replay = post(web_client, "original", identifier, True).json()
    assert first["post_id"] == replay["post_id"] and not replay["awarded"]
    assert len(web_client.get("/api/feed").json()["posts"]) == 1
    analyzer[0].assert_awaited_once()
    assert post(web_client, "changed", identifier, True).status_code == 409
    assert web_client.get("/api/feed").json()["posts"][0]["text"] == "original"


def test_analysis_failure_preserves_photo_and_retry_completes_same_post(web_client, analyzer):
    from app.preview.bridge import analysis

    login(web_client, "failure")
    analyzer[0].side_effect = [analysis.AnalysisUnavailable("일시적인 실패"), analyzer[1]()]
    identifier = str(uuid4())
    assert post(web_client, "saved", identifier, True).status_code == 503
    stored = web_client.get("/api/feed").json()["posts"][0]
    assert stored["analysis_status"] == "failed"
    assert web_client.get(stored["image_url"]).content == png()
    response = post(web_client, "saved", identifier, True)
    assert response.status_code == 200 and response.json()["post_id"] == stored["id"]
    assert len(web_client.get("/api/feed").json()["posts"]) == 1
    assert web_client.get("/api/feed").json()["posts"][0]["analysis_status"] == "completed"


def test_parallel_same_post_only_analyzes_once(web_client, analyzer):
    login(web_client, "parallel")
    started, release = Event(), Event()

    async def wait_for_release(*args):
        started.set()
        await asyncio.to_thread(release.wait, 5)
        return analyzer[1]()

    analyzer[0].side_effect = wait_for_release
    identifier = str(uuid4())
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(post, web_client, "one", identifier)
        assert started.wait(3)
        try:
            assert post(web_client, "one", identifier).status_code == 409
        finally:
            release.set()
        assert future.result(timeout=5).status_code == 200
    analyzer[0].assert_awaited_once()


def test_recover_stale_processing_post_without_duplicate_stack(web_client, analyzer):
    login(web_client, "recovery")
    identifier = str(uuid4())
    saved = post(web_client, "one", identifier).json()
    with Session(get_engine()) as db, db.begin():
        item = db.get(WebPost, saved["post_id"])
        item.analysis_status = "processing"
        item.analysis_data = None
        item.started_at = datetime.now(UTC) - timedelta(minutes=3)
    response = post(web_client, "one", identifier)
    assert response.status_code == 200 and not response.json()["awarded"]
    analyzer[0].assert_awaited_once()


def test_rejected_request_cannot_read_photo_and_search_escapes_wildcards(web_client, analyzer):
    first = login(web_client, "first")
    saved = post(web_client, photo=True).json()
    second = login(web_client, "second")
    assert web_client.get("/api/people?nickname=%25").json() == []
    assert web_client.get("/api/people?nickname=").json() == []
    assert web_client.post("/api/friend-requests", json={"recipient_id": second}).status_code == 400
    request = web_client.post("/api/friend-requests", json={"recipient_id": first}).json()
    assert web_client.post("/api/friend-requests", json={"recipient_id": first}).status_code == 409
    login(web_client, "first")
    assert (
        web_client.post(
            f"/api/friend-requests/{request['id']}/response", json={"accept": False}
        ).status_code
        == 200
    )
    login(web_client, "second")
    assert web_client.get(f"/api/posts/{saved['post_id']}/image").status_code == 404
    assert web_client.get("/api/feed?scope=friends").json()["posts"] == []
    assert web_client.post("/api/friend-requests", json={"recipient_id": first}).status_code == 201


@pytest.mark.parametrize("cursor", ["!!!", base64.urlsafe_b64encode(b"[]").decode(), "bad"])
def test_bad_cursor_is_rejected(web_client, cursor):
    login(web_client, "cursor")
    assert web_client.get("/api/feed", params={"before": cursor}).status_code == 422


def test_invalid_upload_does_not_create_post(web_client):
    login(web_client, "invalid")
    response = web_client.post(
        "/api/keywords", files={"image": ("x.png", b"not-a-photo", "image/png")}
    )
    assert response.status_code == 400
    assert web_client.get("/api/feed").json()["posts"] == []
