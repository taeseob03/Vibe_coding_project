from datetime import UTC, datetime, timedelta

import pytest
from app.accounts.models import LoginSession, User
from app.accounts.service import hash_session_token
from app.core.config import get_settings
from app.core.db import get_engine
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@pytest.fixture
def real_client(client, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    return client


def login(client, username="campus_a"):
    response = client.post("/auth/login", json={"username": username})
    assert response.status_code == 200
    return response


def test_first_access_and_normalized_returning_access(real_client):
    assert real_client.get("/auth/me").status_code == 401
    first = login(real_client, " Campus_A ").json()
    assert first["username"] == "campus_a"
    assert first["auth_mode"] == "id-only"
    assert real_client.get("/auth/me").json() == first
    # DB 연결을 새로 열어도 접속 상태와 계정은 DB에서 복원됩니다.
    get_engine().dispose()
    assert real_client.get("/auth/me").json() == first
    assert real_client.post("/auth/logout").status_code == 204
    assert login(real_client, "campus_a").json() == first
    with Session(get_engine()) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1


def test_korean_ids(real_client):
    assert login(real_client, "캠퍼스_학생1").json()["username"] == "캠퍼스_학생1"


def test_sessions_are_hashed_rotated_and_revoked(real_client):
    response = login(real_client)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=604800" in cookie
    first_token = real_client.cookies.get("campus_session")
    with Session(get_engine()) as db:
        session = db.scalar(select(LoginSession))
        assert session.token_hash == hash_session_token(first_token)
        assert session.token_hash != first_token
    login(real_client)
    second_token = real_client.cookies.get("campus_session")
    assert second_token != first_token
    real_client.cookies.clear()
    real_client.cookies.set("campus_session", first_token, domain="testserver.local")
    assert real_client.get("/auth/me").status_code == 401
    real_client.cookies.clear()
    real_client.cookies.set("campus_session", second_token, domain="testserver.local")
    assert real_client.post("/auth/logout").status_code == 204
    assert not real_client.cookies.get("campus_session")
    real_client.cookies.set("campus_session", second_token, domain="testserver.local")
    assert real_client.get("/auth/me").status_code == 401


def test_expired_session_rejected(real_client):
    login(real_client)
    with Session(get_engine()) as db:
        session = db.scalar(select(LoginSession))
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    response = real_client.get("/records")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


def test_two_accounts_record_isolation_and_returning_access(real_client):
    first = login(real_client, "student_a").json()
    record = real_client.post("/records", json={"text": "A의 공부 기록"}).json()
    assert record["user_id"] == first["id"]
    real_client.post("/auth/logout")
    second = login(real_client, "student_b").json()
    assert second["id"] != first["id"]
    assert real_client.get("/records").json() == []
    assert real_client.get(f"/records/{record['id']}").status_code == 404
    assert real_client.post(f"/records/{record['id']}/retry").status_code == 404
    login(real_client, "student_a")
    assert real_client.get("/records").json()[0]["id"] == record["id"]


@pytest.mark.parametrize(
    "username", ["", "a", "a" * 21, "hello world", "../etc", "<script>", "hi@test", "🙂🙂"]
)
def test_invalid_id(real_client, username):
    response = real_client.post("/auth/login", json={"username": username})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_ignores_no_ownership_fields(real_client):
    response = real_client.post("/auth/login", json={"username": "student", "user_id": "other"})
    assert response.status_code == 422


def test_cross_origin_writes_blocked(real_client):
    assert (
        real_client.post(
            "/auth/login", json={"username": "student"}, headers={"Origin": "https://other.example"}
        ).status_code
        == 403
    )
    login(real_client)
    assert (
        real_client.post(
            "/records", json={"text": "외부 입력"}, headers={"Origin": "null"}
        ).status_code
        == 403
    )
    assert (
        real_client.post("/auth/logout", headers={"Sec-Fetch-Site": "cross-site"}).status_code
        == 403
    )
    assert (
        real_client.post(
            "/records", json={"text": "같은 사이트"}, headers={"Origin": "http://testserver"}
        ).status_code
        == 201
    )


def test_bad_cookie_does_not_fall_back_to_dev_user(client):
    client.cookies.set("campus_session", "invalid")
    assert client.get("/auth/me").status_code == 401


def test_production_cookie_requires_https(real_client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    response = login(real_client)
    assert "Secure" in response.headers["set-cookie"]
