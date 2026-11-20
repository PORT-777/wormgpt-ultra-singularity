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
