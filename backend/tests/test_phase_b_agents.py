"""Phase B — multi-agent tests (offline)."""
from __future__ import annotations

import asyncio

import pytest

from agents.analyst import AnalystAgent
from agents.base_agent import BaseAgent, AgentResult
from agents.coder import CoderAgent
from agents.memory import AgentMemory
from agents.moderator import ModeratorAgent
from agents.orchestrator import OrchestratorAgent
from agents.researcher import ResearcherAgent
from agents.sandbox import SandboxResult, execute_python, static_check
from agents.tool_registry import TOOLS, Tool, available, call_tool, list_tools
from agents.writer import WriterAgent


def test_tool_registry_has_16_tools():
    assert len(TOOLS) >= 16
    assert "rag_query" in TOOLS and "web_search" in TOOLS


def test_tool_registry_list_shapes():
    rows = list_tools()
    assert all({"name", "description", "parameters"} <= set(r) for r in rows)


def test_unknown_tool_returns_error():
    assert "error" in asyncio.run(call_tool("does_not_exist"))


def test_disabled_tool_returns_error():
    async def noop(**kw):
        return True
    TOOLS["probe_disabled"] = Tool("probe_disabled", "x", {}, noop, ["NO_SUCH_KEY_PROBE"])
    r = asyncio.run(call_tool("probe_disabled"))
    assert "error" in r
    TOOLS.pop("probe_disabled", None)


def test_sandbox_forbids_dangerous_patterns():
    assert static_check("import subprocess") is not None
    assert static_check("os.system('x')") is not None
    assert static_check("eval('x')") is not None


def test_sandbox_syntax_error():
    assert "SyntaxError" in (static_check("def bad(:") or "")


def test_sandbox_graceful_without_restrictedpython():
    r = asyncio.run(execute_python("x = 1"))
    assert isinstance(r, SandboxResult)
    assert r.error or r.output is not None


def test_base_agent_result():
    assert AgentResult("ok").answer == "ok"


def test_agent_tool_lists():
    assert "rag_query" in ResearcherAgent().tools
    assert "run_python" in CoderAgent().tools
    assert "check_toxicity" in ModeratorAgent().tools


def test_orchestrator_routes_code():
    assert asyncio.run(OrchestratorAgent().route("fix this python bug")) == "code"


def test_orchestrator_routes_analysis():
    assert asyncio.run(OrchestratorAgent().route("analyze this CSV data")) == "analysis"


def test_orchestrator_routes_writing():
    assert asyncio.run(OrchestratorAgent().route("write a report")) == "writing"


def test_orchestrator_routes_moderation():
    assert asyncio.run(OrchestratorAgent().route("check toxicity")) == "moderation"


def test_orchestrator_routes_research_default():
    assert asyncio.run(OrchestratorAgent().route("tell me about X")) == "research"


def test_orchestrator_run_degrades_without_model(monkeypatch):
    from external_apis.registry import registry as registry_obj
    monkeypatch.setattr(registry_obj, "get", lambda name: None)
    r = asyncio.run(OrchestratorAgent().run("hello"))
    assert r.answer and r.steps[0].get("routed_to")


def test_agent_memory_turns():
    m = AgentMemory()
    m.add_turn("user", "hi")
    m.add_turn("assistant", "hello")
    assert [t.role for t in m.recent(2)] == ["user", "assistant"]


def test_agent_memory_short_term_cap():
    m = AgentMemory()
    for i in range(30):
        m.add_turn("user", str(i))
    assert len(m.short_term) == 20


def test_agent_memory_recall_shape():
    m = AgentMemory()
    out = asyncio.run(m.recall("nothing"))
    assert isinstance(out, list)


def test_legacy_agents_api_preserved():
    from agents import list_agents, list_tasks
    assert isinstance(list_agents(), list)
    assert isinstance(list_tasks(), list)
