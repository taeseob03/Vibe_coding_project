from app.characters.models import Character
from app.core.db import get_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_web_preview import login

CUSTOMIZATION = {
    "grade": 3,
    "major": "computer",
    "appearance": {"base": "male", "hair_length": "short", "hair_color": "blue"},
}


def test_draft_finish_and_relogin_keep_pixel_character(web_client):
    web_client.post("/auth/login", json={"username": "pixel_student"})
    draft = {"nickname": "픽셀친구", "color": "blue", "step": "color", **CUSTOMIZATION}
    assert web_client.put("/profile/me/draft", json=draft).status_code == 200
    web_client.post("/auth/logout")
    web_client.post("/auth/login", json={"username": "pixel_student"})
    profile = web_client.get("/profile/me").json()
    assert all(profile[key] == value for key, value in CUSTOMIZATION.items())
    finished = web_client.post(
        "/profile/me/complete", json={key: value for key, value in draft.items() if key != "step"}
    )
    assert finished.status_code == 200
    for path in ("/profile/me", "/characters/me", "/api/me"):
        body = web_client.get(path).json()
        assert all(body[key] == value for key, value in CUSTOMIZATION.items())
    # A replay cannot silently replace the saved appearance.
    web_client.post("/profile/me/complete", json={"nickname": "새이름", "color": "pink"})
    assert web_client.get("/api/me").json()["appearance"] == CUSTOMIZATION["appearance"]


def test_existing_account_can_customize_without_losing_activity_or_character(web_client):
    login(web_client)
    original = web_client.get("/characters/me").json()
    with Session(get_engine()) as db:
        character = db.scalar(select(Character).where(Character.id == original["id"]))
        character.stats = [
            {
                "category": "공부",
                "count": 7,
                "level": 2,
                "id": "study_book",
                "name": "책 소품",
                "icon": "📚",
                "slot": "hand",
                "color": "#ec4899",
            }
        ]
        db.commit()
    assert web_client.put("/profile/me/appearance", json=CUSTOMIZATION).status_code == 200
    saved = web_client.get("/characters/me").json()
    assert saved["id"] == original["id"] and saved["color"] == original["color"]
    assert saved["stats"][0]["count"] == 7
    assert saved["major"] == "computer"
    for field, bad in [("grade", 5), ("major", "unknown"), ("appearance", {"base": "unknown"})]:
        assert (
            web_client.put("/profile/me/appearance", json={**CUSTOMIZATION, field: bad}).status_code
            == 422
        )
    web_client.post("/auth/logout")
    assert web_client.put("/profile/me/appearance", json=CUSTOMIZATION).status_code == 401
    login(web_client, "another_pixel", "다른픽셀")
    assert web_client.get("/api/me").json()["major"] is None
