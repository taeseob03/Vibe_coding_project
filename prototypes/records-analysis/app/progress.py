"""Single local demo profile. Replace this store with A's authenticated user store."""
from contextlib import contextmanager
import os
import sqlite3
from pathlib import Path

from .analysis import KeywordResult
from .effects import EFFECTS


@contextmanager
def connection():
    path = Path(os.getenv("PROGRESS_DB", str(Path(__file__).resolve().parent.parent / "data" / "progress.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    try:
        with con:
            con.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL, category TEXT)")
            yield con
    finally:
        con.close()


def lookup(record_id, fingerprint):
    with connection() as con:
        row = con.execute("SELECT fingerprint, result FROM records WHERE id=?", (record_id,)).fetchone()
    if row:
        if row[0] != fingerprint:
            raise ValueError("같은 기록 ID로 다른 내용을 제출할 수 없습니다.")
        return KeywordResult.model_validate_json(row[1])
    return None


def save(record_id, fingerprint, result):
    category = result.category if not result.needs_review else None
    with connection() as con:
        cursor = con.execute("INSERT OR IGNORE INTO records VALUES (?, ?, ?, ?)", (record_id, fingerprint, result.model_dump_json(), category))
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
    effects = []
    for category, effect in EFFECTS.items():
        count = counts.get(category, 0)
        level = 0 if count == 0 else 1 if count < 5 else 2 if count < 10 else 3
        effects.append({**effect.model_dump(), "category": category, "count": count, "level": level,
                        "color": ["#d1d5db", "#f9a8d4", "#ec4899", "#be123c"][level]})
    return effects, changes


def state():
    return snapshot()[0]
