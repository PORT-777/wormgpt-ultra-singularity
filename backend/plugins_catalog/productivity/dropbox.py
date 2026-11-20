from typing import Any, Dict

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

API = "https://api.dropboxapi.com/2"
CONTENT = "https://content.dropboxapi.com/2"


@register_plugin
class DropboxPlugin(BasePlugin):
    manifest = PluginManifest(
        id="dropbox",
        name="Dropbox",
        description="Browse, search, upload and share Dropbox files",
        long_description=(
            "Dropbox API v2 with an OAuth access token: list and search folders, "
            "create folders, upload text files, create shared links and inspect "
            "the linked account."
        ),
        version="1.0.0",
        author="outcome",
        icon="📦",
        category="productivity",
        tags=["productivity", "dropbox", "files", "storage", "sharing"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="dropbox.listFolder",
                description="List entries in a Dropbox folder",
                parameters={
                    "path": {"type": "string", "description": "Folder path ('' for root)"},
                    "recursive": {"type": "boolean"},
                },
            ),
            PluginTool(
                name="dropbox.search",
                description="Search files and folders by name/content",
                parameters={"query": {"type": "string"}, "path": {"type": "string"}},
            ),
            PluginTool(
                name="dropbox.createFolder",
                description="Create a folder",
                parameters={"path": {"type": "string"}},
            ),
            PluginTool(
                name="dropbox.uploadText",
                description="Upload a UTF-8 text file",
                parameters={
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            ),
            PluginTool(
                name="dropbox.shareLink",
                description="Create a shared link for a file or folder",
                parameters={"path": {"type": "string"}},
            ),
            PluginTool(
                name="dropbox.getAccount",
                description="Return the linked Dropbox account details",
                parameters={},
            ),
        ],
        website_url="https://www.dropbox.com",
        docs_url="https://www.dropbox.com/developers/documentation/http/documentation",
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
        headers = self._headers
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "dropbox.listFolder":
                resp = await client.post(
                    f"{API}/files/list_folder",
                    headers=headers,
                    json={
                        "path": parameters.get("path") or "",
                        "recursive": bool(parameters.get("recursive")),
                    },
                )
            elif tool_name == "dropbox.search":
                resp = await client.post(
                    f"{API}/files/search_v2",
                    headers=headers,
                    json={
                        "query": parameters["query"],
                        "options": {"path": parameters.get("path") or ""},
                    },
                )
            elif tool_name == "dropbox.createFolder":
                resp = await client.post(
                    f"{API}/files/create_folder_v2",
                    headers=headers,
                    json={"path": parameters["path"], "autorename": True},
                )
            elif tool_name == "dropbox.uploadText":
                resp = await client.post(
                    f"{CONTENT}/files/upload",
                    headers={
                        "Authorization": f"Bearer {self.credentials['access_token']}",
                        "Dropbox-API-Arg": (
                            '{"path": "%s", "mode": "overwrite", "autorename": true}'
                            % str(parameters["path"]).replace('"', '\\"')
                        ),
                        "Content-Type": "application/octet-stream",
                    },
                    content=str(parameters.get("content") or "").encode("utf-8"),
                )
            elif tool_name == "dropbox.shareLink":
                resp = await client.post(
                    f"{API}/sharing/create_shared_link_with_settings",
                    headers=headers,
                    json={"path": parameters["path"]},
                )
            elif tool_name == "dropbox.getAccount":
                resp = await client.post(f"{API}/users/get_current_account", headers=headers)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            if not resp.content:
                return {"status": "ok"}
            return resp.json()
