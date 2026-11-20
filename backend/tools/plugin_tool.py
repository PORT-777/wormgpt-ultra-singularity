"""
Agent bridge into the dynamic plugin system.

Two tools are exposed to the model:

  * PluginList  — discover installed + enabled plugin actions
  * PluginTool  — invoke any of them by fully-qualified name

The active user defaults to PLUGIN_USER_ID (or "default_user"). A contextvar
override is available for future multi-tenant routing.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
from typing import Any, Dict, Optional

from tools.base import Tool

log = logging.getLogger("PluginTool")

_USER_CTX: contextvars.ContextVar[str] = contextvars.ContextVar(
    "plugin_user_id", default=""
)


def set_plugin_user(user_id: str) -> None:
    """Set the plugin-owner for the current run (multi-user hook)."""
    _USER_CTX.set(str(user_id or ""))


def current_plugin_user() -> str:
    return _USER_CTX.get() or os.environ.get("PLUGIN_USER_ID") or "default_user"


def _dump(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


class PluginList(Tool):
    name = "PluginList"
    description = (
        "List third-party plugin actions currently available to you. "
        "Call this before PluginTool when you are unsure which integrations "
        "the user has connected."
    )
    example: Dict[str, Any] = {}

    async def run(self, **kwargs: Any) -> str:
        try:
            from plugins_system.deps import get_runtime

            tools = await get_runtime().get_user_tools(current_plugin_user())
        except Exception as exc:  # never break the agent loop
            log.warning("PluginList failed: %s", exc)
            return f"ERROR: plugin subsystem unavailable: {exc}"

        if not tools:
            return "No plugin actions are currently installed and enabled."

        lines = [f"{len(tools)} plugin action(s) available:"]
        for t in tools:
            params = ", ".join((t.get("parameters") or {}).keys()) or "none"
            lines.append(f"- {t['name']}: {t.get('description', '')} (args: {params})")
        return "\n".join(lines)


class PluginTool(Tool):
    name = "PluginTool"
    description = (
        "Invoke an installed third-party plugin action. Pass the fully-qualified "
        "action name (e.g. virustotal.lookupHash) and its arguments object. "
        "Use PluginList first to see what is available."
    )
    example: Dict[str, Any] = {
        "action": "virustotal.lookupHash",
        "args": {"hash": "44d88612fea8a8f36de82e1278abb02f"},
    }

    async def run(
        self,
        action: str = "",
        args: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        if not action:
            return "ERROR: 'action' is required (e.g. virustotal.lookupHash). Call PluginList to discover actions."

        payload: Dict[str, Any] = dict(args or {})
        # Tolerate models that inline arguments instead of nesting them.
        for key, value in kwargs.items():
            payload.setdefault(key, value)

        try:
            from plugins_system.deps import get_runtime
            from plugins_system.runtime import PluginExecutionError

            result = await get_runtime().execute_tool(
                current_plugin_user(), action, payload
            )
            return _dump(result)
        except PluginExecutionError as exc:
            return f"ERROR: plugin '{exc.plugin_id}' failed: {exc.message}"
        except Exception as exc:
            log.exception("PluginTool crashed for action=%s", action)
            return f"ERROR: plugin call failed: {type(exc).__name__}: {exc}"
