"""Central usage accounting and backend entitlement enforcement."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from . import db, plans


def record(user_id: str, metric: str, amount: float = 1.0, model: str = "",
           session_id: str = "", success: bool = True) -> None:
    c = db.conn()
    c.execute("INSERT INTO saas_usage(user_id,metric,amount,model,session_id,success,ts) VALUES(?,?,?,?,?,?,?)",
              (user_id, metric, float(amount), model, session_id, 1 if success else 0, db.now()))
    c.commit()


def _sum_since(user_id: str, metric: str, since: float) -> float:
    c = db.conn()
    row = c.execute("SELECT COALESCE(SUM(amount),0) AS v FROM saas_usage WHERE user_id=? AND metric=? AND ts>=?",
                    (user_id, metric, since)).fetchone()
    return float(row["v"] if row else 0)


def start_of_day() -> float:
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def start_of_month() -> float:
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, -1))


def usage_summary(user_id: str) -> Dict[str, Any]:
    return {
        "requests_today": _sum_since(user_id, "request", start_of_day()),
        "tokens_month": _sum_since(user_id, "tokens", start_of_month()),
        "agents_today": _sum_since(user_id, "agent", start_of_day()),
        "computer_seconds_today": _sum_since(user_id, "computer_seconds", start_of_day()),
        "by_model": _by_model(user_id),
    }


def _by_model(user_id: str) -> Dict[str, float]:
    c = db.conn()
    rows = c.execute("SELECT model,COALESCE(SUM(amount),0) AS v FROM saas_usage WHERE user_id=? AND metric='tokens' AND ts>=? GROUP BY model",
                     (user_id, start_of_month())).fetchall()
    return {r["model"] or "unknown": float(r["v"]) for r in rows}


def entitlement(user_id: str) -> Dict[str, Any]:
    sub = plans.ensure_subscription(user_id)
    plan = plans.get_plan(sub["plan_id"]) or plans.get_plan("free")
    cfg = plan["config"]
    usage = usage_summary(user_id)
    return {
        "subscription": sub, "plan": plan, "usage": usage,
        "limits": cfg,
        "allowed": {
            "daily_requests": usage["requests_today"] < float(cfg.get("daily_requests", 25)),
            "monthly_tokens": usage["tokens_month"] < float(cfg.get("monthly_tokens", 200000)),
            "agents": usage["agents_today"] < float(cfg.get("agents_per_day", 2)),
            "computer": bool(cfg.get("computer_access", False)),
            "api": bool(cfg.get("api_access", False)),
            "integrations": bool(cfg.get("integrations", False)),
        },
    }


def check_model(user_id: str, model_id: str) -> Dict[str, Any]:
    ent = entitlement(user_id)
    allowed_models = ent["limits"].get("allowed_models", [])
    ok = (not allowed_models) or ("*" in allowed_models) or (model_id in allowed_models)
    return {"allowed": bool(ok and ent["subscription"]["status"] in ("active", "pending")),
            "model": model_id, "reason": "plan model access" if not ok else "ok",
            "subscription_status": ent["subscription"]["status"]}


def enforce(user_id: str, feature: str, model_id: str = "", amount: float = 1.0) -> Dict[str, Any]:
    ent = entitlement(user_id)
    status = ent["subscription"]["status"]
    if status not in ("active", "pending"):
        return {"allowed": False, "reason": f"subscription status: {status}"}
    if model_id and not check_model(user_id, model_id)["allowed"]:
        return {"allowed": False, "reason": "model not included in plan"}
    key = {"request": "daily_requests", "tokens": "monthly_tokens", "agent": "agents"}.get(feature)
    if key and not ent["allowed"].get(key, True):
        return {"allowed": False, "reason": f"{key} limit reached"}
    if feature == "computer" and not ent["allowed"]["computer"]:
        return {"allowed": False, "reason": "computer access requires PRO or ULTIMATE"}
    if feature == "api" and not ent["allowed"]["api"]:
        return {"allowed": False, "reason": "API access requires PRO or ULTIMATE"}
    return {"allowed": True, "reason": "ok", "entitlement": ent}
