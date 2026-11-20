"""Agent-facing adapter for the Code & Binary Intelligence Engine."""
from __future__ import annotations

import json
from typing import Any

from .base import Tool


class CodeIntelligence(Tool):
    name = "CodeIntelligence"
    description = (
        "Real project and binary intelligence. Actions: create_task, scan_project, find_symbol, "
        "call_hierarchy, code_quality, analyze_binary, toolchain, save_report, export_task, list_tasks. "
        "Operates on actual files inside isolated task workspaces and returns real tool output."
    )
    example = {"action": "scan_project", "path": "D:/path/to/project"}

    async def run(
        self,
        action: str = "",
        path: str = "",
        query: str = "",
        task_id: str = "",
        name: str = "analysis",
        include_disasm: bool = False,
        report: dict | None = None,
        **_: Any,
    ) -> str:
        try:
            from intelligence import agents, binary_intel, project_intel, task_workspace, toolchain

            action = (action or "").strip().lower()
            if action == "toolchain":
                result = toolchain.discover()
            elif action == "plan_specialists":
                result = {"plan": agents.plan(query or name or "analyze", path or "project")}
            elif action == "create_task":
                result = task_workspace.create_task(name or "analysis", path or "")
            elif action == "list_tasks":
                result = {"tasks": task_workspace.list_tasks()}
            elif action == "scan_project":
                result = project_intel.scan_project(path or task_workspace.get_task(task_id)["paths"]["project"])
            elif action == "find_symbol":
                result = {"matches": project_intel.find_symbol(path, query)}
            elif action == "call_hierarchy":
                result = project_intel.call_hierarchy(path, query)
            elif action == "code_quality":
                result = project_intel.code_quality(path)
            elif action == "analyze_binary":
                target = path or str(task_workspace.get_task(task_id)["paths"]["input"])
                result = binary_intel.analyze(target, include_disasm=bool(include_disasm))
            elif action == "save_report":
                result = {"path": task_workspace.save_report(task_id, name or "report", report or {})}
            elif action == "export_task":
                result = {"path": task_workspace.export_task(task_id)}
            else:
                return "ERROR: CodeIntelligence action must be one of: " + ", ".join([
                    "toolchain", "create_task", "list_tasks", "scan_project", "find_symbol",
                    "call_hierarchy", "code_quality", "analyze_binary", "save_report", "export_task",
                ])
            return json.dumps(result, ensure_ascii=False, indent=2, default=str)[:60000]
        except Exception as exc:
            return f"ERROR: CodeIntelligence {action} failed: {type(exc).__name__}: {exc}"
