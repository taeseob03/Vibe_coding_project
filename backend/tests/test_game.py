from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.core.db import get_engine
from app.game.models import Member, Title
from app.game.service import award_titles
from app.integrations.models import ActivityRecord
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def game(client, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    return client


def account(client, username, nickname=None):
    client.cookies.clear()
    user = client.post("/auth/login", json={"username": username}).json()
    assert (
        client.post(
            "/profile/me/complete", json={"nickname": nickname or username, "color": "green"}
        ).status_code
        == 200
    )
    return user


def room(client):
    return client.get("/api/lounges").json()[0]["id"]


def sample(client, category, request_id=None):
    return client.post(
        "/api/records/demo",
        data={"category": category, "text": "체험 활동", "request_id": request_id or str(uuid4())},
    )


def values(client):
    return {item["category"]: item for item in client.get("/api/progress").json()["progress"]}


def test_real_invitation_membership_and_access_control(game):
    a = account(game, "friend_a")
    owner_room = room(game)
    b = account(game, "friend_b")
    assert room(game) != owner_room
    assert game.get(f"/api/lounges/{owner_room}/members").status_code == 404
    account(game, "friend_a")
    found = game.get("/api/users", params={"nickname": "friend"}).json()
    assert [user["id"] for user in found] == [b["id"]]
    invitation = game.post(f"/api/lounges/{owner_room}/invitations", json={"recipient_id": b["id"]})
    assert invitation.status_code == 201
    iid = invitation.json()["id"]
    assert (
        game.post(
            f"/api/lounges/{owner_room}/invitations", json={"recipient_id": b["id"]}
        ).status_code
        == 409
    )
    assert (
        game.post(f"/api/lounge-invitations/{iid}/response", json={"accept": True}).status_code
        == 404
    )
    account(game, "friend_b")
    assert game.get("/api/lounge-invitations").json()[0]["id"] == iid
    assert (
        game.post(f"/api/lounge-invitations/{iid}/response", json={"accept": True}).status_code
        == 200
    )
    assert (
        game.post(f"/api/lounge-invitations/{iid}/response", json={"accept": True}).status_code
        == 200
    )
    assert (
        game.post(f"/api/lounge-invitations/{iid}/response", json={"accept": False}).status_code
        == 409
    )
    assert {person["id"] for person in game.get(f"/api/lounges/{owner_room}/members").json()} == {
        a["id"],
        b["id"],
    }
    assert (
        game.post(
            f"/api/lounges/{owner_room}/invitations", json={"recipient_id": a["id"]}
        ).status_code
        == 403
    )
    with Session(get_engine()) as db:
        assert len(db.scalars(select(Member).where(Member.room_id == owner_room)).all()) == 2


def test_decline_then_reinvite_and_sender_spoof(game):
    account(game, "room_owner")
    owner_room = room(game)
    b = account(game, "recipient")
    account(game, "room_owner")
    path = f"/api/lounges/{owner_room}/invitations"
    assert game.post(path, json={"recipient_id": b["id"], "sender_id": b["id"]}).status_code == 422
    iid = game.post(path, json={"recipient_id": b["id"]}).json()["id"]
    account(game, "recipient")
    assert (
        game.post(f"/api/lounge-invitations/{iid}/response", json={"accept": False}).status_code
        == 200
    )
    assert game.get(f"/api/lounges/{owner_room}/members").status_code == 404
    account(game, "room_owner")
    assert game.post(path, json={"recipient_id": b["id"]}).status_code == 201
    assert game.get("/api/lounge-invitations").json()[0]["status"] == "pending"


def test_ordered_b_rules_decrease_without_future_debt(game):
    account(game, "stats_game")
    for _ in range(5):
        assert sample(game, "운동").status_code == 201
    assert values(game)["운동"]["count"] == 5 and values(game)["운동"]["level"] == 2
    rid = str(uuid4())
    response = sample(game, "술", rid)
    record = game.get("/api/records/" + response.json()["id"]).json()
    assert record["source"] == "demo" and record["stack_changes"] == {"술": 1, "운동": -1}
    assert values(game)["운동"]["count"] == 4 and values(game)["운동"]["level"] == 1
    assert sample(game, "술", rid).status_code == 200
    assert values(game)["운동"]["count"] == 4
    for _ in range(6):
        sample(game, "술")
    assert values(game)["운동"]["count"] == 0
    sample(game, "운동")
    assert values(game)["운동"]["count"] == 1


def test_titles_are_earned_selected_and_scoped(game):
    account(game, "title_a")
    assert all(not title["earned"] for title in game.get("/api/titles").json())
    assert game.put("/api/titles/selected", json={"title_id": "campus_explorer"}).status_code == 403
    sample(game, "공부")
    titles = game.get("/api/titles").json()
    assert next(title for title in titles if title["id"] == "first_step")["selected"]
    sample(game, "운동")
    sample(game, "연애")
    assert next(
        title for title in game.get("/api/titles").json() if title["id"] == "campus_explorer"
    )["earned"]
    assert game.put("/api/titles/selected", json={"title_id": "campus_explorer"}).status_code == 200
    assert game.get("/api/me").json()["title"] == "캠퍼스 탐험가"
    game.put("/api/titles/selected", json={"title_id": None})
    sample(game, "공부")
    assert game.get("/api/me").json()["title"] is None
    account(game, "title_b")
    assert all(not title["earned"] for title in game.get("/api/titles").json())


def test_five_distinct_study_days_title(game):
    user = account(game, "study_days")
    for _ in range(5):
        sample(game, "공부")
    with Session(get_engine()) as db, db.begin():
        records = db.scalars(
            select(ActivityRecord).where(ActivityRecord.user_id == user["id"])
        ).all()
        for index, record in enumerate(records):
            record.created_at = datetime(2026, 11, 6, 3, tzinfo=UTC) - timedelta(days=index)
        award_titles(db, user["id"])
    earned = next(
        title for title in game.get("/api/titles").json() if title["id"] == "steady_challenger"
    )
    assert earned["earned"]
    with Session(get_engine()) as db:
        assert db.get(Title, (user["id"], "steady_challenger")) is not None


def test_demo_mode_is_explicit_and_disabled_outside_development(game, monkeypatch):
    account(game, "sample_mode")
    record = sample(game, "공부").json()
    assert record["source"] == "demo"
    saved = game.get("/api/records/" + record["id"]).json()
    assert "AI 분석 결과가 아닙니다" in saved["analysis"]["summary"]
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    assert game.get("/api/runtime").json()["demo_available"] is False
    assert sample(game, "공부").status_code == 404


def test_websocket_rejects_nonmembers_and_bad_origin(game):
    account(game, "ws_owner")
    rid = room(game)
    with pytest.raises(WebSocketDisconnect):
        with game.websocket_connect(
            f"/api/lounges/{rid}/live", headers={"origin": "https://other.example"}
        ):
            pass
    account(game, "ws_other")
    with pytest.raises(WebSocketDisconnect):
        with game.websocket_connect(f"/api/lounges/{rid}/live"):
            pass
    game.cookies.clear()
    with pytest.raises(WebSocketDisconnect):
        with game.websocket_connect(f"/api/lounges/{rid}/live"):
            pass


def test_two_authenticated_clients_share_server_positions(game):
    a = account(game, "socket_a")
    rid = room(game)
    b = account(game, "socket_b")
    account(game, "socket_a")
    iid = game.post(f"/api/lounges/{rid}/invitations", json={"recipient_id": b["id"]}).json()["id"]
    account(game, "socket_b")
    game.post(f"/api/lounge-invitations/{iid}/response", json={"accept": True})
    account(game, "socket_a")
    with game.websocket_connect(f"/api/lounges/{rid}/live") as first:
        initial = first.receive_json()
        assert initial["type"] == "snapshot"
        account(game, "socket_b")
        with game.websocket_connect(f"/api/lounges/{rid}/live") as second:
            left, right = first.receive_json(), second.receive_json()
            for _ in range(30):
                if left["tick"] < right["tick"]:
                    left = first.receive_json()
                elif right["tick"] < left["tick"]:
                    right = second.receive_json()
                else:
                    break
            assert left == right
            assert {person["id"] for person in left["people"]} == {a["id"], b["id"]}


def test_b_state_is_exposed_with_saved_stats(game):
    account(game, "state_view")
    assert game.get("/api/me").json()["state"]["expression"] == "neutral"
    sample(game, "공부")
    assert game.get("/characters/me").json()["state"]["expression"] == "focused"
    assert game.get("/api/progress").json()["state"]["dominant_activity"] == "공부"
