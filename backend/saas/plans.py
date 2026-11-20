"""Configurable plans and subscription state."""
from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional

from . import db

DEFAULT_PLANS = {
    "free": {
        "name": "FREE", "description": "Explore the platform with core models.",
        "monthly_price": 0.0, "annual_price": 0.0,
        "config": {
            "allowed_models": ["auto", "groq", "gemini", "local"],
            "daily_requests": 25, "monthly_tokens": 200000,
            "agents_per_day": 2, "computer_access": False,
            "storage_gb": 1, "integrations": False, "api_access": False,
            "concurrent_tasks": 1,
        },
    },
    "pro": {
        "name": "PRO", "description": "More models, higher limits and API access.",
        "monthly_price": 19.0, "annual_price": 190.0,
        "config": {
            "allowed_models": ["*"],
            "daily_requests": 500, "monthly_tokens": 5000000,
            "agents_per_day": 50, "computer_access": True,
            "storage_gb": 20, "integrations": True, "api_access": True,
            "concurrent_tasks": 5,
        },
    },
    "ultimate": {
        "name": "ULTIMATE", "description": "Highest limits and priority compute.",
        "monthly_price": 49.0, "annual_price": 490.0,
        "config": {
            "allowed_models": ["*"],
            "daily_requests": 5000, "monthly_tokens": 25000000,
            "agents_per_day": 500, "computer_access": True,
            "storage_gb": 100, "integrations": True, "api_access": True,
            "concurrent_tasks": 20,
        },
    },
}


def seed() -> None:
    c = db.conn()
    for pid, data in DEFAULT_PLANS.items():
        if c.execute("SELECT 1 FROM saas_plans WHERE id=?", (pid,)).fetchone():
            continue
        c.execute(
            "INSERT INTO saas_plans(id,name,description,monthly_price,annual_price,currency,config,active,updated) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (pid, data["name"], data["description"], data["monthly_price"], data["annual_price"],
             "USD", db.jdump(data["config"]), 1, db.now()),
        )
    c.commit()


def list_plans(active_only: bool = True) -> List[Dict[str, Any]]:
    seed()
    c = db.conn()
    rows = c.execute("SELECT * FROM saas_plans" + (" WHERE active=1" if active_only else "") +
                     " ORDER BY monthly_price").fetchall()
    out = []
    for r in rows:
        d = dict(r); d["config"] = db.jload(d["config"], {}); d["active"] = bool(d["active"])
        out.append(d)
    return out


def get_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    c = db.conn()
    r = c.execute("SELECT * FROM saas_plans WHERE id=?", (plan_id,)).fetchone()
    if not r:
        return None
    d = dict(r); d["config"] = db.jload(d["config"], {}); d["active"] = bool(d["active"])
    return d


def upsert_plan(plan_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    c = db.conn()
    current = get_plan(plan_id) or {}
    cfg = data.get("config", current.get("config", {}))
    c.execute(
        "INSERT OR REPLACE INTO saas_plans(id,name,description,monthly_price,annual_price,currency,config,active,updated) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (plan_id, data.get("name", current.get("name", plan_id)),
         data.get("description", current.get("description", "")),
         float(data.get("monthly_price", current.get("monthly_price", 0))),
         float(data.get("annual_price", current.get("annual_price", 0))),
         data.get("currency", current.get("currency", "USD")),
         db.jdump(cfg), 1 if data.get("active", current.get("active", True)) else 0, db.now()),
    )
    c.commit()
    return get_plan(plan_id)


def ensure_subscription(user_id: str) -> Dict[str, Any]:
    c = db.conn()
    row = c.execute("SELECT * FROM saas_subscriptions WHERE user_id=? ORDER BY created DESC LIMIT 1",
                    (user_id,)).fetchone()
    if row:
        d = dict(row)
        if d["status"] in ("active", "pending") and d.get("current_period_end", 0) and d["current_period_end"] < db.now():
            d["status"] = "expired"
            c.execute("UPDATE saas_subscriptions SET status='expired',updated=? WHERE id=?", (db.now(), d["id"]))
            c.commit()
        return d
    sid = "sub-" + secrets.token_hex(8)
    c.execute(
        "INSERT INTO saas_subscriptions(id,user_id,plan_id,status,provider,provider_ref,current_period_end,created,updated) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (sid, user_id, "free", "active", "internal", "signup", 0, db.now(), db.now()),
    )
    c.commit()
    return get_subscription(sid)


def get_subscription(sub_id: str) -> Dict[str, Any]:
    c = db.conn()
    r = c.execute("SELECT * FROM saas_subscriptions WHERE id=?", (sub_id,)).fetchone()
    return dict(r) if r else {}


def set_subscription(user_id: str, plan_id: str, status: str = "active", provider: str = "internal",
                     provider_ref: str = "", period_end: float = 0) -> Dict[str, Any]:
    c = db.conn()
    row = c.execute("SELECT * FROM saas_subscriptions WHERE user_id=? ORDER BY created DESC LIMIT 1",
                    (user_id,)).fetchone()
    if row:
        c.execute("UPDATE saas_subscriptions SET plan_id=?,status=?,provider=?,provider_ref=?,current_period_end=?,updated=? WHERE id=?",
                  (plan_id, status, provider, provider_ref, period_end, db.now(), row["id"]))
        sid = row["id"]
    else:
        sid = "sub-" + secrets.token_hex(8)
        c.execute("INSERT INTO saas_subscriptions(id,user_id,plan_id,status,provider,provider_ref,current_period_end,created,updated) VALUES(?,?,?,?,?,?,?,?,?)",
                  (sid, user_id, plan_id, status, provider, provider_ref, period_end, db.now(), db.now()))
    c.commit()
    return get_subscription(sid)
