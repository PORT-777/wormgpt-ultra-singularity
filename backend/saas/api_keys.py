"""Developer API keys — hashed at rest, secret shown once."""
from __future__ import annotations

import hashlib
import secrets
from typing import Any, Dict, List

from . import db


def create(user_id: str, name: str = "", permissions: List[str] | None = None) -> Dict[str, Any]:
    token = "p7_" + secrets.token_urlsafe(32)
    prefix = token[:10]
    kid = "key-" + secrets.token_hex(8)
    c = db.conn()
    c.execute(
        "INSERT INTO saas_api_keys(id,user_id,name,key_hash,prefix,permissions,created,last_used,revoked) "
        "VALUES(?,?,?,?,?,?,?,?,0)",
        (kid, user_id, name or "default", hashlib.sha256(token.encode()).hexdigest(),
         prefix, db.jdump(permissions or ["chat:read", "chat:write"]), db.now(), 0),
    )
    c.commit()
    return {"id": kid, "name": name or "default", "prefix": prefix, "secret": token,
            "created": db.now(), "permissions": permissions or ["chat:read", "chat:write"]}


def list_keys(user_id: str) -> List[Dict[str, Any]]:
    c = db.conn()
    rows = c.execute("SELECT id,name,prefix,permissions,created,last_used,revoked FROM saas_api_keys WHERE user_id=? ORDER BY created DESC",
                     (user_id,)).fetchall()
    return [{"id": r["id"], "name": r["name"], "prefix": r["prefix"],
             "permissions": db.jload(r["permissions"], []), "created": r["created"],
             "last_used": r["last_used"], "revoked": bool(r["revoked"])} for r in rows]


def revoke(user_id: str, key_id: str) -> bool:
    c = db.conn()
    cur = c.execute("UPDATE saas_api_keys SET revoked=1 WHERE id=? AND user_id=?", (key_id, user_id))
    c.commit()
    return cur.rowcount > 0


def resolve(token: str) -> Dict[str, Any] | None:
    if not token.startswith("p7_"):
        return None
    c = db.conn()
    row = c.execute("SELECT * FROM saas_api_keys WHERE key_hash=? AND revoked=0",
                    (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not row:
        return None
    c.execute("UPDATE saas_api_keys SET last_used=? WHERE id=?", (db.now(), row["id"]))
    c.commit()
    return {"user_id": row["user_id"], "id": row["id"], "permissions": db.jload(row["permissions"], [])}
