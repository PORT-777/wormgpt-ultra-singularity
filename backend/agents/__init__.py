"""Production multi-agent package.

Backward compatibility: the historical `agents.py` module (SQLite-persisted
agent/task CRUD) is loaded from its original file path and re-exported, so
existing importers such as `from agents import list_agents` keep working.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_LEGACY = Path(__file__).resolve().parent.parent / "agents.py"
if _LEGACY.exists():
    _spec = importlib.util.spec_from_file_location("legacy_agents", _LEGACY)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        for _name in (
            "create_agent", "get_agent", "list_agents", "delete_agent",
            "create_task", "update_task", "get_task", "list_tasks",
            "check_permission",
        ):
            globals()[_name] = getattr(_mod, _name)
