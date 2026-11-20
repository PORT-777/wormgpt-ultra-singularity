"""
Persistent storage (SQLite + audit trail)

One stdlib sqlite3 file (backend/data/agent.db) holds:
  tables: sessions, messages, scheduled_tasks, audit_log, proposals, kv_store, message_feedback
plus a human-readable data/audit.jsonl mirror of every Full-Access
tool execution for post-hoc review.

All sync (stdlib) — call sites are low-frequency so latency is nil;
heavy paths would use asyncio.to_thread.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import configs as config

DB_DIR = config.BACKEND_DIR / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
# Prefer existing DB filename for backward compatibility, else create agent.db
_legacy = DB_DIR / "🔥😈 PORT 777 EVIL ☠️🔥👹.db"
DB_PATH = _legacy if _legacy.exists() else (DB_DIR / "agent.db")
AUDIT_JSONL = DB_DIR / "audit.jsonl"

_CONN: Optional[sqlite3.Connection] = None


def _conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
        # concurrency: WAL allows readers during a write; busy_timeout
        # makes a blocked writer wait politely instead of raising.
        _CONN.execute("PRAGMA journal_mode=WAL")
        _CONN.execute("PRAGMA busy_timeout=5000")
        _CONN.execute("PRAGMA synchronous=NORMAL")
    return _CONN


def init() -> None:
    c = _conn()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY, created REAL, title TEXT);
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, role TEXT, content TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS scheduled_tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT, interval_minutes INTEGER,
            active INTEGER DEFAULT 1, next_run REAL,
            last_result TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS audit_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL, tool TEXT, detail TEXT, outcome TEXT);
        CREATE TABLE IF NOT EXISTS proposals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL, title TEXT, target TEXT, rationale TEXT,
            content TEXT, status TEXT DEFAULT 'pending',
            session_id TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS kv_store(
            module TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            owner TEXT DEFAULT '',
            workspace TEXT DEFAULT '',
            updated REAL,
            PRIMARY KEY(module, key));
        CREATE TABLE IF NOT EXISTS message_feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL, session_id TEXT, message_id TEXT, vote INTEGER);
        CREATE TABLE IF NOT EXISTS trace_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, run_id TEXT, seq INTEGER, ts REAL,
            kind TEXT, data TEXT);
        """
    )
    # Safe migrations
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(sessions)").fetchall()]
        if "pinned" not in cols:
            c.execute("ALTER TABLE sessions ADD COLUMN pinned INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(messages)").fetchall()]
        if "run_id" not in cols:
            c.execute("ALTER TABLE messages ADD COLUMN run_id TEXT DEFAULT ''")
    except Exception:
        pass
    c.commit()


def _now() -> float:
    return time.time()


# ========================================================================= #
#  Sessions / messages
# ========================================================================= #
def ensure_session(sid: str, title: str = "new session") -> None:
    c = _conn()
    if not c.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone():
        c.execute("INSERT INTO sessions(id, created, title) VALUES (?,?,?)",
                  (sid, _now(), title))
        c.commit()


def add_message(sid: str, role: str, content: str, run_id: str = "") -> int:
    ensure_session(sid)
    c = _conn()
    cur = c.execute(
        "INSERT INTO messages(session_id, role, content, ts, run_id) VALUES (?,?,?,?,?)",
        (sid, role, str(content or "")[:120000], _now(), str(run_id or "")[:80]))
    if role == "user":
        try:
            first = c.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id=? AND role='user'", (sid,)
            ).fetchone()[0]
            if first == 1:  # first user turn names the session
                c.execute("UPDATE sessions SET title=? WHERE id=?",
                          (str(content or "")[:60], sid))
        except Exception:
            pass
    c.commit()
    return int(cur.lastrowid)


def get_history(sid: str, limit: int = 12) -> List[dict]:
    rows = _conn().execute(
        "SELECT role, content FROM messages WHERE session_id=? "
        "ORDER BY id DESC LIMIT ?", (sid, max(1, int(limit or 12)))).fetchall()
    return [{"role": r["role"], "content": r["content"]}
            for r in reversed(rows)]


def get_session_messages(sid: str, limit: int = 500, asc: bool = True) -> List[dict]:
    """Return full message rows for timeline/replay/export."""
    lim = max(1, min(int(limit or 500), 5000))
    order = "ASC" if asc else "DESC"
    rows = _conn().execute(
        f"SELECT id, session_id, role, content, ts, COALESCE(run_id,'') AS run_id "
        f"FROM messages WHERE session_id=? ORDER BY id {order} LIMIT ?",
        (sid, lim)).fetchall()
    out = [dict(r) for r in rows]
    if not asc:
        out = list(reversed(out))
    return out


def list_sessions(q: str = "") -> List[dict]:
    q = (q or "").strip().lower()
    if q:
        like = f"%{q}%"
        rows = _conn().execute(
            "SELECT s.id, s.title, s.created, COALESCE(s.pinned,0) AS pinned, "
            "(SELECT COUNT(*) FROM messages m WHERE m.session_id=s.id) AS n "
            "FROM sessions s WHERE lower(coalesce(s.title,'')) LIKE ? OR lower(s.id) LIKE ? "
            "ORDER BY COALESCE(s.pinned,0) DESC, s.created DESC", (like, like)).fetchall()
    else:
        rows = _conn().execute(
            "SELECT s.id, s.title, s.created, COALESCE(s.pinned,0) AS pinned, "
            "(SELECT COUNT(*) FROM messages m WHERE m.session_id=s.id) AS n "
            "FROM sessions s ORDER BY COALESCE(s.pinned,0) DESC, s.created DESC").fetchall()
    return [dict(r) for r in rows]


def get_session(sid: str) -> Optional[dict]:
    row = _conn().execute(
        "SELECT id, title, created, COALESCE(pinned,0) AS pinned, "
        "(SELECT COUNT(*) FROM messages m WHERE m.session_id=s.id) AS n "
        "FROM sessions s WHERE id=?", (sid,)).fetchone()
    return dict(row) if row else None


def get_session_export(sid: str, message_limit: int = 2000) -> Optional[dict]:
    sess = get_session(sid)
    if not sess:
        return None
    msgs = get_session_messages(sid, limit=message_limit, asc=True)
    traces = list_trace_events(sid, limit=5000)
    return {"session": sess, "messages": msgs, "trace_events": traces, "exported_at": _now()}


def patch_session(sid: str, *, title: Optional[str] = None, pinned: Optional[bool] = None) -> Optional[dict]:
    if not get_session(sid):
        return None
    c = _conn()
    if title is not None:
        c.execute("UPDATE sessions SET title=? WHERE id=?", (str(title)[:200], sid))
    if pinned is not None:
        c.execute("UPDATE sessions SET pinned=? WHERE id=?", (1 if pinned else 0, sid))
    c.commit()
    return get_session(sid)


def delete_session(sid: str) -> int:
    c = _conn()
    if not c.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone():
        raise KeyError(sid)
    try:
        c.execute("DELETE FROM trace_events WHERE session_id=?", (sid,))
    except Exception:
        pass
    n = c.execute("DELETE FROM messages WHERE session_id=?", (sid,)).rowcount
    c.execute("DELETE FROM sessions WHERE id=?", (sid,))
    c.commit()
    return n


def delete_all_sessions() -> dict:
    """Wipe every session plus its messages and trace events.

    Returns counts so the UI can report what was removed.
    """
    c = _conn()
    sessions = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    messages = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    try:
        traces = c.execute("SELECT COUNT(*) FROM trace_events").fetchone()[0]
    except Exception:
        traces = 0
    try:
        c.execute("DELETE FROM trace_events")
    except Exception:
        pass
    c.execute("DELETE FROM messages")
    c.execute("DELETE FROM sessions")
    c.commit()
    try:
        c.execute("VACUUM")
    except Exception:
        pass
    return {"sessions": int(sessions), "messages": int(messages),
            "trace_events": int(traces)}


def duplicate_session(sid: str, new_id: str) -> Optional[dict]:
    src = get_session(sid)
    if not src:
        return None
    c = _conn()
    base = (src.get("title") or sid).strip() or sid
    title = f"{base} (copy)"
    c.execute("INSERT INTO sessions(id, created, title, pinned) VALUES (?,?,?,0)", (new_id, _now(), title[:200]))
    rows = c.execute(
        "SELECT role, content, ts, COALESCE(run_id,'') AS run_id FROM messages WHERE session_id=? ORDER BY id ASC", (sid,)
    ).fetchall()
    for r in rows:
        try:
            c.execute(
                "INSERT INTO messages(session_id, role, content, ts, run_id) VALUES (?,?,?,?,?)",
                (new_id, r["role"], r["content"], r["ts"] or _now(), r["run_id"] or ""),
            )
        except Exception:
            c.execute(
                "INSERT INTO messages(session_id, role, content, ts) VALUES (?,?,?,?)",
                (new_id, r["role"], r["content"], r["ts"] or _now()),
            )
    c.commit()
    return get_session(new_id)


def restore_session(snapshot: dict) -> dict:
    """Restore a deleted session + messages (undo). Local storage only."""
    if not isinstance(snapshot, dict):
        raise ValueError("bad snapshot")
    sid = str(snapshot.get("id") or "").strip()
    if not sid:
        raise ValueError("missing id")
    c = _conn()
    try:
        c.execute("DELETE FROM trace_events WHERE session_id=?", (sid,))
    except Exception:
        pass
    c.execute("DELETE FROM messages WHERE session_id=?", (sid,))
    c.execute("DELETE FROM sessions WHERE id=?", (sid,))
    c.execute(
        "INSERT INTO sessions(id, created, title, pinned) VALUES (?,?,?,?)",
        (sid, float(snapshot.get("created") or _now()), str(snapshot.get("title") or "restored")[:200], int(1 if snapshot.get("pinned") else 0)),
    )
    for m in (snapshot.get("messages") or []):
        if not isinstance(m, dict):
            continue
        try:
            c.execute(
                "INSERT INTO messages(session_id, role, content, ts, run_id) VALUES (?,?,?,?,?)",
                (sid, str(m.get("role") or "user"), str(m.get("content") or "")[:120000], float(m.get("ts") or _now()), str(m.get("run_id") or "")[:80]),
            )
        except Exception:
            c.execute(
                "INSERT INTO messages(session_id, role, content, ts) VALUES (?,?,?,?)",
                (sid, str(m.get("role") or "user"), str(m.get("content") or "")[:120000], float(m.get("ts") or _now())),
            )
    c.commit()
    return get_session(sid) or {"id": sid}


# ========================================================================= #
#  Trace events (timeline/replay)
# ========================================================================= #
def add_trace_event(session_id: str, run_id: str, seq: int, kind: str, data: Any) -> int:
    try:
        payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        payload = str(data)
    c = _conn()
    cur = c.execute(
        "INSERT INTO trace_events(session_id, run_id, seq, ts, kind, data) VALUES (?,?,?,?,?,?)",
        (str(session_id or ""), str(run_id or "")[:80], int(seq or 0), _now(), str(kind or "")[:80], payload[:200000]),
    )
    c.commit()
    return int(cur.lastrowid)


def list_trace_events(session_id: str, run_id: str = "", limit: int = 1000) -> List[dict]:
    lim = max(1, min(int(limit or 1000), 10000))
    if run_id:
        rows = _conn().execute(
            "SELECT id, session_id, run_id, seq, ts, kind, data FROM trace_events WHERE session_id=? AND run_id=? ORDER BY id ASC LIMIT ?",
            (session_id, run_id, lim),
        ).fetchall()
    else:
        rows = _conn().execute(
            "SELECT id, session_id, run_id, seq, ts, kind, data FROM trace_events WHERE session_id=? ORDER BY id ASC LIMIT ?",
            (session_id, lim),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        raw = d.get("data")
        try:
            d["data"] = json.loads(raw) if isinstance(raw, str) and raw[:1] in "[{\"" else raw
        except Exception:
            d["data"] = raw
        out.append(d)
    return out


# ========================================================================= #
#  Audit trail (Full Access Mode actions)
# ========================================================================= #
def audit(tool: str, detail: str, outcome: str = "") -> None:
    entry = {"ts": _now(), "tool": tool,
             "detail": str(detail or "")[:300], "outcome": str(outcome or "")[:120]}
    c = _conn()
    c.execute("INSERT INTO audit_log(ts, tool, detail, outcome) "
              "VALUES (?,?,?,?)",
              (entry["ts"], entry["tool"], entry["detail"], entry["outcome"]))
    c.commit()
    try:
        with open(AUDIT_JSONL, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def get_audit(limit: int = 100) -> List[dict]:
    lim = max(1, min(int(limit or 100), 2000))
    return [dict(r) for r in _conn().execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (lim,))]


# ========================================================================= #
#  Scheduled background tasks
# ========================================================================= #
def add_task(prompt: str, interval_minutes: int) -> int:
    cur = _conn().execute(
        "INSERT INTO scheduled_tasks(prompt, interval_minutes, active, "
        "next_run, created) VALUES (?,?,1,?,?)",
        (str(prompt or ""), int(interval_minutes or 1), _now() + int(interval_minutes or 1) * 60, _now()))
    _conn().commit()
    return int(cur.lastrowid)


def list_tasks() -> List[dict]:
    return [dict(r) for r in _conn().execute(
        "SELECT * FROM scheduled_tasks ORDER BY id DESC").fetchall()]


def remove_task(task_id: int) -> int:
    cur = _conn().execute(
        "DELETE FROM scheduled_tasks WHERE id=?", (int(task_id),))
    _conn().commit()
    return int(cur.rowcount or 0)


def due_tasks() -> List[dict]:
    rows = _conn().execute(
        "SELECT * FROM scheduled_tasks WHERE active=1 AND next_run<=?",
        (_now(),)).fetchall()
    return [dict(r) for r in rows]


def complete_task(task_id: int, result: str) -> None:
    row = _conn().execute(
        "SELECT interval_minutes FROM scheduled_tasks WHERE id=?",
        (int(task_id),)).fetchone()
    if row is None:
        return
    _conn().execute(
        "UPDATE scheduled_tasks SET last_result=?, next_run=? WHERE id=?",
        (str(result or "")[:8000], _next_run(int(row["interval_minutes"] or 1)), int(task_id)))
    _conn().commit()


def _next_run(interval_minutes: int) -> float:
    return _now() + max(1, int(interval_minutes or 1)) * 60


def set_task_active(task_id: int, active: bool) -> int:
    cur = _conn().execute(
        "UPDATE scheduled_tasks SET active=? WHERE id=?",
        (1 if active else 0, int(task_id)))
    _conn().commit()
    return int(cur.rowcount or 0)


# ========================================================================= #
#  Change proposals (human-in-the-loop self-improvement)
# ========================================================================= #
def add_proposal(title: str, target: str, rationale: str, content: str, session_id: str = "") -> int:
    c = _conn()
    cur = c.execute(
        "INSERT INTO proposals(ts, title, target, rationale, content, status, session_id) VALUES (?,?,?,?,?, 'pending', ?)",
        (_now(), str(title or "")[:200], str(target or "")[:300], str(rationale or "")[:4000], str(content or "")[:120000], str(session_id or "")),
    )
    c.commit()
    return int(cur.lastrowid)


def list_proposals(status: Optional[str] = None) -> List[dict]:
    if status:
        rows = _conn().execute(
            "SELECT id, ts, title, target, rationale, status, session_id FROM proposals WHERE status=? ORDER BY id DESC", (str(status),))
    else:
        rows = _conn().execute(
            "SELECT id, ts, title, target, rationale, status, session_id FROM proposals ORDER BY id DESC")
    return [dict(r) for r in rows]


def get_proposal(pid: int) -> Optional[dict]:
    row = _conn().execute(
        "SELECT * FROM proposals WHERE id=?", (int(pid),)).fetchone()
    return dict(row) if row else None


def set_proposal_status(pid: int, status: str) -> int:
    cur = _conn().execute(
        "UPDATE proposals SET status=? WHERE id=?",
        (str(status or "pending"), int(pid)))
    _conn().commit()
    return int(cur.rowcount or 0)


# ========================================================================= #
#  Message feedback (thumbs up/down)
# ========================================================================= #
def add_feedback(session_id: str, message_id: str, vote: int) -> int:
    try:
        v = int(vote)
    except Exception:
        v = 0
    cur = _conn().execute(
        "INSERT INTO message_feedback(ts, session_id, message_id, vote) VALUES (?,?,?,?)",
        (_now(), str(session_id or ""), str(message_id or ""), v))
    _conn().commit()
    return int(cur.lastrowid)


# ========================================================================= #
#  Simple KV store
# ========================================================================= #
def kv_set(module: str, key: str, value: Any, owner: str = "", workspace: str = "") -> None:
    try:
        payload = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        payload = json.dumps(str(value), ensure_ascii=False)
    c = _conn()
    c.execute(
        "INSERT INTO kv_store(module,key,value,owner,workspace,updated) VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(module,key) DO UPDATE SET value=excluded.value, owner=excluded.owner, workspace=excluded.workspace, updated=excluded.updated",
        (str(module or ""), str(key or ""), payload, str(owner or ""), str(workspace or ""), _now()),
    )
    c.commit()


def kv_get(module: str, key: str, default: Any = None) -> Any:
    row = _conn().execute(
        "SELECT value FROM kv_store WHERE module=? AND key=?",
        (str(module or ""), str(key or "")),
    ).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return row["value"]
