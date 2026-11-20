"""
OAuth 2.0 Authorization Code flow with PKCE, OIDC support, refresh and
revocation.

Design guarantees enforced here:

* ``state`` is 256 bits of entropy, single-use, bound to (user, plugin), and
  expires after ten minutes.
* PKCE uses S256 and is enabled for every provider that advertises it.
* The authorization code is exchanged server-side only.
* Tokens are encrypted before persistence and never serialized into API
  responses, redirect URLs, logs, or the model context.
* A second authorization for the same (user, plugin) replaces the existing
  connection instead of creating a duplicate.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode, urlsplit

import httpx

from integrations.providers import ProviderSpec, get_provider
from integrations.store import AuthSession, IntegrationStore, OAuthConnection, SESSION_TTL

logger = logging.getLogger("OAuthService")

USER_AGENT = "WormGPT-Ultra/4.0 (+integration-auth)"
TIMEOUT = httpx.Timeout(45.0, connect=20.0)

_SENSITIVE_PATTERN = re.compile(
    r"(access_token|refresh_token|client_secret|code_verifier|authorization)\s*[=:]\s*[^&\s,}]+",
    re.IGNORECASE,
)


class OAuthError(Exception):
    """Base class for authorization failures."""

    code = "oauth_error"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class OAuthNotSupported(OAuthError):
    code = "oauth_not_supported"


class ProviderNotConfigured(OAuthError):
    code = "provider_not_configured"


class AuthorizationStateError(OAuthError):
    code = "invalid_state"


class TokenExchangeError(OAuthError):
    code = "token_exchange_failed"


@dataclass
class CallbackOutcome:
    ok: bool
    plugin_id: str = ""
    provider_group: str = ""
    return_to: str = "/"
    popup: bool = False
    account_name: str = ""
    error_code: str = ""
    error_detail: str = ""
    connection: Optional[Dict[str, Any]] = None


def _scrub(value: Any) -> str:
    text = str(value or "")
    text = _SENSITIVE_PATTERN.sub(r"\1=***", text)
    return text[:400]


def _dig(payload: Any, path: str) -> Any:
    if not path:
        return None
    current = payload
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if current is None:
            return None
    return current


def _pkce_pair() -> Tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def safe_return_to(return_to: Optional[str]) -> str:
    """Only allow same-origin relative paths (open-redirect protection)."""
    candidate = (return_to or "/").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    parts = urlsplit(candidate)
    if parts.scheme or parts.netloc:
        return "/"
    return candidate or "/"


class OAuthService:
    def __init__(self, store: IntegrationStore) -> None:
        self.store = store
        self._refresh_locks: Dict[str, asyncio.Lock] = {}

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def provider(plugin_id: str) -> Optional[ProviderSpec]:
        return get_provider(plugin_id)

    def _lock_for(self, user_id: str, plugin_id: str) -> asyncio.Lock:
        key = IntegrationStore.key(user_id, plugin_id)
        lock = self._refresh_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._refresh_locks[key] = lock
        return lock

    async def audit(
        self,
        user_id: str,
        plugin_id: str,
        action: str,
        *,
        status: str = "ok",
        detail: Optional[str] = None,
        account: Optional[str] = None,
    ) -> None:
        """Public wrapper used by the API layer for test/other events."""
        await self._audit(
            user_id,
            plugin_id,
            action,
            status=status,
            detail=detail,
            account=account,
        )

    async def _audit(
        self,
        user_id: str,
        plugin_id: str,
        action: str,
        *,
        status: str = "ok",
        detail: Optional[str] = None,
        account: Optional[str] = None,
    ) -> None:
        """Best-effort audit trail: never breaks the OAuth flow."""
        try:
            await self.store.record_event(
                user_id,
                plugin_id,
                action,
                status=status,
                detail=detail,
                account=account,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("audit write failed: %s", exc)

    # ------------------------------------------------------------- authorization

    async def create_authorization(
        self,
        *,
        user_id: str,
        plugin_id: str,
        redirect_uri: str,
        return_to: str = "/",
        popup: bool = False,
    ) -> Dict[str, Any]:
        spec = get_provider(plugin_id)
        if not spec:
            raise OAuthNotSupported(
                f"'{plugin_id}' does not expose an official OAuth 2.0 flow."
            )
        missing = spec.missing_config()
        if missing:
            raise ProviderNotConfigured(
                "OAuth client is not configured. Set: " + ", ".join(missing)
            )

        state = self.store.new_state()
        verifier, challenge = ("", "")
        if spec.pkce:
            verifier, challenge = _pkce_pair()
        nonce = secrets.token_urlsafe(24) if spec.oidc else None

        now = time.time()
        session = AuthSession(
            state=state,
            user_id=user_id,
            plugin_id=plugin_id,
            provider_group=spec.group,
            code_verifier=verifier,
            redirect_uri=redirect_uri,
            return_to=safe_return_to(return_to),
            popup=bool(popup),
            created_at=now,
            expires_at=now + SESSION_TTL,
            nonce=nonce,
        )
        await self.store.create_session(session)

        params: Dict[str, str] = {
            spec.client_id_param: spec.client_id(),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        if spec.scopes:
            params[spec.scope_param] = spec.scope_separator.join(spec.scopes)
        if spec.pkce:
            params["code_challenge"] = challenge
            params["code_challenge_method"] = "S256"
        if nonce:
            params["nonce"] = nonce
        params.update({k: str(v) for k, v in spec.authorize_extra.items()})

        url = f"{spec.authorization_endpoint}?{urlencode(params)}"
        return {
            "authorization_url": url,
            "state": state,
            "expires_at": session.expires_at,
            "provider": spec.public(),
        }

    async def handle_callback(
        self,
        *,
        state: Optional[str],
        code: Optional[str],
        error: Optional[str] = None,
        error_description: Optional[str] = None,
    ) -> CallbackOutcome:
        if not state:
            return CallbackOutcome(
                ok=False, error_code="invalid_state", error_detail="Missing state."
            )

        session = await self.store.pop_session(state)
        if session is None:
            return CallbackOutcome(
                ok=False,
                error_code="invalid_state",
                error_detail="Authorization session is unknown, expired, or already used.",
            )

        outcome = CallbackOutcome(
            ok=False,
            plugin_id=session.plugin_id,
            provider_group=session.provider_group,
            return_to=session.return_to,
            popup=session.popup,
        )

        if session.is_expired():
            outcome.error_code = "expired_state"
            outcome.error_detail = "Authorization session expired. Start again."
            await self._audit(
                session.user_id,
                session.plugin_id,
                "authorization_expired",
                status="error",
                detail=outcome.error_detail,
            )
            return outcome

        if error:
            denied = str(error) in {"access_denied", "user_denied", "consent_required"}
            outcome.error_code = "permission_denied" if denied else str(error)
            outcome.error_detail = _scrub(error_description or error)
            await self._audit(
                session.user_id,
                session.plugin_id,
                "permission_denied" if denied else "authorization_failed",
                status="error",
                detail=outcome.error_detail,
            )
            return outcome

        if not code:
            outcome.error_code = "missing_code"
            outcome.error_detail = "The provider did not return an authorization code."
            await self._audit(
                session.user_id,
                session.plugin_id,
                "missing_code",
                status="error",
                detail=outcome.error_detail,
            )
            return outcome

        spec = get_provider(session.plugin_id)
        if not spec:
            outcome.error_code = "oauth_not_supported"
            outcome.error_detail = "Provider descriptor disappeared."
            return outcome
        if spec.missing_config():
            outcome.error_code = "provider_not_configured"
            outcome.error_detail = "OAuth client credentials are missing."
            return outcome

        try:
            tokens = await self._exchange_code(
                spec=spec,
                code=code,
                redirect_uri=session.redirect_uri,
                code_verifier=session.code_verifier,
            )
            userinfo = await self._fetch_userinfo(spec, tokens)
            account = self._extract_account(spec, tokens, userinfo)
            extra = await self._finalize(spec, tokens, userinfo, account)
        except OAuthError as exc:
            outcome.error_code = exc.code
            outcome.error_detail = _scrub(exc)
            await self._audit(
                session.user_id,
                session.plugin_id,
                "token_exchange_failed",
                status="error",
                detail=outcome.error_detail,
            )
            return outcome
        except Exception as exc:  # never leak a stack trace to the browser
            logger.exception("OAuth callback crashed for %s", session.plugin_id)
            outcome.error_code = "authorization_failed"
            outcome.error_detail = _scrub(f"{type(exc).__name__}: {exc}")
            await self._audit(
                session.user_id,
                session.plugin_id,
                "authorization_failed",
                status="error",
                detail=outcome.error_detail,
            )
            return outcome

        scopes = self._extract_scopes(spec, tokens)
        expires_in = tokens.get("expires_in")
        expires_at = None
        if expires_in is not None:
            try:
                expires_at = time.time() + float(expires_in)
            except (TypeError, ValueError):
                expires_at = None

        connection = OAuthConnection(
            user_id=session.user_id,
            plugin_id=session.plugin_id,
            provider_group=spec.group,
            access_token=str(tokens.get("access_token") or ""),
            refresh_token=(str(tokens["refresh_token"]) if tokens.get("refresh_token") else None),
            token_type=str(tokens.get("token_type") or "Bearer"),
            scopes=scopes,
            expires_at=expires_at,
            account_id=_stringify(account.get("id")),
            account_name=_stringify(account.get("name")),
            account_email=_stringify(account.get("email")),
            workspace_name=_stringify(account.get("workspace")),
            extra=extra,
            status="connected",
            last_error=_stringify(account.get("warning")),
        )
        if not connection.access_token:
            outcome.error_code = "authorization_failed"
            outcome.error_detail = "The provider did not return an access token."
            await self._audit(
                session.user_id,
                session.plugin_id,
                "authorization_failed",
                status="error",
                detail=outcome.error_detail,
            )
            return outcome

        previous = self.store.get_sync(session.user_id, session.plugin_id)
        await self.store.upsert(connection)
        await self._activate_plugin(session.user_id, session.plugin_id)
        await self._audit(
            session.user_id,
            session.plugin_id,
            "reconnect" if previous else "connect",
            status="ok",
            account=connection.account_name or connection.account_email,
            detail=f"scopes={','.join(scopes) or 'default'}",
        )

        outcome.ok = True
        outcome.account_name = connection.account_name or connection.account_email or ""
        outcome.connection = connection.public()
        logger.info(
            "OAuth connected plugin=%s user=%s account=%s scopes=%s",
            session.plugin_id,
            session.user_id,
            outcome.account_name or "unknown",
            ",".join(scopes) or "default",
        )
        return outcome

    # ------------------------------------------------------------- code exchange

    async def _exchange_code(
        self,
        *,
        spec: ProviderSpec,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> Dict[str, Any]:
        data: Dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        client_id = spec.client_id()
        client_secret = spec.client_secret()
        auth: Optional[Tuple[str, str]] = None

        if spec.token_auth == "basic":
            auth = (client_id, client_secret)
        elif spec.token_auth == "post":
            data[spec.token_client_id_field] = client_id
            if client_secret:
                data[spec.token_client_secret_field] = client_secret
        else:  # public client
            data[spec.token_client_id_field] = client_id

        if spec.pkce and code_verifier:
            data["code_verifier"] = code_verifier
        data.update({k: str(v) for k, v in spec.token_extra.items()})

        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
                resp = await client.post(
                    spec.token_endpoint, data=data, auth=auth, headers=headers
                )
        except httpx.HTTPError as exc:
            raise TokenExchangeError(f"Token endpoint unreachable: {_scrub(exc)}") from exc

        payload = self._parse_token_response(resp)
        if resp.status_code >= 400 or payload.get("error"):
            code_val = str(payload.get("error") or f"http_{resp.status_code}")
            desc = payload.get("error_description") or payload.get("error_message") or ""
            raise TokenExchangeError(
                f"Provider rejected the code ({code_val}). {_scrub(desc)}".strip(),
                code="permission_denied" if code_val in {"access_denied", "invalid_scope"} else "token_exchange_failed",
            )

        if not (payload.get("access_token") or payload.get("token")):
            raise TokenExchangeError("Token response contained no access token.")
        if payload.get("token"):
            payload["access_token"] = payload["token"]
        return payload

    @staticmethod
    def _parse_token_response(resp: httpx.Response) -> Dict[str, Any]:
        content_type = (resp.headers.get("content-type") or "").lower()
        if "json" in content_type:
            try:
                data = resp.json()
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        body = (resp.text or "").strip()
        if body.startswith("{"):
            try:
                import json

                data = json.loads(body)
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        # application/x-www-form-urlencoded fallback (older GitHub/Reddit)
        try:
            from urllib.parse import parse_qs

            return {k: v[0] for k, v in parse_qs(body).items() if v}
        except Exception:
            return {}

    @staticmethod
    def _extract_scopes(spec: ProviderSpec, tokens: Dict[str, Any]) -> List[str]:
        raw = tokens.get("scope") or tokens.get("scopes")
        if isinstance(raw, str):
            parts = [p for p in re.split(r"[\s,]+", raw) if p]
            return parts
        if isinstance(raw, list):
            return [str(p) for p in raw if p]
        return list(spec.scopes)

    # ----------------------------------------------------------------- userinfo

    async def _fetch_userinfo(
        self, spec: ProviderSpec, tokens: Dict[str, Any]
    ) -> Dict[str, Any]:
        if spec.account_source == "token":
            return tokens
        if not spec.userinfo_endpoint:
            return {}

        headers = {
            "Authorization": f"Bearer {tokens.get('access_token')}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        headers.update(spec.userinfo_headers)

        # Some providers (e.g. HubSpot) expose identity at a token-in-path URL.
        endpoint = spec.userinfo_endpoint.replace(
            "{access_token}", str(tokens.get("access_token") or "")
        )

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                if spec.userinfo_method.upper() == "POST":
                    if spec.userinfo_body is not None:
                        resp = await client.post(
                            endpoint, headers=headers, json=spec.userinfo_body
                        )
                    else:
                        resp = await client.post(endpoint, headers=headers)
                else:
                    resp = await client.get(endpoint, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("userinfo request failed for %s: %s", spec.plugin_id, _scrub(exc))
            return {}

        if resp.status_code >= 400:
            logger.warning(
                "userinfo returned HTTP %s for %s", resp.status_code, spec.plugin_id
            )
            return {}
        try:
            payload = resp.json()
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _extract_account(
        self,
        spec: ProviderSpec,
        tokens: Dict[str, Any],
        userinfo: Dict[str, Any],
    ) -> Dict[str, Any]:
        source = userinfo or tokens
        account = {
            "id": _dig(source, spec.account_id_path),
            "name": _dig(source, spec.account_name_path),
            "email": _dig(source, spec.account_email_path),
            "workspace": _dig(source, spec.account_workspace_path),
            "warning": None,
        }
        if not account["name"]:
            account["name"] = account["email"] or account["id"]
        return account

    # ------------------------------------------------------- provider finalizers

    async def _finalize(
        self,
        spec: ProviderSpec,
        tokens: Dict[str, Any],
        userinfo: Dict[str, Any],
        account: Dict[str, Any],
    ) -> Dict[str, str]:
        """Discover capability identifiers some plugins need (page id, cloud id)."""
        extra: Dict[str, str] = {}
        token = tokens.get("access_token")
        headers = {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}

        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            if spec.plugin_id == "facebook":
                try:
                    resp = await client.get(
                        "https://graph.facebook.com/v19.0/me/accounts",
                        headers=headers,
                        params={"fields": "id,name,access_token"},
                    )
                    pages = (resp.json() or {}).get("data") or []
                    if pages:
                        page = pages[0]
                        extra["page_id"] = str(page.get("id") or "")
                        extra["page_token"] = str(page.get("access_token") or "")
                        account["name"] = page.get("name") or account.get("name")
                        account["id"] = page.get("id") or account.get("id")
                    else:
                        account["warning"] = (
                            "No Facebook Page is available for this account; "
                            "Page publishing tools will fail until one is granted."
                        )
                except Exception as exc:
                    logger.warning("facebook page discovery failed: %s", _scrub(exc))

            elif spec.plugin_id == "instagram":
                try:
                    resp = await client.get(
                        "https://graph.facebook.com/v19.0/me/accounts",
                        headers=headers,
                        params={
                            "fields": "id,name,instagram_business_account{id,username}"
                        },
                    )
                    for page in (resp.json() or {}).get("data") or []:
                        ig = page.get("instagram_business_account") or {}
                        if ig.get("id"):
                            extra["ig_user_id"] = str(ig["id"])
                            account["name"] = ig.get("username") or account.get("name")
                            account["id"] = str(ig["id"])
                            break
                    if "ig_user_id" not in extra:
                        account["warning"] = (
                            "No Instagram Business account is linked to a Facebook Page."
                        )
                except Exception as exc:
                    logger.warning("instagram discovery failed: %s", _scrub(exc))

            elif spec.plugin_id == "threads":
                uid = account.get("id")
                if uid:
                    extra["threads_user_id"] = str(uid)

            elif spec.plugin_id == "jira":
                try:
                    resp = await client.get(
                        "https://api.atlassian.com/oauth/token/accessible-resources",
                        headers=headers,
                    )
                    resources = resp.json() or []
                    if isinstance(resources, list) and resources:
                        site = resources[0]
                        extra["cloud_id"] = str(site.get("id") or "")
                        extra["site_url"] = str(site.get("url") or "")
                        host = urlsplit(extra["site_url"]).hostname or ""
                        if host.endswith(".atlassian.net"):
                            extra["domain"] = host[: -len(".atlassian.net")]
                        account["workspace"] = site.get("name") or account.get("workspace")
                        account["name"] = (
                            account.get("name")
                            or site.get("name")
                            or extra.get("domain")
                        )
                except Exception as exc:
                    logger.warning("jira accessible-resources failed: %s", _scrub(exc))

            elif spec.plugin_id == "tiktok":
                # userinfo already carries data.user.*; nothing extra required.
                pass

        # Declarative extra credentials (e.g. Salesforce instance_url) may live
        # in either the userinfo document or the token response.
        for key, path in spec.extra_credentials.items():
            value = _dig(userinfo, path)
            if value in (None, ""):
                value = _dig(tokens, path)
            if value not in (None, ""):
                extra[key] = str(value)

        return {k: v for k, v in extra.items() if v}

    # ------------------------------------------------------------------ refresh

    async def ensure_fresh(
        self, user_id: str, plugin_id: str, *, skew_seconds: int = 60
    ) -> Optional[OAuthConnection]:
        connection = self.store.get_sync(user_id, plugin_id)
        if not connection:
            return None

        if connection.status == "connected" and not connection.is_expired(skew_seconds):
            return connection

        spec = get_provider(plugin_id)
        if not spec or not spec.refresh or not connection.refresh_token:
            if connection.is_expired(skew_seconds) and connection.status == "connected":
                await self.store.update_status(
                    user_id, plugin_id, "expired", "Access token expired; reconnect required."
                )
                await self._audit(
                    user_id,
                    plugin_id,
                    "expired",
                    status="warn",
                    detail="Access token expired and no refresh token is available.",
                )
            return connection

        try:
            return await self.refresh(user_id, plugin_id, force=True)
        except Exception as exc:
            logger.warning(
                "token refresh failed for %s/%s: %s", user_id, plugin_id, _scrub(exc)
            )
            return self.store.get_sync(user_id, plugin_id)

    async def refresh(
        self, user_id: str, plugin_id: str, *, force: bool = False
    ) -> OAuthConnection:
        spec = get_provider(plugin_id)
        if not spec:
            raise OAuthNotSupported("No provider descriptor for this plugin.")
        if not spec.refresh:
            raise OAuthError("This provider does not issue refresh tokens.", code="no_refresh")

        lock = self._lock_for(user_id, plugin_id)
        async with lock:
            connection = self.store.get_sync(user_id, plugin_id)
            if not connection:
                raise OAuthError("No connection to refresh.", code="not_connected")
            if not connection.refresh_token:
                await self.store.update_status(
                    user_id, plugin_id, "expired", "No refresh token was issued."
                )
                await self._audit(
                    user_id,
                    plugin_id,
                    "refresh_failed",
                    status="error",
                    detail="No refresh token was issued.",
                )
                raise OAuthError("No refresh token stored.", code="no_refresh")
            if not force and connection.status == "connected" and not connection.is_expired():
                return connection

            data: Dict[str, str] = {
                "grant_type": "refresh_token",
                "refresh_token": connection.refresh_token,
            }
            client_id = spec.client_id()
            client_secret = spec.client_secret()
            auth: Optional[Tuple[str, str]] = None
            if spec.token_auth == "basic":
                auth = (client_id, client_secret)
            elif spec.token_auth == "post":
                data[spec.token_client_id_field] = client_id
                if client_secret:
                    data[spec.token_client_secret_field] = client_secret
            else:
                data[spec.token_client_id_field] = client_id
            data.update({k: str(v) for k, v in spec.token_extra.items()})

            try:
                async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
                    resp = await client.post(
                        spec.token_endpoint,
                        data=data,
                        auth=auth,
                        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                    )
            except httpx.HTTPError as exc:
                await self.store.update_status(
                    user_id, plugin_id, "expired", "Refresh endpoint unreachable."
                )
                await self._audit(
                    user_id,
                    plugin_id,
                    "refresh_failed",
                    status="error",
                    detail=f"Refresh endpoint unreachable: {_scrub(exc)}",
                )
                raise OAuthError(f"Refresh endpoint unreachable: {_scrub(exc)}") from exc

            payload = self._parse_token_response(resp)
            if resp.status_code >= 400 or payload.get("error"):
                err = str(payload.get("error") or f"http_{resp.status_code}")
                await self.store.update_status(
                    user_id,
                    plugin_id,
                    "expired",
                    f"Refresh rejected ({err}). Reconnect required.",
                )
                await self._audit(
                    user_id,
                    plugin_id,
                    "refresh_failed",
                    status="error",
                    detail=f"Refresh rejected ({err}).",
                )
                raise OAuthError(
                    f"Refresh rejected ({err}).",
                    code="refresh_rejected",
                )

            access = payload.get("access_token") or payload.get("token")
            if not access:
                await self.store.update_status(
                    user_id, plugin_id, "expired", "Refresh returned no access token."
                )
                await self._audit(
                    user_id,
                    plugin_id,
                    "refresh_failed",
                    status="error",
                    detail="Refresh returned no access token.",
                )
                raise OAuthError("Refresh returned no access token.")

            connection.access_token = str(access)
            if payload.get("refresh_token"):
                connection.refresh_token = str(payload["refresh_token"])
            if payload.get("token_type"):
                connection.token_type = str(payload["token_type"])
            scopes = self._extract_scopes(spec, payload)
            if scopes:
                connection.scopes = scopes
            expires_in = payload.get("expires_in")
            if expires_in is not None:
                try:
                    connection.expires_at = time.time() + float(expires_in)
                except (TypeError, ValueError):
                    pass
            connection.status = "connected"
            connection.last_error = None
            connection.last_refreshed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            connection.touch()
            await self.store.upsert(connection)
            await self._audit(
                user_id,
                plugin_id,
                "refresh",
                status="ok",
                account=connection.account_name or connection.account_email,
                detail="Access token refreshed automatically.",
            )
            logger.info("OAuth token refreshed for plugin=%s user=%s", plugin_id, user_id)
            return connection

    # ---------------------------------------------------------------- disconnect

    async def disconnect(self, user_id: str, plugin_id: str) -> Dict[str, Any]:
        connection = self.store.get_sync(user_id, plugin_id)
        if not connection:
            return {"ok": True, "revoked": False, "message": "No active connection."}

        revoked = await self._revoke(connection)
        deleted = await self.store.delete(user_id, plugin_id)

        # Legacy API-key records must not silently take over after disconnect.
        try:
            from plugins_system.deps import get_manager

            manager = get_manager()
            await manager.disable_plugin(user_id, plugin_id)
            await manager.db.delete_plugin_credentials(user_id, plugin_id)
        except Exception as exc:
            logger.debug("post-disconnect plugin cleanup failed: %s", _scrub(exc))

        await self._audit(
            user_id,
            plugin_id,
            "disconnect",
            status="ok" if revoked else "warn",
            account=connection.account_name or connection.account_email,
            detail=(
                "Tokens revoked at the provider and deleted locally."
                if revoked
                else "Deleted locally; the provider does not expose a usable revocation endpoint."
            ),
        )

        return {"ok": True, "revoked": revoked, "deleted": deleted}

    async def _revoke(self, connection: OAuthConnection) -> bool:
        spec = get_provider(connection.plugin_id)
        if not spec:
            return False
        token = connection.access_token
        if not token:
            return False

        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        data: Dict[str, str] = {}
        auth: Optional[Tuple[str, str]] = None
        url = spec.revocation_endpoint or ""
        method = "POST"

        try:
            # Provider-specific documented revocation shapes.
            if spec.plugin_id == "github":
                url = url.format(client_id=spec.client_id())
                method = "DELETE"
                auth = (spec.client_id(), spec.client_secret())
                headers["Accept"] = "application/vnd.github+json"
                data = {"access_token": token}
            elif spec.plugin_id == "slack":
                url = "https://slack.com/api/auth.revoke"
                headers["Authorization"] = f"Bearer {token}"
            elif spec.group == "meta" and not url:
                url = "https://graph.facebook.com/v19.0/me/permissions"
                method = "DELETE"
                headers["Authorization"] = f"Bearer {token}"
            elif spec.plugin_id == "google_drive" or spec.group == "google":
                url = "https://oauth2.googleapis.com/revoke"
                data = {"token": token}
            elif spec.plugin_id == "tiktok":
                data = {
                    "client_key": spec.client_id(),
                    "client_secret": spec.client_secret(),
                    "token": token,
                }
            elif spec.token_auth == "basic" and url:
                auth = (spec.client_id(), spec.client_secret())
                data = {"token": token, "token_type_hint": "access_token"}
            elif url:
                data = {
                    "token": token,
                    "token_type_hint": "access_token",
                    "client_id": spec.client_id(),
                    "client_secret": spec.client_secret(),
                }
            else:
                # No documented revocation endpoint: local deletion still
                # guarantees the token is gone from this system.
                return False

            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
                if method == "DELETE":
                    resp = await client.request(
                        "DELETE", url, headers=headers, auth=auth, json=data or None
                    )
                else:
                    resp = await client.post(url, headers=headers, auth=auth, data=data or None)
            ok = resp.status_code < 400
            if not ok:
                logger.info(
                    "revocation returned HTTP %s for %s",
                    resp.status_code,
                    connection.plugin_id,
                )
            return ok
        except Exception as exc:
            logger.warning("revocation failed for %s: %s", connection.plugin_id, _scrub(exc))
            return False

    # --------------------------------------------------------------- credentials

    def get_credentials_sync(self, user_id: str, plugin_id: str) -> Optional[Dict[str, str]]:
        """
        Resolve the credentials a plugin instance expects.

        Called by the broker *after* ``ensure_fresh``. Returns None rather than a
        stale token when the link is no longer usable.
        """
        connection = self.store.get_sync(user_id, plugin_id)
        if not connection or connection.status != "connected" or not connection.access_token:
            return None
        spec = get_provider(plugin_id)
        if not spec:
            return None

        creds: Dict[str, str] = {
            spec.credential_key: connection.access_token,
            "access_token": connection.access_token,
            "token_type": connection.token_type or "Bearer",
        }
        if connection.refresh_token:
            creds["refresh_token"] = connection.refresh_token
        creds.update(connection.extra)
        if connection.account_id:
            creds["account_id"] = str(connection.account_id)
        if connection.account_name:
            creds["account_name"] = str(connection.account_name)
        return creds

    # ------------------------------------------------------------------- status

    def public_status(self, user_id: str, plugin_id: str) -> Dict[str, Any]:
        spec = get_provider(plugin_id)
        connection = self.store.get_sync(user_id, plugin_id)
        if not spec:
            return {
                "plugin_id": plugin_id,
                "oauth_supported": False,
                "status": "unsupported",
                "configured": False,
            }
        if not connection:
            return {
                "plugin_id": plugin_id,
                "oauth_supported": True,
                "status": "not_connected",
                "configured": spec.is_configured(),
                "provider": spec.public(),
            }
        status = connection.status
        if status == "connected" and connection.is_expired(0):
            status = "expired"
        return {
            "plugin_id": plugin_id,
            "oauth_supported": True,
            "status": status,
            "configured": spec.is_configured(),
            "provider": spec.public(),
            "connection": connection.public(),
        }

    async def _activate_plugin(self, user_id: str, plugin_id: str) -> None:
        try:
            from plugins_system.deps import get_manager

            manager = get_manager()
            await manager.install_plugin(user_id, plugin_id)
            await manager.enable_plugin(user_id, plugin_id)
            # Remove any legacy API key so it cannot shadow OAuth credentials.
            await manager.db.delete_plugin_credentials(user_id, plugin_id)
        except Exception as exc:
            logger.warning("could not activate plugin %s: %s", plugin_id, _scrub(exc))


def _stringify(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_list(values: Iterable[Any]) -> List[str]:
    return [str(v) for v in values if v]
