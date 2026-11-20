"""User profiles, credits, webhook events and administrative audit records."""
from __future__ import annotations

import hashlib
import secrets
from typing import Any, Dict, List, Optional

from .. import database
from . import db

PROFILE_FIELDS = (
    "display_name", "bio", "avatar_path", "system_prompt",
    "model_preferences", "memory", "preferences",
)


def get_profile(user_id: str) -> Dict[str, Any]:
    row = db.conn().execute(
        "SELECT * FROM user_profiles WHERE user_id=?", (user_id,)
    ).fetchone()
    if not row:
        return {"user_id": user_id, **{k: "" for k in PROFILE_FIELDS}}
    data = dict(row)
    for key in ("model_preferences", "memory", "preferences"):
        data[key] = db.jload(data.get(key), {})
    return data


def upsert_profile(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    current = get_profile(user_id)
    values = []
    for key in PROFILE_FIELDS:
        value = payload.get(key, current.get(key, ""))
        if key in ("model_preferences", "memory", "preferences"):
            value = db.jdump(value)
        values.append(str(value)[:100000] if value is not None else "")
    c = db.conn()
    with database.transaction(c):
        if c.execute("SELECT 1 FROM user_profiles WHERE user_id=?", (user_id,)).fetchone():
            sets = ", ".join(f"{k}=?" for k in PROFILE_FIELDS)
            c.execute(f"UPDATE user_profiles SET {sets},updated=? WHERE user_id=?",
                      tuple(values + [db.now(), user_id]))
        else:
            cols = ", ".join(["user_id"] + list(PROFILE_FIELDS) + ["updated"])
            marks = ", ".join(["?"] * (len(PROFILE_FIELDS) + 2))
            c.execute(f"INSERT INTO user_profiles({cols}) VALUES({marks})",
                      tuple([user_id] + values + [db.now()]))
    return get_profile(user_id)


def credit_balance(user_id: str) -> float:
    row = db.conn().execute(
        "SELECT balance FROM credit_balances WHERE user_id=?", (user_id,)
    ).fetchone()
    return float(row[0] or 0) if row else 0.0


def adjust_credit(user_id: str, delta: float, reason: str = "", actor: str = "system") -> float:
    c = db.conn()
    with database.transaction(c):
        balance = credit_balance(user_id) + float(delta)
        c.execute(
            "INSERT OR REPLACE INTO credit_balances(user_id,balance,updated) VALUES(?,?,?)",
            (user_id, balance, db.now()),
        )
        c.execute(
            "INSERT INTO credit_ledger(user_id,delta,reason,actor,created) VALUES(?,?,?,?,?)",
            (user_id, float(delta), str(reason)[:300], str(actor)[:100], db.now()),
        )
    return balance


def credit_history(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    rows = db.conn().execute(
        "SELECT delta,reason,actor,created FROM credit_ledger WHERE user_id=? "
        "ORDER BY id DESC LIMIT ?", (user_id, min(int(limit), 500)),
    ).fetchall()
    return [dict(r) for r in rows]


def record_webhook(provider: str, event_type: str, payload: Dict[str, Any],
                   signature_valid: bool, processed: bool = True) -> str:
    data = db.jdump(payload)
    event_id = "wh-" + hashlib.sha256(f"{provider}|{event_type}|{data}".encode()).hexdigest()[:24]
    c = db.conn()
    c.execute(
        "INSERT OR REPLACE INTO webhook_events(id,provider,event_type,payload,signature_valid,processed,created) "
        "VALUES(?,?,?,?,?,?,?)",
        (event_id, provider, str(event_type)[:120], data, 1 if signature_valid else 0,
         1 if processed else 0, db.now()),
    )
    c.commit()
    return event_id


def audit(actor: str, action: str, target: str = "", detail: Any = "") -> None:
    c = db.conn()
    c.execute(
        "INSERT INTO audit_events(actor,action,target,detail,created) VALUES(?,?,?,?,?)",
        (str(actor)[:100], str(action)[:120], str(target)[:200], db.jdump(detail), db.now()),
    )
    c.commit()


def audit_events(page: int = 1, limit: int = 50) -> Dict[str, Any]:
    p, size, offset = database.page_params(page, limit)
    c = db.conn()
    total = c.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
    rows = c.execute(
        "SELECT actor,action,target,detail,created FROM audit_events "
        "ORDER BY id DESC LIMIT ? OFFSET ?", (size, offset),
    ).fetchall()
    return {"events": [dict(r) for r in rows], "total": int(total),
            "page": p, "limit": size}
