"""
Encrypted persistence for OAuth connections and authorization sessions.

* Connections live in ``backend/data/integrations.json``.
* Access and refresh tokens are Fernet-encrypted (AES-256) before they touch
  disk. Metadata (account label, scopes, expiry) stays queryable.
* Authorization sessions are process-local, single-use, and expire after
  ``SESSION_TTL`` seconds. They never leave memory and are never logged.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import secrets
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins_system.auth import CredentialEncryption

logger = logging.getLogger("IntegrationStore")

SESSION_TTL = 600.0  # 10 minutes
HISTORY_LIMIT = 400  # bounded audit trail (no secrets, ever)
REDACT_PATTERN = re.compile(
    r"(?i)(access_token|refresh_token|client_secret|token|authorization)\s*[:=]\s*\S+"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_detail(detail: Optional[str]) -> Optional[str]:
    if not detail:
        return None
    text = REDACT_PATTERN.sub(lambda m: f"{m.group(1)}=<redacted>", str(detail))
    return text[:300]


def connection_health(
    conn: OAuthConnection,
    spec: Any = None,
    *,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Derived health for one connection. Never contains token material."""
    moment = now if now is not None else time.time()
    expires_at = conn.expires_at
    expires_in = int(float(expires_at) - moment) if expires_at else None
    expired = bool(expires_at and moment >= float(expires_at))
    connected = conn.status == "connected" and bool(conn.access_token)
    has_refresh = bool(conn.refresh_token)
    auto_refresh = bool(spec is not None and spec.refresh and has_refresh)
    return {
        "status": conn.status,
        "connected": connected,
        "healthy": bool(connected and not expired),
        "expires_at": expires_at,
        "expires_in": expires_in,
        "expiring_soon": bool(expires_in is not None and 0 <= expires_in <= 900),
        "expired": expired,
        "has_refresh_token": has_refresh,
        "auto_refresh": auto_refresh,
        "needs_reconnect": bool((not connected) or (expired and not auto_refresh)),
        "last_refreshed_at": conn.last_refreshed_at,
        "last_error": conn.last_error,
    }


@dataclass
class OAuthConnection:
    """A live (decrypted, in-memory only) account link."""

    user_id: str
    plugin_id: str
    provider_group: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    scopes: List[str] = field(default_factory=list)
    expires_at: Optional[float] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    account_email: Optional[str] = None
    workspace_name: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)
    status: str = "connected"
    last_error: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    last_refreshed_at: Optional[str] = None

    # ------------------------------------------------------------------ state

    def is_expired(self, skew_seconds: int = 60) -> bool:
        if not self.expires_at:
            return False
        return time.time() >= (float(self.expires_at) - skew_seconds)

    def is_usable(self) -> bool:
        return self.status == "connected" and bool(self.access_token)

    def touch(self) -> None:
        self.updated_at = _now_iso()

    def public(self) -> Dict[str, Any]:
        """Frontend-safe view. Tokens are never included."""
        return {
            "plugin_id": self.plugin_id,
            "provider_group": self.provider_group,
            "status": self.status,
            "account": {
                "id": self.account_id,
                "name": self.account_name,
                "email": self.account_email,
                "workspace": self.workspace_name,
            },
            "scopes": list(self.scopes),
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_refreshed_at": self.last_refreshed_at,
            "last_error": self.last_error,
            "has_refresh_token": bool(self.refresh_token),
            "token_type": self.token_type,
        }

    def secrets(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "extra": dict(self.extra),
        }

    def apply_secrets(self, payload: Dict[str, Any]) -> None:
        self.access_token = str(payload.get("access_token") or "")
        refresh = payload.get("refresh_token")
        self.refresh_token = str(refresh) if refresh else None
        extra = payload.get("extra")
        self.extra = {str(k): str(v) for k, v in (extra or {}).items() if v not in (None, "")}

    def metadata(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "plugin_id": self.plugin_id,
            "provider_group": self.provider_group,
            "token_type": self.token_type,
            "scopes": list(self.scopes),
            "expires_at": self.expires_at,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "account_email": self.account_email,
            "workspace_name": self.workspace_name,
            "status": self.status,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_refreshed_at": self.last_refreshed_at,
        }


@dataclass
class AuthSession:
    """Short-lived authorization attempt bound to one user/plugin."""

    state: str
    user_id: str
    plugin_id: str
    provider_group: str
    code_verifier: str
    redirect_uri: str
    return_to: str
    popup: bool
    created_at: float
    expires_at: float
    nonce: Optional[str] = None

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class IntegrationStore:
    def __init__(self, path: str | Path, encryption: CredentialEncryption) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._encryption = encryption
        self._connections: Dict[str, OAuthConnection] = {}
        self._sessions: Dict[str, AuthSession] = {}
        self._history: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._load()

    # ------------------------------------------------------------------ keys

    @staticmethod
    def key(user_id: str, plugin_id: str) -> str:
        return f"{user_id}::{plugin_id}"

    # ------------------------------------------------------------- persistence

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("integrations store unreadable (%s): %s", self.path, exc)
            return

        for key, record in (raw.get("connections") or {}).items():
            try:
                blob = base64.b64decode(record["secrets"])
                secrets_payload = self._encryption.decrypt(blob)
                conn = OAuthConnection(
                    user_id=record["user_id"],
                    plugin_id=record["plugin_id"],
                    provider_group=record.get("provider_group", ""),
                    access_token="",
                    refresh_token=None,
                    token_type=record.get("token_type", "Bearer"),
                    scopes=list(record.get("scopes") or []),
                    expires_at=record.get("expires_at"),
                    account_id=record.get("account_id"),
                    account_name=record.get("account_name"),
                    account_email=record.get("account_email"),
                    workspace_name=record.get("workspace_name"),
                    status=record.get("status", "connected"),
                    last_error=record.get("last_error"),
                    created_at=record.get("created_at") or _now_iso(),
                    updated_at=record.get("updated_at") or _now_iso(),
                    last_refreshed_at=record.get("last_refreshed_at"),
                )
                conn.apply_secrets(secrets_payload)
                # A record whose token could not be decrypted must not appear
                # connected: surface it as expired so the user can re-authorize.
                if not conn.access_token:
                    conn.status = "expired"
                self._connections[key] = conn
            except Exception as exc:
                logger.error("could not decrypt integration %s: %s", key, exc)

        for entry in raw.get("history") or []:
            if not isinstance(entry, dict) or not entry.get("plugin_id"):
                continue
            self._history.append(entry)
        self._history = self._history[-HISTORY_LIMIT:]

        logger.info(
            "integrations loaded: %d connection(s), %d history event(s)",
            len(self._connections),
            len(self._history),
        )

    def _persist(self) -> None:
        payload = {
            "version": 2,
            "connections": {},
            "history": self._history[-HISTORY_LIMIT:],
        }
        for key, conn in self._connections.items():
            record = conn.metadata()
            record["secrets"] = base64.b64encode(
                self._encryption.encrypt(conn.secrets())
            ).decode()
            payload["connections"][key] = record

        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # -------------------------------------------------------------- connections

    def get_sync(self, user_id: str, plugin_id: str) -> Optional[OAuthConnection]:
        return self._connections.get(self.key(user_id, plugin_id))

    async def get(self, user_id: str, plugin_id: str) -> Optional[OAuthConnection]:
        return self.get_sync(user_id, plugin_id)

    async def list_for_user(self, user_id: str) -> List[OAuthConnection]:
        return [c for c in self._connections.values() if c.user_id == user_id]

    async def upsert(self, conn: OAuthConnection) -> OAuthConnection:
        """Insert or replace by (user, plugin) - never duplicates a record."""
        async with self._lock:
            existing = self._connections.get(self.key(conn.user_id, conn.plugin_id))
            if existing:
                # Preserve the first-link timestamp; refresh the rest.
                conn.created_at = existing.created_at
            self._connections[self.key(conn.user_id, conn.plugin_id)] = conn
            self._persist()
            return conn

    async def update_status(
        self,
        user_id: str,
        plugin_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        async with self._lock:
            conn = self._connections.get(self.key(user_id, plugin_id))
            if not conn:
                return
            conn.status = status
            conn.last_error = error
            conn.touch()
            self._persist()

    async def delete(self, user_id: str, plugin_id: str) -> bool:
        async with self._lock:
            existed = self._connections.pop(self.key(user_id, plugin_id), None) is not None
            if existed:
                self._persist()
            return existed

    # ------------------------------------------------------------------ history

    async def record_event(
        self,
        user_id: str,
        plugin_id: str,
        action: str,
        *,
        status: str = "ok",
        detail: Optional[str] = None,
        account: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append one sanitized audit event. Tokens are never accepted here."""
        entry = {
            "id": secrets.token_hex(8),
            "at": _now_iso(),
            "timestamp": time.time(),
            "user_id": user_id,
            "plugin_id": plugin_id,
            "action": action,
            "status": status,
            "detail": _safe_detail(detail),
            "account": (str(account)[:160] if account else None),
        }
        async with self._lock:
            self._history.append(entry)
            if len(self._history) > HISTORY_LIMIT:
                self._history = self._history[-HISTORY_LIMIT:]
            self._persist()
        return entry

    def history(
        self,
        user_id: str,
        *,
        plugin_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        capped = max(1, min(int(limit or 50), 200))
        rows = [
            dict(entry)
            for entry in self._history
            if entry.get("user_id") == user_id
            and (plugin_id is None or entry.get("plugin_id") == plugin_id)
        ]
        rows.sort(key=lambda e: e.get("timestamp") or 0, reverse=True)
        return rows[:capped]

    # ----------------------------------------------------------------- sessions

    async def create_session(self, session: AuthSession) -> None:
        async with self._lock:
            self._purge_sessions()
            self._sessions[session.state] = session

    async def pop_session(self, state: str) -> Optional[AuthSession]:
        """Single-use: remove the state entry whether or not it is still valid."""
        async with self._lock:
            self._purge_sessions()
            return self._sessions.pop(state, None)

    def _purge_sessions(self) -> None:
        now = time.time()
        for state in [s for s, sess in self._sessions.items() if sess.expires_at <= now]:
            self._sessions.pop(state, None)

    @staticmethod
    def new_state() -> str:
        return secrets.token_urlsafe(32)
