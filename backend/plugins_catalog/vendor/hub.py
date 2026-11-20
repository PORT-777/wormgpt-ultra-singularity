"""One validated plugin per vendored repository.

Every plugin is read-only, needs no credentials, and exposes the same safe
surface: repo info, skill search/read, file list/read and text search. Oh My
Zsh additionally exposes its plugin/theme catalogs.
"""
from __future__ import annotations

from typing import Any, Dict, List

try:
    from plugins_system.registry import registry_instance
    from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
except ImportError:  # pragma: no cover - discovery imports with backend on sys.path
    from backend.plugins_system.registry import registry_instance
    from backend.plugins_system.sdk import BasePlugin, PluginManifest, PluginTool

import vendor_hub


def _tool(pid: str, suffix: str, description: str,
          properties: Dict[str, Any] | None = None) -> PluginTool:
    return PluginTool(
        name=f"{pid}.{suffix}",
        display_name=suffix.replace("_", " ").title(),
        description=description,
        parameters={
            "type": "object",
            "properties": properties or {},
            "additionalProperties": False,
        },
        requires_auth=False,
    )


def _tools(pid: str, repo_id: str) -> List[PluginTool]:
    tools = [
        _tool(pid, "info", f"Show metadata and skill count for {repo_id}."),
        _tool(pid, "skills", f"Search the SKILL.md catalog of {repo_id}.",
              {"query": {"type": "string"}, "limit": {"type": "integer"}}),
        _tool(pid, "skill_read", f"Read one SKILL.md from {repo_id}.",
              {"skill_id": {"type": "string"}}),
        _tool(pid, "search", f"Search source text inside {repo_id}.",
              {"query": {"type": "string"}, "limit": {"type": "integer"}}),
        _tool(pid, "list", f"List files in {repo_id}.",
              {"path": {"type": "string"}, "limit": {"type": "integer"}}),
        _tool(pid, "read", f"Read a text file from {repo_id}.",
              {"path": {"type": "string"}}),
    ]
    if repo_id == "ohmyzsh":
        tools += [
            _tool(pid, "plugins_list", "List Oh My Zsh plugins."),
            _tool(pid, "themes_list", "List Oh My Zsh themes."),
        ]
    elif repo_id == "ruflo":
        tools.append(_tool(pid, "agents_list", "List Ruflo agent definitions."))
    elif repo_id == "agentic-skills":
        tools.append(_tool(pid, "categories", "List Agentic Awesome Skills categories."))
    return tools


def _manifest(meta: Dict[str, Any], pid: str) -> PluginManifest:
    return PluginManifest(
        id=pid,
        name=f"Vendor: {meta['name']}",
        description=f"Read-only access to the vendored {meta['name']} repository.",
        long_description=(
            f"{meta['role']}. Search and read its SKILL.md playbooks and source "
            "files with path confinement and size limits. No credentials required."
        ),
        version="1.0.0",
        author="PORT 777 AI",
        icon="📚",
        category=meta.get("category", "custom"),
        tags=["vendor", "reference", str(meta.get("keywords", ["reference"])[0])],
        auth_type="none",
        auth_config={},
        tools=_tools(pid, meta["id"]),
        website_url=meta.get("url") or "https://github.com",
        docs_url=meta.get("url") or "https://github.com",
        is_free=True,
        is_official=False,
    )


class _VendorRepoPlugin(BasePlugin):
    """Base implementation; `manifest` and `_repo_id` are set per subclass."""

    manifest: PluginManifest
    _repo_id: str = ""

    def _validate_credentials(self) -> bool:
        return True

    async def test_connection(self) -> Dict[str, Any]:
        info = vendor_hub.repo_info(self._repo_id)
        return {"status": "ok" if info["checked_out"] else "missing",
                "repo": self._repo_id, "skills": info["skills"]}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        repo_id = self._repo_id
        suffix = tool_name.split(".", 1)[-1] if "." in tool_name else tool_name
        params = parameters or {}
        if suffix == "info":
            return vendor_hub.repo_info(repo_id)
        if suffix == "skills":
            return vendor_hub.search(str(params.get("query") or repo_id),
                                     repo_id, int(params.get("limit") or 10))
        if suffix == "skill_read":
            return vendor_hub.read_skill(str(params.get("skill_id") or ""))
        if suffix == "search":
            return vendor_hub.repo_search(repo_id, str(params.get("query") or ""),
                                          int(params.get("limit") or 20))
        if suffix == "list":
            return vendor_hub.list_files(repo_id, str(params.get("path") or ""),
                                         int(params.get("limit") or 100))
        if suffix == "read":
            return vendor_hub.read_file(repo_id, str(params.get("path") or ""))
        if suffix == "plugins_list":
            return vendor_hub.list_files(repo_id, "plugins", 300)
        if suffix == "themes_list":
            return vendor_hub.list_files(repo_id, "themes", 300)
        if suffix == "agents_list":
            return vendor_hub.list_files(repo_id, ".agents", 300)
        if suffix == "categories":
            return vendor_hub.list_files(repo_id, "plugins", 300)
        raise ValueError(f"unknown tool: {tool_name}")


def _make_plugin(meta: Dict[str, Any], pid: str):
    repo_id = meta["id"]
    name = f"Vendor{repo_id.replace('-', '_')}"
    plugin_cls = type(name, (_VendorRepoPlugin,), {
        "manifest": _manifest(meta, pid),
        "_repo_id": repo_id,
        "__module__": __name__,
    })
    return plugin_cls


for _meta in vendor_hub.REPOS:
    _pid = "vendor_" + _meta["id"].replace("-", "_")
    registry_instance.register_plugin(_make_plugin(_meta, _pid))
