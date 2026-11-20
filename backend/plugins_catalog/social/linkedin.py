from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.linkedin.com"
REST = "https://api.linkedin.com/rest"


@register_plugin
class LinkedInPlugin(BasePlugin):
    manifest = PluginManifest(
        id="linkedin",
        name="LinkedIn",
        description="Publish posts and read profile / organisation data",
        long_description=(
            "Posts as a member or an organisation through the modern /rest/posts "
            "endpoint, reads the authenticated profile via OpenID userinfo, resolves "
            "organisation ACLs and fetches share statistics."
        ),
        version="1.0.0",
        author="outcome",
        icon="💼",
        category="social",
        tags=["social", "linkedin", "publishing", "professional", "b2b"],
        auth_type="oauth2",
        auth_config={"token_field": "access_token"},
        tools=[
            PluginTool(
                name="linkedin.getProfile",
                display_name="Profile",
                description="Get the authenticated member's name, email and picture",
                parameters={},
            ),
            PluginTool(
                name="linkedin.createPost",
                display_name="Create Post",
                description="Publish a text post as a member (urn:li:person:{id}) or organisation",
                parameters={
                    "text": {"type": "string"},
                    "author": {
                        "type": "string",
                        "description": "Optional urn:li:person:xxx or urn:li:organization:xxx",
                    },
                    "visibility": {"type": "string", "description": "PUBLIC | CONNECTIONS"},
                },
            ),
            PluginTool(
                name="linkedin.getPost",
                display_name="Get Post",
                description="Fetch a post's commentary, state and timestamps by urn",
                parameters={"post_urn": {"type": "string", "description": "urn:li:share:..."}},
            ),
            PluginTool(
                name="linkedin.listOrganizationAcls",
                display_name="Organisation Access",
                description="List organisations the authenticated member can post for",
                parameters={},
            ),
            PluginTool(
                name="linkedin.getShareStatistics",
                display_name="Share Statistics",
                description="Read impressions, clicks, likes and comments for a share urn",
                parameters={
                    "organizational_entity": {
                        "type": "string",
                        "description": "urn:li:organization:123 or urn:li:share:456",
                    }
                },
            ),
        ],
        website_url="https://www.linkedin.com",
        docs_url="https://learn.microsoft.com/en-us/linkedin/",
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
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202411",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "linkedin.getProfile":
                resp = await client.get(f"{BASE}/v2/userinfo", headers=self._headers)

            elif tool_name == "linkedin.createPost":
                author = parameters.get("author")
                if not author:
                    me = await client.get(f"{BASE}/v2/userinfo", headers=self._headers)
                    me.raise_for_status()
                    author = f"urn:li:person:{me.json().get('sub')}"
                payload: Dict[str, Any] = {
                    "author": author,
                    "commentary": parameters.get("text", ""),
                    "visibility": parameters.get("visibility") or "PUBLIC",
                    "distribution": {
                        "feedDistribution": "MAIN_FEED",
                        "targetEntities": [],
                        "thirdPartyDistributionChannels": [],
                    },
                    "lifecycleState": "PUBLISHED",
                    "isReshareDisabledByAuthor": False,
                }
                resp = await client.post(f"{REST}/posts", headers=self._headers, json=payload)
                resp.raise_for_status()
                return {
                    "status": "published",
                    "post_urn": resp.headers.get("x-restli-id") or resp.headers.get("X-RestLi-Id"),
                }

            elif tool_name == "linkedin.getPost":
                urn = parameters["post_urn"]
                resp = await client.get(
                    f"{REST}/posts/{urn}", headers=self._headers
                )

            elif tool_name == "linkedin.listOrganizationAcls":
                resp = await client.get(
                    f"{BASE}/v2/organizationAcls",
                    headers=self._headers,
                    params={"q": "roleAssignee", "state": "APPROVED"},
                )

            elif tool_name == "linkedin.getShareStatistics":
                resp = await client.get(
                    f"{REST}/organizationalEntityShareStatistics",
                    headers=self._headers,
                    params={"q": "organizationalEntity", "organizationalEntity": parameters["organizational_entity"]},
                )

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"LinkedIn HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
