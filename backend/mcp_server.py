"""Minimal stdio MCP server for the local WormGPT backend.

Dependency-free JSON-RPC over newline-delimited JSON. It exposes read-only
introspection tools so the MCP config in ../.mcp.json has a real target.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from plugins_system.registry import registry_instance  # noqa: E402
import vendor_hub  # noqa: E402

TOOLS = [
    {
        "name": "agent_status",
        "description": "Report backend version and how many plugins are registered.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "plugins_list",
        "description": "List registered plugin ids, names and categories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "max entries (default 100)"}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "vendor_repos_list",
        "description": "List all vendored repositories with their skill counts and roles.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "vendor_info",
        "description": "Show metadata for one vendored repository.",
        "inputSchema": {
            "type": "object",
            "properties": {"repo": {"type": "string"}},
            "required": ["repo"], "additionalProperties": False,
        },
    },
    {
        "name": "vendor_skills_search",
        "description": "Search SKILL.md playbooks across all vendored repositories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "repo": {"type": "string", "description": "optional repo id"},
                "limit": {"type": "integer"},
            },
            "required": ["query"], "additionalProperties": False,
        },
    },
    {
        "name": "vendor_skill_read",
        "description": "Read one indexed SKILL.md by its id (repo:relative/path).",
        "inputSchema": {
            "type": "object",
            "properties": {"skill_id": {"type": "string"}},
            "required": ["skill_id"], "additionalProperties": False,
        },
    },
    {
        "name": "vendor_file_list",
        "description": "List files inside a vendored repository (read-only).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "path": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["repo"], "additionalProperties": False,
        },
    },
    {
        "name": "vendor_file_read",
        "description": "Read a text file inside a vendored repository (read-only, size limited).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["repo", "path"], "additionalProperties": False,
        },
    },
    {
        "name": "vendor_repo_search",
        "description": "Search source text inside one vendored repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["repo", "query"], "additionalProperties": False,
        },
    },
    {
        "name": "vendor_plugins",
        "description": "List the vendor plugin catalog and the tools each plugin exposes.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

_discovered = False


def _text(payload) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}]}


async def _ensure_discovered() -> None:
    global _discovered
    if not _discovered:
        await registry_instance.discover_plugins()
        _discovered = True


async def _call(name: str, arguments: dict):
    await _ensure_discovered()
    if name == "agent_status":
        return _text({
            "service": "WormGPT_Ultra_Singularity",
            "plugins_loaded": len(registry_instance._plugins),
        })
    if name == "plugins_list":
        limit = int(arguments.get("limit") or 100)
        manifests = registry_instance.get_all_manifests()[:limit]
        return _text([
            {
                "id": m.get("id"),
                "name": m.get("name"),
                "category": m.get("category"),
            }
            for m in manifests
        ])
    if name == "vendor_repos_list":
        return _text(vendor_hub.list_repos())
    if name == "vendor_info":
        return _text(vendor_hub.repo_info(arguments.get("repo", "")))
    if name == "vendor_skills_search":
        return _text(vendor_hub.search(
            arguments.get("query", ""), arguments.get("repo", ""),
            int(arguments.get("limit") or 10)))
    if name == "vendor_skill_read":
        return _text(vendor_hub.read_skill(arguments.get("skill_id", "")))
    if name == "vendor_file_list":
        return _text(vendor_hub.list_files(
            arguments.get("repo", ""), arguments.get("path", ""),
            int(arguments.get("limit") or 100)))
    if name == "vendor_file_read":
        return _text(vendor_hub.read_file(
            arguments.get("repo", ""), arguments.get("path", "")))
    if name == "vendor_repo_search":
        return _text(vendor_hub.repo_search(
            arguments.get("repo", ""), arguments.get("query", ""),
            int(arguments.get("limit") or 20)))
    if name == "vendor_plugins":
        return _text(vendor_hub.plugin_tools())
    raise ValueError(f"unknown tool: {name}")


async def _dispatch(message: dict):
    method = message.get("method")
    params = message.get("params") or {}
    msg_id = message.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "wormgpt-local", "version": "6.1.0"},
            },
        }
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        try:
            result = await _call(params.get("name", ""), params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except Exception as exc:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32000, "message": f"{type(exc).__name__}: {exc}"},
            }
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


async def _serve() -> None:
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            return
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = await _dispatch(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(_serve())
