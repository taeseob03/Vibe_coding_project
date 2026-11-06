"""Run the game in an isolated DB and verify two browsers. --live-ai calls Gemini once."""

import argparse
import io
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw
from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-ai", action="store_true")
    parser.add_argument("--screenshots", type=Path, default=Path("/tmp/campus-game-preview"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.screenshots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="campus-browser-") as scratch:
        env = os.environ.copy()
        env.update(
            DATABASE_URL=f"sqlite:///{scratch}/game.db",
            DEV_AUTH_ENABLED="false",
            APP_ENV="development",
            PYTHONPATH="",
        )
        if not args.live_ai:
            env["GEMINI_API_KEY"] = ""
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env=env, check=True
        )
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        with open(Path(scratch) / "server.log", "w") as log:
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=root,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        if httpx.get(base + "/health", timeout=1).status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    if server.poll() is not None:
                        raise RuntimeError("Game server stopped before startup")
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Game server startup timed out")
                verify_browser(base, args, scratch)
            finally:
                server.terminate()
                server.wait(timeout=10)


def register(page, base, username, nickname):
    page.goto(base + "/?mode=demo")
    page.locator("#username").fill(username)
    page.locator("#login-form button").click()
    page.locator("#nickname").wait_for(state="visible")
    page.locator("#nickname").fill(nickname)
    page.locator("#setup-next").click()
    page.locator('input[name="color"][value="green"]').check()
    page.locator("#setup-complete").click()
    game = page.frame_locator("#game-frame")
    game.locator("#main-character canvas").wait_for(state="visible", timeout=30000)
    return game


def post(game, category, text="체험 활동"):
    game.locator("#open-post").click()
    game.locator("#post-text").fill(text)
    game.locator("#sample-category").select_option(label=category)
    game.locator("#submit-post").click()
    game.locator("#post-result").wait_for(state="visible", timeout=15000)
    game.locator("#show-character").click()


def verify_browser(base, args, scratch):
    token = uuid4().hex[:6]
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        first = browser.new_context(viewport={"width": 1280, "height": 1000})
        second = browser.new_context(viewport={"width": 1280, "height": 1000})
        page, friend = first.new_page(), second.new_page()
        for item in [page, friend]:
            item.on("pageerror", lambda error: errors.append(str(error)))
        a = register(page, base, "qa_a_" + token, "초록" + token)
        b = register(friend, base, "qa_b_" + token, "친구" + token)
        a.locator("#open-look").click()
        a.locator("#look-grade").select_option("3")
        a.locator("#look-major").select_option("embedded")
        a.locator("#look-base").select_option("male")
        a.locator("#look-length").select_option("short")
        a.locator("#look-color").select_option("blue")
        a.locator('#look-form button[type="submit"]').click()
        expect(a.locator("#look-dialog")).not_to_be_visible()
        profile = page.request.get(base + "/profile/me").json()
        assert (
            profile["grade"] == 3
            and profile["major"] == "embedded"
            and profile["appearance"]["hair_color"] == "blue"
        )
        post(a, "운동")
        assert page.request.get(base + "/api/me").json()["state"]["expression"] == "energetic"
        post(a, "술")
        assert page.request.get(base + "/api/me").json()["state"]["expression"] == "relaxed"
        current = page.request.get(base + "/api/progress").json()["progress"]
        assert next(item for item in current if item["category"] == "운동")["count"] == 0
        expect(a.locator('#title-select option[value="first_step"]')).to_be_enabled()
        if args.live_ai:
            page.goto(base + "/?mode=gemini")
            a = page.frame_locator("#game-frame")
            a.locator("#main-character canvas").wait_for(state="visible")
            a.locator("#open-post").click()
            a.locator("#post-text").fill("도서관에서 책을 펴고 시험 공부를 했어요.")
            photo = Image.new("RGB", (320, 240), "#eee8dc")
            draw = ImageDraw.Draw(photo)
            draw.rectangle((35, 60, 150, 190), fill="#6c9ab5")
            draw.rectangle((155, 60, 270, 190), fill="#fffdf5")
            for y in range(80, 180, 18):
                draw.line((175, y, 250, y), fill="#6a7c8f", width=2)
            image = io.BytesIO()
            photo.save(image, format="PNG")
            a.locator("#post-image").set_input_files(
                {"name": "study.png", "mimeType": "image/png", "buffer": image.getvalue()}
            )
            a.locator("#submit-post").click()
            a.locator("#post-result").wait_for(state="visible", timeout=90000)
            expect(a.locator("#result-category")).to_contain_text("공부")
            a.locator("#show-character").click()
            records = page.request.get(base + "/api/records").json()
            assert records[0]["source"] == "gemini" and records[0]["stat_status"] == "applied"
            print("Real Gemini photo → keywords → saved user stats passed")
        else:
            post(a, "공부")
        expect(a.locator('#title-select option[value="campus_explorer"]')).to_be_enabled()
        a.locator("#title-select").select_option("campus_explorer")
        a.locator("#lounge-tab").click()
        a.locator("#open-friends").click()
        a.locator("#friend-query").fill("친구" + token)
        a.locator("#friend-search button").click()
        a.locator("#search-results .person-row").filter(has_text="친구" + token).get_by_role(
            "button", name="초대", exact=True
        ).click()
        expect(a.locator("#friend-status")).to_contain_text("보냈어요")
        a.locator("#close-friends").click()
        b.locator("#lounge-tab").click()
        b.locator("#open-inbox").click()
        b.locator("#received-invitations").get_by_role("button", name="수락", exact=True).click()
        expect(a.locator("#room-members .member-chip")).to_have_count(2, timeout=15000)
        expect(b.locator("#room-members .member-chip")).to_have_count(2, timeout=15000)
        expect(a.locator("#live-status")).to_contain_text("접속 2명", timeout=10000)
        expect(b.locator("#live-status")).to_contain_text("접속 2명", timeout=10000)
        page.wait_for_timeout(400)
        assert a.locator("#screen").evaluate("element=>element.scrollLeft") == 0
        page.screenshot(path=str(args.screenshots / "lounge.png"), full_page=True)
        a.locator("#home-tab").click()
        page.wait_for_timeout(400)
        page.screenshot(path=str(args.screenshots / "desktop.png"), full_page=True)
        page.reload()
        a = page.frame_locator("#game-frame")
        a.locator("#main-character canvas").wait_for(state="visible")
        expect(a.locator("#title-select")).to_have_value("campus_explorer")
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        phone = mobile.new_page()
        phone.goto(base)
        phone.locator("#guest-demo").click()
        m = phone.frame_locator("#game-frame")
        m.locator("#main-character canvas").wait_for(state="visible")
        phone.wait_for_timeout(600)
        phone.screenshot(path=str(args.screenshots / "mobile.png"), full_page=True)
        assert m.locator("body").evaluate("element => element.scrollWidth <= innerWidth + 1")
        assert not errors, errors
        print(
            "Browser QA passed: login/setup, Phaser, stack changes, titles, "
            "invitation/acceptance, two live clients, reload, mobile"
        )
        print("Screenshots:", args.screenshots)
        browser.close()


if __name__ == "__main__":
    main()
