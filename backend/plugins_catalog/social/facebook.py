from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://graph.facebook.com/v21.0"


@register_plugin
class FacebookPlugin(BasePlugin):
    manifest = PluginManifest(
        id="facebook",
        name="Facebook Pages",
        description="Publish posts and read Page insights via the Graph API",
        long_description=(
            "Manage a Facebook Page from the agent: publish text/link posts, list recent "
            "posts, reply to comments and read Page-level insights."
        ),
        version="1.0.0",
        author="outcome",
        icon="📘",
        category="social",
        tags=["social", "facebook", "meta", "pages", "marketing"],
        auth_type="oauth2",
        auth_config={"token_field": "page_token", "user_id_field": "page_id"},
        tools=[
            PluginTool(
                name="facebook.publishPost",
                display_name="Publish Post",
                description="Publish a message (optionally with a link) to the Page",
                parameters={
                    "message": {"type": "string"},
                    "link": {"type": "string"},
                },
            ),
            PluginTool(
                name="facebook.listPosts",
                display_name="List Posts",
                description="List recent Page posts with engagement fields",
                parameters={"limit": {"type": "integer"}},
            ),
            PluginTool(
                name="facebook.comment",
                display_name="Comment",
                description="Comment on a post by id",
                parameters={"post_id": {"type": "string"}, "message": {"type": "string"}},
            ),
            PluginTool(
                name="facebook.pageInsights",
                display_name="Page Insights",
                description="Read Page metrics such as impressions and engaged users",
                parameters={
                    "metric": {
                        "type": "string",
                        "description": "page_impressions, page_engaged_users, page_fans",
                    },
                    "period": {"type": "string", "description": "day | week | days_28"},
                },
            ),
        ],
        website_url="https://www.facebook.com",
        docs_url="https://developers.facebook.com/docs/graph-api",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("page_token")) and bool(self.credentials.get("page_id"))

    @property
    def _token(self) -> str:
        return self.credentials["page_token"]

    @property
    def _page(self) -> str:
        return self.credentials["page_id"]

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "facebook.publishPost":
                data = {"message": parameters.get("message", ""), "access_token": self._token}
                if parameters.get("link"):
                    data["link"] = parameters["link"]
                resp = await client.post(f"{BASE}/{self._page}/feed", data=data)
            elif tool_name == "facebook.listPosts":
                resp = await client.get(
                    f"{BASE}/{self._page}/posts",
                    params={
                        "fields": "id,message,created_time,permalink_url,shares,reactions.summary(total_count),comments.summary(total_count)",
                        "limit": int(parameters.get("limit") or 25),
                        "access_token": self._token,
                    },
                )
            elif tool_name == "facebook.comment":
                resp = await client.post(
                    f"{BASE}/{parameters['post_id']}/comments",
                    data={"message": parameters.get("message", ""), "access_token": self._token},
                )
            elif tool_name == "facebook.pageInsights":
                resp = await client.get(
                    f"{BASE}/{self._page}/insights",
                    params={
                        "metric": parameters.get("metric") or "page_impressions",
                        "period": parameters.get("period") or "day",
                        "access_token": self._token,
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
