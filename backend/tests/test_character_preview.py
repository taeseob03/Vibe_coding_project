import io

import pytest
from app.character_preview import gemini
from app.core.config import get_settings
from PIL import Image

URL = "/character-preview/analyze"


def fake_result(category, keywords, evidence):
    return gemini.KeywordResult(
        keywords=keywords,
        summary="요약",
        category=category,
        category_keywords=evidence,
        category_reason="이유",
        needs_review=category is None,
    )


@pytest.fixture
def fake_gemini(monkeypatch):
    calls = []

    async def fake(text, image, mime):
        calls.append((text, image, mime))
        if "술" in text:
            return fake_result("술", ["술자리", "동기"], ["술자리"])
        if "공부" in text or image:
            return fake_result("공부", ["도서관", "공부"], ["공부"])
        return fake_result(None, ["집"], [])

    monkeypatch.setattr(gemini, "extract_keywords", fake)
    return calls


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_text_is_classified_into_category_key(client, fake_gemini):
    body = client.post(URL, data={"text": "동기들과 술자리"}).json()
    assert body["category"] == "drink"
    assert body["category_label"] == "술"
    assert body["needs_review"] is False


def test_unrelated_post_has_no_category(client, fake_gemini):
    body = client.post(URL, data={"text": "집에서 쉬었다"}).json()
    assert body["category"] is None
    assert body["needs_review"] is True


def test_photo_only_post_is_sent_with_mime(client, fake_gemini):
    files = {"image": ("photo.png", png_bytes(), "image/png")}
    response = client.post(URL, data={"text": ""}, files=files)
    assert response.status_code == 200
    assert response.json()["category"] == "study"
    assert fake_gemini[0][2] == "image/png"


def test_empty_and_invalid_posts_are_rejected(client, fake_gemini):
    assert client.post(URL, data={"text": "  "}).json()["error"]["code"] == "EMPTY_POST"
    files = {"image": ("fake.png", b"not an image", "image/png")}
    response = client.post(URL, data={"text": "공부"}, files=files)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMAGE_INVALID"
    assert fake_gemini == []


def test_missing_api_key_is_reported(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    response = client.post(URL, data={"text": "도서관에서 공부"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GEMINI_NOT_CONFIGURED"
