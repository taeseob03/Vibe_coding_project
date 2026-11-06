import pytest


def test_profile_and_pixel_appearance_survive_relogin(client):
    client.post("/auth/login", json={"username": "pixel_user"})
    look = {
        "grade": 3,
        "major": "embedded",
        "appearance": {"base": "male", "hair_length": "short", "hair_color": "blue"},
    }
    draft = client.put(
        "/profile/me/draft", json={"nickname": "픽셀친구", "color": "blue", "step": "color", **look}
    )
    assert draft.status_code == 200
    assert draft.json()["appearance"] == look["appearance"]
    completed = client.post("/profile/me/complete", json={"nickname": "픽셀친구", "color": "blue"})
    assert completed.status_code == 200
    assert completed.json()["character"]["appearance"] == look["appearance"]
    client.post("/auth/logout")
    client.post("/auth/login", json={"username": "pixel_user"})
    profile = client.get("/profile/me").json()
    assert profile["grade"] == 3 and profile["major"] == "embedded"
    assert client.get("/api/me").json()["appearance"] == look["appearance"]


def test_completed_appearance_can_change_without_touching_stats(client):
    client.post("/auth/login", json={"username": "dress_user"})
    client.post("/profile/me/complete", json={"nickname": "옷친구", "color": "pink"})
    before = client.get("/characters/me").json()
    body = {
        "grade": 2,
        "major": "ict",
        "appearance": {"base": "female", "hair_length": "medium", "hair_color": "silver"},
    }
    assert client.put("/profile/me/appearance", json=body).status_code == 200
    after = client.get("/characters/me").json()
    assert before["id"] == after["id"] and before["stats"] == after["stats"]
    assert after["appearance"] == body["appearance"]


@pytest.mark.parametrize(
    "body",
    [
        {"grade": 5},
        {"major": "unknown"},
        {"appearance": {"hair_color": "anything"}},
        {"appearance": {"base": "unknown"}},
        {"grade": True},
    ],
)
def test_invalid_appearance_rejected(client, body):
    client.post("/auth/login", json={"username": "look_valid"})
    assert client.put("/profile/me/draft", json={"nickname": "친구", **body}).status_code == 422


def test_other_account_appearance_is_independent(client):
    client.post("/auth/login", json={"username": "look_first"})
    client.post(
        "/profile/me/complete",
        json={
            "nickname": "처음친구",
            "color": "green",
            "appearance": {"base": "male", "hair_length": "short", "hair_color": "red"},
        },
    )
    client.post("/auth/login", json={"username": "look_second"})
    client.post("/profile/me/complete", json={"nickname": "두번째", "color": "blue"})
    assert client.get("/characters/me").json()["appearance"]["hair_color"] == "black"
    client.post("/auth/login", json={"username": "look_first"})
    assert client.get("/characters/me").json()["appearance"]["hair_color"] == "red"
