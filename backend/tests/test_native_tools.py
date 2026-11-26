"""Native tool-calling path and its text-ReAct fallback."""
from __future__ import annotations

from types import SimpleNamespace

import agent_engine
import native_tools
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from tools import TOOL_REGISTRY


class NativeBrain:
    def __init__(self, replies):
        self.replies = list(replies)
        self.bound = None
        self.seen = []

    def bind_tools(self, defs):
        self.bound = defs
        return self

    async def ainvoke(self, messages, **_):
        self.seen.append(list(messages))
        return self.replies.pop(0)


def _call(name, args, cid):
    return {"name": name, "args": args, "id": cid}


def test_definitions_cover_registry():
    defs = native_tools.build_definitions()
    assert len(defs) == len(TOOL_REGISTRY)
    names = {d["function"]["name"] for d in defs}
    assert names == set(TOOL_REGISTRY)
    for d in defs:
        params = d["function"]["parameters"]
        assert params["type"] == "object"
        assert isinstance(params["required"], list)


def test_tool_subset_is_bounded_and_task_relevant():
    names = native_tools.select_tool_names("convert hex 0x10 to decimal", 8)
    assert 1 <= len(names) <= 8
    assert "MemoryLogicCalculator" in names
    assert len(set(names)) == len(names)
    defs = native_tools.build_definitions(names)
    assert len(defs) == len(names)
    assert all(len(d["function"]["parameters"]["properties"]) >= 1 for d in defs)


def test_manager_order_avoids_broken_kilo_first():
    from model_router import ModelRouter

    router = ModelRouter()
    seen = []
    original = router.get

    def fake(name):
        seen.append(name)
        return object() if name == "groq" else None

    router.get = fake
    route, model = router.manager()
    assert route == "groq" and model is not None
    assert "kilo" not in seen
    assert seen.index("groq") < len(seen)


def test_prepare_falls_back_without_bind_tools():
    class Plain:
        pass

    brain = Plain()
    out, enabled = native_tools.prepare(brain)
    assert out is brain and enabled is False


def test_failover_chat_delegates_bind_tools():
    from model_router import FailoverChat

    class FakeModel:
        def __init__(self):
            self.bound = None

        def bind_tools(self, tools):
            clone = type(self)()
            clone.bound = tools
            return clone

    pool = FailoverChat("test", [("m", FakeModel)])
    tools = [{"name": "x"}]
    bound = pool.bind_tools(tools)
    assert isinstance(bound, FailoverChat)
    assert bound._instances[0].bound == tools
    assert pool._instances[0].bound is None  # original pool untouched


async def test_native_call_executes_tool_and_feeds_result(monkeypatch):
    monkeypatch.setattr(agent_engine.config, "MEMORY_ENABLED", False)
    brain = NativeBrain([
        AIMessage(content="", tool_calls=[
            _call("MemoryLogicCalculator",
                  {"op": "hex2dec", "value": "0x10"}, "c1"),
        ]),
        AIMessage(content="Final Answer: 16"),
    ])
    engine = agent_engine.AgentEngine()
    events = []
    async for ev, payload in engine._loop(
            brain, [SystemMessage(content="sys")], "hex to dec", "hex to dec"):
        events.append((ev, payload))

    assert brain.bound is not None
    kinds = [e for e, _ in events]
    assert "action" in kinds and "observation" in kinds and "final" in kinds
    action = [p[1] for e, p in events if e == "action"][0]
    assert action["tool"] == "MemoryLogicCalculator"
    assert action.get("native") is True
    obs = [p[1] for e, p in events if e == "observation"][0]
    assert "16" in str(obs["output"])
    # second model turn must see the tool result as a ToolMessage
    assert any(isinstance(m, ToolMessage) for m in brain.seen[1])


async def test_native_failure_falls_back_to_text(monkeypatch):
    monkeypatch.setattr(agent_engine.config, "MEMORY_ENABLED", False)

    class Broken(NativeBrain):
        def bind_tools(self, defs):
            raise RuntimeError("unsupported")

    brain = Broken([SimpleNamespace(content="Thought: done\nFinal Answer: text path")])
    engine = agent_engine.AgentEngine()
    finals = []
    async for ev, payload in engine._loop(
            brain, [SystemMessage(content="sys")], "hello", "hello"):
        if ev == "final":
            finals.append(payload[1])
    assert finals == ["text path"]
