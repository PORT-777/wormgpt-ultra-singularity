"""Specialist agent roles for software and binary analysis.

The orchestrator (multi_agent.MultiAgentOrchestrator) assigns these roles;
this module defines the prompts and keeps the assignment inside the existing
agent engine rather than creating a second orchestration system.
"""
from __future__ import annotations

from typing import Any, Dict, List

SPECIALISTS: Dict[str, str] = {
    "project_explorer": "Map the project tree, languages, frameworks, entry points and file roles. Do not modify files.",
    "architecture_analyst": "Derive module relationships, dependency direction, layers and architecture risks from the scan output.",
    "code_review": "Review changed code for correctness, edge cases and regressions. Report concrete file/line findings.",
    "refactoring": "Propose the smallest safe refactor that preserves behaviour; list exactly which files change.",
    "debugging": "Use failing test output and tool observations to identify root cause; verify with a rerun.",
    "binary_analysis": "Identify binary format, architecture, imports, sections, strings and hardening from real tool output.",
    "reverse_engineering": "Disassemble/decompile with available tools; label recovered output as approximate and never invent source.",
    "dependency_analyst": "Analyse imports, packages, circular dependencies and version risks.",
    "security_analysis": "Flag security-relevant code and binary indicators without executing uploaded artifacts.",
    "testing": "Design and run the smallest harmless verification; report real exit codes and output.",
    "build_agent": "Inspect build systems and run builds only when authorized; verify produced artifacts exist.",
    "independent_verification": "Independently re-check the findings against actual files/tool output and resolve contradictions.",
}


def plan(task_description: str, artifact_type: str = "project") -> List[Dict[str, Any]]:
    base = ["project_explorer", "dependency_analyst", "independent_verification"]
    if artifact_type in ("binary", "apk", "exe", "elf", "dll"):
        base = ["binary_analysis", "reverse_engineering", "security_analysis", "independent_verification"]
    elif any(word in task_description.lower() for word in ("refactor", "improve", "cleanup")):
        base = ["project_explorer", "code_review", "refactoring", "testing", "independent_verification"]
    elif any(word in task_description.lower() for word in ("bug", "fail", "error", "debug")):
        base = ["project_explorer", "debugging", "testing", "independent_verification"]
    elif any(word in task_description.lower() for word in ("build", "package", "release")):
        base = ["project_explorer", "build_agent", "testing", "independent_verification"]
    return [{"agent": role, "instruction": SPECIALISTS[role]} for role in base]
