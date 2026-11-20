from typing import Any, Dict, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://bsky.social/xrpc"


@register_plugin
class BlueskyPlugin(BasePlugin):
    manifest = PluginManifest(
        id="bluesky",
        name="Bluesky",
        description="Post, like and search on the AT Protocol network",
        long_description=(
            "Authenticates with an app password, then publishes posts (with link and "
            "image embeds), reads author feeds and search results, fetches profiles, "
            "likes posts and lists notifications."
        ),
        version="1.0.0",
        author="outcome",
        icon="🦋",
        category="social",
        tags=["social", "bluesky", "atproto", "microblog", "decentralized"],
        auth_type="apikey",
        auth_config={"api_key_field": "app_password", "extra_fields": ["handle", "service"]},
        tools=[
            PluginTool(
                name="bluesky.post",
                display_name="Create Post",
                description="Publish a post (max 300 chars) with optional link preview",
                parameters={
                    "text": {"type": "string"},
                    "lang": {"type": "string", "description": "Default en"},
                    "reply_to": {"type": "string", "description": "AT-URI of the parent post"},
                },
            ),
            PluginTool(
                name="bluesky.authorFeed",
                display_name="Author Feed",
                description="List recent posts from a handle or DID",
                parameters={"actor": {"type": "string"}, "limit": {"type": "integer"}},
            ),
            PluginTool(
                name="bluesky.searchPosts",
                display_name="Search Posts",
                description="Full-text search across public posts",
                parameters={
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                    "sort": {"type": "string", "description": "latest | top"},
                },
            ),
            PluginTool(
                name="bluesky.getProfile",
                display_name="Get Profile",
                description="Get followers, follows and post counts for an actor",
                parameters={"actor": {"type": "string"}},
            ),
            PluginTool(
                name="bluesky.like",
                display_name="Like Post",
                description="Like a post by AT-URI (returns the like record uri)",
                parameters={"uri": {"type": "string"}, "cid": {"type": "string"}},
            ),
        ],
        website_url="https://bsky.app",
        docs_url="https://docs.bsky.app/docs/category/http-reference",
        is_free=True,
        is_official=True,
    )

    def __init__(self, credentials: Dict[str, Any]):
        self._session_token: Optional[str] = None
        self._did: Optional[str] = None
        super().__init__(credentials)

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("app_password")) and bool(
            self.credentials.get("handle")
        )

    @property
    def _service(self) -> str:
        raw = (self.credentials.get("service") or "https://bsky.social").rstrip("/")
        if not raw.startswith("http"):
            raw = "https://" + raw
        return raw + "/xrpc"

    async def _login(self) -> str:
        if self._session_token:
            return self._session_token
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{self._service}/com.atproto.server.createSession",
                json={
                    "identifier": self.credentials["handle"],
                    "password": self.credentials["app_password"],
                },
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Bluesky login HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
        self._session_token = data["accessJwt"]
        self._did = data.get("did")
        return self._session_token

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        token = await self._login()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        repo = self._did or self.credentials["handle"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "bluesky.post":
                record: Dict[str, Any] = {
                    "text": parameters.get("text", ""),
                    "langs": [parameters.get("lang") or "en"],
                    "createdAt": _now_iso(),
                }
                if parameters.get("reply_to"):
                    record["reply"] = {"root": {"uri": parameters["reply_to"]}, "parent": {"uri": parameters["reply_to"]}}
                resp = await client.post(
                    f"{self._service}/com.atproto.repo.createRecord",
                    headers=headers,
                    json={
                        "repo": repo,
                        "collection": "app.bsky.feed.post",
                        "record": record,
                    },
                )
            elif tool_name == "bluesky.authorFeed":
                resp = await client.get(
                    f"{self._service}/app.bsky.feed.getAuthorFeed",
                    headers=headers,
                    params={
                        "actor": parameters.get("actor") or repo,
                        "limit": min(int(parameters.get("limit") or 20), 50),
                    },
                )
                return _feed_summary(resp)
            elif tool_name == "bluesky.searchPosts":
                resp = await client.get(
                    f"{self._service}/app.bsky.feed.searchPosts",
                    headers=headers,
                    params={
                        "q": parameters.get("query", ""),
                        "limit": min(int(parameters.get("limit") or 20), 50),
                        "sort": parameters.get("sort") or "latest",
                    },
                )
                return _feed_summary(resp)
            elif tool_name == "bluesky.getProfile":
                resp = await client.get(
                    f"{self._service}/app.bsky.actor.getProfile",
                    headers=headers,
                    params={"actor": parameters.get("actor") or repo},
                )
            elif tool_name == "bluesky.like":
                resp = await client.post(
                    f"{self._service}/com.atproto.repo.createRecord",
                    headers=headers,
                    json={
                        "repo": repo,
                        "collection": "app.bsky.feed.like",
                        "record": {
                            "subject": {
                                "uri": parameters["uri"],
                                "cid": parameters.get("cid", ""),
                            },
                            "createdAt": _now_iso(),
                        },
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Bluesky HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _feed_summary(resp: httpx.Response) -> Dict[str, Any]:
    if resp.status_code >= 400:
        raise RuntimeError(f"Bluesky HTTP {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    posts = data.get("feed") or data.get("posts") or []
    out = []
    for item in posts:
        post = item.get("post") if isinstance(item, dict) and "post" in item else item
        if not isinstance(post, dict):
            continue
        out.append(
            {
                "uri": post.get("uri"),
                "author": ((post.get("author") or {}).get("handle")),
                "text": post.get("record", {}).get("text"),
                "likes": post.get("likeCount", 0),
                "reposts": post.get("repostCount", 0),
                "replies": post.get("replyCount", 0),
                "created": post.get("record", {}).get("createdAt"),
            }
        )
    return {"posts": out, "count": len(out)}
