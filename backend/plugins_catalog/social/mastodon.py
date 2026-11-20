from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class MastodonPlugin(BasePlugin):
    manifest = PluginManifest(
        id="mastodon",
        name="Mastodon",
        description="Post to the fediverse, read timelines and notifications",
        long_description=(
            "Works with any Mastodon-compatible instance: publish statuses with "
            "visibility control, upload media, read home and hashtag timelines, list "
            "account notifications and delete your own posts."
        ),
        version="1.0.0",
        author="outcome",
        icon="🐘",
        category="social",
        tags=["social", "mastodon", "fediverse", "activitypub", "microblog"],
        auth_type="apikey",
        auth_config={"api_key_field": "access_token", "extra_fields": ["instance"]},
        tools=[
            PluginTool(
                name="mastodon.postStatus",
                display_name="Post Status",
                description="Publish a status with optional media ids and visibility",
                parameters={
                    "status": {"type": "string"},
                    "visibility": {"type": "string", "description": "public | unlisted | private | direct"},
                    "media_ids": {"type": "array"},
                    "spoiler_text": {"type": "string"},
                    "in_reply_to_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="mastodon.homeTimeline",
                display_name="Home Timeline",
                description="Read the authenticated user's home timeline",
                parameters={
                    "limit": {"type": "integer", "description": "Default 20, max 40"},
                    "max_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="mastodon.tagTimeline",
                display_name="Hashtag Timeline",
                description="Read the public timeline for a hashtag",
                parameters={"hashtag": {"type": "string"}, "limit": {"type": "integer"}},
            ),
            PluginTool(
                name="mastodon.uploadMedia",
                display_name="Upload Media",
                description="Upload media from a public URL and get a media id",
                parameters={
                    "url": {"type": "string"},
                    "description": {"type": "string", "description": "Alt text"},
                },
            ),
            PluginTool(
                name="mastodon.notifications",
                display_name="Notifications",
                description="List mentions, favourites, boosts and follows",
                parameters={"limit": {"type": "integer"}, "types": {"type": "array"}},
            ),
            PluginTool(
                name="mastodon.deleteStatus",
                display_name="Delete Status",
                description="Delete one of your own statuses by id",
                parameters={"status_id": {"type": "string"}},
            ),
        ],
        website_url="https://joinmastodon.org",
        docs_url="https://docs.joinmastodon.org/api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _base(self) -> str:
        raw = (self.credentials.get("instance") or "mastodon.social").strip().rstrip("/")
        if not raw.startswith("http"):
            raw = "https://" + raw
        return raw + "/api/v1"

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.credentials['access_token']}"}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "mastodon.postStatus":
                payload: Dict[str, Any] = {
                    "status": parameters.get("status", ""),
                    "visibility": parameters.get("visibility") or "public",
                }
                if parameters.get("media_ids"):
                    payload["media_ids"] = parameters["media_ids"]
                if parameters.get("spoiler_text"):
                    payload["spoiler_text"] = parameters["spoiler_text"]
                if parameters.get("in_reply_to_id"):
                    payload["in_reply_to_id"] = parameters["in_reply_to_id"]
                resp = await client.post(
                    f"{self._base}/statuses", headers=self._headers, json=payload
                )
            elif tool_name == "mastodon.homeTimeline":
                resp = await client.get(
                    f"{self._base}/timelines/home",
                    headers=self._headers,
                    params={
                        "limit": min(int(parameters.get("limit") or 20), 40),
                        **({"max_id": parameters["max_id"]} if parameters.get("max_id") else {}),
                    },
                )
            elif tool_name == "mastodon.tagTimeline":
                resp = await client.get(
                    f"{self._base}/timelines/tag/{parameters['hashtag']}",
                    headers=self._headers,
                    params={"limit": min(int(parameters.get("limit") or 20), 40)},
                )
            elif tool_name == "mastodon.uploadMedia":
                async with httpx.AsyncClient(timeout=120.0) as downloader:
                    media = await downloader.get(parameters["url"])
                    media.raise_for_status()
                files = {
                    "file": (
                        "upload",
                        media.content,
                        media.headers.get("content-type", "application/octet-stream"),
                    )
                }
                data = {"description": parameters.get("description", "")}
                resp = await client.post(
                    f"{self._base}/media", headers=self._headers, files=files, data=data
                )
            elif tool_name == "mastodon.notifications":
                params: Dict[str, Any] = {"limit": min(int(parameters.get("limit") or 20), 40)}
                if parameters.get("types"):
                    params["types[]"] = parameters["types"]
                resp = await client.get(
                    f"{self._base}/notifications", headers=self._headers, params=params
                )
            elif tool_name == "mastodon.deleteStatus":
                resp = await client.delete(
                    f"{self._base}/statuses/{parameters['status_id']}", headers=self._headers
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Mastodon HTTP {resp.status_code}: {resp.text[:400]}")
            if not resp.content:
                return {"status": "ok"}
            return resp.json()
