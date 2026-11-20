"""Gamification: XP, analyst levels, achievements and activity streaks.

State lives in the project SQLite database (backend/data/*.db) next to
sessions/messages, so progress survives restarts without any extra service.
One row per operator id (default: "operator").

Design notes
------------
* Pure stdlib. No network calls, no external dependencies.
* Awards are idempotent per request only; repeated identical events DO
  accumulate (analysing two samples should give XP twice). Callers that
  need de-duplication pass a ``ref`` (achievement ids are unique anyway).
* Achievements unlock automatically from counters, so the UI never has to
  know the thresholds.

Public API
----------
    state(user_id="operator")            -> dict (level, xp, progress, ...)
    award(event, user_id="operator", amount=None, meta=None) -> dict
    catalog()                            -> {"levels": [...], "events": {...}, "achievements": [...]}
    reset(user_id="operator")            -> dict (fresh state)
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import storage

DEFAULT_USER = "operator"

# (level, title, xp required)
LEVELS: List[Tuple[int, str, int]] = [
    (1, "Trainee", 0),
    (2, "Analyst I", 500),
    (3, "Analyst II", 1500),
    (4, "Senior", 3500),
    (5, "Expert", 7500),
    (6, "Elite", 15000),
    (7, "Legendary", 30000),
]

# event -> (xp, counter metric)
EVENTS: Dict[str, Tuple[int, str]] = {
    "analysis_complete": (50, "analyses"),
    "ioc_extracted": (5, "iocs"),
    "yara_generated": (30, "yara"),
    "sigma_generated": (30, "sigma"),
    "hunt_completed": (100, "hunts"),
    "report_generated": (75, "reports"),
    "attribution_correct": (200, "attributions"),
    "daily_challenge": (150, "challenges"),
    "sandbox_run": (15, "sandbox_runs"),
    "intel_lookup": (5, "intel_lookups"),
    "detection_deployed": (40, "detections"),
    "re_session": (20, "re_sessions"),
    "packed_identified": (25, "packed_samples"),
    "message_sent": (2, "messages"),
    "streak_7_days": (500, "streak_bonus_7"),
    "streak_30_days": (2000, "streak_bonus_30"),
}

# id, name, description, xp, counter metric, threshold
ACHIEVEMENTS: List[Tuple[str, str, str, int, str, int]] = [
    ("first_blood", "First Blood", "Complete your first analysis", 100, "analyses", 1),
    ("century", "Century", "Analyse 100 samples", 500, "analyses", 100),
    ("hunter", "Hunter", "Complete your first threat hunt", 150, "hunts", 1),
    ("persistent", "Persistent", "Reach a 30-day streak", 1000, "streak", 30),
    ("yara_master", "YARA Master", "Generate 50 YARA rules", 300, "yara", 50),
    ("ioc_hoarder", "IOC Hoarder", "Extract 1000 indicators", 500, "iocs", 1000),
    ("wordsmith", "Wordsmith", "Generate your first report", 100, "reports", 1),
    ("prolific", "Prolific", "Generate 50 reports", 600, "reports", 50),
    ("binary_whisperer", "Binary Whisperer", "Open your first RE session", 150, "re_sessions", 1),
    ("unpacker", "Unpacker", "Identify packed malware 10 times", 200, "packed_samples", 10),
    ("profiler", "Profiler", "Attribute 10 campaigns", 400, "attributions", 10),
    ("streak_7", "Week Warrior", "Keep a 7-day streak", 500, "streak", 7),
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS gamification(
    user_id      TEXT PRIMARY KEY,
    xp           INTEGER NOT NULL DEFAULT 0,
    level        INTEGER NOT NULL DEFAULT 1,
    streak       INTEGER NOT NULL DEFAULT 0,
    last_active  TEXT,
    counters     TEXT NOT NULL DEFAULT '{}',
    achievements TEXT NOT NULL DEFAULT '{}',
    recent       TEXT NOT NULL DEFAULT '[]',
    updated      REAL
);
"""


def _cols() -> set:
    try:
        rows = storage._conn().execute("PRAGMA table_info(gamification)").fetchall()
        return {str(r["name"]) for r in rows}
    except Exception:
        return set()


def _ensure() -> None:
    c = storage._conn()
    c.executescript(_SCHEMA)
    if not _cols():
        c.executescript(_SCHEMA)
    c.commit()


def _today() -> str:
    return date.today().isoformat()


def _level_for(xp: int) -> Tuple[int, str, int, int]:
    """Return (level, title, current_floor_xp, next_requirement or 0)."""
    level, title, floor = LEVELS[0]
    nxt = 0
    for lv, name, req in LEVELS:
        if xp >= req:
            level, title, floor = lv, name, req
        else:
            nxt = req
            break
    return level, title, floor, nxt


def _default_row() -> Dict[str, Any]:
    return {"user_id": DEFAULT_USER, "xp": 0, "level": 1, "streak": 0,
            "last_active": None, "counters": {}, "achievements": {},
            "recent": [], "updated": time.time()}


def _row(user_id: str) -> Dict[str, Any]:
    _ensure()
    r = storage._conn().execute(
        "SELECT * FROM gamification WHERE user_id=?", (user_id,)
    ).fetchone()
    if r is None:
        return {**_default_row(), "user_id": user_id}
    return {
        "user_id": r["user_id"],
        "xp": int(r["xp"] or 0),
        "level": int(r["level"] or 1),
        "streak": int(r["streak"] or 0),
        "last_active": r["last_active"],
        "counters": _loads(r["counters"], {}),
        "achievements": _loads(r["achievements"], {}),
        "recent": _loads(r["recent"], []),
        "updated": r["updated"] or time.time(),
    }


def _loads(raw: Any, fallback: Any) -> Any:
    try:
        v = json.loads(raw or "")
        return v if isinstance(v, type(fallback)) else fallback
    except Exception:
        return fallback


def _save(row: Dict[str, Any]) -> None:
    _ensure()
    c = storage._conn()
    c.execute(
        """INSERT INTO gamification
               (user_id, xp, level, streak, last_active, counters,
                achievements, recent, updated)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
               xp=excluded.xp, level=excluded.level, streak=excluded.streak,
               last_active=excluded.last_active, counters=excluded.counters,
               achievements=excluded.achievements, recent=excluded.recent,
               updated=excluded.updated""",
        (row["user_id"], int(row["xp"]), int(row["level"]), int(row["streak"]),
         row["last_active"], json.dumps(row["counters"], ensure_ascii=False),
         json.dumps(row["achievements"], ensure_ascii=False),
         json.dumps(row["recent"][-40:], ensure_ascii=False),
         time.time()),
    )
    c.commit()


def _touch_streak(row: Dict[str, Any]) -> Dict[str, Any]:
    """Advance / reset the daily streak based on the last activity date."""
    today = _today()
    last = row.get("last_active")
    if last == today:
        return row
    try:
        last_d = date.fromisoformat(last) if last else None
    except ValueError:
        last_d = None
    if last_d is not None and last_d == date.today() - timedelta(days=1):
        row["streak"] = int(row.get("streak") or 0) + 1
    elif last_d is None:
        row["streak"] = max(1, int(row.get("streak") or 0))
    else:
        row["streak"] = 1
    row["last_active"] = today
    return row


def _unlock(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unlock every achievement whose threshold is met. Returns new ones."""
    counters = row["counters"]
    unlocked: List[Dict[str, Any]] = []
    have = row["achievements"]
    for aid, name, desc, xp, metric, threshold in ACHIEVEMENTS:
        if aid in have:
            continue
        if int(counters.get(metric, 0)) >= threshold:
            have[aid] = {"unlocked_at": time.time(), "name": name, "xp": xp}
            row["xp"] = int(row["xp"]) + int(xp)
            unlocked.append({"id": aid, "name": name, "description": desc,
                             "xp": xp, "metric": metric, "threshold": threshold})
    return unlocked


def state(user_id: str = DEFAULT_USER) -> Dict[str, Any]:
    """Return the full public state for one operator."""
    row = _row(user_id)
    before_streak = int(row.get("streak") or 0)
    row = _touch_streak(row)
    unlocked = _unlock(row)
    level, title, floor, nxt = _level_for(int(row["xp"]))
    row["level"] = level
    if unlocked or row["last_active"] != (row.get("last_active_before") or row["last_active"]):
        _save(row)
    span = max(1, (nxt - floor)) if nxt else 1
    progress = 100.0 if not nxt else round(((row["xp"] - floor) / span) * 100.0, 1)
    return _public(row, level, title, floor, nxt, progress, unlocked,
                   streak_gained=row["streak"] > before_streak)


def _public(row: Dict[str, Any], level: int, title: str, floor: int, nxt: int,
            progress: float, unlocked: List[Dict[str, Any]],
            streak_gained: bool = False) -> Dict[str, Any]:
    total = len(ACHIEVEMENTS)
    return {
        "ok": True,
        "user_id": row["user_id"],
        "xp": int(row["xp"]),
        "level": level,
        "level_name": title,
        "level_floor_xp": floor,
        "next_level_xp": nxt,
        "xp_to_next": max(0, nxt - int(row["xp"])) if nxt else 0,
        "progress": progress,
        "streak": int(row["streak"]),
        "streak_gained": streak_gained,
        "last_active": row["last_active"],
        "counters": row["counters"],
        "achievements": row["achievements"],
        "achievements_unlocked": len(row["achievements"]),
        "achievements_total": total,
        "new_achievements": unlocked,
        "recent": row["recent"][-20:],
        "updated": row["updated"],
    }


def award(event: str, user_id: str = DEFAULT_USER, amount: Optional[int] = None,
          meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Record an event, add XP, bump its counter and unlock achievements."""
    key = str(event or "").strip().lower()
    if key not in EVENTS:
        raise ValueError(
            f"unknown event '{event}' — valid: {sorted(EVENTS)}")
    base_xp, metric = EVENTS[key]
    gain = int(amount) if amount is not None else int(base_xp)
    if gain < 0:
        raise ValueError("amount must be >= 0")
    row = _row(user_id)
    before_level = _level_for(int(row["xp"]))[0]
    row = _touch_streak(row)
    row["xp"] = int(row["xp"]) + gain
    row["counters"][metric] = int(row["counters"].get(metric, 0)) + 1
    row["recent"] = (row["recent"] + [{
        "event": key, "xp": gain, "metric": metric, "at": time.time(),
        "meta": meta or {},
    }])[-40:]
    unlocked = _unlock(row)
    level, title, floor, nxt = _level_for(int(row["xp"]))
    row["level"] = level
    _save(row)
    span = max(1, (nxt - floor)) if nxt else 1
    progress = 100.0 if not nxt else round(((row["xp"] - floor) / span) * 100.0, 1)
    out = _public(row, level, title, floor, nxt, progress, unlocked)
    out.update({
        "awarded": gain,
        "event": key,
        "leveled_up": level > before_level,
        "levels_gained": max(0, level - before_level),
    })
    return out


def catalog() -> Dict[str, Any]:
    """Static definitions so the UI can render goals without hard-coding."""
    return {
        "ok": True,
        "levels": [{"level": lv, "name": name, "xp_required": req}
                   for lv, name, req in LEVELS],
        "events": {k: {"xp": xp, "metric": metric}
                   for k, (xp, metric) in EVENTS.items()},
        "achievements": [
            {"id": aid, "name": name, "description": desc, "xp": xp,
             "metric": metric, "threshold": threshold}
            for aid, name, desc, xp, metric, threshold in ACHIEVEMENTS
        ],
    }


def reset(user_id: str = DEFAULT_USER) -> Dict[str, Any]:
    _ensure()
    storage._conn().execute("DELETE FROM gamification WHERE user_id=?", (user_id,))
    storage._conn().commit()
    return state(user_id)
