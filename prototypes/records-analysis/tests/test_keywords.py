import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from app import analysis, routes
from app.main import app
from fastapi.testclient import TestClient
from google.genai import types
from google.genai.errors import APIError
from PIL import Image

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_progress(monkeypatch, tmp_path):
    monkeypatch.setenv("PROGRESS_DB", str(tmp_path / "test.sqlite3"))


def png():
    data = io.BytesIO()
    Image.new("RGB", (20, 20), "blue").save(data, format="PNG")
    return data.getvalue()


@pytest.mark.parametrize("mode", ["text", "image", "both"])
def test_three_input_modes(monkeypatch, mode):
    service = AsyncMock(
        return_value=analysis.KeywordResult(
            keywords=["학업"],
            summary="공부 기록입니다.",
            category="공부",
            category_keywords=["학업"],
            category_reason="학습 활동",
            needs_review=False,
        )
    )
    monkeypatch.setattr(routes, "extract_keywords", service)
    data = {"text": "도서관에서 공부했다"} if mode != "image" else {}
    files = {"image": ("sample.png", png(), "image/png")} if mode != "text" else None
    response = client.post("/api/keywords", data=data, files=files)
    assert response.status_code == 200
    assert response.json()["keywords"] == ["학업"]
    args = service.call_args.args
    assert bool(args[0]) == (mode != "image")
    assert bool(args[1]) == (mode != "text")


@pytest.mark.parametrize(
    "data,files,code",
    [
        ({"text": "  "}, None, 400),
        ({"text": "a" * 5001}, None, 400),
        ({}, {"image": ("fake.png", b"not an image", "image/png")}, 400),
        ({}, {"image": ("empty.png", b"", "image/png")}, 400),
        ({}, {"image": ("big.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")}, 413),
    ],
)
def test_invalid_inputs_never_call_ai(monkeypatch, data, files, code):
    service = AsyncMock()
    monkeypatch.setattr(routes, "extract_keywords", service)
    assert client.post("/api/keywords", data=data, files=files).status_code == code
    service.assert_not_called()


def test_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post("/api/keywords", data={"text": "공부"})
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


@pytest.mark.parametrize(
    "error,code",
    [
        (httpx.ReadTimeout("secret"), 504),
        (APIError(403, {"error": {"message": "secret"}}), 503),
        (APIError(429, {"error": {"message": "secret"}}), 429),
        (APIError(404, {"error": {"message": "secret"}}), 503),
        (APIError(500, {"error": {"message": "secret"}}), 502),
    ],
)
def test_safe_errors(monkeypatch, error, code):
    monkeypatch.setattr(routes, "extract_keywords", AsyncMock(side_effect=error))
    response = client.post("/api/keywords", data={"text": "공부"})
    assert response.status_code == code
    assert "secret" not in response.text


def test_sdk_payload_and_result(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    generate = AsyncMock(
        return_value=SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)],
            text='{"keywords":["책"],"summary":"책입니다.","category":"공부","category_keywords":["책"],"category_reason":"독서","needs_review":false}',
        )
    )
    sdk = AsyncMock()
    sdk.__aenter__.return_value = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    monkeypatch.setattr(analysis.genai, "Client", lambda **kwargs: SimpleNamespace(aio=sdk))
    result = asyncio.run(analysis.extract_keywords("공부", png(), "image/png"))
    assert result.keywords == ["책"]
    generate.assert_awaited_once()
    payload = generate.call_args.kwargs
    parts = payload["contents"].parts
    assert parts[0].text == "공부"
    assert parts[1].inline_data.mime_type == "image/png"
    assert parts[1].inline_data.data == png()


def test_incomplete_result(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    sdk = AsyncMock()
    sdk.__aenter__.return_value = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=AsyncMock(return_value=SimpleNamespace(candidates=[], text=None))
        )
    )
    monkeypatch.setattr(analysis.genai, "Client", lambda **kwargs: SimpleNamespace(aio=sdk))
    with pytest.raises(analysis.AnalysisUnavailable):
        asyncio.run(analysis.extract_keywords("공부", None, None))


def test_page_and_static():
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/lounge").status_code == 200
    assert client.get("/static/lounge-view.mjs").status_code == 200
    assert "javascript" in client.get("/static/lounge-engine.mjs").headers["content-type"]
    assert client.get("/.env").status_code == 404


@pytest.mark.parametrize(
    "category,effect_id",
    [
        ("술", "drink_mug"),
        ("공부", "study_book"),
        ("연애", "love_hearts"),
        ("운동", "exercise_dumbbell"),
    ],
)
def test_category_effect_mapping(monkeypatch, category, effect_id):
    service = AsyncMock(
        return_value=analysis.KeywordResult(
            keywords=[category],
            summary="활동 기록",
            category=category,
            category_keywords=[category],
            category_reason="명시적 활동",
            needs_review=False,
        )
    )
    monkeypatch.setattr(routes, "extract_keywords", service)
    response = client.post("/api/keywords", data={"text": "활동 기록"})
    assert response.status_code == 200
    assert response.json()["category"] == category
    assert response.json()["character_effect"]["id"] == effect_id
    service.assert_awaited_once()


def test_invalid_category_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        analysis.KeywordResult(
            keywords=[], summary="", category="여행", category_reason="", needs_review=True
        )
