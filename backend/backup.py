"""Platform backup/restore: serialize kv_store + storage tables."""
from __future__ import annotations

import json
import time
import storage
import kv_store


def snapshot() -> dict:
    c = storage._conn()
    tables = {}
    for t in ("sessions", "messages", "scheduled_tasks", "audit_log", "proposals"):
        try:
            tables[t] = [dict(r) for r in c.execute(f"SELECT * FROM {t}").fetchall()]
        except Exception:
            tables[t] = []
    kv = {}
    for r in c.execute("SELECT module,key,value,owner,workspace,updated FROM kv_store").fetchall():
        kv.setdefault(r["module"], {})[r["key"]] = {
            "value": r["value"], "owner": r["owner"],
            "workspace": r["workspace"], "updated": r["updated"]}
    return {"version": 2, "created_at": time.time(), "tables": tables, "kv": kv}


def restore(data: dict) -> dict:
    c = storage._conn()
    # kv restore
    c.execute("DELETE FROM kv_store")
    for mod, items in (data.get("kv") or {}).items():
        for key, rec in items.items():
            c.execute("INSERT OR REPLACE INTO kv_store(module,key,value,owner,workspace,updated) VALUES (?,?,?,?,?,?)",
                      (mod, key, rec["value"], rec.get("owner", ""), rec.get("workspace", ""), rec.get("updated")))
    c.commit()
    return {"restored": True}


def to_json() -> str:
    return json.dumps(snapshot(), indent=2, default=str)


def from_json(s: str) -> dict:
    return restore(json.loads(s))
