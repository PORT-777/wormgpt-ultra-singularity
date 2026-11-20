"""
Tool :: McpTool (guarded MCP tool execution bridge)

Task 3: allows the agent to call a configured MCP server tool only when:
- global MCP is enabled (config MCP_ENABLED=true)
- request has Full Access (per-run context)
- server/tool/args are valid
- MCP SDK is installed

Execution is audited and output is bounded.
"""
from __future__ import annotations

import json
from typing import Any

from .base import Tool, full_access


class McpTool(Tool):
    name = "McpTool"
    description = (
        "Call a configured MCP server tool. Available on every message when "
        "MCP_ENABLED=true; wormgpt-local exposes all vendor_* tools. Full Access "
        "is required for execution. Input: {'server':'name','tool':'tool_name','arguments':{...}}"
    )
    example = {"server": "filesystem", "tool": "list_directory", "arguments": {"path": "."}}

    async def run(self, **kw: Any) -> str:
        import mcp_manager

        server = str(kw.get("server", "") or kw.get("server_name", "")).strip()
        tool = str(kw.get("tool", "") or kw.get("tool_name", "")).strip()
        arguments = kw.get("arguments", kw.get("args", {}))
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return "ERROR: MCP 'arguments' must be a JSON object"

        result = await mcp_manager.call_tool(
            server, tool, arguments, allow_execution=True)
        if result.get("ok"):
            payload = result.get("result") or {}
            text = payload.get("text") or ""
            if payload.get("structuredContent") is not None and not text:
                try:
                    text = json.dumps(payload["structuredContent"], ensure_ascii=False, indent=2)
                except Exception:
                    text = str(payload["structuredContent"])
            if not text:
                text = "[MCP tool returned no text content]"
            header = f"[MCP ok] {server}.{tool} ({result.get('elapsed_ms', '?')} ms)"
            if payload.get("truncated"):
                header += " [truncated]"
            return header + "\n" + text

        err = result.get("error") or "unknown MCP error"
        return f"ERROR: MCP {server}.{tool} failed — {err}"
