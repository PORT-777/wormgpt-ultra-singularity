"""One-click plugin connection.

Old flow: user copies an API key/token from the provider's dashboard, pastes it
into the app, then saves.

New flow: user clicks «ربط / Connect». The backend opens the provider's official
site in a managed Chromium window. After the user signs in (or creates an
account) and grants consent, this module captures the credential the provider's
own front-end uses (Authorization header, X-API-Key, or a token in its JSON
responses), stores it encrypted through the normal plugin manager, installs and
enables the plugin. No key is ever pasted into this application.

OAuth-capable plugins use the existing official OAuth redirect instead; the
callback already links the account automatically.
"""
from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException

log = logging.getLogger("Connect")

router = APIRouter(prefix="/api/connect", tags=["connect"])

_sessions: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

# Official account / API-key pages. Fallback is the plugin's website_url.
ONBOARD_URLS: Dict[str, str] = {
    "openai": "https://platform.openai.com/api-keys",
    "claude": "https://console.anthropic.com/settings/keys",
    "gemini": "https://aistudio.google.com/app/apikey",
    "deepseek": "https://platform.deepseek.com/api_keys",
    "mistral": "https://console.mistral.ai/api-keys/",
    "cohere": "https://dashboard.cohere.com/api-keys",
    "perplexity": "https://www.perplexity.ai/settings/api",
    "grok": "https://console.x.ai/",
    "github": "https://github.com/settings/tokens",
    "gitlab": "https://gitlab.com/-/profile/personal_access_tokens",
    "slack": "https://api.slack.com/apps",
    "discord": "https://discord.com/developers/applications",
    "telegram": "https://t.me/BotFather",
    "shodan": "https://account.shodan.io/",
    "virustotal": "https://www.virustotal.com/gui/user/profile/apikey",
    "abuseipdb": "https://www.abuseipdb.com/account/api",
    "greynoise": "https://viz.greynoise.io/account/api-key",
    "hibp": "https://haveibeenpwned.com/API/Key",
    "urlhaus": "https://urlhaus.abuse.ch/api/",
    "misp": "https://misp-project.org/",
    "thehive": "https://github.com/TheHive-Project/TheHive",
    "otx": "https://otx.alienvault.com/settings",
    "nvd": "https://nvd.nist.gov/developers/request-an-api-key",
    "cisa_kev": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
    "malwarebazaar": "https://bazaar.abuse.ch/api/",
    "splunk": "https://www.splunk.com/en_us/free-trial.html",
    "elastic": "https://cloud.elastic.co/login",
    "wazuh": "https://documentation.wazuh.com/",
    "sentinel": "https://portal.azure.com/",
    "graylog": "https://www.graylog.org/products/open-source",
    "datadog": "https://app.datadoghq.com/organization-settings/api-keys",
    "sentry": "https://sentry.io/settings/account/api/auth-tokens/",
    "vercel": "https://vercel.com/account/tokens",
    "jenkins": "https://www.jenkins.io/doc/book/security/",
    "aws": "https://console.aws.amazon.com/iamv2/home#/users",
    "azure": "https://portal.azure.com/",
    "cloudflare": "https://dash.cloudflare.com/profile/api-tokens",
    "digitalocean": "https://cloud.digitalocean.com/account/api/tokens",
    "google_calendar": "https://console.cloud.google.com/apis/credentials",
    "google_drive": "https://console.cloud.google.com/apis/credentials",
    "google_sheets": "https://console.cloud.google.com/apis/credentials",
    "notion": "https://www.notion.so/profile/integrations",
    "airtable": "https://airtable.com/create/tokens",
    "asana": "https://app.asana.com/0/my-apps",
    "clickup": "https://app.clickup.com/settings/apps",
    "dropbox": "https://www.dropbox.com/developers/apps",
    "jira": "https://id.atlassian.com/manage-profile/security/api-tokens",
    "linear": "https://linear.app/settings/api",
    "monday": "https://monday.com/developers",
    "obsidian": "https://obsidian.md/",
    "trello": "https://trello.com/power-ups/admin",
    "hubspot": "https://app.hubspot.com/",
    "salesforce": "https://login.salesforce.com/",
    "twilio": "https://console.twilio.com/",
    "sendgrid": "https://app.sendgrid.com/settings/api_keys",
    "pushover": "https://pushover.net/apps/build",
    "email": "https://myaccount.google.com/security",
    "matrix": "https://matrix.org/",
    "zoom": "https://marketplace.zoom.us/",
    "facebook": "https://developers.facebook.com/apps/",
    "instagram": "https://developers.facebook.com/apps/",
    "linkedin": "https://www.linkedin.com/developers/apps",
    "reddit": "https://www.reddit.com/prefs/apps",
    "tiktok": "https://developers.tiktok.com/",
    "twitch": "https://dev.twitch.tv/console/apps",
    "twitter_x": "https://developer.x.com/en/portal/dashboard",
    "whatsapp": "https://developers.facebook.com/apps/",
    "youtube": "https://console.cloud.google.com/apis/credentials",
    "bluesky": "https://bsky.app/settings/app-passwords",
    "mastodon": "https://joinmastodon.org/",
    "threads": "https://developers.facebook.com/apps/",
    "spotify": "https://developer.spotify.com/dashboard",
}

_TOKEN_KEYS = {
    "api_key", "apikey", "apiKey", "api_key_value", "access_token", "token",
    "secret", "secret_key", "client_secret", "bearer", "auth_token", "key",
    "personal_access_token", "session_token",
}
_HEADER_KEYS = {"authorization", "x-api-key", "api-key", "x-auth-token", "x-access-token"}
_QUERY_KEYS = {"api_key", "apikey", "access_token", "token", "key"}


def _manifest(plugin_id: str) -> Optional[Dict[str, Any]]:
    try:
        from plugins_system.registry import registry_instance

        cls = registry_instance.get(plugin_id)
        if cls is None:
            return None
        m = cls.manifest.model_dump()
        return m
    except Exception as exc:
        log.warning("manifest lookup failed for %s: %s", plugin_id, exc)
        return None


def _official_url(manifest: Dict[str, Any]) -> str:
    pid = manifest.get("id", "")
    return ONBOARD_URLS.get(pid) or manifest.get("website_url") or manifest.get("docs_url") or "https://www.google.com"


def _credential_field(manifest: Dict[str, Any]) -> str:
    cfg = manifest.get("auth_config") or {}
    for key in ("api_key_field", "token_field", "webhook_url_field", "username_field"):
        if cfg.get(key):
            return str(cfg[key])
    if manifest.get("auth_type") == "webhook":
        return "webhook_url"
    return "access_token"


def _scan_json(obj: Any, out: Dict[str, str], depth: int = 0) -> None:
    if depth > 6 or not isinstance(obj, (dict, list)):
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and k in _TOKEN_KEYS and 8 <= len(v) <= 4096 and "***" not in v:
                out[str(k)] = v
            else:
                _scan_json(v, out, depth + 1)
    else:
        for item in obj[:40]:
            _scan_json(item, out, depth + 1)


def _is_local(host: str) -> bool:
    h = (host or "").lower()
    return h in {"127.0.0.1", "localhost", "::1"} or h.endswith(".local")


def _browser_worker(sid: str, manifest: Dict[str, Any], official_url: str) -> None:
    session = _sessions[sid]
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            session["browser"] = browser
            session["status"] = "waiting_for_login"
            session["official_url"] = official_url

            def on_request(req):
                if _is_local(req.url.split("/")[2] if "//" in req.url else ""):
                    return
                try:
                    headers = req.headers or {}
                    for hk, v in headers.items():
                        if hk.lower() in _HEADER_KEYS and v and len(v) >= 8:
                            token = v.split(None, 1)[-1] if v.lower().startswith("bearer ") else v
                            if "***" not in token:
                                session["found"] = {"source": "header:" + hk, "value": token}
                                session["status"] = "credential_found"
                except Exception:
                    pass

            def on_response(resp):
                if _is_local(resp.url.split("/")[2] if "//" in resp.url else ""):
                    return
                found: Dict[str, str] = {}
                try:
                    if "json" in (resp.headers or {}).get("content-type", ""):
                        _scan_json(resp.json(), found)
                except Exception:
                    pass
                if found:
                    key = _credential_field(manifest)
                    value = found.get(key) or next(iter(found.values()))
                    session["found"] = {"source": "response:" + key, "value": value}
                    session["status"] = "credential_found"

            page.on("request", on_request)
            page.on("response", on_response)

            try:
                page.goto(official_url, wait_until="domcontentloaded", timeout=45000)
            except Exception as exc:
                session["message"] = f"opened with warning: {exc}"

            deadline = time.time() + 600
            while time.time() < deadline:
                if session.get("cancelled"):
                    break
                if manifest.get("auth_type") == "webhook":
                    url = page.url or ""
                    if any(x in url for x in ("hooks.slack.com", "discord.com/api/webhooks")):
                        session["found"] = {"source": "page_url", "value": url}
                        session["status"] = "credential_found"
                        break
                if session["status"] == "credential_found":
                    break
                page.wait_for_timeout(700)

            if session.get("cancelled"):
                session["status"] = "cancelled"
            elif session["status"] != "credential_found":
                session["status"] = "timeout"
                session["message"] = "No credential observed. Sign in on the official site and keep this window open."
    except Exception as exc:
        log.exception("connect browser session failed")
        session["status"] = "error"
        session["message"] = str(exc)
    finally:
        if session.get("status") in ("credential_found", "cancelled", "timeout", "error"):
            browser = session.pop("browser", None)
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass


# --- endpoints -----------------------------------------------------------
@router.get("/info/{plugin_id}")
async def connect_info(plugin_id: str):
    manifest = _manifest(plugin_id)
    if manifest is None:
        raise HTTPException(404, f"unknown plugin: {plugin_id}")
    auth_type = manifest.get("auth_type", "")
    spec = None
    try:
        from integrations.providers import get_provider

        spec = get_provider(plugin_id)
    except Exception:
        pass
    if spec is not None and not getattr(spec, "missing_config", lambda: ["unknown"])():
        return {
            "id": plugin_id,
            "name": manifest.get("name"),
            "mode": "oauth",
            "official_url": None,
            "field": spec.credential_key,
            "instructions": "Opens the provider's official authorization page; the callback links the account automatically.",
        }
    return {
        "id": plugin_id,
        "name": manifest.get("name"),
        "mode": "browser" if auth_type in ("apikey", "webhook", "oauth2") else "manual",
        "official_url": _official_url(manifest),
        "field": _credential_field(manifest),
        "instructions": (
            "A managed Chromium window opens on the provider's official site. "
            "Sign in or create an account, grant access, then return here — the "
            "credential is detected and stored encrypted automatically."
        ),
    }


@router.post("/start/{plugin_id}")
async def connect_start(plugin_id: str, payload: dict = Body(default_factory=dict)):
    info = await connect_info(plugin_id)
    if info["mode"] == "oauth":
        return {"sid": None, "mode": "oauth", "url": f"/api/integrations/{plugin_id}/connect?popup=1"}
    if info["mode"] == "manual":
        return {"sid": None, "mode": "manual", "official_url": info["official_url"]}

    sid = secrets.token_urlsafe(12)
    session: Dict[str, Any] = {
        "sid": sid,
        "plugin_id": plugin_id,
        "user_id": str(payload.get("user_id") or "default_user"),
        "field": info["field"],
        "status": "starting",
        "official_url": info["official_url"],
        "found": None,
        "cancelled": False,
        "browser": None,
        "created": time.time(),
    }
    manifest = _manifest(plugin_id)
    with _lock:
        _sessions[sid] = session
    thread = threading.Thread(
        target=_browser_worker, args=(sid, manifest, info["official_url"]), daemon=True
    )
    thread.start()
    return {"sid": sid, "mode": "browser", "official_url": info["official_url"]}


@router.get("/status/{sid}")
async def connect_status(sid: str):
    session = _sessions.get(sid)
    if not session:
        raise HTTPException(404, "unknown connect session")
    return {
        "sid": sid,
        "plugin_id": session["plugin_id"],
        "status": session["status"],
        "message": session.get("message", ""),
        "has_credential": session.get("found") is not None,
    }


@router.post("/finish/{sid}")
async def connect_finish(sid: str):
    session = _sessions.get(sid)
    if not session:
        raise HTTPException(404, "unknown connect session")
    found = session.get("found")
    if not found:
        raise HTTPException(409, "no credential captured yet")
    from plugins_system.deps import get_manager

    manager = get_manager()
    plugin_id = session["plugin_id"]
    user_id = session["user_id"]
    credentials = {session["field"]: found["value"]}
    ok = await manager.authenticate_plugin(user_id, plugin_id, credentials)
    if ok:
        await manager.install_plugin(user_id, plugin_id)
        await manager.enable_plugin(user_id, plugin_id)
    browser = session.pop("browser", None)
    if browser is not None:
        try:
            browser.close()
        except Exception:
            pass
    session["status"] = "linked" if ok else "store_failed"
    return {
        "ok": ok,
        "plugin_id": plugin_id,
        "field": session["field"],
        "status": session["status"],
    }


@router.delete("/cancel/{sid}")
async def connect_cancel(sid: str):
    session = _sessions.get(sid)
    if not session:
        raise HTTPException(404, "unknown connect session")
    session["cancelled"] = True
    browser = session.pop("browser", None)
    if browser is not None:
        try:
            browser.close()
        except Exception:
            pass
    session["status"] = "cancelled"
    return {"ok": True}
