"""Small live classification smoke test against the local app."""

import os
import tempfile

from app.main import app
from fastapi.testclient import TestClient

cases = [
    ("친구들과 술집에서 맥주를 마셨다.", "술"),
    ("도서관에서 내일 시험을 준비하며 공부했다.", "공부"),
    ("연인과 기념일 데이트를 했다.", "연애"),
    ("헬스장에서 근력 운동을 하고 달렸다.", "운동"),
    ("오늘 하늘이 파랗다.", None),
    ("연인과 데이트하며 커플 반지를 맞췄다.", "연애"),
    ("술은 마시지 않았고 도서관에서 시험 공부만 했다.", "공부"),
]

with tempfile.TemporaryDirectory() as directory, TestClient(app) as client:
    os.environ["PROGRESS_DB"] = os.path.join(directory, "live-test.sqlite3")
    for text, expected in cases:
        response = client.post("/api/keywords", data={"text": text})
        response.raise_for_status()
        data = response.json()
        print(
            text,
            "=>",
            data["category"],
            data["category_keywords"],
            "awarded=",
            data["awarded"],
            flush=True,
        )
        assert data["category"] == expected
        if text == "오늘 하늘이 파랗다.":
            assert data["needs_review"] is True
