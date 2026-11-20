"""Provider credentials manager: maps provider to secret-store key name."""
from __future__ import annotations

from typing import Dict, Optional

CRED_MAP: Dict[str, str] = {}


def set_credential(provider: str, secret_name: str) -> None:
    CRED_MAP[provider] = secret_name


def get_secret_name(provider: str) -> Optional[str]:
    return CRED_MAP.get(provider)


def resolve(provider: str) -> Optional[str]:
    from secret_store import get_key
    name = CRED_MAP.get(provider)
    if not name:
        return None
    return get_key(name)


def list_all() -> Dict[str, str]:
    return dict(CRED_MAP)
