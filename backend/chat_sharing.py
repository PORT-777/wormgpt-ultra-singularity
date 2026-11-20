"""Chat sharing: create/revoke share links with expiry."""
from __future__ import annotations

import secrets
import time
from typing import Dict, Optional

SHARES: Dict[str, dict] = {}


def create(session_id: str, expires_in: int = 86400) -> dict:
    token = secrets.token_urlsafe(24)
    rec = {"token": token, "session_id": session_id,
           "created_at": time.time(), "expires_at": time.time() + expires_in,
           "revoked": False}
    SHARES[token] = rec
    return rec


def get(token: str) -> Optional[dict]:
    rec = SHARES.get(token)
    if not rec or rec["revoked"]:
        return None
    if time.time() > rec["expires_at"]:
        return None
    return rec


def revoke(token: str) -> bool:
    rec = SHARES.get(token)
    if not rec:
        return False
    rec["revoked"] = True
    return True


def list_all(session_id: Optional[str] = None) -> list:
    out = list(SHARES.values())
    if session_id:
        out = [s for s in out if s["session_id"] == session_id]
    return out
