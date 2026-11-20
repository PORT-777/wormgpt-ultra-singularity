"""Generic persistent KV store backed by SQLite storage.kv_store."""
from __future__ import annotations

import json
import time
from typing import Any, List, Optional, Dict

import storage


def set(module: str, key: str, value: Any, owner: str = "", workspace: str = "") -> None:
    c = storage._conn()
    c.execute(
        "INSERT OR REPLACE INTO kv_store(module,key,value,owner,workspace,updated) "
        "VALUES (?,?,?,?,?,?)",
        (module, key, json.dumps(value, default=str), owner, workspace, time.time()))
    c.commit()


def get(module: str, key: str) -> Optional[Any]:
    row = storage._conn().execute(
        "SELECT value FROM kv_store WHERE module=? AND key=?", (module, key)).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["value"])
    except Exception:
        return None


def delete(module: str, key: str) -> bool:
    c = storage._conn()
    n = c.execute("DELETE FROM kv_store WHERE module=? AND key=?", (module, key)).rowcount
    c.commit()
    return n > 0


def list_all(module: str, owner: Optional[str] = None,
             workspace: Optional[str] = None) -> List[Dict]:
    q = "SELECT key,value,owner,workspace,updated FROM kv_store WHERE module=?"
    params = [module]
    if owner is not None and owner != "":
        q += " AND owner=?"
        params.append(owner)
    if workspace is not None and workspace != "":
        q += " AND workspace=?"
        params.append(workspace)
    rows = storage._conn().execute(q, params).fetchall()
    out = []
    for r in rows:
        try:
            v = json.loads(r["value"])
        except Exception:
            v = None
        out.append({"key": r["key"], "value": v, "owner": r["owner"],
                    "workspace": r["workspace"], "updated": r["updated"]})
    return out


def clear(module: str) -> int:
    c = storage._conn()
    n = c.execute("DELETE FROM kv_store WHERE module=?", (module,)).rowcount
    c.commit()
    return n
