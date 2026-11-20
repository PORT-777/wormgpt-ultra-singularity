"""Encrypted at-rest store for OAuth client credentials.

`.env` stays readable for non-secret settings; provider client IDs/secrets are
also written here as a single Fernet-encrypted blob so a packaged binary never
carries them in clear text. On startup the values are exported into os.environ
so ProviderSpec.client_id()/client_secret() keep working unchanged.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict

from cryptography.fernet import Fernet

logger = logging.getLogger("PlatformSecrets")

_BACKEND_DIR = Path(__file__).resolve().parent
_STORE = _BACKEND_DIR / "data" / ".platform_secrets.enc"
_KEY_FILE = _BACKEND_DIR / ".plugin_key"


def _fernet() -> Fernet:
    key = (os.getenv("PLUGIN_ENCRYPTION_KEY") or "").strip()
    if not key and _KEY_FILE.is_file():
        key = _KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        key = Fernet.generate_key().decode()
        _KEY_FILE.write_text(key, encoding="utf-8")
    return Fernet(key.encode())


def _read() -> Dict[str, str]:
    if not _STORE.is_file():
        return {}
    try:
        raw = _fernet().decrypt(_STORE.read_bytes())
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("could not read encrypted secret store: %s", exc)
        return {}


def _write(data: Dict[str, str]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    blob = _fernet().encrypt(json.dumps(data).encode("utf-8"))
    _STORE.write_bytes(blob)


def set_many(values: Dict[str, str]) -> None:
    data = _read()
    data.update({str(k): str(v) for k, v in values.items() if v not in (None, "")})
    _write(data)


def get(key: str) -> str:
    return str(_read().get(key, ""))


def load_into_env() -> int:
    data = _read()
    loaded = 0
    for key, value in data.items():
        if value and not os.environ.get(key):
            os.environ[key] = str(value)
            loaded += 1
    return loaded
