from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.core.config import get_settings
from fastapi.testclient import TestClient


@pytest.fixture
def web_client(client, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    monkeypatch.setenv("LOCAL_WEB_PREVIEW_ENABLED", "true")
    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as preview:
        yield preview


def login(client, username="local_test", nickname="테스트친구"):
    result = client.post("/auth/login", json={"username": username})
    assert result.status_code == 200
    result = client.post("/profile/me/complete", json={"nickname": nickname, "color": "blue"})
    assert result.status_code == 200


def test_guest_and_setup_gates(web_client):
    assert web_client.get("/app", follow_redirects=False).headers["location"] == "/"
    assert web_client.get("/api/me").status_code == 401
    assert web_client.post("/api/keywords", data={"text": "공부"}).status_code == 401
    web_client.post("/auth/login", json={"username": "setup_needed"})
    assert web_client.get("/api/me").status_code == 409
    assert web_client.get("/app", follow_redirects=False).headers["location"] == "/"


def test_completed_setup_opens_app_and_bootstraps_account(web_client):
    login(web_client)
    page = web_client.get("/app")
    assert page.status_code == 200 and "post-dialog" in page.text
    assert page.headers["cache-control"] == "no-store"
    me = web_client.get("/api/me").json()
    assert me["nickname"] == "테스트친구" and me["color"] == "blue"
    bootstrap = web_client.get("/api/frontend-config.js")
    assert bootstrap.status_code == 200
    assert "javascript" in bootstrap.headers["content-type"]
    assert me["id"] in bootstrap.text
    assert "GEMINI_API_KEY" not in bootstrap.text
    for path in ["/static/app.js", "/static/api.mjs", "/shared/main.js"]:
        response = web_client.get(path)
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]


def test_logged_in_posts_are_isolated_and_persist_after_relogin(web_client, monkeypatch):
    from app.preview.bridge import analysis, routes

    def result(category):
        return analysis.KeywordResult(
            keywords=[category],
            summary=category,
            category=category,
            category_keywords=[category],
            category_reason="키워드 근거",
            needs_review=False,
        )

    service = AsyncMock(side_effect=[result("운동"), result("술"), result("공부")])
    monkeypatch.setattr(routes, "extract_keywords", service)
    login(web_client, "first_user", "첫번째")
    shared_record_id = str(uuid4())
    first = web_client.post("/api/keywords", data={"text": "운동", "record_id": shared_record_id})
    assert first.status_code == 200 and first.json()["awarded"]
    drink = {"text": "술", "record_id": str(uuid4())}
    assert web_client.post("/api/keywords", data=drink).json()["stack_changes"] == {
        "술": 1,
        "운동": -1,
    }
    assert not web_client.post("/api/keywords", data=drink).json()["awarded"]
    web_client.post("/auth/logout")
    assert web_client.get("/api/progress").status_code == 401
    login(web_client, "second_user", "두번째")
    assert all(item["count"] == 0 for item in web_client.get("/api/progress").json()["progress"])
    # The same UUID is allowed in another account and cannot reveal the first account's result.
    second = web_client.post(
        "/api/keywords", data={"text": "공부", "record_id": shared_record_id}
    ).json()
    assert second["category"] == "공부"
    web_client.post("/auth/logout")
    web_client.post("/auth/login", json={"username": "first_user"})
    counts = {
        item["category"]: item["count"]
        for item in web_client.get("/api/progress").json()["progress"]
    }
    assert counts == {"술": 1, "공부": 0, "연애": 0, "운동": 0}
    assert service.await_count == 3


def test_preview_is_opt_in(client):
    assert client.get("/api/preview-status").json() == {"enabled": False}
    assert client.get("/app").status_code == 404
