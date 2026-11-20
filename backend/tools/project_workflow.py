"""
Tool :: ProjectWorkflow

Autonomous engineering workflow state machine:
  PLAN -> IMPLEMENT -> TEST -> DEBUG -> VERIFY -> DONE
  (loops back to DEBUG on failure, up to MAX cycles)

Each state uses the AgentEngine's tool-calling loop to execute and
self-correct. Designed for Wave 3: Engineering Mastery.
"""
from __future__ import annotations

import asyncio
import re
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import Tool


def _engine():
    """Lazy import to avoid circular import: agent_engine imports from tools."""
    from agent_engine import ENGINE  # noqa: WPS433
    return ENGINE


class WorkflowState(str, Enum):
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    TEST = "TEST"
    DEBUG = "DEBUG"
    VERIFY = "VERIFY"
    DONE = "DONE"


class ProjectWorkflow(Tool):
    name = "ProjectWorkflow"
    description = (
        "Autonomous engineering workflow: PLAN -> IMPLEMENT -> TEST -> "
        "DEBUG -> VERIFY -> DONE. Runs the full software engineering loop "
        "with self-correction. Input: { goal: '...', workspace_path: '...', "
        "max_cycles: 5 }."
    )
    example = {
        "goal": "Add a CLI health-check command to the project",
        "workspace_path": ".",
        "max_cycles": 5,
    }

    # ------------------------------------------------------------------ #
    #  Entry point
    # ------------------------------------------------------------------ #
    async def run(
        self,
        goal: str = "",
        workspace_path: str = ".",
        max_cycles: int = 5,
        **_: Any,
    ) -> str:
        if not goal.strip():
            return "ERROR: empty goal"

        max_cycles = max(1, min(int(max_cycles or 5), 10))
        state = WorkflowState.PLAN
        cycle = 0
        plan: Optional[str] = None
        implementation_notes: List[str] = []
        test_results: List[str] = []
        debug_attempts: List[str] = []

        lines: List[str] = [
            f"⚙️ ProjectWorkflow — Goal: {goal}",
            f"📂 Workspace: {workspace_path}",
            f"🔁 Max cycles: {max_cycles}",
            "",
        ]

        while state != WorkflowState.DONE and cycle < max_cycles:
            cycle += 1
            lines.append(f"--- Cycle {cycle}: State = {state.value} ---")

            if state == WorkflowState.PLAN:
                plan = await self._state_plan(goal, workspace_path)
                lines.append(f"[PLAN] {plan[:600]}")
                state = WorkflowState.IMPLEMENT

            elif state == WorkflowState.IMPLEMENT:
                result = await self._state_implement(goal, plan or goal, workspace_path)
                implementation_notes.append(result)
                lines.append(f"[IMPLEMENT] {result[:400]}")
                state = WorkflowState.TEST

            elif state == WorkflowState.TEST:
                result = await self._state_test(goal, workspace_path, implementation_notes)
                test_results.append(result)
                passed = "PASS" in result.upper() or "✓" in result or "success" in result.lower()
                lines.append(f"[TEST] {result[:400]}")
                if passed:
                    state = WorkflowState.VERIFY
                else:
                    state = WorkflowState.DEBUG

            elif state == WorkflowState.DEBUG:
                result = await self._state_debug(
                    goal, workspace_path, test_results[-1] if test_results else "",
                    implementation_notes, debug_attempts,
                )
                debug_attempts.append(result)
                lines.append(f"[DEBUG] {result[:400]}")
                # After debugging, go back to TEST to re-verify
                state = WorkflowState.TEST

            elif state == WorkflowState.VERIFY:
                result = await self._state_verify(goal, workspace_path, implementation_notes, test_results)
                lines.append(f"[VERIFY] {result[:500]}")
                state = WorkflowState.DONE

        if state == WorkflowState.DONE:
            lines.append("")
            lines.append("✅ Workflow complete — DONE")
        else:
            lines.append("")
            lines.append(f"⚠️ Workflow hit max cycles ({max_cycles}) without reaching DONE")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  State implementations
    # ------------------------------------------------------------------ #
    async def _state_plan(self, goal: str, workspace_path: str) -> str:
        """PLAN: break the goal into concrete, ordered steps."""
        prompt = (
            "You are a senior systems engineer. Create a concise, ordered "
            "implementation plan for the goal below. Each step must be "
            "actionable (read file, edit file, create file, run command). "
            "Output ONLY the plan as a numbered list.\n\n"
            f"GOAL: {goal}\nWORKSPACE: {workspace_path}"
        )
        return await _engine().run(
            prompt,
            session_id="workflow-plan",
            system_prompt="You are a planning engineer. Output ONLY a numbered plan.",
            depth="deep",
            model_route="auto",
        )

    async def _state_implement(self, goal: str, plan: str, workspace_path: str) -> str:
        """IMPLEMENT: execute each plan step using tools."""
        prompt = (
            "You are a senior software engineer implementing a plan. "
            "Execute each step using your tools (read_file, write_file, "
            "SmartEdit, DiffPatchTool, execute_command). Ship complete, "
            "working code. After implementing, briefly summarize what was "
            "changed.\n\n"
            f"GOAL: {goal}\nWORKSPACE: {workspace_path}\n\nPLAN:\n{plan}"
        )
        return await _engine().run(
            prompt,
            session_id="workflow-implement",
            system_prompt="You are an implementation engineer. Ship working code.",
            depth="singularity",
            model_route="auto",
        )

    async def _state_test(
        self, goal: str, workspace_path: str, notes: List[str],
    ) -> str:
        """TEST: run tests/commands to verify the implementation."""
        latest = notes[-1] if notes else ""
        prompt = (
            "You are a QA engineer. Verify the implementation works by "
            "running relevant commands (tests, lint, compile, run). "
            "Report exact pass/fail with observed output. "
            "Output must start with PASS or FAIL.\n\n"
            f"GOAL: {goal}\nWORKSPACE: {workspace_path}\n"
            f"IMPLEMENTATION NOTES: {latest[:1000]}"
        )
        return await _engine().run(
            prompt,
            session_id="workflow-test",
            system_prompt="You are a QA tester. Start your answer with PASS or FAIL.",
            depth="deep",
            model_route="auto",
        )

    async def _state_debug(
        self,
        goal: str,
        workspace_path: str,
        test_output: str,
        notes: List[str],
        attempts: List[str],
    ) -> str:
        """DEBUG: analyze failures and fix them."""
        attempt_no = len(attempts) + 1
        prompt = (
            "You are a debugging engineer. The implementation failed testing. "
            "Analyze the error, fix the code using your tools, and summarize "
            "the fix. Do not repeat previous failed approaches.\n\n"
            f"GOAL: {goal}\nWORKSPACE: {workspace_path}\n"
            f"TEST OUTPUT (FAILURE): {test_output[:1500]}\n"
            f"PREVIOUS DEBUG ATTEMPTS: {len(attempts)}\n"
            f"LATEST NOTES: {notes[-1] if notes else '(none)'[:500]}"
        )
        return await _engine().run(
            prompt,
            session_id=f"workflow-debug-{attempt_no}",
            system_prompt="You are a debugging engineer. Fix failures.",
            depth="deep",
            model_route="auto",
        )

    async def _state_verify(
        self,
        goal: str,
        workspace_path: str,
        notes: List[str],
        test_results: List[str],
    ) -> str:
        """VERIFY: final confirmation that the goal is met."""
        prompt = (
            "You are a verification engineer. Confirm the implementation "
            "fully satisfies the goal. Review the implementation notes and "
            "test results. Output a concise verification report.\n\n"
            f"GOAL: {goal}\nWORKSPACE: {workspace_path}\n"
            f"IMPLEMENTATION NOTES: {' | '.join(notes)[:1500]}\n"
            f"TEST RESULTS: {' | '.join(test_results)[:1000]}"
        )
        return await _engine().run(
            prompt,
            session_id="workflow-verify",
            system_prompt="You are a verification engineer. Confirm the goal is met.",
            depth="deep",
            model_route="auto",
        )


__all__ = ["ProjectWorkflow", "WorkflowState"]
