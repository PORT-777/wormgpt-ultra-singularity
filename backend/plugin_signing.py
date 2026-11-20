"""HMAC signing for plugin manifests and update payloads.

Uses the existing Fernet key material already present in the deployment. A
signature is optional for now: signed manifests are verified when a `.sig`
sidecar exists, so the current 86 plugins keep loading unchanged.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
_KEY_FILE = _BACKEND_DIR / ".plugin_key"


def _key() -> bytes:
    value = (os.getenv("PLUGIN_ENCRYPTION_KEY") or "").strip()
    if not value and _KEY_FILE.is_file():
        value = _KEY_FILE.read_text(encoding="utf-8").strip()
    return value.encode("utf-8")


def sign(content: bytes | str) -> str:
    raw = content.encode("utf-8") if isinstance(content, str) else content
    return hmac.new(_key(), raw, hashlib.sha256).hexdigest()


def verify(content: bytes | str, signature: str) -> bool:
    return hmac.compare_digest(sign(content), str(signature or ""))


def sign_file(path: str | Path) -> str:
    return sign(Path(path).read_bytes())


def verify_file(path: str | Path, signature: str) -> bool:
    return verify(Path(path).read_bytes(), signature)
