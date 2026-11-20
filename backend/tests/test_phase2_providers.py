"""Regression tests for the new OAuth providers and the completed legacy plugins.

No network access: every HTTP call is served by an ``httpx.MockTransport`` that
also records the request so headers, bodies and endpoints can be asserted.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List

import httpx
import pytest

from integrations.providers import PROVIDERS
from plugins_system.registry import registry_instance

import plugins_catalog.siem.splunk as splunk_module
import plugins_catalog.communication.teams as teams_module


NEW_OAUTH_PLUGINS = (
    "dropbox",
    "spotify",
    "hubspot",
    "salesforce",
    "asana",
    "clickup",
    "monday",
    "zoom",
    "teams",
)


# --------------------------------------------------------------------------- #
#  Mock transport helpers
# --------------------------------------------------------------------------- #

class Recorder:
    def __init__(self, handler):
        self.requests: List[httpx.Request] = []
        self._handler = handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def patch_client(monkeypatch, module, recorder: Recorder) -> None:
    real_client = httpx.AsyncClient

    def factory(*args: Any, **kwargs: Any):
        kwargs.pop("transport", None)
        kwargs["transport"] = httpx.MockTransport(recorder)
        kwargs["timeout"] = 5
        return real_client(*args, **kwargs)

    monkeypatch.setattr(module.httpx, "AsyncClient", factory)


def json_response(payload: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


# --------------------------------------------------------------------------- #
#  Catalog / provider wiring
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_new_plugins_are_discovered():
    await registry_instance.discover_plugins()
    ids = {m["id"] for m in registry_instance.get_all_manifests()}
    for plugin_id in NEW_OAUTH_PLUGINS + ("splunk", "wazuh", "whatsapp", "discord", "trello"):
        assert plugin_id in ids, f"{plugin_id} is missing from the plugin catalog"


def test_new_oauth_providers_are_registered():
    for plugin_id in NEW_OAUTH_PLUGINS:
        spec = PROVIDERS.get(plugin_id)
        assert spec is not None, f"{plugin_id} has no OAuth provider"
        assert spec.authorization_endpoint.startswith("https://")
        assert spec.token_endpoint.startswith("https://")
        assert spec.userinfo_endpoint.startswith("https://")
        assert spec.client_id_env, f"{plugin_id} client_id_env is empty"
        assert spec.client_secret_env, f"{plugin_id} client_secret_env is empty"
        assert spec.refresh is True
        # Teams/Asana/ClickUp use a fixed permission set with no `scope` param.
        if spec.plugin_id not in {"asana", "clickup", "monday", "teams"}:
            assert spec.scopes, f"{plugin_id} scopes are empty"


def test_no_oauth_reasons_no_longer_claim_teams_uses_no_graph():
    from integrations.providers import no_oauth_reason

    assert "Graph" in no_oauth_reason("teams")
    for plugin_id in NEW_OAUTH_PLUGINS:
        assert plugin_id in PROVIDERS, f"{plugin_id} must not be reported as unsupported"


# --------------------------------------------------------------------------- #
#  Splunk
# --------------------------------------------------------------------------- #

def _splunk_credentials(**extra: Any) -> Dict[str, Any]:
    creds = {"splunk_token": "classic-token", "splunk_host": "splunk.example.com"}
    creds.update(extra)
    return creds


def test_splunk_host_normalisation():
    plugin_cls = registry_instance.get("splunk")
    assert plugin_cls is not None
    plugin = plugin_cls(_splunk_credentials())
    assert plugin._host_from("splunk.example.com") == "https://splunk.example.com:8089"
    assert plugin._host_from("https://splunk.example.com:8089") == "https://splunk.example.com:8089"
    assert (
        plugin._host_from("http://splunk.internal:8000/services")
        == "http://splunk.internal:8000"
    )


@pytest.mark.asyncio
async def test_splunk_search_polls_the_job_and_returns_results(monkeypatch):
    plugin = registry_instance.get("splunk")(_splunk_credentials())

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/services/search/jobs":
            return json_response({"sid": "123.45"})
        if request.method == "GET" and path == "/services/search/jobs/123.45":
            return json_response(
                {"entry": [{"content": {"isDone": True, "dispatchState": "DONE"}}]}
            )
        if request.method == "GET" and path == "/services/search/jobs/123.45/results":
            return json_response(
                {"results": [{"_raw": "error", "host": "web-01"}], "fields": []}
            )
        return json_response({"unexpected": str(request.url)}, 404)

    recorder = Recorder(handler)
    patch_client(monkeypatch, splunk_module, recorder)

    result = await plugin.execute(
        "splunk.search", {"query": "search index=main error", "max_results": 10}
    )

    assert result["count"] == 1
    assert result["results"][0]["host"] == "web-01"
    assert recorder.requests[0].headers["Authorization"] == "Splunk classic-token"
    body = recorder.requests[0].content.decode()
    assert "search=search+index%3Dmain+error" in body or "index%3Dmain" in body
    # The result request must carry the requested page size, not a default.
    assert recorder.requests[-1].url.params["count"] == "10"


@pytest.mark.asyncio
async def test_splunk_uses_bearer_for_jwt_tokens(monkeypatch):
    plugin = registry_instance.get("splunk")(
        _splunk_credentials(splunk_token="eyJhbGciOiJIUzI1NiJ9.payload.sig")
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/services/alerts/fired_alerts"):
            return json_response({"entry": [{"name": "Brute force", "content": {"count": "3"}}]})
        return json_response({}, 404)

    recorder = Recorder(handler)
    patch_client(monkeypatch, splunk_module, recorder)

    result = await plugin.execute("splunk.getAlerts", {"count": 5})
    assert result["alerts"][0]["name"] == "Brute force"
    assert recorder.requests[0].headers["Authorization"].startswith("Bearer eyJ")
    assert recorder.requests[0].url.params["count"] == "5"


@pytest.mark.asyncio
async def test_splunk_create_alert_hits_saved_searches(monkeypatch):
    plugin = registry_instance.get("splunk")(_splunk_credentials())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/services/saved/searches":
            return json_response({"entry": [{"name": "IOC sweep", "content": {"is_scheduled": "1"}}]})
        return json_response({}, 404)

    recorder = Recorder(handler)
    patch_client(monkeypatch, splunk_module, recorder)

    result = await plugin.execute(
        "splunk.createAlert",
        {"name": "IOC sweep", "query": "index=* malware", "alert_actions": "email"},
    )
    assert result["status"] == "created"

    form = recorder.requests[0].content.decode()
    assert "name=IOC+sweep" in form
    assert "is_scheduled=1" in form
    assert "alert_actions=email" in form
    assert "search=search+index%3D%2A+malware" in form


@pytest.mark.asyncio
async def test_splunk_lookup_ioc_escapes_quotes(monkeypatch):
    plugin = registry_instance.get("splunk")(_splunk_credentials())
    captured: Dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/services/search/jobs":
            captured["body"] = request.content.decode()
            return json_response({"sid": "1"})
        if request.url.path.endswith("/services/search/jobs/1"):
            return json_response({"entry": [{"content": {"isDone": True}}]})
        if request.url.path.endswith("/results"):
            return json_response({"results": []})
        return json_response({}, 404)

    recorder = Recorder(handler)
    patch_client(monkeypatch, splunk_module, recorder)

    await plugin.execute("splunk.lookupIOC", {"ioc": 'evil" OR index=*'})
    body = captured["body"]
    assert "evil%5C%22" in body
    assert "earliest_time=-7d" in body


def test_splunk_tls_verification_is_secure_by_default():
    plugin_cls = registry_instance.get("splunk")
    assert plugin_cls(_splunk_credentials())._verify_tls is True
    assert (
        plugin_cls(_splunk_credentials(allow_insecure_tls="true"))._verify_tls is False
    )


def test_splunk_rejects_missing_credentials():
    plugin_cls = registry_instance.get("splunk")
    with pytest.raises(ValueError):
        plugin_cls({"splunk_token": "x"})
    with pytest.raises(ValueError):
        plugin_cls({"splunk_host": "splunk.example.com"})


# --------------------------------------------------------------------------- #
#  Microsoft Teams
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_teams_webhook_only_cannot_run_graph_tools():
    plugin = registry_instance.get("teams")({"webhook_url": "https://example.com/hook"})
    with pytest.raises(ValueError, match="Microsoft Graph token"):
        await plugin.execute("teams.listTeams", {})


@pytest.mark.asyncio
async def test_teams_oauth_only_cannot_post_to_webhook():
    plugin = registry_instance.get("teams")({"access_token": "graph-token"})
    with pytest.raises(ValueError, match="incoming webhook"):
        await plugin.execute("teams.sendMessage", {"text": "hi"})


@pytest.mark.asyncio
async def test_teams_graph_lists_teams_and_channels(monkeypatch):
    plugin = registry_instance.get("teams")({"access_token": "graph-token"})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1.0/me/joinedTeams":
            return json_response({"value": [{"id": "t1", "displayName": "SecOps"}]})
        if request.url.path == "/v1.0/teams/t1/channels":
            return json_response({"value": [{"id": "c1", "displayName": "Alerts"}]})
        return json_response({}, 404)

    recorder = Recorder(handler)
    patch_client(monkeypatch, teams_module, recorder)

    teams = await plugin.execute("teams.listTeams", {})
    assert teams["teams"][0]["displayName"] == "SecOps"

    channels = await plugin.execute("teams.listChannels", {"team_id": "t1"})
    assert channels["channels"][0]["id"] == "c1"
    assert recorder.requests[0].headers["Authorization"] == "Bearer graph-token"


@pytest.mark.asyncio
async def test_teams_create_meeting_builds_real_graph_payload(monkeypatch):
    plugin = registry_instance.get("teams")({"access_token": "graph-token"})
    captured: Dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1.0/me/onlineMeetings":
            captured["body"] = json.loads(request.content)
            return json_response(
                {
                    "id": "m1",
                    "subject": "Incident review",
                    "joinWebUrl": "https://teams.microsoft.com/l/meetup-join/x",
                }
            )
        return json_response({}, 404)

    recorder = Recorder(handler)
    patch_client(monkeypatch, teams_module, recorder)

    result = await plugin.execute(
        "teams.createMeeting",
        {
            "subject": "Incident review",
            "start": "2026-01-01T10:00:00Z",
            "end": "2026-01-01T11:00:00Z",
            "attendees": ["soc@example.com", {"email": "ciso@example.com"}],
        },
    )

    assert result["join_url"].startswith("https://teams.microsoft.com/")
    body = captured["body"]
    assert body["startDateTime"] == "2026-01-01T10:00:00Z"
    assert len(body["participants"]["attendees"]) == 2
    assert (
        body["participants"]["attendees"][0]["identity"]["user"]["id"]
        == "soc@example.com"
    )


@pytest.mark.asyncio
async def test_teams_upload_file_resolves_channel_folder(monkeypatch):
    plugin = registry_instance.get("teams")({"access_token": "graph-token"})
    payload = b"report-bytes"
    captured: Dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1.0/teams/t1/channels/c1/filesFolder":
            return json_response(
                {"id": "item1", "parentReference": {"driveId": "drive1"}}
            )
        if request.url.path == "/v1.0/drives/drive1/items/item1:/report.txt:/content":
            captured["content"] = request.content
            return json_response(
                {"id": "f1", "name": "report.txt", "size": len(payload), "webUrl": "https://x"}
            )
        return json_response({}, 404)

    recorder = Recorder(handler)
    patch_client(monkeypatch, teams_module, recorder)

    result = await plugin.execute(
        "teams.uploadFile",
        {
            "team_id": "t1",
            "channel_id": "c1",
            "filename": "report.txt",
            "content_b64": base64.b64encode(payload).decode(),
        },
    )

    assert result["status"] == "uploaded"
    assert captured["content"] == payload
    assert result["web_url"] == "https://x"


@pytest.mark.asyncio
async def test_teams_rejects_invalid_base64():
    plugin = registry_instance.get("teams")({"access_token": "graph-token"})
    with pytest.raises(ValueError, match="base64"):
        await plugin.execute(
            "teams.uploadFile",
            {"team_id": "t", "channel_id": "c", "filename": "f", "content_b64": "!!!"},
        )


# --------------------------------------------------------------------------- #
#  New OAuth plugins accept the credential overlay
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("plugin_id", NEW_OAUTH_PLUGINS)
def test_new_plugins_instantiate_with_oauth_credentials(plugin_id):
    plugin_cls = registry_instance.get(plugin_id)
    assert plugin_cls is not None
    creds = {"access_token": "oauth-token", "instance_url": "https://acme.my.salesforce.com"}
    plugin = plugin_cls(creds)
    assert plugin.credentials["access_token"] == "oauth-token"

