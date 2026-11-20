from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://graph.threads.net/v1.0"


@register_plugin
class ThreadsPlugin(BasePlugin):
    manifest = PluginManifest(
        id="threads",
        name="Threads",
        description="Publish text and image threads plus account insights",
        long_description=(
            "Meta's Threads API: create text posts, image posts and reply chains, list "
            "your published threads and read views, likes, replies and reposts."
        ),
        version="1.0.0",
        author="outcome",
        icon="🧵",
        category="social",
        tags=["social", "threads", "meta", "publishing", "microblog"],
        auth_type="oauth2",
        auth_config={"token_field": "access_token", "user_id_field": "threads_user_id"},
        tools=[
            PluginTool(
                name="threads.publishText",
                display_name="Publish Text",
                description="Publish a text post, optionally as a reply to another thread",
                parameters={
                    "text": {"type": "string"},
                    "reply_to_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="threads.publishImage",
                display_name="Publish Image",
                description="Publish an image post from a public URL",
                parameters={"image_url": {"type": "string"}, "text": {"type": "string"}},
            ),
            PluginTool(
                name="threads.listThreads",
                display_name="List Threads",
                description="List your published threads with permalinks",
                parameters={"limit": {"type": "integer", "description": "Default 25"}},
            ),
            PluginTool(
                name="threads.insights",
                display_name="Insights",
                description="Read views, likes, replies, reposts and quotes totals",
                parameters={
                    "metric": {
                        "type": "string",
                        "description": "views | likes | replies | reposts | quotes",
                    }
                },
            ),
        ],
        website_url="https://www.threads.net",
        docs_url="https://developers.facebook.com/docs/threads",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token")) and bool(
            self.credentials.get("threads_user_id")
        )

    @property
    def _uid(self) -> str:
        return self.credentials["threads_user_id"]

    @property
    def _token(self) -> str:
        return self.credentials["access_token"]

    async def _publish(self, params: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            created = await client.post(
                f"{BASE}/{self._uid}/threads",
                data={**params, "access_token": self._token},
            )
            if created.status_code >= 400:
                raise RuntimeError(f"Threads HTTP {created.status_code}: {created.text[:400]}")
            creation_id = created.json().get("id")

            published = await client.post(
                f"{BASE}/{self._uid}/threads_publish",
                data={"creation_id": creation_id, "access_token": self._token},
            )
            if published.status_code >= 400:
                raise RuntimeError(
                    f"Threads HTTP {published.status_code}: {published.text[:400]}"
                )
            return {"status": "published", "thread_id": published.json().get("id")}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "threads.publishText":
            params: Dict[str, Any] = {
                "media_type": "TEXT",
                "text": parameters.get("text", ""),
            }
            if parameters.get("reply_to_id"):
                params["reply_to_id"] = parameters["reply_to_id"]
            return await self._publish(params)

        if tool_name == "threads.publishImage":
            return await self._publish(
                {
                    "media_type": "IMAGE",
                    "image_url": parameters["image_url"],
                    "text": parameters.get("text", ""),
                }
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "threads.listThreads":
                resp = await client.get(
                    f"{BASE}/{self._uid}/threads",
                    params={
                        "fields": "id,text,media_type,permalink,timestamp",
                        "limit": min(int(parameters.get("limit") or 25), 100),
                        "access_token": self._token,
                    },
                )
            elif tool_name == "threads.insights":
                resp = await client.get(
                    f"{BASE}/{self._uid}/threads_insights",
                    params={
                        "metric": parameters.get("metric") or "views",
                        "access_token": self._token,
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Threads HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
