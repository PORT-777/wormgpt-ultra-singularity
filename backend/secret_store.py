"""Encrypted at-rest storage for provider API keys.

Uses Fernet. Master key MUST come from ENCRYPTION_MASTER_KEY env var.
Fails closed if missing. Never derived from AUTH_SECRET.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet, InvalidToken


def _master_key() -> bytes:
    raw = os.getenv("ENCRYPTION_MASTER_KEY", "").strip()
    if not raw:
        raise RuntimeError("ENCRYPTION_MASTER_KEY is required (fail-closed)")
    try:
        key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        if len(key) == 32:
            return base64.urlsafe_b64encode(key)
    except Exception:
        pass
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())


def _fernet() -> Fernet:
    return Fernet(_master_key())


def _store_file() -> Path:
    p = os.getenv("SECRET_STORE_PATH", "").strip()
    if p:
        return Path(p).expanduser()
    return Path(__file__).resolve().parent / "data" / "secrets.enc.json"


def _load() -> Dict[str, str]:
    p = _store_file()
    if not p.exists():
        return {}
    try:
        blob = p.read_bytes()
        plain = _fernet().decrypt(blob)
        return json.loads(plain.decode("utf-8"))
    except (InvalidToken, Exception):
        return {}


def _save(data: Dict[str, str]) -> None:
    p = _store_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    blob = _fernet().encrypt(json.dumps(data).encode("utf-8"))
    p.write_bytes(blob)


def set_key(name: str, value: str) -> None:
    if not name or not value:
        raise ValueError("name and value required")
    data = _load()
    data[name] = value
    _save(data)


def get_key(name: str) -> Optional[str]:
    return _load().get(name)


def delete_key(name: str) -> bool:
    data = _load()
    if name in data:
        del data[name]
        _save(data)
        return True
    return False


def list_keys() -> list:
    return sorted(_load().keys())


def masked(name: str) -> Optional[str]:
    v = get_key(name)
    if v is None:
        return None
    if len(v) <= 8:
        return "*" * len(v)
    return v[:4] + "*" * (len(v) - 8) + v[-4:]
