"""
Regression Testing Suite — Wave 1 through Wave 4 Intelligence Engine.
No network, no API keys needed. Verifies:
  - ReasoningController classification
  - Tool-call / Final Answer parsing
  - AgentManager sub-agent spawning
  - Auditor Agent independent verification
  - CodeAnalyzer static analysis
  - ProjectWorkflow state machine structure
  - WorkspaceManager locking + snapshots
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import tempfile
import os
from pathlib import Path

# Ensure backend is importable (tests/ is one level below backend/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent_engine
from agent_engine import (
    AgentEngine, AgentManager, ReasoningController, ReasoningLevel,
    ContextIntelligenceEngine, ENGINE, AGENT_MANAGER,
)
from model_router import ROUTER
from tools import TOOL_REGISTRY
from tools.code_analyzer import CodeAnalyzer
from workspace_manager import WorkspaceManager

failures: list = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(name)


# ------------------------------------------------------------------ #
#  Wave 1: ReasoningController
# ------------------------------------------------------------------ #
def test_reasoning_levels():
    r = ReasoningController()
    check("L1 greeting", r.classify("مرحبا") == ReasoningLevel.L1_FAST)
    check("L1 hello", r.classify("hello how are you") == ReasoningLevel.L1_FAST)
    check("L2 simple code", r.classify("write python code to parse json") == ReasoningLevel.L2_STANDARD)
    check("L4 complex", r.classify("Architect a multi-step pipeline to audit the project") in
          (ReasoningLevel.L4_EXPERT, ReasoningLevel.L5_SINGULARITY))
    check("L5 singularity hint", r.classify("hi", depth_hint="singularity") == ReasoningLevel.L5_SINGULARITY)
    check("L1 deep hint on greeting", r.classify("hi", depth_hint="deep") == ReasoningLevel.L4_EXPERT)


# ------------------------------------------------------------------ #
#  Wave 1: Action / Final Answer parsing
# ------------------------------------------------------------------ #
def test_parsing():
    TOOL_CALL_RE = re.compile(
        r"^\s*Action:\s*(?P<tool>[^\n]+)\s*\n\s*Action Input:\s*(?P<raw>.*?)(?=\n\s*(?:Thought|Action|Final Answer):|\Z)",
        re.DOTALL | re.IGNORECASE | re.MULTILINE,
    )
    FINAL_RE = re.compile(r"^\s*Final Answer:\s*(?P<text>.*)$", re.DOTALL | re.IGNORECASE | re.MULTILINE)

    sample = ('Thought: I need to list files.\n'
              'Action: list_files\n'
              'Action Input: {"workspace_id": "ws1", "directory": "."}\n'
              'Final Answer: done')

    m = TOOL_CALL_RE.search(sample)
    check("parse action tool", m is not None and m.group("tool") == "list_files")
    if m:
        args = json.loads(m.group("raw"))
        check("parse action args", args == {"workspace_id": "ws1", "directory": "."})

    fm = FINAL_RE.search(sample)
    check("parse final answer", fm is not None and fm.group("text").strip() == "done")

    # No action → no crash
    m2 = TOOL_CALL_RE.search("Thought: just thinking\nFinal Answer: hi")
    check("no action returns None", m2 is None)


# ------------------------------------------------------------------ #
#  Wave 1: Model routing via ReasoningLevel
# ------------------------------------------------------------------ #
def test_routing_by_level():
    check("L1 -> groq", ROUTER.classify("hello", reasoning_level=1) == "groq")
    check("L2 -> groq", ROUTER.classify("code", reasoning_level=2) == "groq")
    check("L3 -> gemini", ROUTER.classify("code", reasoning_level=3) == "gemini")
    check("L4 -> gemini", ROUTER.classify("code", reasoning_level=4) == "gemini")
    check("L5 -> hf", ROUTER.classify("code", reasoning_level=5) == "hf")


# ------------------------------------------------------------------ #
#  Wave 1: Self-critique verifier exists
# ------------------------------------------------------------------ #
def test_self_critique_exists():
    check("_self_critique_verify callable",
          callable(ENGINE._self_critique_verify))


# ------------------------------------------------------------------ #
#  Wave 2: AgentManager sub-agent spawning (structure)
# ------------------------------------------------------------------ #
def test_agent_manager_structure():
    check("AgentManager exists", AgentManager is not None)
    check("spawn_subagents callable", callable(AGENT_MANAGER.spawn_subagents))
    check("run_orchestration callable", callable(AGENT_MANAGER.run_orchestration))
    check("_decompose_goal produces all personas",
          set(AGENT_MANAGER._decompose_goal("test goal", ["researcher", "coder", "auditor"]).keys())
          == {"researcher", "coder", "auditor"})


# ------------------------------------------------------------------ #
#  Wave 2: ResearchEngine registered
# ------------------------------------------------------------------ #
def test_research_engine_registered():
    check("ResearchEngine in TOOL_REGISTRY", "ResearchEngine" in TOOL_REGISTRY)


# ------------------------------------------------------------------ #
#  Wave 3: CodeAnalyzer
# ------------------------------------------------------------------ #
def test_code_analyzer():
    check("CodeAnalyzer in TOOL_REGISTRY", "CodeAnalyzer" in TOOL_REGISTRY)
    a = CodeAnalyzer()
    check("CodeAnalyzer.run callable", callable(a.run))


# ------------------------------------------------------------------ #
#  Wave 3: ProjectWorkflow
# ------------------------------------------------------------------ #
def test_project_workflow():
    from tools.project_workflow import ProjectWorkflow, WorkflowState
    check("ProjectWorkflow in TOOL_REGISTRY", "ProjectWorkflow" in TOOL_REGISTRY)
    check("WorkflowState has PLAN..DONE",
          set(s.value for s in WorkflowState) == {"PLAN", "IMPLEMENT", "TEST", "DEBUG", "VERIFY", "DONE"})
    w = ProjectWorkflow()
    check("ProjectWorkflow.run callable", callable(w.run))


# ------------------------------------------------------------------ #
#  Wave 3: WorkspaceManager locking + snapshots
# ------------------------------------------------------------------ #
def test_workspace_locking_snapshot():
    wm = WorkspaceManager()
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "sub"), exist_ok=True)
        Path(td, "a.txt").write_text("hello")
        Path(td, "sub", "b.txt").write_text("world")

        r = wm.attach_workspace("wstest", td)
        check("attach ok", r.get("status") == "attached")

        check("lock", wm.lock_workspace("wstest").get("status") == "locked")
        check("is_locked", wm.is_locked("wstest") is True)
        check("lock again already_locked",
              wm.lock_workspace("wstest").get("status") == "already_locked")
        check("unlock", wm.unlock_workspace("wstest").get("status") == "unlocked")
        check("is_locked after unlock", wm.is_locked("wstest") is False)

        check("create_snapshot",
              wm.create_snapshot("wstest", "label").get("status") == "created")
        snaps = wm.list_snapshots("wstest")
        check("list_snapshots non-empty", len(snaps["snapshots"]) >= 1)

        check("read_file",
              wm.read_file("wstest", "a.txt").get("content") == "hello")
        check("edit_file", wm.edit_file("wstest", "a.txt", "hello", "HELLO").get("status") == "edited")
        check("read after edit",
              wm.read_file("wstest", "a.txt").get("content") == "HELLO")

        wm.detach_workspace("wstest")


# ------------------------------------------------------------------ #
#  Wave 4: Auditor Agent
# ------------------------------------------------------------------ #
def test_auditor_exists():
    check("auditor in PERSONAS", "auditor" in agent_engine.PERSONAS)
    check("AgentManager.audit_task callable", callable(AGENT_MANAGER.audit_task))


# ------------------------------------------------------------------ #
#  Run all
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    print("=== Regression Testing Suite (Wave 1-4) ===")
    test_reasoning_levels()
    test_parsing()
    test_routing_by_level()
    test_self_critique_exists()
    test_agent_manager_structure()
    test_research_engine_registered()
    test_code_analyzer()
    test_project_workflow()
    test_workspace_locking_snapshot()
    test_auditor_exists()
    print()
    if failures:
        print(f"FAILURES ({len(failures)}): {failures}")
        sys.exit(1)
    print("ALL REGRESSION TESTS PASSED")
