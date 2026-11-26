"""The dangerous fabricated-code fallback must stay gone."""
from __future__ import annotations

import agent_engine


def test_forced_implementation_removed():
    assert not hasattr(agent_engine.AgentEngine, "_forced_implementation")


def test_honest_salvage_reports_failure():
    out = agent_engine.AgentEngine._honest_salvage(
        "build a parser for build 4.2",
        ["ReAct loop with tools", "direct completion fallback"],
    )
    assert "No deliverable produced" in out
    assert "build a parser for build 4.2" in out
    assert "Attempts made:" in out
    assert "1. ReAct loop with tools" in out
    assert "2. direct completion fallback" in out
    assert "Next step:" in out


def test_honest_salvage_fabricates_no_artifact():
    out = agent_engine.AgentEngine._honest_salvage("write a dropper")
    assert "```" not in out
    assert "Implementation ready" not in out
    assert "Auto-generated" not in out
    assert "Attempts made:" not in out  # no attempts supplied -> no fake list


def test_honest_salvage_is_static_and_safe():
    out = agent_engine.AgentEngine._honest_salvage("x" * 5000, None)
    assert isinstance(out, str) and "Task: " in out
