"""Unified tool registry + execution with schema validation & permissions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

TOOL_REGISTRY: Dict[str, "Tool"] = {}


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], Any]
    requires_approval: bool = False
    allowed_roles: List[str] = field(default_factory=lambda: ["admin", "user"])


def register(tool: Tool) -> None:
    TOOL_REGISTRY[tool.name] = tool


def list_tools(role: str = "user") -> List[dict]:
    out = []
    for t in TOOL_REGISTRY.values():
        if role in t.allowed_roles:
            out.append({"name": t.name, "description": t.description,
                        "input_schema": t.input_schema,
                        "requires_approval": t.requires_approval})
    return out


def _validate(schema: dict, args: dict) -> Optional[str]:
    required = schema.get("required", [])
    for r in required:
        if r not in args:
            return f"missing required field: {r}"
    props = schema.get("properties", {})
    for k, v in args.items():
        if k in props:
            typ = props[k].get("type")
            if typ == "string" and not isinstance(v, str):
                return f"{k} must be string"
            if typ == "number" and not isinstance(v, (int, float)):
                return f"{k} must be number"
            if typ == "boolean" and not isinstance(v, bool):
                return f"{k} must be boolean"
    return None


def execute(name: str, args: dict, role: str = "user",
            approved: bool = False) -> dict:
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return {"ok": False, "error": "tool not found"}
    if role not in tool.allowed_roles:
        return {"ok": False, "error": "permission denied"}
    err = _validate(tool.input_schema, args or {})
    if err:
        return {"ok": False, "error": err}
    if tool.requires_approval and not approved:
        return {"ok": False, "error": "approval required", "requires_approval": True}
    try:
        result = tool.handler(args or {})
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
