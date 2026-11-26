"""Native tool-calling adapter.

Converts the existing Tool registry into OpenAI-style function definitions,
binds them to a model that supports it, and reads structured tool calls back.
When the model cannot bind tools the engine keeps its text-ReAct path.

No network calls, no keys, no provider-specific imports here.
"""
from __future__ import annotations

import inspect
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, ToolMessage

from tools import TOOL_REGISTRY

log = logging.getLogger("native_tools")

_TYPE_MAP = {
    str: "string", int: "integer", float: "number", bool: "boolean",
    list: "array", dict: "object", List: "array", Dict: "object",
}


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: Dict[str, Any]
    id: str


def _json_type(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return "string"
    origin = getattr(annotation, "__origin__", None)
    if origin in (list, List, set):
        return "array"
    if origin in (dict, Dict):
        return "object"
    return _TYPE_MAP.get(annotation, "string")


def _description_for(cls: type, param: str) -> str:
    """Pull the Args: line for a parameter from the tool's run docstring."""
    doc = inspect.getdoc(getattr(cls, "run", None)) or ""
    for line in doc.splitlines():
        s = line.strip()
        if s.startswith(param + ":") or s.startswith(param + " ("):
            return s.split(":", 1)[-1].strip()[:200]
    return ""


def build_definitions(names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """OpenAI-style function specs for every registered tool.

    Explicit `run()` parameters take precedence; tools that only accept
    **kwargs fall back to their `example` dict so the model still sees the
    expected argument shape.
    """
    defs: List[Dict[str, Any]] = []
    for name in sorted(names or TOOL_REGISTRY):
        cls = TOOL_REGISTRY.get(name)
        if cls is None:
            continue
        try:
            sig = inspect.signature(cls.run)
        except (TypeError, ValueError):
            sig = None
        props: Dict[str, Any] = {}
        required: List[str] = []
        if sig is not None:
            for pname, param in sig.parameters.items():
                if pname in ("self", "cls", "args", "kwargs"):
                    continue
                if param.kind in (inspect.Parameter.VAR_POSITIONAL,
                                  inspect.Parameter.VAR_KEYWORD):
                    continue
                entry: Dict[str, Any] = {"type": _json_type(param.annotation)}
                desc = _description_for(cls, pname)
                if desc:
                    entry["description"] = desc
                props[pname] = entry
                if param.default is inspect.Parameter.empty:
                    required.append(pname)
        example = getattr(cls, "example", None)
        if not props and isinstance(example, dict):
            for key, value in example.items():
                props[str(key)] = {"type": _json_type(type(value))}
            # Operation-selector tools need only `op`; marking every example
            # key required made models invent fields for unrelated ops.
            required = ["op"] if "op" in props else list(props)
        defs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": str(getattr(cls, "description", name))[:400],
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            },
        })
    return defs


# Core tools that must always be available when native calling is on.
_CORE_TOOLS = ("MemoryLogicCalculator", "UniversalFileManager",
               "PythonInterpreter", "WebSearch")


def select_tool_names(task: str, limit: int) -> List[str]:
    """Pick the most task-relevant tool names, capped at `limit`.

    Binding all 44 definitions exceeded Groq's 8000 TPM on-demand limit
    (413: requested 8456). Relevance here is cheap lexical overlap; it only
    decides which schemas are advertised, never what the agent may execute.
    """
    text = re.findall(r"\w+", str(task or "").lower(), re.UNICODE)
    if not text:
        return list(_CORE_TOOLS[:limit])
    scored: List[Tuple[float, str]] = []
    for name, cls in TOOL_REGISTRY.items():
        blob = f"{name} {getattr(cls, 'description', '')} {getattr(cls, 'example', '')}".lower()
        hits = sum(1 for token in set(text) if len(token) > 2 and token in blob)
        value = float(hits) + (2.0 if name in _CORE_TOOLS else 0.0)
        scored.append((value, name))
    scored.sort(key=lambda item: (-item[0], item[1]))
    picked = [name for _, name in scored[:max(1, limit)]]
    for core in _CORE_TOOLS:
        if len(picked) >= limit:
            break
        if core not in picked:
            picked.append(core)
    return picked[:max(1, limit)]


def prepare(brain: Any, defs: Optional[List[Dict[str, Any]]] = None
            ) -> Tuple[Any, bool]:
    """Return (brain_to_use, native_enabled).

    A model without `bind_tools`, or one that raises on binding, is used as-is
    so the text-ReAct path still works.
    """
    binder = getattr(brain, "bind_tools", None)
    if not callable(binder):
        return brain, False
    try:
        bound = binder(defs if defs is not None else build_definitions())
        if bound is None:
            return brain, False
        return bound, True
    except Exception as exc:
        log.info("native tool binding unavailable: %s", exc)
        return brain, False


def extract_calls(message: Any) -> List[ToolCall]:
    """Read structured calls from a LangChain AIMessage."""
    raw = getattr(message, "tool_calls", None) or []
    calls: List[ToolCall] = []
    for item in raw:
        if isinstance(item, dict):
            name = item.get("name")
            args = item.get("args") or {}
            cid = item.get("id") or ""
        else:
            name = getattr(item, "name", None)
            args = getattr(item, "args", {}) or {}
            cid = getattr(item, "id", "") or ""
        if not name:
            continue
        calls.append(ToolCall(str(name), dict(args) if isinstance(args, dict)
                              else {"model_input": args}, str(cid)))
    return calls


def make_tool_message(call: ToolCall, observation: str) -> ToolMessage:
    return ToolMessage(content=str(observation), tool_call_id=call.id or "unknown",
                       name=call.name)


__all__ = ["ToolCall", "build_definitions", "prepare", "extract_calls",
           "make_tool_message", "AIMessage"]
