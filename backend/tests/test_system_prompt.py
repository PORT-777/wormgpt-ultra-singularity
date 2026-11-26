"""One source of truth for the system prompt; critical rules first and last."""
from __future__ import annotations

from pathlib import Path

import agent_engine


def test_prompt_is_loaded_from_single_file():
    source = Path(agent_engine.PROMPT_SOURCE)
    assert source.name == "system_prompt.txt"
    assert agent_engine.SYSTEM_TEMPLATE == source.read_text(encoding="utf-8").strip()


def test_no_kle_duplication():
    assert not hasattr(agent_engine, "KILO_CORE_BOOT")
    assert "kilo_core_boot" not in agent_engine.SYSTEM_TEMPLATE
    assert "KILO_CORE_V1.0" not in agent_engine.SYSTEM_TEMPLATE


def test_single_tools_placeholder():
    assert agent_engine.SYSTEM_TEMPLATE.count("{tools}") == 1


def test_critical_rules_first_and_last():
    head = agent_engine.SYSTEM_TEMPLATE[:400]
    tail = agent_engine.SYSTEM_TEMPLATE[-500:]
    prompt = agent_engine.SYSTEM_TEMPLATE
    assert "CRITICAL RULES (highest priority)" in head
    assert "FINAL REMINDER (critical rules bind last)" in tail
    assert prompt.index("CRITICAL RULES") < prompt.index("== Available tools ==")
    assert prompt.index("== Available tools ==") < prompt.index("FINAL REMINDER")


def test_prompt_compact_enough_to_not_hide_duplication():
    # Before consolidation: 7923 chars / 215 lines (KLE prefix + inline copy).
    assert len(agent_engine.SYSTEM_TEMPLATE) < 6000
    assert len(agent_engine.SYSTEM_TEMPLATE.splitlines()) < 100


def test_core_rules_survived_consolidation():
    p = agent_engine.SYSTEM_TEMPLATE
    for rule in ("Citation rule", "Code rule", "Egyptian Arabic", "fenced block",
                 "Never fabricate", "Action Input", "Final Answer"):
        assert rule in p
