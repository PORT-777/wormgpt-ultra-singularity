from typing import Any, Dict
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class ObsidianPlugin(BasePlugin):
    manifest = PluginManifest(
        id="obsidian",
        name="Obsidian",
        description="Sync notes and findings with your Obsidian vault",
        long_description="Talks to the Obsidian Local REST API plugin. Drop findings, reports, and IOC dossiers straight into your vault as markdown notes.",
        version="1.0.0",
        author="outcome",
        icon="📓",
        category="productivity",
        tags=["notes", "knowledge-base", "markdown", "vault"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key", "url_field": "vault_url"},
        tools=[
            PluginTool(
                name="obsidian.createNote",
                display_name="Create Note",
                description="Create a new markdown note in the vault",
                parameters={
                    "path": {"type": "string", "description": "Vault-relative path, e.g. Findings/2026-01-01.md"},
                    "content": {"type": "string"},
                },
            ),
            PluginTool(
                name="obsidian.updateNote",
                display_name="Update Note",
                description="Overwrite an existing note's contents",
                parameters={"path": {"type": "string"}, "content": {"type": "string"}},
            ),
            PluginTool(
                name="obsidian.appendToNote",
                display_name="Append To Note",
                description="Append content to an existing note",
                parameters={"path": {"type": "string"}, "content": {"type": "string"}},
            ),
            PluginTool(
                name="obsidian.getNote",
                display_name="Get Note",
                description="Read a note's contents",
                parameters={"path": {"type": "string"}},
            ),
            PluginTool(
                name="obsidian.searchVault",
                display_name="Search Vault",
                description="Full-text search across the vault",
                parameters={"query": {"type": "string"}},
            ),
            PluginTool(
                name="obsidian.listNotes",
                display_name="List Notes",
                description="List notes in a folder",
                parameters={"folder": {"type": "string"}},
            ),
        ],
        website_url="https://obsidian.md",
        docs_url="https://coddingtonbear.github.io/obsidian-local-rest-api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key")) and bool(self.credentials.get("vault_url"))

    @property
    def _base(self) -> str:
        return self.credentials["vault_url"].rstrip("/")

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['api_key']}",
            "Content-Type": "text/markdown",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
            if tool_name in {"obsidian.createNote", "obsidian.updateNote"}:
                resp = await client.put(
                    f"{self._base}/vault/{parameters['path']}",
                    headers={**self._headers, "Content-Type": "text/markdown"},
                    content=parameters["content"].encode("utf-8"),
                )
            elif tool_name == "obsidian.appendToNote":
                resp = await client.post(
                    f"{self._base}/vault/{parameters['path']}",
                    headers={**self._headers, "Content-Type": "text/markdown"},
                    content=parameters["content"].encode("utf-8"),
                )
            elif tool_name == "obsidian.getNote":
                resp = await client.get(
                    f"{self._base}/vault/{parameters['path']}",
                    headers=self._headers,
                )
                resp.raise_for_status()
                return {"path": parameters["path"], "content": resp.text}
            elif tool_name == "obsidian.searchVault":
                resp = await client.post(
                    f"{self._base}/search/simple/",
                    headers={**self._headers, "Content-Type": "application/json"},
                    params={"query": parameters["query"]},
                )
            elif tool_name == "obsidian.listNotes":
                folder = parameters.get("folder", "").strip("/")
                resp = await client.get(
                    f"{self._base}/vault/{folder}",
                    headers={**self._headers, "Accept": "application/json"},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            if not resp.content:
                return {"status": "ok"}
            ct = resp.headers.get("content-type", "")
            return resp.json() if "json" in ct else {"raw": resp.text}
