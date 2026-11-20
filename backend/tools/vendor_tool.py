"""Agent-facing tool for every vendored repository (auto-discovered)."""
from __future__ import annotations

import json
from typing import Any

from .base import Tool


def _hub():
    import vendor_hub

    return vendor_hub


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)[:40000]


class VendorTool(Tool):
    name = "VendorTool"
    description = (
        "Search and read the vendored reference repositories (AutoGPT, Claude Skills, "
        "OpenHands, ECC, Hermes Agent, DeepSeek Harness, Career Ops, Oh My Zsh, Ruflo, "
        "Agentic Awesome Skills). Actions: repos, info, skills, skill, search, files, "
        "read, plugins. Always available; all access is read-only."
    )
    example = {"action": "skills", "query": "swarm orchestration", "limit": 5}

    async def run(self, action: str = "repos", repo: str = "", query: str = "",
                  skill_id: str = "", path: str = "", limit: int = 10,
                  **_: Any) -> str:
        try:
            hub = _hub()
            if action == "repos":
                return _dump(hub.list_repos())
            if action == "info":
                return _dump(hub.repo_info(repo))
            if action == "skills" or action == "search":
                return _dump(hub.search(query, repo, limit))
            if action == "skill":
                return _dump(hub.read_skill(skill_id))
            if action == "files":
                return _dump(hub.list_files(repo, path, limit))
            if action == "read":
                return _dump(hub.read_file(repo, path))
            if action == "plugins":
                return _dump(hub.plugin_tools())
            return ("ERROR: VendorTool action must be "
                    "repos|info|skills|skill|search|files|read|plugins")
        except Exception as exc:
            return f"ERROR: VendorTool {action} failed: {type(exc).__name__}: {exc}"
