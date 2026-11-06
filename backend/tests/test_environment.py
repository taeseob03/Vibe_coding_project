from uuid import UUID

import pytest
from app.accounts.dependencies import CurrentUser, get_current_user
from app.accounts.models import User
from app.core.config import Settings
from app.core.db import get_engine
from pydantic import ValidationError
from sqlalchemy.orm import Session

OTHER_USER = "00000000-0000-4000-8000-000000000002"


def test_health_frontend_and_openapi(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert 'lang="ko"' in client.get("/").text
    assert client.get("/shared/main.js").status_code == 200
    assert "/records/{record_id}" in client.get("/openapi.json").json()["paths"]
    assert client.get("/.env").status_code == 404


def test_record_persistence_and_contract(client):
    created = client.post("/records", json={"text": "도서관에서 공부했어요."})
    assert created.status_code == 201
    record = created.json()
    UUID(record["id"])
    assert record["status"] == "completed"
    assert record["analysis"]["category"] == "study"
    assert record["effect_status"] == "not_requested"
    assert record["created_at"].endswith("Z")
    assert client.get(f"/records/{record['id']}").json() == record
    assert client.get("/records").json() == [record]
    # 새 세션에도 원본 글과 분석이 저장되어 있습니다.
    with Session(get_engine()) as db:
        from app.records.models import Record

        assert db.get(Record, record["id"]).text == "도서관에서 공부했어요."


def test_other_users_cannot_read_or_retry(client):
    record = client.post("/records", json={"text": "내 기록"}).json()
    with Session(get_engine()) as db:
        db.add(User(id=OTHER_USER))
        db.commit()
    client.app.dependency_overrides[get_current_user] = lambda: CurrentUser(OTHER_USER)
    assert client.get("/records").json() == []
    assert client.get(f"/records/{record['id']}").status_code == 404
    assert client.post(f"/records/{record['id']}/retry").status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"text": " "},
        {"text": "a" * 10001},
        {"text": "기록", "user_id": OTHER_USER},
    ],
)
def test_record_validation(client, body):
    response = client.post("/records", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unimplemented_features_are_explicit(client):
    assert client.get("/characters/me").status_code == 404
    record = client.post("/records", json={"text": "기록"}).json()
    assert client.post(f"/records/{record['id']}/retry").status_code == 501


def test_missing_auth_is_rejected(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    response = client.get("/records")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("environment", ["production", "staging", "test"])
def test_dev_auth_cannot_run_outside_development(environment):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env=environment, dev_auth_enabled=True)
