"""
🔥😈 PORT 777 EVIL ☠️🔥👹 engine tests â€” no network, no API keys needed.
"""
from __future__ import annotations

import pytest

import agent_engine
from agent_engine import AgentEngine, FINAL_MARKER
from conftest import FakeBrain


# --------------------------------------------------------------------- #
#  ReAct format parsing
# --------------------------------------------------------------------- #
def test_parse_action_roundtrip():
    text = ("Thought: I should list files\n"
            "Action: UniversalFileManager\n"
            'Action Input: {"action": "list"}')
    engine = AgentEngine()
    tool, args = engine._parse_action(text)
    assert tool == "UniversalFileManager"
    assert args == {"action": "list"}


def test_parse_action_broken_json_gets_queried_fallback():
    engine = AgentEngine()
    tool, args = engine._parse_action(
        "Action: PythonInterpreter\nAction Input: {'code': bad json")
    assert tool == "PythonInterpreter"
    assert "model_input" in args          # degraded but never crashes


def test_parse_final_case_insensitive():
    assert AgentEngine()._parse_final("final ANSWER: everything done") \
        == "everything done"


def test_final_marker_regex():
    assert FINAL_MARKER.search("blah Final Answer: hi")


# --------------------------------------------------------------------- #
#  Full loop with a scripted brain (final in one shot)
# --------------------------------------------------------------------- #
async def test_loop_single_final_answer(monkeypatch):
    monkeypatch.setattr(agent_engine.config, "MEMORY_ENABLED", False)
    brain = FakeBrain(["Thought: trivial\nFinal Answer: 42"])
    engine = AgentEngine()
    events = []
    async for ev, payload in engine._loop(
        brain, [], "compute", "compute"
    ):
        events.append((ev, payload))
    kinds = [e for e, _ in events]
    assert kinds[-1] == "final"
    assert events[-1][1][1] == "42"


# --------------------------------------------------------------------- #
#  Reflection: an errored tool triggers the manager and a corrected call
# --------------------------------------------------------------------- #
async def test_reflection_retry_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_engine.config, "MEMORY_ENABLED", False)
    # keep the test hermetic: write sandbox must point at a temp dir
    monkeypatch.setattr(agent_engine.config, "WORKSPACE_DIR", tmp_path)

    brain = FakeBrain([
        # 1st reply: broken tool (full_access off -> denied error)
        'Thought: host path\nAction: UniversalFileManager\n'
        'Action Input: {"action": "read", "path": "x.md", "scope": "host"}',
        # 2nd reply: after recovery, conclude
        "Thought: fixed\nFinal Answer: recovered after reflection",
    ])

    async def reflect(task, ledger, force):
        return {
            "diagnosis": "host access denied â€” write to workspace instead",
            "tool": "UniversalFileManager",
            "input": {"action": "write", "path": "x.md", "content": "hi"},
        }

    engine = AgentEngine()
    monkeypatch.setattr(engine, "_reflect", reflect)

    events = []
    async for ev, payload in engine._loop(brain, [], "read file", "read file"):
        events.append((ev, payload))
    kinds = [e for e, _ in events]
    # the coach diagnosis is surfaced as an observable reflection event
    assert kinds.count("reflection") >= 1
    assert kinds.count("action") >= 2       # original + corrected retry
    assert kinds[-1] == "final"
    assert events[-1][1][1].startswith("recovered")


# --------------------------------------------------------------------- #
#  Citation gate: raw hex without tool evidence gets flagged + corrected
# --------------------------------------------------------------------- #
async def test_citation_gate_appends_warning_when_no_evidence():
    import agent_engine as ae
    engine = AgentEngine()
    # clean answer without hex -> gate stays silent
    assert engine._citation_gate("just prose", set()) is None
    # hex WITH evidence -> gate stays silent
    assert engine._citation_gate("value 0x12345", {"MemoryLogicCalculator"}) \
        is None
    # hex WITHOUT evidence -> gate fires
    assert engine._citation_gate("base 0x7FF6A1B2C000", set()) is not None


async def test_citation_gate_correction_round(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_engine.config, "MEMORY_ENABLED", False)
    brain = FakeBrain([
        # round 1: states a raw offset with zero tool evidence
        "Thought: guess\nFinal Answer: the offset is 0x13177137",
        # round 2: still guessing after the nudge
        "Thought: guess again\nFinal Answer: offset stays 0x13177137",
    ])
    engine = AgentEngine()
    outcome = await engine._execute_goal(brain, [], "find the offset",
                                         "find the offset")
    assert outcome["final"] is not None
    assert "Citation gate" in outcome["final"]          # warned, not faked
    kinds = [e["type"] for e in outcome["events"]]
    assert "reflection" in kinds                        # gate is observable


async def test_citation_gate_passes_on_calc_evidence():
    import agent_engine as ae
    brain = FakeBrain([
        "Thought: derive\nAction: MemoryLogicCalculator\n"
        'Action Input: {"op": "hex2dec", "value": "0x10"}',
        "Thought: cited\nFinal Answer: 0x10 = 16 (MemoryLogicCalculator)",
    ])
    engine = AgentEngine()
    outcome = await engine._execute_goal(brain, [], "hex to dec", "hex2dec")
    assert "Citation gate" not in (outcome["final"] or "")
    assert any(e["type"] == "observation" and
               e["data"].get("tool") == "MemoryLogicCalculator"
               for e in outcome["events"])


# --------------------------------------------------------------------- #
#  Sandbox / security
# --------------------------------------------------------------------- #
def test_safe_path_blocks_traversal():
    from tools.base import Tool
    with pytest.raises(ValueError):
        Tool.safe_path("../../../etc/passwd")


def test_full_access_scoped_per_context():
    from tools.base import set_full_access, full_access
    set_full_access(False)
    assert full_access() is False
    set_full_access(True)
    assert full_access() is True       # visible in this context
    set_full_access(False)             # restore for other tests


# --------------------------------------------------------------------- #
#  Storage roundtrip
# --------------------------------------------------------------------- #
def test_storage_session_roundtrip(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(storage, "AUDIT_JSONL", tmp_path / "a.jsonl")
    storage._CONN = None                     # reopen at tmp path
    storage.init()
    storage.add_message("s1", "user", "hello world")
    hist = storage.get_history("s1")
    assert hist and hist[0]["content"] == "hello world"
    assert any(s["id"] == "s1" for s in storage.list_sessions())


# --------------------------------------------------------------------- #
#  Streaming: tokens after the Final Answer marker are surfaced
# --------------------------------------------------------------------- #
async def test_stream_call_surfaces_final_tokens():
    import agent_engine as ae

    brain = FakeBrain(["Thought: x\nFinal Answer: hello "])
    engine = AgentEngine()
    pieces = []
    async for kind, payload in engine._stream_call(brain, []):
        if kind == "stream":
            pieces.append(payload)
    assert "".join(pieces) == "hello "

def test_arabic_refusal_detected():
    assert agent_engine._REFUSAL_RE.search("أنا آسف، لا يمكنني مساعدتك في هذا الطلب")

