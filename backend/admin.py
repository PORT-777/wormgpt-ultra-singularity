"""Admin dashboard aggregations."""
from __future__ import annotations

from typing import Dict, Any

from usage_tracker import summary as usage_summary
from health_monitor import all_status
from api_logger import recent_errors
from agents import list_agents
from scheduled_tasks import list_all as list_scheduled
from workspaces import list_all as list_workspaces


def dashboard() -> Dict[str, Any]:
    return {
        "usage": usage_summary(),
        "providers": all_status(),
        "errors_recent": len(recent_errors(100)),
        "agents": len(list_agents()),
        "scheduled_tasks": len(list_scheduled()),
        "workspaces": len(list_workspaces()),
    }
