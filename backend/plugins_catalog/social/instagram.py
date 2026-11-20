from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://graph.facebook.com/v21.0"


@register_plugin
class InstagramPlugin(BasePlugin):
    manifest = PluginManifest(
        id="instagram",
        name="Instagram",
        description="Publish posts, reels and read Instagram business media",
        long_description=(
            "Uses the Instagram Graph API for business/creator accounts: publish photos, "
            "reels and carousels, list recent media, pull account insights and reply to comments."
        ),
        version="1.0.0",
        author="outcome",
        icon="📸",
        category="social",
        tags=["social", "instagram", "meta", "publishing", "marketing"],
        auth_type="oauth2",
        auth_config={"token_field": "access_token", "user_id_field": "ig_user_id"},
        tools=[
            PluginTool(
                name="instagram.publishPhoto",
                display_name="Publish Photo",
                description="Publish an image from a public URL with a caption",
                parameters={
                    "image_url": {"type": "string"},
                    "caption": {"type": "string"},
                },
            ),
            PluginTool(
                name="instagram.publishReel",
                display_name="Publish Reel",
                description="Publish a video/reel from a public URL",
                parameters={"video_url": {"type": "string"}, "caption": {"type": "string"}},
            ),
            PluginTool(
                name="instagram.getMedia",
                display_name="List Media",
                description="List recent posts with like and comment counts",
                parameters={"limit": {"type": "integer", "description": "Default 25"}},
            ),
            PluginTool(
                name="instagram.getAccount",
                display_name="Account Info",
                description="Get follower count, media count and profile fields",
                parameters={},
            ),
            PluginTool(
                name="instagram.replyComment",
                display_name="Reply to Comment",
                description="Post a reply to a comment by id",
                parameters={"comment_id": {"type": "string"}, "message": {"type": "string"}},
            ),
        ],
        website_url="https://www.instagram.com",
        docs_url="https://developers.facebook.com/docs/instagram-platform",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token")) and bool(
            self.credentials.get("ig_user_id")
        )

    @property
    def _token(self) -> str:
        return self.credentials["access_token"]

    @property
    def _uid(self) -> str:
        return self.credentials["ig_user_id"]

    async def _publish(self, params: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            created = await client.post(
                f"{BASE}/{self._uid}/media", data={**params, "access_token": self._token}
            )
            created.raise_for_status()
            creation_id = created.json().get("id")

            published = await client.post(
                f"{BASE}/{self._uid}/media_publish",
                data={"creation_id": creation_id, "access_token": self._token},
            )
            published.raise_for_status()
            return {"status": "published", "media_id": published.json().get("id")}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "instagram.publishPhoto":
            return await self._publish(
                {"image_url": parameters["image_url"], "caption": parameters.get("caption", "")}
            )

        if tool_name == "instagram.publishReel":
            return await self._publish(
                {
                    "media_type": "REELS",
                    "video_url": parameters["video_url"],
                    "caption": parameters.get("caption", ""),
                }
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "instagram.getMedia":
                resp = await client.get(
                    f"{BASE}/{self._uid}/media",
                    params={
                        "fields": "id,caption,media_type,permalink,timestamp,like_count,comments_count",
                        "limit": int(parameters.get("limit") or 25),
                        "access_token": self._token,
                    },
                )
            elif tool_name == "instagram.getAccount":
                resp = await client.get(
                    f"{BASE}/{self._uid}",
                    params={
                        "fields": "id,username,name,biography,followers_count,follows_count,media_count,profile_picture_url",
                        "access_token": self._token,
                    },
                )
            elif tool_name == "instagram.replyComment":
                resp = await client.post(
                    f"{BASE}/{parameters['comment_id']}/replies",
                    data={"message": parameters.get("message", ""), "access_token": self._token},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
