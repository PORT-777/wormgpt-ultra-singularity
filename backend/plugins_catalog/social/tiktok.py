from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://open.tiktokapis.com/v2"


@register_plugin
class TikTokPlugin(BasePlugin):
    manifest = PluginManifest(
        id="tiktok",
        name="TikTok",
        description="Publish videos and read TikTok profile analytics",
        long_description=(
            "TikTok Content Posting API: publish a video from a public URL, inspect your "
            "profile stats, list recent videos and check publishing status."
        ),
        version="1.0.0",
        author="outcome",
        icon="🎵",
        category="social",
        tags=["social", "tiktok", "video", "publishing", "analytics"],
        auth_type="oauth2",
        auth_config={"token_field": "access_token"},
        tools=[
            PluginTool(
                name="tiktok.publishVideo",
                display_name="Publish Video",
                description="Publish a video from a public URL with a caption",
                parameters={
                    "video_url": {"type": "string"},
                    "title": {"type": "string"},
                    "privacy": {
                        "type": "string",
                        "description": "PUBLIC_TO_EVERYONE | MUTUAL_FOLLOW_FRIENDS | SELF_ONLY",
                    },
                },
            ),
            PluginTool(
                name="tiktok.getProfile",
                display_name="Profile Stats",
                description="Get follower count, likes and video count",
                parameters={},
            ),
            PluginTool(
                name="tiktok.listVideos",
                display_name="List Videos",
                description="List recent videos with view and like counts",
                parameters={"limit": {"type": "integer", "description": "Max 20"}},
            ),
        ],
        website_url="https://www.tiktok.com",
        docs_url="https://developers.tiktok.com/doc/content-posting-api-get-started",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "tiktok.publishVideo":
            payload = {
                "post_info": {
                    "title": parameters.get("title", ""),
                    "privacy_level": parameters.get("privacy") or "SELF_ONLY",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": parameters["video_url"],
                },
            }
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{BASE}/post/publish/video/init/", headers=self._headers, json=payload
                )
                resp.raise_for_status()
                return resp.json()

        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "tiktok.getProfile":
                resp = await client.get(
                    f"{BASE}/user/info/",
                    headers=self._headers,
                    params={
                        "fields": "open_id,union_id,avatar_url,display_name,follower_count,following_count,likes_count,video_count"
                    },
                )
            elif tool_name == "tiktok.listVideos":
                resp = await client.post(
                    f"{BASE}/video/list/",
                    headers=self._headers,
                    params={
                        "fields": "id,title,video_description,duration,cover_image_url,share_url,view_count,like_count,comment_count,create_time"
                    },
                    json={"max_count": min(int(parameters.get("limit") or 10), 20)},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
