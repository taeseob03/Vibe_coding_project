import pytest
from app.characters.models import Character
from app.core.config import get_settings
from app.core.db import get_engine
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture
def account_client(client, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    assert client.post("/auth/login", json={"username": "student_a"}).status_code == 200
    return client


def finish(client, **changes):
    body = {"nickname": "새내기", "color": "blue"} | changes
    return client.post("/profile/me/complete", json=body)


def test_draft_resumes_after_logout(account_client):
    client = account_client
    profile = client.get("/profile/me").json()
    assert profile["onboarding_completed"] is False
    assert profile["step"] == "nickname" and profile["nickname"] is None
    assert client.get("/characters/me").status_code == 404
    body = {"nickname": "  캠퍼스 친구  ", "color": "pink", "step": "color"}
    saved = client.put("/profile/me/draft", json=body).json()
    assert saved["nickname"] == "캠퍼스 친구"
    assert saved["color"] == "pink" and saved["step"] == "color"
    client.post("/auth/logout")
    client.post("/auth/login", json={"username": "student_a"})
    assert client.get("/profile/me").json() == saved
    assert client.get("/characters/me").status_code == 404


def test_partial_nickname_can_be_saved(account_client):
    response = account_client.put("/profile/me/draft", json={"nickname": "새"})
    assert response.status_code == 200
    assert response.json()["nickname"] == "새"
    assert response.json()["onboarding_completed"] is False


def test_complete_is_idempotent_and_preserves_character(account_client):
    client = account_client
    response = finish(client)
    assert response.status_code == 200
    result = response.json()
    assert result["profile"]["onboarding_completed"] is True
    assert result["profile"]["nickname"] == "새내기"
    assert result["character"]["color"] == "blue"
    assert result["character"]["effects"] == []
    # 응답 유실 후 재시도나 다른 탭의 요청이 기존 캐릭터를 바꾸지 않습니다.
    assert finish(client, nickname="다른이름", color="pink").json() == result
    assert client.get("/characters/me").json() == result["character"]
    client.post("/auth/logout")
    client.post("/auth/login", json={"username": "student_a"})
    assert client.get("/profile/me").json() == result["profile"]
    assert client.get("/characters/me").json() == result["character"]
    assert client.put("/profile/me/draft", json={"nickname": "덮어쓰기"}).status_code == 409
    with Session(get_engine()) as db:
        assert db.scalar(select(func.count()).select_from(Character)) == 1
        with pytest.raises(IntegrityError):
            db.add(Character(user_id=result["character"]["user_id"], color="green"))
            db.commit()


def test_profiles_and_characters_are_separate(account_client):
    client = account_client
    first = finish(client).json()
    client.post("/auth/login", json={"username": "student_b"})
    assert client.get("/profile/me").json()["onboarding_completed"] is False
    assert client.get("/characters/me").status_code == 404
    # 닉네임은 표시용 이름이므로 계정 사이의 중복을 허용합니다.
    second = finish(client, color="purple").json()
    assert second["profile"]["nickname"] == first["profile"]["nickname"]
    assert second["character"]["id"] != first["character"]["id"]
    client.post("/auth/login", json={"username": "student_a"})
    assert client.get("/characters/me").json() == first["character"]


@pytest.mark.parametrize(
    "body",
    [
        {"nickname": " ", "color": "green"},
        {"nickname": "a", "color": "green"},
        {"nickname": "a" * 13, "color": "green"},
        {"nickname": "친구", "color": "red"},
        {"nickname": "친구"},
        {"nickname": "친구", "color": "blue", "user_id": "other"},
    ],
)
def test_invalid_completion_keeps_setup_unfinished(account_client, body):
    assert account_client.post("/profile/me/complete", json=body).status_code == 422
    assert account_client.get("/profile/me").json()["onboarding_completed"] is False
    assert account_client.get("/characters/me").status_code == 404


def test_completion_rolls_back_profile_when_character_save_fails(account_client, monkeypatch):
    def fail_commit(_session):
        raise RuntimeError("simulate character save failure")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        with pytest.raises(RuntimeError):
            finish(account_client)
    assert account_client.get("/profile/me").json()["onboarding_completed"] is False
    assert account_client.get("/characters/me").status_code == 404
    assert finish(account_client).status_code == 200


def test_profile_requires_session(account_client):
    account_client.post("/auth/logout")
    assert account_client.get("/profile/me").status_code == 401
    assert account_client.put("/profile/me/draft", json={"nickname": "새내기"}).status_code == 401
    assert finish(account_client).status_code == 401
    assert account_client.get("/characters/me").status_code == 401


def test_concurrent_completion_creates_one_consistent_character(account_client):
    from concurrent.futures import ThreadPoolExecutor

    def request_setup(color):
        return finish(account_client, nickname=color, color=color)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(request_setup, ["blue", "pink"]))
    assert [response.status_code for response in responses] == [200, 200]
    first, second = [response.json() for response in responses]
    assert first == second
    assert first["profile"]["nickname"] == first["character"]["color"]
