"""Single local demo profile. Replace this store with A's authenticated user store."""

import os
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .analysis import KeywordResult
from .effects import EFFECTS

_database_override = ContextVar("preview_progress_database", default=None)


@contextmanager
def use_database(path):
    """Bind a trusted server-selected database to one request, including worker threads."""
    token = _database_override.set(path)
    try:
        yield
    finally:
        _database_override.reset(token)


@contextmanager
def connection():
    path = Path(
        _database_override.get()
        or os.getenv(
            "PROGRESS_DB", str(Path(__file__).resolve().parent.parent / "data" / "progress.sqlite3")
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    try:
        with con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS records ("
                "id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, "
                "result TEXT NOT NULL, category TEXT)"
            )
            yield con
    finally:
        con.close()


def lookup(record_id, fingerprint):
    with connection() as con:
        row = con.execute(
            "SELECT fingerprint, result FROM records WHERE id=?", (record_id,)
        ).fetchone()
    if row:
        if row[0] != fingerprint:
            raise ValueError("같은 기록 ID로 다른 내용을 제출할 수 없습니다.")
        return KeywordResult.model_validate_json(row[1])
    return None


def save(record_id, fingerprint, result):
    category = result.category if not result.needs_review else None
    with connection() as con:
        cursor = con.execute(
            "INSERT OR IGNORE INTO records VALUES (?, ?, ?, ?)",
            (record_id, fingerprint, result.model_dump_json(), category),
        )
        inserted = cursor.rowcount == 1
    # A concurrent request may already have committed this record.
    return lookup(record_id, fingerprint), inserted and category is not None


def snapshot(record_id=None):
    """Replay committed records in insertion order; drinking never creates exercise debt."""
    with connection() as con:
        records = con.execute(
            "SELECT id, category FROM records WHERE category IS NOT NULL ORDER BY rowid"
        ).fetchall()
    counts = dict.fromkeys(EFFECTS, 0)
    changes = {}
    for saved_id, category in records:
        if category not in counts:
            continue
        delta = {category: 1}
        counts[category] += 1
        if category == "술" and counts["운동"] > 0:
            counts["운동"] -= 1
            delta["운동"] = -1
        if saved_id == record_id:
            changes = delta
    return calculate_progress(counts), changes


def eligible_category(result):
    return result.category if not result.needs_review else None


def advance_counts(counts, category):
    counts = {key: counts.get(key, 0) for key in EFFECTS}
    if category in counts:
        counts[category] += 1
        if category == "술":
            counts["운동"] = max(0, counts["운동"] - 1)
    return counts


def calculate_progress(counts):
    effects = []
    for category, effect in EFFECTS.items():
        count = counts.get(category, 0)
        level = 0 if count == 0 else 1 if count < 5 else 2 if count < 10 else 3
        effects.append(
            {
                **effect.model_dump(),
                "category": category,
                "count": count,
                "level": level,
                "color": ["#d1d5db", "#f9a8d4", "#ec4899", "#be123c"][level],
            }
        )
    return effects


def state():
    return snapshot()[0]
