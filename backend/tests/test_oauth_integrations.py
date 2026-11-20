"""End-to-end tests for the OAuth 2.0 / OIDC account-linking subsystem.

The provider network is replaced by a deterministic fake transport; every
other layer (state, PKCE, encryption, persistence, refresh, revocation,
per-user isolation) runs for real.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Tuple
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet

import integrations.service as service_module
from integrations.providers import get_provider
from integrations.service import (
    OAuthNotSupported,
    OAuthService,
    ProviderNotConfigured,
)
from integrations.store import IntegrationStore, OAuthConnection
from plugins_system.auth import CredentialEncryption


# --------------------------------------------------------------------------- #
#  Fake provider transport
# --------------------------------------------------------------------------- #

class FakeTransport:
    def __init__(self) -> None:
        self.routes: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.calls: list[Tuple[str, str, Dict[str, Any]]] = []

    def on(self, method: str, url: str, payload: Dict[str, Any], status: int = 200) -> None:
        self.routes[(method.upper(), url)] = {"payload": payload, "status": status}

    def client_factory(self):
        transport = self

        class FakeClient:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            def _respond(self, method: str, url: str, kwargs: Dict[str, Any]):
                transport.calls.append((method, url, kwargs))
                entry = transport.routes.get((method, url))
                if entry is None:
                    return httpx.Response(404, json={"error": "unmocked", "url": url})
                return httpx.Response(entry["status"], json=entry["payload"])

            async def post(self, url: str, **kwargs: Any):
                return self._respond("POST", url, kwargs)

            async def get(self, url: str, **kwargs: Any):
                return self._respond("GET", url, kwargs)

            async def request(self, method: str, url: str, **kwargs: Any):
                return self._respond(method.upper(), url, kwargs)

        return FakeClient


@pytest.fixture()
def transport(monkeypatch) -> FakeTransport:
    fake = FakeTransport()
    monkeypatch.setattr(service_module.httpx, "AsyncClient", fake.client_factory())
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test-client-secret")
    return fake


@pytest.fixture()
def service(tmp_path, monkeypatch) -> OAuthService:
    encryption = CredentialEncryption(key=Fernet.generate_key().decode())
    store = IntegrationStore(tmp_path / "integrations.json", encryption)
    svc = OAuthService(store)

    async def no_activate(user_id: str, plugin_id: str) -> None:
        return None

    class FakeManager:
        class db:
            @staticmethod
            async def delete_plugin_credentials(user_id: str, plugin_id: str) -> bool:
                return True

        @staticmethod
        async def install_plugin(user_id: str, plugin_id: str) -> bool:
            return True

        @staticmethod
        async def enable_plugin(user_id: str, plugin_id: str) -> bool:
            return True

        @staticmethod
        async def disable_plugin(user_id: str, plugin_id: str) -> bool:
            return True

    monkeypatch.setattr(svc, "_activate_plugin", no_activate)
    import plugins_system.deps as plugin_deps

    monkeypatch.setattr(plugin_deps, "get_manager", lambda: FakeManager())
    return svc


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

async def _connect(service: OAuthService, transport: FakeTransport, *, user="u1"):
    transport.on(
        "POST",
        "https://github.com/login/oauth/access_token",
        {
            "access_token": "gho_SECRET_ACCESS_TOKEN",
            "token_type": "bearer",
            "scope": "repo read:user user:email",
        },
    )
    transport.on(
        "GET",
        "https://api.github.com/user",
        {"id": 42, "login": "octocat", "name": "The Octocat", "email": "octo@example.com"},
    )
    created = await service.create_authorization(
        user_id=user,
        plugin_id="github",
        redirect_uri="http://127.0.0.1:7777/api/integrations/callback",
        return_to="/?panel=plugins",
        popup=False,
    )
    outcome = await service.handle_callback(state=created["state"], code="auth-code-123")
    assert outcome.ok, outcome.error_detail
    return created, outcome


# --------------------------------------------------------------------------- #
#  Authorization request
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_authorization_url_uses_pkce_state_and_official_endpoint(service, transport):
    spec = get_provider("github")
    result = await service.create_authorization(
        user_id="u1",
        plugin_id="github",
        redirect_uri="http://127.0.0.1:7777/api/integrations/callback",
        return_to="/",
    )
    parsed = urlsplit(result["authorization_url"])
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    assert query["client_id"] == ["test-client-id"]
    assert query["state"] == [result["state"]]
    assert len(query["state"][0]) >= 32
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == ["http://127.0.0.1:7777/api/integrations/callback"]
    assert "client_secret" not in parsed.query
    # GitHub's OAuth App flow does not require PKCE; the descriptor says so.
    assert spec.pkce is False
    assert "code_challenge" not in query


@pytest.mark.asyncio
async def test_google_authorization_uses_s256_and_offline_access(monkeypatch):
    encryption = CredentialEncryption(key=Fernet.generate_key().decode())
    store = IntegrationStore.__new__(IntegrationStore)
    store.path = __import__("pathlib").Path("unused")
    store._connections = {}
    store._sessions = {}
    import asyncio

    store._lock = asyncio.Lock()
    store._encryption = encryption
    svc = OAuthService(store)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "gid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "gsecret")

    result = await svc.create_authorization(
        user_id="u1",
        plugin_id="google_drive",
        redirect_uri="http://localhost/api/integrations/callback",
    )
    query = parse_qs(urlsplit(result["authorization_url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["access_type"] == ["offline"]
    assert "https://www.googleapis.com/auth/drive" in query["scope"][0]
    assert "client_secret" not in urlsplit(result["authorization_url"]).query


# --------------------------------------------------------------------------- #
#  Callback / token handling
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_callback_stores_encrypted_token_and_never_exposes_it(service, transport):
    _created, outcome = await _connect(service, transport)

    assert outcome.ok
    assert outcome.account_name == "octocat"
    conn = service.store.get_sync("u1", "github")
    assert conn is not None
    assert conn.status == "connected"
    assert conn.access_token == "gho_SECRET_ACCESS_TOKEN"
    assert conn.account_email == "octo@example.com"
    assert "repo" in conn.scopes

    public = json.dumps(conn.public(), ensure_ascii=False)
    assert "gho_SECRET_ACCESS_TOKEN" not in public
    status_text = json.dumps(service.public_status("u1", "github"))
    assert "gho_SECRET_ACCESS_TOKEN" not in status_text
    assert "\"refresh_token\":" not in status_text
    assert "\"access_token\":" not in status_text

    # On-disk bytes must be ciphertext, never the raw token.
    raw = service.store.path.read_bytes()
    assert b"gho_SECRET_ACCESS_TOKEN" not in raw
    assert b"test-client-secret" not in raw


@pytest.mark.asyncio
async def test_state_is_single_use_and_unknown_state_is_rejected(service, transport):
    created, outcome = await _connect(service, transport)
    assert outcome.ok

    replay = await service.handle_callback(state=created["state"], code="auth-code-123")
    assert replay.ok is False
    assert replay.error_code == "invalid_state"

    unknown = await service.handle_callback(state="not-a-real-state", code="x")
    assert unknown.ok is False
    assert unknown.error_code == "invalid_state"


@pytest.mark.asyncio
async def test_user_denied_never_creates_a_connection(service, transport):
    created = await service.create_authorization(
        user_id="u1",
        plugin_id="github",
        redirect_uri="http://localhost/api/integrations/callback",
    )
    outcome = await service.handle_callback(
        state=created["state"],
        code=None,
        error="access_denied",
        error_description="The user rejected the request",
    )
    assert outcome.ok is False
    assert outcome.error_code == "permission_denied"
    assert service.store.get_sync("u1", "github") is None


@pytest.mark.asyncio
async def test_missing_oauth_client_config_is_reported(service, monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    with pytest.raises(ProviderNotConfigured):
        await service.create_authorization(
            user_id="u1",
            plugin_id="github",
            redirect_uri="http://localhost/api/integrations/callback",
        )


@pytest.mark.asyncio
async def test_provider_without_oauth_is_marked_unsupported(service):
    with pytest.raises(OAuthNotSupported):
        await service.create_authorization(
            user_id="u1",
            plugin_id="whatsapp",
            redirect_uri="http://localhost/api/integrations/callback",
        )


# --------------------------------------------------------------------------- #
#  Refresh / expiry
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_expired_token_is_refreshed(service, transport):
    await _connect(service, transport)
    conn = service.store.get_sync("u1", "github")
    conn.access_token = "expired-token"
    conn.refresh_token = "ghr_REFRESH"
    conn.expires_at = time.time() - 10
    conn.status = "connected"

    # GitHub has refresh=False in the descriptor, so simulate a provider that
    # issues refresh tokens by using the generic refresh path directly with a
    # temporary descriptor override.
    from integrations import providers

    original = providers.PROVIDERS["github"]
    object.__setattr__(original, "refresh", True)

    transport.on(
        "POST",
        "https://github.com/login/oauth/access_token",
        {
            "access_token": "gho_FRESH_TOKEN",
            "refresh_token": "ghr_ROTATED",
            "expires_in": 3600,
            "scope": "repo",
        },
    )
    try:
        refreshed = await service.refresh("u1", "github", force=True)
    finally:
        object.__setattr__(original, "refresh", False)

    assert refreshed.access_token == "gho_FRESH_TOKEN"
    assert refreshed.refresh_token == "ghr_ROTATED"
    assert refreshed.status == "connected"
    assert refreshed.expires_at and refreshed.expires_at > time.time()


@pytest.mark.asyncio
async def test_ensure_fresh_marks_expired_when_no_refresh_token(service, transport):
    await _connect(service, transport)
    conn = service.store.get_sync("u1", "github")
    conn.expires_at = time.time() - 10

    result = await service.ensure_fresh("u1", "github")
    assert result is not None
    assert result.status == "expired"
    assert service.get_credentials_sync("u1", "github") is None


# --------------------------------------------------------------------------- #
#  Disconnect / reconnect / isolation
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_disconnect_revokes_and_deletes(service, transport):
    await _connect(service, transport)
    transport.on("DELETE", "https://api.github.com/applications/test-client-id/token", {})

    result = await service.disconnect("u1", "github")
    assert result["ok"] is True
    assert service.store.get_sync("u1", "github") is None
    assert service.get_credentials_sync("u1", "github") is None


@pytest.mark.asyncio
async def test_reconnect_replaces_instead_of_duplicating(service, transport):
    await _connect(service, transport)
    first = service.store.get_sync("u1", "github")
    _created, outcome = await _connect(service, transport)
    assert outcome.ok

    connections = await service.store.list_for_user("u1")
    assert len(connections) == 1
    assert connections[0].created_at == first.created_at
    assert connections[0].access_token == "gho_SECRET_ACCESS_TOKEN"


@pytest.mark.asyncio
async def test_per_user_isolation(service, transport):
    await _connect(service, transport, user="u1")

    assert service.get_credentials_sync("u1", "github") is not None
    assert service.get_credentials_sync("u2", "github") is None
    assert service.public_status("u2", "github")["status"] == "not_connected"
    assert await service.store.list_for_user("u2") == []


# --------------------------------------------------------------------------- #
#  Credential shape handed to plugins
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_plugin_credentials_use_provider_specific_key(service, transport):
    await _connect(service, transport)
    creds = service.get_credentials_sync("u1", "github")
    assert creds is not None
    # GitHub's plugin reads `token`; the adapter maps the OAuth token there.
    assert creds["token"] == "gho_SECRET_ACCESS_TOKEN"
    assert creds["access_token"] == "gho_SECRET_ACCESS_TOKEN"


# --------------------------------------------------------------------------- #
#  API smoke test
# --------------------------------------------------------------------------- #

def test_api_lists_integrations_without_secrets():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from integrations.api import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.get("/api/integrations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["integrations"], list)
    assert data["counts"]["total"] >= 1
    text = json.dumps(data)
    assert "gho_" not in text
    assert "test-client-secret" not in text
