import asyncio
import math
import random
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.accounts.service import find_session_user
from app.core.config import get_settings
from app.core.db import get_engine
from app.game.models import Member
from app.game.service import members

router = APIRouter()


def authenticate(token, room_id):
    if not token:
        return None
    with Session(get_engine()) as db:
        user = find_session_user(db, token)
        if user is None or db.get(Member, (room_id, user.id)) is None:
            return None
        return user.id


def room_people(room_id):
    with Session(get_engine()) as db:
        member = db.scalar(select(Member).where(Member.room_id == room_id))
        return members(db, member.user_id, room_id) if member else []


class LiveLounges:
    def __init__(self):
        self.peers = {}
        self.tasks = {}
        self.positions = {}

    async def join(self, room_id, socket, user_id, token):
        self.peers.setdefault(room_id, {})[socket] = (user_id, token)
        if room_id not in self.tasks:
            self.tasks[room_id] = asyncio.create_task(self.run(room_id))

    def leave(self, room_id, socket):
        self.peers.get(room_id, {}).pop(socket, None)

    async def run(self, room_id):
        previous = time.monotonic()
        users = []
        refreshed = 0
        tick = 0
        try:
            while self.peers.get(room_id):
                now = time.monotonic()
                elapsed = min(now - previous, 0.15)
                previous = now
                peers = self.peers.get(room_id, {})
                if now - refreshed >= 1:
                    users = await run_in_threadpool(room_people, room_id)
                    for socket, (user_id, token) in list(peers.items()):
                        if await run_in_threadpool(authenticate, token, room_id) != user_id:
                            self.leave(room_id, socket)
                            await socket.close(code=1008)
                    refreshed = now
                actors = []
                positions = self.positions.setdefault(room_id, {})
                online = {item[0] for item in peers.values()}
                for user in users:
                    position = positions.setdefault(
                        user["id"],
                        {
                            "x": random.uniform(100, 800),
                            "y": random.uniform(180, 400),
                            "tx": random.uniform(100, 800),
                            "ty": random.uniform(180, 400),
                            "wait": 0,
                        },
                    )
                    dx, dy = position["tx"] - position["x"], position["ty"] - position["y"]
                    distance = math.hypot(dx, dy)
                    moving = position["wait"] <= 0 and distance > 3
                    if position["wait"] > 0:
                        position["wait"] -= elapsed
                    elif distance <= 3:
                        position.update(
                            tx=random.uniform(80, 820),
                            ty=random.uniform(170, 420),
                            wait=random.uniform(0.7, 2.0),
                        )
                    else:
                        position["x"] += dx / distance * min(distance, 52 * elapsed)
                        position["y"] += dy / distance * min(distance, 52 * elapsed)
                    actors.append(
                        {
                            **user,
                            "x": position["x"],
                            "y": position["y"],
                            "moving": moving,
                            "direction": -1 if dx < 0 else 1,
                            "online": user["id"] in online,
                        }
                    )
                tick += 1
                frame = {"type": "snapshot", "room_id": room_id, "tick": tick, "people": actors}
                for socket in list(peers):
                    try:
                        await socket.send_json(frame)
                    except Exception:
                        self.leave(room_id, socket)
                await asyncio.sleep(0.1)
        finally:
            self.tasks.pop(room_id, None)

    async def close(self):
        for task in list(self.tasks.values()):
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()
        self.peers.clear()
        self.positions.clear()


live = LiveLounges()


@router.websocket("/api/lounges/{room_id}/live")
async def lounge_socket(socket: WebSocket, room_id: str):
    origin = socket.headers.get("origin")
    expected = f"{'https' if socket.url.scheme == 'wss' else 'http'}://{socket.url.netloc}"
    if origin is not None and origin.rstrip("/") != expected:
        await socket.close(code=1008)
        return
    token = socket.cookies.get(get_settings().session_cookie_name)
    user_id = await run_in_threadpool(authenticate, token, room_id)
    if user_id is None:
        await socket.close(code=1008)
        return
    await socket.accept()
    await live.join(room_id, socket, user_id, token)
    try:
        while True:
            message = await socket.receive_text()
            if len(message) > 1024:
                await socket.close(code=1009)
                break
    except WebSocketDisconnect:
        pass
    finally:
        live.leave(room_id, socket)
